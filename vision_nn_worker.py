#!/usr/bin/env python3

import sys
import struct
import json
import time
import math
import statistics

from collections import deque
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F

from PIL import Image
from transformers import (
    AutoImageProcessor,
    AutoModelForDepthEstimation,
)


# ============================================================
# CONFIG
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

TEMPORAL_WINDOW = 5
DT_CHANGING = 1.7
DT_ABRUPT = 2.7


# ============================================================
# OFFSEG
# ============================================================

OFFSEG_ROOT = Path(
    "/home/devlin/CognitiveOps/"
    "experiments/local_perception/OFFSEG"
)

OFFSEG_WEIGHT = (
    OFFSEG_ROOT
    / "extracted_weights"
    / "Offseg weights"
    / "model_final3.pth"
)

sys.path.insert(
    0,
    str(OFFSEG_ROOT / "Pipeline"),
)

from lib.models.bisenetv2 import BiSeNetV2
from lib.transform_cv2 import ToTensor


# ============================================================
# IO
# ============================================================

def log(msg):
    print(
        msg,
        file=sys.stderr,
        flush=True,
    )


def read_exact(
    stream,
    size,
):
    data = b""

    while len(data) < size:

        chunk = stream.read(
            size - len(data)
        )

        if not chunk:
            return None

        data += chunk

    return data


stdin = sys.stdin.buffer
stdout = sys.stdout.buffer


# ============================================================
# CAMERA GEOMETRY
# ============================================================

def camera_geometry(
    width,
    height,
):

    hfov = math.radians(
        HFOV_DEG
    )

    fx = (
        width
        / (
            2.0
            * math.tan(
                hfov / 2.0
            )
        )
    )

    fy = fx

    cx = (
        width - 1
    ) / 2.0

    cy = (
        height - 1
    ) / 2.0

    return (
        fx,
        fy,
        cx,
        cy,
    )


def build_ground_geometry(
    width,
    height,
):

    (
        fx,
        fy,
        cx,
        cy,
    ) = camera_geometry(
        width,
        height,
    )

    pitch = math.radians(
        PITCH_DEG
    )

    ys = np.arange(
        height,
        dtype=np.float32,
    )

    ray_angle = (
        pitch
        + np.arctan(
            (ys - cy)
            / fy
        )
    )

    ground_distance = np.full(
        height,
        np.nan,
        dtype=np.float32,
    )

    valid = (
        ray_angle
        > math.radians(0.5)
    )

    ground_distance[
        valid
    ] = (
        CAMERA_HEIGHT_M
        / np.tan(
            ray_angle[valid]
        )
    )

    horizon = (
        cy
        - fy
        * math.tan(
            pitch
        )
    )

    xs = np.arange(
        width,
        dtype=np.float32,
    )

    x_normalized = (
        (xs - cx)
        / max(
            cx,
            1.0,
        )
    )

    return (
        ground_distance,
        x_normalized,
        horizon,
    )


# ============================================================
# ROBUST GROUND FIT
# ============================================================

def robust_ground_fit(
    depth_score,
    ground_distance,
    x_normalized,
    horizon,
):

    h, w = depth_score.shape

    yy, xx = np.indices(
        (h, w)
    )

    d = ground_distance[
        yy
    ]

    valid = (
        np.isfinite(d)
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

    inv_d = np.zeros_like(
        depth_score,
        dtype=np.float32,
    )

    inv_d[valid] = (
        1.0
        / d[valid]
    )

    xmap = np.broadcast_to(
        x_normalized.reshape(
            1,
            -1,
        ),
        (h, w),
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
        xmap[valid],
    ])

    mask = np.ones(
        len(values),
        dtype=bool,
    )

    beta = None

    for _ in range(
        FIT_ITERATIONS
    ):

        if (
            np.count_nonzero(
                mask
            )
            < 100
        ):
            break

        beta, *_ = (
            np.linalg.lstsq(
                X[mask],
                values[mask],
                rcond=None,
            )
        )

        predicted = (
            X @ beta
        )

        residual = (
            values
            - predicted
        )

        r = residual[
            mask
        ]

        med = np.median(
            r
        )

        mad = np.median(
            np.abs(
                r - med
            )
        )

        sigma = (
            1.4826
            * mad
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

    predicted = (
        X @ beta
    )

    y = values[
        mask
    ]

    yp = predicted[
        mask
    ]

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
        np.count_nonzero(
            mask
        )
        / len(mask)
    )

    return {
        "A": float(A),
        "B": float(B),
        "C": float(C),
        "r2": float(r2),
        "inliers": float(
            inlier_fraction
        ),
    }


# ============================================================
# GEOMETRY CONFIDENCE
# ============================================================

def geometry_confidence(
    A,
    r2,
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
        confidence,
    ):

        if (
            tilt is None
            or confidence == "LOW"
        ):

            return (
                "UNKNOWN",
                None,
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

            ad = abs(
                delta
            )

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
            delta,
        )


# ============================================================
# METRIC DISTANCE
# ============================================================

def candidate_distance(
    depth_score,
    candidates,
    fit,
    x_normalized,
):

    A = fit["A"]
    B = fit["B"]
    C = fit["C"]

    h, w = (
        depth_score.shape
    )

    xmap = np.broadcast_to(
        x_normalized.reshape(
            1,
            -1,
        ),
        (h, w),
    )

    denom = (
        depth_score
        - B
        - C
        * xmap
    )

    distance = np.full(
        (h, w),
        np.nan,
        dtype=np.float32,
    )

    valid = (
        candidates
        & (A > 0)
        & (
            denom
            > MIN_DENOM
        )
    )

    distance[
        valid
    ] = (
        A
        / denom[valid]
    )

    return distance


def percentile(
    values,
    q,
):

    values = values[
        np.isfinite(
            values
        )
    ]

    if len(values) == 0:
        return None

    return float(
        np.percentile(
            values,
            q,
        )
    )


# ============================================================
# LOAD MODELS
# ============================================================

torch.set_grad_enabled(
    False
)

log(
    "VisionNN worker starting"
)


# ------------------------------------------------------------
# DEPTH
# ------------------------------------------------------------

log(
    f"Loading Depth Anything: "
    f"{DEPTH_MODEL_ID}"
)

t0 = time.perf_counter()

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
depth_model.to("cpu")

log(
    "Depth model loaded in "
    f"{time.perf_counter() - t0:.3f}s"
)


# ------------------------------------------------------------
# OFFSEG
# ------------------------------------------------------------

log(
    f"Loading OFFSEG: "
    f"{OFFSEG_WEIGHT}"
)

t0 = time.perf_counter()

offseg_model = BiSeNetV2(
    n_classes=4
)

state = torch.load(
    OFFSEG_WEIGHT,
    map_location="cpu",
)

offseg_model.load_state_dict(
    state,
    strict=False,
)

offseg_model.eval()
offseg_model.to("cpu")

offseg_to_tensor = ToTensor(
    mean=(
        0.3257,
        0.3690,
        0.3223,
    ),
    std=(
        0.2112,
        0.2148,
        0.2115,
    ),
)

log(
    "OFFSEG loaded in "
    f"{time.perf_counter() - t0:.3f}s"
)


# ============================================================
# TEMPORAL STATE
# ============================================================

temporal = TemporalTilt()


# ============================================================
# WARM-UP
# ============================================================

log(
    "Warm-up START"
)

dummy_rgb = np.zeros(
    (240, 320, 3),
    dtype=np.uint8,
)

dummy_pil = Image.fromarray(
    dummy_rgb
)

depth_inputs = depth_processor(
    images=dummy_pil,
    return_tensors="pt",
)

with torch.inference_mode():

    _ = depth_model(
        **depth_inputs
    )


x_off = (
    offseg_to_tensor(
        dict(
            im=dummy_rgb.copy(),
            lb=None,
        )
    )["im"]
    .unsqueeze(0)
)

with torch.inference_mode():

    _ = offseg_model(
        x_off
    )


log(
    "Warm-up END"
)

log(
    "VisionNN worker ready"
)


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    header = read_exact(
        stdin,
        4,
    )

    if header is None:
        break

    image_size = struct.unpack(
        "!I",
        header,
    )[0]

    image_bytes = read_exact(
        stdin,
        image_size,
    )

    if image_bytes is None:
        break

    try:

        frame_start = (
            time.perf_counter()
        )

        # ----------------------------------------------------
        # JPEG -> RGB
        # ----------------------------------------------------

        np_buffer = np.frombuffer(
            image_bytes,
            dtype=np.uint8,
        )

        frame = cv2.imdecode(
            np_buffer,
            cv2.IMREAD_COLOR,
        )

        if frame is None:
            raise RuntimeError(
                "Could not decode JPEG"
            )

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB,
        )

        h, w = rgb.shape[:2]

        pil = Image.fromarray(
            rgb
        )


        # ====================================================
        # DEPTH ANYTHING
        # ====================================================

        t0 = time.perf_counter()

        depth_inputs = (
            depth_processor(
                images=pil,
                return_tensors="pt",
            )
        )

        with torch.inference_mode():

            depth_out = (
                depth_model(
                    **depth_inputs
                )
                .predicted_depth
            )

        depth_score = (
            F.interpolate(
                depth_out.unsqueeze(1),
                size=(h, w),
                mode="bicubic",
                align_corners=False,
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


        # ====================================================
        # GROUND GEOMETRY
        # ====================================================

        (
            ground_distance,
            x_normalized,
            horizon,
        ) = build_ground_geometry(
            w,
            h,
        )

        fit = robust_ground_fit(
            depth_score,
            ground_distance,
            x_normalized,
            horizon,
        )


        # ====================================================
        # OFFSEG
        # ====================================================

        t0 = time.perf_counter()

        x_off = (
            offseg_to_tensor(
                dict(
                    im=rgb.copy(),
                    lb=None,
                )
            )["im"]
            .unsqueeze(0)
        )

        with torch.inference_mode():

            off_out = (
                offseg_model(
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

        # Safety in case model output
        # is not exactly input size.
        if (
            off_mask.shape[0] != h
            or off_mask.shape[1] != w
        ):

            off_mask = cv2.resize(
                off_mask,
                (w, h),
                interpolation=cv2.INTER_NEAREST,
            )

        traversable = (
            off_mask == 1
        )

        offseg_time = (
            time.perf_counter()
            - t0
        )


        # ====================================================
        # OFFSEG GLOBAL FRACTIONS
        # ====================================================

        class_counts = np.bincount(
            off_mask.reshape(-1),
            minlength=4,
        )

        class_fractions = (
            class_counts
            / off_mask.size
        )


        # ====================================================
        # FAILED GEOMETRY
        # ====================================================

        if fit is None:

            result = {
                "accepted": False,

                "source":
                    "vision_nn_fusion",

                "geometry_confidence":
                    "LOW",

                "temporal_stability":
                    "UNKNOWN",

                "fit": None,

                "regions": {},

                "offseg_class_fractions": [
                    round(
                        float(x),
                        4,
                    )
                    for x
                    in class_fractions
                ],

                "depth_time_s":
                    round(
                        depth_time,
                        4,
                    ),

                "offseg_time_s":
                    round(
                        offseg_time,
                        4,
                    ),

                "total_nn_time_s":
                    round(
                        time.perf_counter()
                        - frame_start,
                        4,
                    ),
            }

        else:

            # =================================================
            # FIT / CONFIDENCE
            # =================================================

            A = fit["A"]
            B = fit["B"]
            C = fit["C"]
            r2 = fit["r2"]

            confidence = (
                geometry_confidence(
                    A,
                    r2,
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
                delta_tilt,
            ) = temporal.update(
                tilt,
                confidence,
            )


            # =================================================
            # CANDIDATES
            # =================================================

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
                    1,
                    -1,
                ),
                (h, w),
            )

            valid = (
                np.isfinite(
                    dground
                )
                & (
                    yy > horizon
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
                dtype=np.float32,
            )

            expected[
                valid
            ] = (
                A
                / dground[
                    valid
                ]
                + B
                + C
                * xmap[
                    valid
                ]
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

            distance = (
                candidate_distance(
                    depth_score,
                    candidates,
                    fit,
                    x_normalized,
                )
            )


            # =================================================
            # LEFT / FRONT / RIGHT FUSION
            # =================================================

            thirds = [
                (
                    "left",
                    0,
                    w // 3,
                ),
                (
                    "front",
                    w // 3,
                    2 * w // 3,
                ),
                (
                    "right",
                    2 * w // 3,
                    w,
                ),
            ]

            region_data = {}

            for (
                region,
                x0,
                x1,
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
                    n_cand
                    / n_valid
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
                    25,
                )

                region_data[
                    region
                ] = {

                    "candidate_fraction":
                        round(
                            float(
                                candidate_fraction
                            ),
                            4,
                        ),

                    "traversable_fraction":
                        round(
                            float(
                                traversable_fraction
                            ),
                            4,
                        ),

                    "candidate_traversable_fraction":
                        (
                            round(
                                float(
                                    cand_trav
                                ),
                                4,
                            )
                            if cand_trav
                            is not None
                            else None
                        ),

                    "candidate_nontraversable_fraction":
                        (
                            round(
                                float(
                                    cand_nontrav
                                ),
                                4,
                            )
                            if cand_nontrav
                            is not None
                            else None
                        ),

                    "distance_p25_m":
                        (
                            round(
                                float(p25),
                                3,
                            )
                            if p25
                            is not None
                            else None
                        ),
                }


            # =================================================
            # RESULT
            # =================================================

            result = {

                # IMPORTANT:
                # still force GPT fallback.
                "accepted": False,

                "source":
                    "vision_nn_fusion",

                "geometry_confidence":
                    confidence,

                "temporal_stability":
                    temporal_stability,

                "fit": {
                    "A":
                        round(A, 5),

                    "B":
                        round(B, 5),

                    "C":
                        round(C, 5),

                    "r2":
                        round(r2, 5),

                    "inliers":
                        round(
                            fit[
                                "inliers"
                            ],
                            4,
                        ),

                    "tilt":
                        (
                            round(
                                tilt,
                                5,
                            )
                            if tilt
                            is not None
                            else None
                        ),

                    "delta_tilt":
                        (
                            round(
                                delta_tilt,
                                5,
                            )
                            if delta_tilt
                            is not None
                            else None
                        ),
                },

                "regions":
                    region_data,

                "offseg_class_fractions": [
                    round(
                        float(x),
                        4,
                    )
                    for x
                    in class_fractions
                ],

                "depth_time_s":
                    round(
                        depth_time,
                        4,
                    ),

                "offseg_time_s":
                    round(
                        offseg_time,
                        4,
                    ),

                "total_nn_time_s":
                    round(
                        time.perf_counter()
                        - frame_start,
                        4,
                    ),
            }


    except Exception as exc:

        result = {
            "accepted": False,
            "source":
                "vision_nn_worker_error",
            "error":
                str(exc),
        }


    # ========================================================
    # RETURN JSON
    # ========================================================

    payload = json.dumps(
        result
    ).encode(
        "utf-8"
    )

    stdout.write(
        struct.pack(
            "!I",
            len(payload),
        )
    )

    stdout.write(
        payload
    )

    stdout.flush()
