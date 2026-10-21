# Field test — Local Qwen L2 — 2026-10-21

## Context

Four autonomous rover runs were analysed after moving L2 tactical reasoning from the remote OpenAI path to local **Qwen 2.5 7B via Ollama**, reached from the Raspberry Pi through a persistent SSH worker on the ZBook.

The test included difficult lighting conditions (low frontal sun during the first part), changes in terrain/vegetation, and a temporary loss of phone GPS connectivity. Motor commands were active during these runs.

## Log summary

| Metric | Result |
|---|---:|
| Recorded cycles/images | 318 |
| Tactical decisions | 297 |
| `MOVE_FORWARD` | 118 |
| `FORWARD_LEFT` | 69 |
| `FORWARD_RIGHT` | 47 |
| `MOVE_BACKWARD` | 63 |
| Perception HIGH (`0.9`) | 230 |
| Perception MEDIUM (`0.7`) | 19 |
| Perception LOW (`0.3`) | 48 |
| Explicit GPS/navigation HOLD cycles | 20 |

VisionNN inference was very stable: **0.313 s mean**, **0.311 s median**, with observed values from **0.298 s to 0.425 s**.

## Main findings

### 1. Overall behaviour was robust and stable

The full stack remained operational across the runs. The local Qwen safety micro-task integrated correctly with perception, L3 guidance, validation and RA4M1 commands.

### 2. Conservative reactions are mostly explained by perception uncertainty

There were **63 `MOVE_BACKWARD` decisions**. Of these, **48 coincided with LOW perception confidence (`0.3`)**, where the current policy forces a deterministic `MOVE_BACKWARD` without calling Qwen.

Reviewing the corresponding images showed that many of these events occurred in genuinely difficult visual conditions: frontal low sun/glare, strong shadows, rough gravel, nearby vegetation, curbs/benches and objects occupying a large part of the low-mounted camera view.

This suggests that the perceived "startle" behaviour is mainly caused by the current safety policy reacting strongly to a single LOW-confidence frame, rather than instability in the overall architecture.

### 3. GPS loss failed safely

During the long run the phone stopped providing fresh navigation data. L3 detected stale position/heading, changed guidance to `HOLD`, and L1 repeatedly sent `STOP` until fresh data returned.

This is the expected safe behaviour: the rover did not continue navigating on stale phone GPS data.

### 4. Qwen is useful for safety, but not for numeric heading control

For clear-path cycles with valid heading information, the Qwen heading micro-task matched the intended ±8° rule in **189/217 cases (87.1%)**, with **28 mismatches**.

Because heading correction is only a numeric threshold operation, this does not justify an LLM call. The design was therefore changed after the test:

- Qwen remains responsible for the **safety/obstacle micro-task**.
- Heading is now **deterministic code**:
  - `heading_error > +8°` → `FORWARD_RIGHT`
  - `heading_error < -8°` → `FORWARD_LEFT`
  - otherwise → `MOVE_FORWARD`

This removes one LLM call from normal clear-path cycles and eliminates avoidable heading interpretation errors.

## Next tuning candidate

Do **not** change perception thresholds yet. The next candidate is the temporal policy for LOW confidence. A likely improvement is:

- isolated LOW frame → `STOP`
- LOW persisting for two consecutive cycles → `MOVE_BACKWARD`

This should reduce unnecessary reverse manoeuvres while preserving conservative behaviour in genuinely uncertain scenes.

## Conclusion

The test validates the local Qwen/Ollama L2 architecture as a practical replacement for the remote tactical LLM path. The strongest results are the stability of the local perception pipeline, correct safe handling of GPS loss, and reliable Qwen obstacle/safety decisions. The main remaining refinement is to make LOW-confidence handling less reactive over a single frame.
