#!/usr/bin/env python3

import sys
import csv
import math
import time
import html
import statistics
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForDepthEstimation


# ============================================================
# PATHS
# ============================================================

BASE = Path("/home/devlin/CognitiveOps/merged_run")

OUT_DIR = BASE / "fusion_benchmark"
CSV_PATH = BASE / "fusion_results.csv"
HTML_PATH = BASE / "review_fusion.html"

OFFSEG_ROOT = Path(
    "/home/devlin/CognitiveOps/experiments/local_perception/OFFSEG"
)

OFFSEG_PIPE = OFFSEG_ROOT / "Pipeline"

OFFSEG_CKPT = (
    OFFSEG_ROOT
    / "extracted_weights"
    / "Offseg weights"
    / "model_final3.pth"
)

# ============================================================
# DEPTH CONFIG
# ============================================================

DEPTH_MODEL_ID = (
    "depth-anything/Depth-Anything-V2-Small-hf"
)

CAMERA_HEIGHT_M = 0.20
HFOV_DEG = 70.0
PITCH_DEG = 10.0

SCORE_MARGIN = 0.25
BOTTOM_FRACTION = 0.92

FIT_ITERATIONS = 6
LOWER_SIGMA = 3.0
UPPER_SIGMA = 2.0

MIN_DENOM = 0.05

# ============================================================
# TEMPORAL
# ============================================================

TEMPORAL_WINDOW = 5

DT_CHANGING = 1.7
DT_ABRUPT = 2.7

# ============================================================
# THREADS
# ============================================================

# Leave PyTorch free to use CPU efficiently.
# Uncomment if later we want controlled thermal testing:
#
# torch.set_num_threads(8)

# ============================================================
# OFFSEG IMPORT
# ============================================================

sys.path.insert(0, str(OFFSEG_PIPE))

import lib.transform_cv2 as T
from lib.models import model_factory
from configs import cfg_factory


# ============================================================
# CAMERA GEOMETRY
# ============================================================

def camera_geometry(width, height):

    hfov = math.radians(HFOV_DEG)

    fx = width / (
        2.0 * math.tan(hfov / 2.0)
    )

    fy = fx

    cx = (width - 1) / 2.0
    cy = (height - 1) / 2.0

    return fx, fy, cx, cy


def build_ground_geometry(width, height):

    fx, fy, cx, cy = camera_geometry(
        width,
        height
    )

    pitch = math.radians(
        PITCH_DEG
    )

    ys = np.arange(
        height,
        dtype=np.float32
    )

    ray_angle = (
        pitch
        + np.arctan(
            (ys - cy) / fy
        )
    )

    ground_distance = np.full(
        height,
        np.nan,
        dtype=np.float32
    )

    valid = (
        ray_angle
        > math.radians(0.5)
    )

    ground_distance[valid] = (
        CAMERA_HEIGHT_M
        / np.tan(
            ray_angle[valid]
        )
    )

    horizon = (
        cy
        - fy * math.tan(pitch)
    )

    xs = np.arange(
        width,
        dtype=np.float32
    )

    x_normalized = (
        (xs - cx)
        / max(cx, 1.0)
    )

    return (
        ground_distance,
        x_normalized,
        horizon
    )


# ============================================================
# ROBUST GROUND FIT
# ============================================================

def robust_ground_fit(
    depth_score,
    ground_distance,
    x_normalized,
    horizon
):

    h, w = depth_score.shape

    yy, xx = np.indices(
        (h, w)
    )

    d = ground_distance[yy]

    valid = (
        np.isfinite(d)
        & (yy > horizon)
        & (
            yy
            < h * BOTTOM_FRACTION
        )
    )

    inv_d = np.zeros_like(
        depth_score,
        dtype=np.float32
    )

    inv_d[valid] = (
        1.0 / d[valid]
    )

    xmap = np.broadcast_to(
        x_normalized.reshape(
            1, -1
        ),
        (h, w)
    )

    values = depth_score[
        valid
    ]

    X = np.column_stack([
        inv_d[valid],
        np.ones(
            np.count_nonzero(
                valid
            )
        ),
        xmap[valid]
    ])

    mask = np.ones(
        len(values),
        dtype=bool
    )

    beta = None

    for _ in range(
        FIT_ITERATIONS
    ):

        if (
            np.count_nonzero(mask)
            < 100
        ):
            break

        beta, *_ = (
            np.linalg.lstsq(
                X[mask],
                values[mask],
                rcond=None
            )
        )

        predicted = X @ beta

        residual = (
            values
            - predicted
        )

        r = residual[mask]

        med = np.median(r)

        mad = np.median(
            np.abs(r - med)
        )

        sigma = (
            1.4826 * mad
        )

        if sigma < 1e-6:
            break

        lower = (
            med
            - LOWER_SIGMA
            * sigma
        )

        upper = (
            med
            + UPPER_SIGMA
            * sigma
        )

        mask = (
            (residual >= lower)
            & (residual <= upper)
        )

    if beta is None:
        return None

    A, B, C = beta

    predicted = X @ beta

    y = values[mask]
    yp = predicted[mask]

    if len(y) < 2:

        r2 = 0.0

    else:

        ss_res = np.sum(
            (y - yp) ** 2
        )

        ss_tot = np.sum(
            (
                y
                - np.mean(y)
            ) ** 2
        )

        if ss_tot > 1e-12:

            r2 = (
                1.0
                - ss_res
                / ss_tot
            )

        else:
            r2 = 0.0

    inlier_fraction = (
        np.count_nonzero(mask)
        / len(mask)
    )

    return {
        "A": float(A),
        "B": float(B),
        "C": float(C),
        "r2": float(r2),
        "inliers": float(
            inlier_fraction
        )
    }


# ============================================================
# CONFIDENCE
# ============================================================

def geometry_confidence(
    A,
    r2
):

    if (
        A <= 0
        or r2 < 0.95
    ):
        return "LOW"

    if r2 < 0.985:
        return "MEDIUM"

    return "HIGH"


# ============================================================
# TEMPORAL TILT
# ============================================================

class TemporalTilt:

    def __init__(self):

        self.history = deque(
            maxlen=TEMPORAL_WINDOW
        )

    def update(
        self,
        tilt,
        confidence
    ):

        if (
            tilt is None
            or confidence == "LOW"
        ):

            return (
                "UNKNOWN",
                None
            )

        stability = "UNKNOWN"
        delta = None

        if len(
            self.history
        ) >= 3:

            reference = (
                statistics.median(
                    self.history
                )
            )

            delta = (
                tilt
                - reference
            )

            ad = abs(delta)

            if ad > DT_ABRUPT:

                stability = (
                    "ABRUPT"
                )

            elif ad > DT_CHANGING:

                stability = (
                    "CHANGING"
                )

            else:

                stability = (
                    "STABLE"
                )

        self.history.append(
            tilt
        )

        return (
            stability,
            delta
        )


# ============================================================
# DISTANCE METRIC
# ============================================================

def candidate_distance(
    depth_score,
    candidates,
    fit,
    x_normalized
):

    A = fit["A"]
    B = fit["B"]
    C = fit["C"]

    h, w = (
        depth_score.shape
    )

    xmap = np.broadcast_to(
        x_normalized.reshape(
            1, -1
        ),
        (h, w)
    )

    denom = (
        depth_score
        - B
        - C * xmap
    )

    distance = np.full(
        (h, w),
        np.nan,
        dtype=np.float32
    )

    valid = (
        candidates
        & (A > 0)
        & (
            denom
            > MIN_DENOM
        )
    )

    distance[valid] = (
        A
        / denom[valid]
    )

    return distance


# ============================================================
# PERCENTILE
# ============================================================

def percentile(
    values,
    q
):

    values = values[
        np.isfinite(values)
    ]

    if len(values) == 0:
        return None

    return float(
        np.percentile(
            values,
            q
        )
    )


# ============================================================
# OVERLAY
# ============================================================

def create_overlay(
    rgb,
    valid,
    candidates,
    traversable
):

    img = rgb.copy().astype(
        np.float32
    )

    # -----------------------------------------
    # Soft green:
    # OFFSEG traversable terrain.
    # -----------------------------------------

    green_mask = (
        valid
        & traversable
        & ~candidates
    )

    green = np.array(
        [0, 255, 0],
        dtype=np.float32
    )

    img[green_mask] = (
        0.82
        * img[green_mask]
        + 0.18
        * green
    )

    # -----------------------------------------
    # Yellow:
    # Depth protrusion but OFFSEG says terrain
    # is traversable.
    # -----------------------------------------

    yellow_mask = (
        candidates
        & traversable
    )

    yellow = np.array(
        [255, 220, 0],
        dtype=np.float32
    )

    img[yellow_mask] = (
        0.45
        * img[yellow_mask]
        + 0.55
        * yellow
    )

    # -----------------------------------------
    # Red:
    # Depth protrusion + OFFSEG non-traversable.
    # -----------------------------------------

    red_mask = (
        candidates
        & ~traversable
    )

    red = np.array(
        [255, 0, 0],
        dtype=np.float32
    )

    img[red_mask] = (
        0.35
        * img[red_mask]
        + 0.65
        * red
    )

    return np.clip(
        img,
        0,
        255
    ).astype(np.uint8)


# ============================================================
# MODELS
# ============================================================

print(
    "Loading Depth Anything..."
)

depth_processor = (
    AutoImageProcessor
    .from_pretrained(
        DEPTH_MODEL_ID
    )
)

depth_model = (
    AutoModelForDepthEstimation
    .from_pretrained(
        DEPTH_MODEL_ID
    )
)

depth_model.eval()

print(
    "Loading OFFSEG..."
)

cfg = cfg_factory[
    "bisenetv2"
]

offseg = (
    model_factory[
        cfg.model_type
    ](4)
)

state = torch.load(
    OFFSEG_CKPT,
    map_location="cpu"
)

offseg.load_state_dict(
    state,
    strict=True
)

offseg.eval()

offseg_to_tensor = (
    T.ToTensor(
        mean=(
            0.3257,
            0.3690,
            0.3223
        ),
        std=(
            0.2112,
            0.2148,
            0.2115
        )
    )
)


# ============================================================
# FILES
# ============================================================

files = sorted([
    p
    for p in BASE.iterdir()
    if (
        p.suffix.lower()
        in {
            ".jpg",
            ".jpeg",
            ".png"
        }
        and p.stem.isdigit()
    )
])

print(
    f"Frames: {len(files)}"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

temporal = TemporalTilt()

rows = []

depth_times = []
offseg_times = []
total_times = []


# ============================================================
# MAIN LOOP
# ============================================================

for index, path in enumerate(
    files,
    start=1
):

    frame_start = (
        time.perf_counter()
    )

    # -----------------------------------------
    # RGB
    # -----------------------------------------

    pil = Image.open(
        path
    ).convert("RGB")

    rgb = np.array(pil)

    h, w = rgb.shape[:2]

    # -----------------------------------------
    # DEPTH ANYTHING
    # -----------------------------------------

    t0 = time.perf_counter()

    inputs = depth_processor(
        images=pil,
        return_tensors="pt"
    )

    with torch.no_grad():

        depth_out = (
            depth_model(
                **inputs
            ).predicted_depth
        )

    depth_score = (
        torch.nn.functional
        .interpolate(
            depth_out.unsqueeze(1),
            size=(h, w),
            mode="bicubic",
            align_corners=False
        )
        .squeeze()
        .cpu()
        .numpy()
        .astype(np.float32)
    )

    depth_time = (
        time.perf_counter()
        - t0
    )

    # -----------------------------------------
    # GROUND GEOMETRY
    # -----------------------------------------

    (
        ground_distance,
        x_normalized,
        horizon
    ) = build_ground_geometry(
        w,
        h
    )

    fit = robust_ground_fit(
        depth_score,
        ground_distance,
        x_normalized,
        horizon
    )

    # -----------------------------------------
    # OFFSEG
    # -----------------------------------------

    t0 = time.perf_counter()

    x_off = (
        offseg_to_tensor(
            dict(
                im=rgb.copy(),
                lb=None
            )
        )["im"]
        .unsqueeze(0)
    )

    with torch.no_grad():

        off_out = (
            offseg(
                x_off
            )
        )

    off_mask = (
        off_out[0]
        .argmax(dim=1)
        .squeeze()
        .cpu()
        .numpy()
        .astype(np.uint8)
    )

    traversable = (
        off_mask == 1
    )

    offseg_time = (
        time.perf_counter()
        - t0
    )

    # -----------------------------------------
    # FAILED FIT
    # -----------------------------------------

    if fit is None:

        total_time = (
            time.perf_counter()
            - frame_start
        )

        rows.append({
            "frame": path.name,
            "geometry_confidence":
                "LOW",
            "temporal_stability":
                "UNKNOWN",
            "r2": "",
            "A": "",
            "B": "",
            "C": "",
            "T": "",
            "dT": "",
            "depth_time_s":
                depth_time,
            "offseg_time_s":
                offseg_time,
            "total_time_s":
                total_time
        })

        print(
            f"[{index:3d}/{len(files)}] "
            f"{path.name} FIT FAILED"
        )

        continue

    A = fit["A"]
    B = fit["B"]
    C = fit["C"]
    r2 = fit["r2"]

    confidence = (
        geometry_confidence(
            A,
            r2
        )
    )

    tilt = (
        C / A
        if (
            A > 0
            and confidence
            != "LOW"
        )
        else None
    )

    (
        temporal_stability,
        delta_tilt
    ) = temporal.update(
        tilt,
        confidence
    )

    # -----------------------------------------
    # CANDIDATES
    # -----------------------------------------

    yy, xx = np.indices(
        (h, w)
    )

    dground = (
        ground_distance[
            yy
        ]
    )

    xmap = np.broadcast_to(
        x_normalized.reshape(
            1, -1
        ),
        (h, w)
    )

    valid = (
        np.isfinite(
            dground
        )
        & (
            yy
            > horizon
        )
        & (
            yy
            < h
            * BOTTOM_FRACTION
        )
    )

    expected = np.full(
        (h, w),
        np.nan,
        dtype=np.float32
    )

    expected[valid] = (
        A / dground[valid]
        + B
        + C * xmap[valid]
    )

    residual = (
        depth_score
        - expected
    )

    candidates = (
        valid
        & (
            residual
            > SCORE_MARGIN
        )
    )

    distance = candidate_distance(
        depth_score,
        candidates,
        fit,
        x_normalized
    )

    # -----------------------------------------
    # REGIONS
    # -----------------------------------------

    thirds = [
        (
            "left",
            0,
            w // 3
        ),
        (
            "front",
            w // 3,
            2 * w // 3
        ),
        (
            "right",
            2 * w // 3,
            w
        )
    ]

    region_data = {}

    for (
        region,
        x0,
        x1
    ) in thirds:

        region_valid = (
            valid[
                :,
                x0:x1
            ]
        )

        region_cand = (
            candidates[
                :,
                x0:x1
            ]
        )

        region_trav = (
            traversable[
                :,
                x0:x1
            ]
        )

        region_dist = (
            distance[
                :,
                x0:x1
            ]
        )

        n_valid = (
            np.count_nonzero(
                region_valid
            )
        )

        n_cand = (
            np.count_nonzero(
                region_cand
            )
        )

        candidate_fraction = (
            n_cand / n_valid
            if n_valid
            else 0.0
        )

        traversable_fraction = (
            np.count_nonzero(
                region_valid
                & region_trav
            )
            / n_valid
            if n_valid
            else 0.0
        )

        if n_cand > 0:

            cand_trav = (
                np.count_nonzero(
                    region_cand
                    & region_trav
                )
                / n_cand
            )

            cand_nontrav = (
                1.0
                - cand_trav
            )

        else:

            cand_trav = None
            cand_nontrav = None

        cand_distances = (
            region_dist[
                region_cand
            ]
        )

        p25 = percentile(
            cand_distances,
            25
        )

        region_data[region] = {
            "candidate_fraction":
                candidate_fraction,
            "traversable_fraction":
                traversable_fraction,
            "candidate_traversable_fraction":
                cand_trav,
            "candidate_nontraversable_fraction":
                cand_nontrav,
            "distance_p25_m":
                p25
        }

    # -----------------------------------------
    # OVERLAY
    # -----------------------------------------

    overlay = create_overlay(
        rgb,
        valid,
        candidates,
        traversable
    )

    # Region separators
    cv2.line(
        overlay,
        (w // 3, 0),
        (w // 3, h - 1),
        (255, 255, 255),
        1
    )

    cv2.line(
        overlay,
        (2 * w // 3, 0),
        (2 * w // 3, h - 1),
        (255, 255, 255),
        1
    )

    # Header
    header = (
        f"{path.name} "
        f"{confidence} "
        f"{temporal_stability} "
        f"R2={r2:.3f}"
    )

    cv2.rectangle(
        overlay,
        (0, 0),
        (
            min(
                w - 1,
                430
            ),
            28
        ),
        (0, 0, 0),
        -1
    )

    cv2.putText(
        overlay,
        header,
        (6, 19),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (255, 255, 255),
        1,
        cv2.LINE_AA
    )

    overlay_path = (
        OUT_DIR
        / f"{path.stem}_fusion.jpg"
    )

    cv2.imwrite(
        str(overlay_path),
        cv2.cvtColor(
            overlay,
            cv2.COLOR_RGB2BGR
        )
    )

    # -----------------------------------------
    # TIMING
    # -----------------------------------------

    total_time = (
        time.perf_counter()
        - frame_start
    )

    depth_times.append(
        depth_time
    )

    offseg_times.append(
        offseg_time
    )

    total_times.append(
        total_time
    )

    # -----------------------------------------
    # CSV ROW
    # -----------------------------------------

    row = {
        "frame":
            path.name,

        "geometry_confidence":
            confidence,

        "temporal_stability":
            temporal_stability,

        "r2":
            r2,

        "A":
            A,

        "B":
            B,

        "C":
            C,

        "T":
            tilt,

        "dT":
            delta_tilt,

        "depth_time_s":
            depth_time,

        "offseg_time_s":
            offseg_time,

        "total_time_s":
            total_time
    }

    for region in (
        "left",
        "front",
        "right"
    ):

        d = region_data[
            region
        ]

        prefix = (
            region + "_"
        )

        row[
            prefix
            + "candidate_fraction"
        ] = d[
            "candidate_fraction"
        ]

        row[
            prefix
            + "traversable_fraction"
        ] = d[
            "traversable_fraction"
        ]

        row[
            prefix
            + "candidate_traversable_fraction"
        ] = d[
            "candidate_traversable_fraction"
        ]

        row[
            prefix
            + "candidate_nontraversable_fraction"
        ] = d[
            "candidate_nontraversable_fraction"
        ]

        row[
            prefix
            + "distance_p25_m"
        ] = d[
            "distance_p25_m"
        ]

    rows.append(row)

    print(
        f"[{index:3d}/{len(files)}] "
        f"{path.name} "
        f"{confidence:6s} "
        f"{temporal_stability:8s} "
        f"depth={depth_time:.3f}s "
        f"offseg={offseg_time:.3f}s "
        f"total={total_time:.3f}s"
    )


# ============================================================
# CSV
# ============================================================

fieldnames = []

for row in rows:

    for key in row.keys():

        if key not in fieldnames:
            fieldnames.append(key)

with CSV_PATH.open(
    "w",
    newline="",
    encoding="utf-8"
) as fp:

    writer = csv.DictWriter(
        fp,
        fieldnames=fieldnames
    )

    writer.writeheader()

    for row in rows:

        writer.writerow(
            row
        )


# ============================================================
# HTML
# ============================================================

def fmt_pct(v):

    if (
        v is None
        or v == ""
    ):
        return "-"

    return (
        f"{100*float(v):.1f}%"
    )


def fmt_dist(v):

    if (
        v is None
        or v == ""
    ):
        return "-"

    return (
        f"{float(v):.2f}m"
    )


cards = []

for row in rows:

    frame = row["frame"]

    stem = Path(
        frame
    ).stem

    original_rel = (
        frame
    )

    fusion_rel = (
        "fusion_benchmark/"
        + stem
        + "_fusion.jpg"
    )

    conf = row.get(
        "geometry_confidence",
        "?"
    )

    temporal_state = row.get(
        "temporal_stability",
        "?"
    )

    border = "#777"

    if conf == "LOW":
        border = "#d62728"

    elif conf == "MEDIUM":
        border = "#ff9800"

    elif temporal_state == "ABRUPT":
        border = "#8e44ad"

    elif temporal_state == "CHANGING":
        border = "#2980b9"

    rows_html = []

    for region in (
        "left",
        "front",
        "right"
    ):

        candidate = row.get(
            region
            + "_candidate_fraction"
        )

        trav = row.get(
            region
            + "_traversable_fraction"
        )

        cand_trav = row.get(
            region
            + "_candidate_traversable_fraction"
        )

        cand_nontrav = row.get(
            region
            + "_candidate_nontraversable_fraction"
        )

        distance = row.get(
            region
            + "_distance_p25_m"
        )

        rows_html.append(
            f"""
            <tr>
              <td>{region.upper()}</td>
              <td>{fmt_pct(candidate)}</td>
              <td>{fmt_pct(trav)}</td>
              <td>{fmt_pct(cand_trav)}</td>
              <td>{fmt_pct(cand_nontrav)}</td>
              <td>{fmt_dist(distance)}</td>
            </tr>
            """
        )

    cards.append(
        f"""
        <div class="card"
             style="border-color:{border}">

          <h2>{html.escape(frame)}</h2>

          <div class="status">
            geometry=<b>{conf}</b>
            &nbsp;&nbsp;
            temporal=<b>{temporal_state}</b>
            &nbsp;&nbsp;
            R²={row.get('r2','')}
            <br>
            depth={float(row.get('depth_time_s',0)):.3f}s
            &nbsp;
            OFFSEG={float(row.get('offseg_time_s',0)):.3f}s
            &nbsp;
            total={float(row.get('total_time_s',0)):.3f}s
          </div>

          <div class="images">
            <div>
              <div class="label">Original</div>
              <img src="{original_rel}">
            </div>

            <div>
              <div class="label">Fusion</div>
              <img src="{fusion_rel}">
            </div>
          </div>

          <table>
            <tr>
              <th>Region</th>
              <th>Depth candidates</th>
              <th>Traversable</th>
              <th>Candidate+trav</th>
              <th>Candidate+nontrav</th>
              <th>P25 distance</th>
            </tr>

            {''.join(rows_html)}

          </table>

        </div>
        """
    )


html_doc = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>CognitiveOps Depth + OFFSEG Fusion Review</title>

<style>

body {{
    font-family: Arial, sans-serif;
    background: #111;
    color: #ddd;
    margin: 20px;
}}

h1 {{
    color: white;
}}

.legend {{
    background: #222;
    padding: 12px;
    margin-bottom: 20px;
    line-height: 1.6;
}}

.card {{
    border: 4px solid #777;
    background: #1a1a1a;
    padding: 14px;
    margin-bottom: 26px;
}}

.images {{
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
}}

.images > div {{
    flex: 1 1 420px;
}}

img {{
    width: 100%;
    max-width: 700px;
    border: 1px solid #555;
}}

.label {{
    margin-bottom: 5px;
    font-weight: bold;
}}

.status {{
    margin-bottom: 10px;
    font-family: monospace;
}}

table {{
    border-collapse: collapse;
    margin-top: 12px;
    width: 100%;
}}

td, th {{
    border: 1px solid #555;
    padding: 6px;
    text-align: right;
}}

td:first-child,
th:first-child {{
    text-align: left;
}}

</style>

</head>

<body>

<h1>Depth Anything + OFFSEG Fusion Review</h1>

<div class="legend">

<b>Overlay:</b><br>

🟢 green = OFFSEG traversable terrain<br>
🟡 yellow = Depth candidate + OFFSEG traversable<br>
🔴 red = Depth candidate + OFFSEG non-traversable<br>

<br>

<b>Card border:</b><br>

grey = normal<br>
orange = geometry MEDIUM<br>
red = geometry LOW<br>
blue = temporal CHANGING<br>
purple = temporal ABRUPT

</div>

{''.join(cards)}

</body>
</html>
"""


HTML_PATH.write_text(
    html_doc,
    encoding="utf-8"
)


# ============================================================
# SUMMARY
# ============================================================

print()
print("================================")
print("BENCHMARK COMPLETE")
print("================================")

print(
    "frames:",
    len(rows)
)

if depth_times:

    print(
        f"Depth mean:   "
        f"{np.mean(depth_times):.3f}s"
    )

    print(
        f"OFFSEG mean:  "
        f"{np.mean(offseg_times):.3f}s"
    )

    print(
        f"Total mean:   "
        f"{np.mean(total_times):.3f}s"
    )

    print(
        f"Total median: "
        f"{np.median(total_times):.3f}s"
    )

print()
print(
    "CSV:",
    CSV_PATH
)

print(
    "HTML:",
    HTML_PATH
)

print(
    "Overlays:",
    OUT_DIR
)



