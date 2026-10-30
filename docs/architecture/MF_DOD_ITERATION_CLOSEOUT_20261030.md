# MF-DoD — Iteration closeout (2026-10-30)

## Scope and checkpoint
Implementation frozen for review at this document's commit. Development branch: `feature/mf-dod-cognitive-architecture`. Previous stable tag: `baseline/mf-dod-cognitive-validation-20261030` (commit `2c54a6b`). Do not interpret this as permission for physical movement.

## Workstation-validated results
- Llombai simulation mission package with operator-accepted approximate visual candidates; not a real authorized geofence.
- GPT-5.4 L4 proposed four reviewable objectives; explicit operator approval was used for lab-only execution.
- Synthetic L3 blockage triggered GPT L3 `REQUEST_L4_REPLAN` and GPT L4 continuation over remaining approved objectives; 10/10 combined tests previously passed.
- Memory replay supplied historical blocked POI to a subsequent GPT-5.4 decision; order unchanged, reasoning accounted for historical nature. Separate tests 2/2 passed.
- A/B/C experiment automation passed 2/2 tests; live GPT comparisons did not change order. PDF experiment recovered 3 excerpts from FM 3-25.26 pages 155–157, but citation relevance and benefit not established (#14 closed as exploratory with limitations).
- Structured JSONL event replay passed 2/2 tests; 4 synthetic navigation events consumed.
- Historical physical text-log normalization passed 2/2 tests:
  - Navigation reference: 168 cycles, GPS populated 156, guidance HOLD 13, 1 software-reported arrival.
  - US05: 95 cycles, GPS populated 92, guidance HOLD 3, 9 recovery notices, 26 invalid ultrasonic samples.
- Read-only US05 shadow diagnostic passed 2/2 tests: GPS unavailable 3, diagnostic accuracy uncertain 52 (>10m or missing), ultrasonic invalid 26, recovery notices 9, repeated-recovery window alerts 3. No GPT calls or physical actions.

## Explicit limitations
- Physical rover main, L1, L2, VisionNN, and firmware have not been changed or integrated with the new cognitive agent.
- Live shadow mode with motors inhibited has **not** been tested.
- Existing field logs lack a verified link to Llombai visual simulation POIs; position data must not be ascribed to those objectives.
- A software-reported navigation arrival is not proof of successful inspection or high-accuracy position.
- The US05 diagnostic is heuristic, not an L3 GPT model inference or validated physical safety case.
- Repeated recovery notices are not proof of separate reverse motions.
- The A/B/C experiment contains an experimental-label confound; claim grounding not verified.
- Geofence permission, terrain safety, timeouts, live communications failure, watchdog, emergency stop, and rollback require independent review.

## Next iteration: Issue #15
1. Inventory and establish physical runtime adapter boundary.
2. Develop strictly non-actuating **live shadow** input stream using replayed/real telemetry; verify network failure, stale data, STOP/HOLD behavior.
3. Independently verify permitted operating region and operator emergency stop before considering any physical trial.
4. Begin supervised single-goal tests only after documented readiness gates.
5. Capture timing, quality, error and recovery logs; use findings to scope the next full cognitive iteration.

No claim of field-ready autonomous mission capability is made.
