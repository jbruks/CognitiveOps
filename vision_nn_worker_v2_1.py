#!/usr/bin/env python3
"""ProjectRover Vision NN V2.1 — experimental, read-only.

Compatible with the original worker protocol: stdin [uint32 big-endian length][JPEG];
stdout [uint32 big-endian length][JSON]. All logs go to stderr.

V2 changes:
 - Keep the original global ground-residual detector.
 - Fit ground preferentially on OFFSEG class 1 if it provides enough samples.
 - Add independent, local near-side depth discontinuities.
 - OR fusion with both signals, without suppressing detections by OFFSEG.
 - Publish independent diagnostics and connected-component counts.
 - No movement permission: accepted=False, always.
"""
import json
import math
import os
import struct
import sys
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForDepthEstimation

DEPTH_MODEL_ID = "depth-anything/Depth-Anything-V2-Small-hf"
CAMERA_HEIGHT_M = 0.20
HFOV_DEG = 70.0
PITCH_DEG = 10.0
BOTTOM_FRACTION = 0.92
SCORE_MARGIN = 0.25
FIT_ITERATIONS = 6
LOWER_SIGMA = 3.0
UPPER_SIGMA = 2.0
# Experimental recall-first local detector. All thresholds in arbitrary
# Depth Anything score units; NOT meters. Tune on labeled photographs.
LOCAL_WINDOW = 31       # pixel window at original JPEG resolution
LOCAL_MIN_SCORE = 0.15  # absolute floor in relative depth-score units
LOCAL_NOISE_MULT = 2.0  # adaptation to robust local spread
MIN_GROUND_FIT_PIXELS = 1500
MIN_GROUND_FIT_FRACTION = 0.15
MAX_IMAGE_BYTES = 30_000_000
OFFSEG_ROOT = Path("/home/devlin/CognitiveOps/experiments/local_perception/OFFSEG")
OFFSEG_WEIGHT = OFFSEG_ROOT / "extracted_weights" / "Offseg weights" / "model_final3.pth"
sys.path.insert(0, str(OFFSEG_ROOT / "Pipeline"))
from lib.models.bisenetv2 import BiSeNetV2
from lib.transform_cv2 import ToTensor


def log(*args):
    print(*args, file=sys.stderr, flush=True)


def read_exact(stream, size):
    b = bytearray()
    while len(b) < size:
        part = stream.read(size - len(b))
        if not part:
            return None
        b.extend(part)
    return bytes(b)


def ground_geometry(width, height):
    fx = width / (2.0 * math.tan(math.radians(HFOV_DEG) / 2.0))
    fy = fx
    cx, cy = (width - 1) / 2.0, (height - 1) / 2.0
    ys = np.arange(height, dtype=np.float32)
    angle = math.radians(PITCH_DEG) + np.arctan((ys - cy) / fy)
    g = np.full(height, np.nan, dtype=np.float32)
    ok = angle > math.radians(0.5)
    g[ok] = CAMERA_HEIGHT_M / np.tan(angle[ok])
    horizon = cy - fy * math.tan(math.radians(PITCH_DEG))
    xnorm = (np.arange(width, dtype=np.float32) - cx) / max(cx, 1.0)
    return g, xnorm, horizon


def robust_fit(score, inv_ground, xmap, mask):
    values = score[mask].astype(np.float64)
    if len(values) < 100:
        return None
    X = np.column_stack([
        inv_ground[mask], np.ones(len(values)), xmap[mask]
    ]).astype(np.float64)
    inlier = np.ones(len(values), dtype=bool)
    beta = None
    for _ in range(FIT_ITERATIONS):
        if inlier.sum() < 100:
            break
        beta, *_ = np.linalg.lstsq(X[inlier], values[inlier], rcond=None)
        error = values - X @ beta
        e = error[inlier]
        med = np.median(e)
        sigma = 1.4826 * np.median(np.abs(e - med))
        if sigma < 1e-6:
            break
        updated = (error >= med - LOWER_SIGMA * sigma) & (
            error <= med + UPPER_SIGMA * sigma)
        if updated.sum() < 100:
            break
        inlier = updated
    if beta is None:
        return None
    observed, predicted = values[inlier], (X @ beta)[inlier]
    var = float(np.sum((observed - np.mean(observed)) ** 2))
    r2 = 1.0 - float(np.sum((observed - predicted) ** 2)) / var if var > 1e-12 else 0.0
    return dict(A=float(beta[0]), B=float(beta[1]), C=float(beta[2]),
                r2=r2, inliers=float(inlier.mean()))


def fit_quality(fit):
    if fit is None or fit["A"] <= 0 or fit["r2"] < 0.95:
        return "LOW"
    if fit["r2"] < 0.985:
        return "MEDIUM"
    return "HIGH"


def local_discontinuities(score, roi):
    """Detect local positive protrusions after cancelling the smooth depth slope.

    Unlike V2, DO NOT compare to window minimum: doing so labels normal
    perspective gradient as an obstacle. Compare to a symmetric low-pass
    background instead; a planar ramp has approximately zero residual.
    Outputs are experimental relative-score signals, not metric distances.
    """
    smooth = cv2.GaussianBlur(score, (5, 5), 0.9).astype(np.float32)
    size = LOCAL_WINDOW | 1
    # Float32-compatible symmetric background; OpenCV 5 medianBlur with
    # kernel >=7 only supports uint8. Gaussian cancels linear ground slope.
    background = cv2.GaussianBlur(smooth, (size, size), 0)
    contrast = np.maximum(smooth - background, 0.0)
    residual = smooth - background
    if np.any(roi):
        sample = residual[roi]
        median = float(np.median(sample))
        mad = float(np.median(np.abs(sample - median)))
    else:
        mad = 0.0
    threshold = max(LOCAL_MIN_SCORE, LOCAL_NOISE_MULT * 1.4826 * mad)
    detections = (contrast > threshold) & roi
    return detections, contrast, threshold


def components(mask):
    """Describe candidate connected components for diagnostics only."""
    count, labels, stats, centers = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), connectivity=8)
    out = []
    for idx in range(1, count):
        x, y, w, h, area = (int(v) for v in stats[idx])
        if area >= 6:
            out.append({"x": x, "y": y, "w": w, "h": h, "pixels": area})
    return sorted(out, key=lambda r: r["pixels"], reverse=True)[:20]


def fractions(candidates, roi):
    denominator = int(np.count_nonzero(roi))
    return round(float(np.count_nonzero(candidates & roi)) / denominator, 4) if denominator else 0.0


def save_debug(debug_dir, index, rgb, score, offmask, global_mask,
               local_mask, combined, contrast):
    """Optional sidecar diagnostic image; never written to stdout."""
    h, w = score.shape
    lo, hi = np.percentile(score, [2, 98])
    scaled = np.uint8(np.clip((score - lo) / max(hi - lo, 1e-6) * 255, 0, 255))
    depth = cv2.applyColorMap(scaled, cv2.COLORMAP_TURBO)
    offpalette = np.array([[85, 85, 85], [65, 170, 70],
                           [200, 80, 170], [35, 170, 220]], dtype=np.uint8)
    off = offpalette[np.clip(offmask, 0, 3)]
    overlay = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    overlay[combined] = ((overlay[combined].astype(np.float32) * 0.35)
                         + np.array([0, 0, 255], dtype=np.float32) * 0.65).astype(np.uint8)
    masks = np.zeros((h, w, 3), np.uint8)
    masks[global_mask] = (255, 100, 20)
    masks[local_mask] = (20, 210, 255)
    masks[global_mask & local_mask] = (255, 255, 255)
    first = np.hstack([cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), depth, off])
    second = np.hstack([masks, overlay,
                        cv2.applyColorMap(np.uint8(np.clip(contrast /
                            max(float(np.percentile(contrast, 98)), 1e-6) * 255, 0, 255)),
                            cv2.COLORMAP_TURBO)])
    cv2.imwrite(str(debug_dir / f"{index:04d}.jpg"),
                np.vstack([first, second]), [cv2.IMWRITE_JPEG_QUALITY, 88])


def main():
    torch.set_grad_enabled(False)
    torch.set_num_threads(max(1, int(os.environ.get("ROVER_NN_TORCH_THREADS", "4"))))
    log("VisionNN V2.1 starting (experimental, accepted=False)")
    t = time.perf_counter()
    processor = AutoImageProcessor.from_pretrained(DEPTH_MODEL_ID)
    depth_model = AutoModelForDepthEstimation.from_pretrained(DEPTH_MODEL_ID)
    depth_model.to("cpu").eval()
    log("Depth model ready in %.2fs" % (time.perf_counter() - t))
    t = time.perf_counter()
    off_model = BiSeNetV2(n_classes=4)
    state = torch.load(OFFSEG_WEIGHT, map_location="cpu", weights_only=False)
    off_model.load_state_dict(state, strict=False)
    off_model.to("cpu").eval()
    to_tensor = ToTensor(mean=(0.3257, 0.3690, 0.3223),
                         std=(0.2112, 0.2148, 0.2115))
    log("OFFSEG ready in %.2fs" % (time.perf_counter() - t))
    debug_dir = os.environ.get("ROVER_NN_V2_DEBUG_DIR")
    debug_path = Path(debug_dir) if debug_dir else None
    if debug_path:
        debug_path.mkdir(parents=True, exist_ok=True)
    index = 0
    last_fit = deque(maxlen=5)
    while True:
        hdr = read_exact(sys.stdin.buffer, 4)
        if hdr is None:
            break
        n = struct.unpack("!I", hdr)[0]
        if n == 0 or n > MAX_IMAGE_BYTES:
            log("Invalid JPEG length:", n)
            break
        jpeg = read_exact(sys.stdin.buffer, n)
        if jpeg is None:
            break
        index += 1
        started = time.perf_counter()
        try:
            bgr = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
            if bgr is None:
                raise ValueError("Could not decode JPEG")
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            t = time.perf_counter()
            inputs = processor(images=Image.fromarray(rgb), return_tensors="pt")
            with torch.inference_mode():
                depth_out = depth_model(**inputs).predicted_depth
                score = F.interpolate(depth_out.unsqueeze(1), size=(h, w),
                                      mode="bicubic", align_corners=False
                                      ).squeeze().cpu().numpy().astype(np.float32)
            depth_time = time.perf_counter() - t

            t = time.perf_counter()
            xoff = to_tensor(dict(im=rgb.copy(), lb=None))["im"].unsqueeze(0)
            with torch.inference_mode():
                off_out = off_model(xoff)
            offmask = off_out[0].argmax(dim=1).squeeze().cpu().numpy().astype(np.uint8)
            if offmask.shape != (h, w):
                offmask = cv2.resize(offmask, (w, h), interpolation=cv2.INTER_NEAREST)
            off_time = time.perf_counter() - t
            class_counts = np.bincount(offmask.ravel(), minlength=4).astype(np.float64)
            class_fractions = (class_counts / offmask.size).round(4).tolist()

            g, xnorm, horizon = ground_geometry(w, h)
            yy = np.arange(h)[:, None]
            valid_rows = np.isfinite(g) & (np.arange(h) > horizon) & (
                np.arange(h) < h * BOTTOM_FRACTION)
            valid = np.broadcast_to(valid_rows[:, None], (h, w)).copy()
            inv = np.zeros((h, w), np.float32)
            inv[valid] = np.broadcast_to((1.0 / g)[:, None], (h, w))[valid]
            xmap = np.broadcast_to(xnorm[None, :], (h, w))
            ground_only = valid & (offmask == 1)
            count = int(ground_only.sum())
            min_needed = max(MIN_GROUND_FIT_PIXELS, int(valid.sum() * MIN_GROUND_FIT_FRACTION))
            use_offseg = count >= min_needed
            fit_mask = ground_only if use_offseg else valid
            fit = robust_fit(score, inv, xmap, fit_mask)
            fit_source = "offseg_class_1" if use_offseg else "full_roi_fallback"
            if fit is None and use_offseg:
                fit = robust_fit(score, inv, xmap, valid)
                fit_source = "full_roi_fallback"
            confidence = fit_quality(fit)

            if fit:
                expected = fit["A"] * inv + fit["B"] + fit["C"] * xmap
                residual = score - expected
                global_mask = valid & (residual > SCORE_MARGIN)
            else:
                global_mask = np.zeros((h, w), dtype=bool)
            # The local detector still operates if the global fit fails.
            local_mask, contrast, threshold = local_discontinuities(score, valid)
            combined = global_mask | local_mask
            thirds = [("left", 0, w // 3),
                      ("front", w // 3, 2 * w // 3),
                      ("right", 2 * w // 3, w)]
            regions = {}
            for name, x0, x1 in thirds:
                selector = np.zeros((h, w), dtype=bool)
                selector[:, x0:x1] = valid[:, x0:x1]
                traversable = offmask == 1
                regions[name] = {
                    "candidate_fraction": fractions(combined, selector),
                    "global_candidate_fraction": fractions(global_mask, selector),
                    "local_candidate_fraction": fractions(local_mask, selector),
                    "traversable_fraction": fractions(traversable, selector),
                    "candidate_traversable_fraction": (
                        round(float(np.count_nonzero(combined & selector & traversable))
                              / int(np.count_nonzero(combined & selector)), 4)
                        if np.any(combined & selector) else None),
                    "candidate_nontraversable_fraction": (
                        round(float(np.count_nonzero(combined & selector & ~traversable))
                              / int(np.count_nonzero(combined & selector)), 4)
                        if np.any(combined & selector) else None),
                    # Relative depth from one camera is not validated in meters.
                    "distance_p25_m": None,
                    "object_status": "CANDIDATE" if np.any(combined & selector) else "UNKNOWN",
                }
            current_tilt = fit["C"] / fit["A"] if fit and fit["A"] > 0 else None
            temporal = "UNKNOWN"
            delta_tilt = None
            if current_tilt is not None and confidence != "LOW":
                if len(last_fit) >= 3:
                    delta_tilt = current_tilt - float(np.median(last_fit))
                    temporal = ("ABRUPT" if abs(delta_tilt) > 2.7 else
                                "CHANGING" if abs(delta_tilt) > 1.7 else "STABLE")
                last_fit.append(current_tilt)
            fit_out = None if fit is None else {
                **{k: round(v, 5) for k, v in fit.items()},
                "tilt": None if current_tilt is None else round(current_tilt, 5),
                "delta_tilt": None if delta_tilt is None else round(delta_tilt, 5),
            }
            result = {
                "accepted": False,
                "source": "vision_nn_fusion_v2_1_experimental",
                "geometry_confidence": confidence,
                "temporal_stability": temporal,
                "fit": fit_out,
                "fit_source": fit_source,
                "regions": regions,
                "offseg_class_fractions": class_fractions,
                "local_contrast_threshold": round(threshold, 5),
                "global_candidate_fraction": fractions(global_mask, valid),
                "local_candidate_fraction": fractions(local_mask, valid),
                "combined_candidate_fraction": fractions(combined, valid),
                "candidate_components": components(combined),
                "local_component_count": len(components(local_mask)),
                "depth_time_s": round(depth_time, 4),
                "offseg_time_s": round(off_time, 4),
                "total_nn_time_s": round(time.perf_counter() - started, 4),
                "experimental": True,
                "algorithm_version": "2.1",
            }
            if debug_path:
                save_debug(debug_path, index, rgb, score, offmask,
                           global_mask, local_mask, combined, contrast)
        except Exception as exc:
            log("V2 frame %d error: %r" % (index, exc))
            result = {"accepted": False, "source": "vision_nn_worker_v2_1_error",
                      "experimental": True,
                "algorithm_version": "2.1", "error": str(exc)}
        payload = json.dumps(result, allow_nan=False).encode("utf-8")
        sys.stdout.buffer.write(struct.pack("!I", len(payload)))
        sys.stdout.buffer.write(payload)
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
