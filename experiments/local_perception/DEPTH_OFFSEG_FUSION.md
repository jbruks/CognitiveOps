# CognitiveOps — Local Perception Fusion Summary

## Objective

Replace the routine multimodal LLM perception call with a fast local perception stack that can provide useful geometry and traversability information to the rover control loop.

The current local stack combines:

- **Depth Anything V2 Small** for geometric structure, ground-plane fitting, protrusion candidates, approximate metric distance, and geometry confidence.
- **OFFSEG / BiSeNetV2** for off-road traversability segmentation.
- A **fusion layer** that distinguishes between terrain relief and likely non-traversable structure.

The VLM is kept as an **on-demand fallback**, not as a mandatory step every cycle.

---

## 1. Geometry perception — Depth Anything V2 Small

Model:

`depth-anything/Depth-Anything-V2-Small-hf`

Current provisional camera assumptions:

- Camera height: `0.20 m`
- Horizontal FOV: `70°`
- Downward pitch: `10°`

Ground model:

`score(x,y) = A / ground_distance(y) + B + C*x_normalized`

The model is robustly fitted per frame. Pixels significantly above the expected ground score are treated as **candidate protrusions**.

Current candidate threshold:

`observed_score - expected_ground_score > 0.25`

Geometry confidence:

- `LOW`: `A <= 0` or `R² < 0.95`
- `MEDIUM`: `0.95 <= R² < 0.985`
- `HIGH`: `R² >= 0.985`

Distance is estimated by inverting the fitted score model:

`d = A / (score - B - C*x)`

The geometry layer is intentionally interpreted as:

> “surface protruding from expected ground”

and **not automatically as an obstacle**.

---

## 2. Traversability perception — OFFSEG

Model:

- OFFSEG official repository
- BiSeNetV2
- 4 output classes
- Pretrained RUGD weights

The original OFFSEG pipeline explicitly treats **class 1 as traversable**.

Typical CPU inference observed in the current environment:

- approximately `0.03–0.05 s/frame`

OFFSEG proved much more useful for this project than generic COCO detection or the tested GOOSE configurations because it provides a direct signal about **off-road traversability**.

---

## 3. Depth + OFFSEG fusion

For each image region (`LEFT`, `FRONT`, `RIGHT`) the fusion benchmark records:

- `candidate_fraction`
- `traversable_fraction`
- `candidate_traversable_fraction`
- `candidate_nontraversable_fraction`
- `distance_p25_m`
- geometry confidence
- temporal stability

Interpretation:

### Case A — relief / rough terrain

Depth detects significant protrusion, but OFFSEG says the same pixels are traversable.

Example: `0151.jpg`

- Geometry: `HIGH`
- Left candidate fraction: `36.4%`
- Candidate traversable fraction: `100%`

Interpretation:

**strong terrain relief, but likely traversable**

### Case B — unsafe / closed scene

Depth confidence collapses while OFFSEG reports almost no traversable terrain.

Example: `0155.jpg`

- Geometry: `LOW`
- Front candidate fraction: `72.4%`
- Front traversable fraction: `0%`
- Candidate non-traversable fraction: `100%`

Example: `0174.jpg`

- Geometry: `LOW`
- Front traversable fraction: `0%`
- Candidate non-traversable fraction: approximately `100%`

Interpretation:

**scene not safely understood / blocked / candidate for stop, caution or VLM escalation**

### Case C — geometric obstacle that OFFSEG may miss

Example: `0060.jpg`, fence scene.

- Geometry: `HIGH`
- Front candidate fraction: `6.2%`
- Front P25 distance: `0.56 m`
- Right candidate fraction: `16.7%`
- Right P25 distance: `0.30 m`
- OFFSEG still considers almost all of the ROI traversable.

This is an important result:

> OFFSEG must never override Depth geometry by itself.

OFFSEG is a terrain/traversability signal; Depth remains necessary for detecting local protruding structures such as the fence.

---

## 4. Full 177-frame replay

The combined pipeline was replayed on the complete merged rover dataset:

`0001.jpg ... 0177.jpg`

Benchmark outputs:

- `fusion_results.csv`
- `review_fusion.html`
- one fusion overlay per frame

Visual overlay:

- **green** — OFFSEG traversable terrain
- **yellow** — Depth candidate + OFFSEG traversable
- **red** — Depth candidate + OFFSEG non-traversable

Geometry-confidence distribution:

- `162 HIGH`
- `11 MEDIUM`
- `4 LOW`

Temporal behavior was stable on almost all valid frames, with expected UNKNOWN states at startup and on LOW-confidence geometry.

Representative difficult frames such as `0155`, `0156` and `0174` are correctly rejected by the geometry confidence and also produce very low traversability.

The system also recovers cleanly on subsequent frames such as `0175`.

---

## 5. Performance

Measured on the current CPU-only workstation during the full replay:

- Depth Anything mean: approximately `0.179 s/frame`
- OFFSEG mean: approximately `0.039 s/frame`
- Total local perception mean: approximately `0.238 s/frame`
- Total median: approximately `0.232 s/frame`

This corresponds to roughly **4 Hz local perception**, before further optimization or parallel execution.

Compared with the previous mandatory remote multimodal LLM perception step of roughly **6–7 seconds**, the local stack is fast enough to fundamentally change the control-loop architecture.

---

## 6. Current architectural conclusion

Recommended perception architecture for the POC:

```text
RGB camera
   |
   +--> Depth Anything V2 Small
   |      - ground geometry
   |      - candidate protrusions
   |      - approximate distances
   |      - geometry confidence
   |
   +--> OFFSEG BiSeNetV2
          - off-road traversability
          - coarse terrain viability
              |
              v
        local fusion
              |
              v
      structured world state
              |
      +-------+--------+
      |                |
scene understood    ambiguous/unsafe
      |                |
      v                v
 text LLM L2       VLM on demand
      |                |
      +-------+--------+
              |
           action
```

The key design principle is:

> Use fast local perception every cycle. Use the VLM only when the local perception is insufficient or contradictory.

---

## 7. Status

### Point 1 — Fast geometry
**POC complete**

### Point 2 — Fast traversability / semantic signal
**POC complete**

### Next step
Integrate the fused local perception into the live CognitiveOps rover loop and validate it on the real rover before tuning escalation rules or replacing the L2 decision model.
