# ProjectRover — GO_TO_POINT Field Test Report

**Test date:** 2026-10-15  
**Status:** Successful according to onboard L4 completion criterion  
**Repository:** `jbruks/CognitiveOps`  
**Branch:** `feature/l3-l4-gnc`  
**Committed baseline:** `8693ecf` (`feat: establish successful autonomous GO_TO_POINT baseline`)  
**Software provenance:** The commit represents the laptop working tree preserved after the test; an exact comparison with the Raspberry Pi deployment remains to be completed.  
**Primary evidence:** `goto_test_nav_cam_sol11_500tokens.log` (595,365 bytes)  
**Evidence SHA-256:** `73c74fca29e4050bd9acdcbf51407e35eff6b2a3ef8abf0033a05ff57321c881`

## 1. Executive summary

The Axial SCX10 II-based ProjectRover completed a `GO_TO_POINT` mission. The run began at approximately 11:04:37 and ended at 11:34:43 (approximately 30 minutes and 6 seconds), spanning 185 logged control cycles. L4 declared completion when the GPS-derived distance to the target was approximately 4.86 m. This establishes completion against the software's navigation criterion, **not** independently verified physical arrival accuracy.

The test demonstrates an important improvement in terrain interpretation, while also exposing safety and efficiency concerns requiring further study.

## 2. Platform and test context

- Vehicle: Axial SCX10 II 4×4 crawler with original, non-portal axles.
- Width: approximately 0.30 m.
- Minimum ground clearance: approximately 0.07 m.
- Low-mounted monocular camera, making nearby gravel and vegetation appear disproportionately large.
- Perception prompt adapted to the rover's actual traversability capabilities.
- GPS-based waypoint guidance and L2 tactical control.

Hardware, firmware, VLM model identifier, prompt token budget, and exact Raspberry Pi deployment revision should be recorded from the test environment before publication.

## 3. Mission outcome

| Metric | Observed value |
|---|---:|
| Start time | 11:04:37 |
| End time | 11:34:43 |
| Elapsed time | ~30 min 6 s |
| Logged control cycles | 185 |
| Initial GPS distance to target | 45.24 m |
| Final GPS distance to target | 4.86 m |
| Final reported GPS accuracy | 2.39 m |
| L4 status | `GO_TO_POINT completed` |
| Final L1 command | `STOP` |

The GPS-derived distance varied substantially during the mission and should not be interpreted as a monotonic physical trajectory. Reconstructing the route and evaluating GPS noise remain follow-up tasks.

## 4. Tactical control and safety

Previously extracted L1 action counts from the log:

| Action | Count |
|---|---:|
| STOP | 204 |
| FORWARD_RIGHT | 62 |
| FORWARD_LEFT | 52 |
| MOVE_FORWARD | 20 |
| MOVE_BACKWARD | 26 |
| HOLD | 6 |

Among movement actions, 134/160 (83.8%) were forward or forward-turning; 26/160 (16.2%) were reverse actions. **Reverse maneuvers are a priority safety concern** because the vehicle lacks rearward obstacle perception. These counts should be revalidated with a reproducible parser before final publication.

Six L2 safety-veto messages were previously identified. Their triggers and subsequent executed actions should be examined cycle by cycle.

## 5. Perception findings

A preliminary extraction parsed 159 VLM JSON results from the 185 cycles. **The remaining 26 cycles have not yet been reconciled**, so the following statistics describe the parsed subset only:

- No reported obstacles: 65/159 (40.9%).
- Five reported obstacles: 20/159 (12.6%).
- Front region marked traversable: 118/159.
- Mean reported confidence: approximately 0.826.

The rover-specific prompt distinguishes traversable gravel, small stones, loose dirt, and sparse vegetation from genuinely restrictive hazards. The successful test is consistent with an improvement in perception, but does not isolate the prompt as the sole cause: the committed changes also include schema conversion, geometric clearance logic, L2 safety handling, and a dependency version change.

## 6. Navigation and timing

- A previous extraction found 167 L3 guidance entries with numeric distances.
- Nineteen L3 `Guidance: HOLD` entries were found; some had no usable distance, bearing, or heading error, while the final HOLD corresponds to goal completion.
- VLM request latency across 185 requests was previously estimated at a mean of ~4.75 s, median ~3.60 s, and maximum ~27.91 s. These values require independent script-based verification before final sign-off.

The non-monotonic distance progression and intermittent guidance gaps warrant investigation before performance optimization.

## 7. Risks and limitations

1. **Blind reversing:** 26 reverse actions without rear perception; correlate each with the preceding VLM result and L2 decision.
2. **Intermittent L3 HOLD:** identify GPS validity, fix age, and L4/L2 behavior during missing guidance.
3. **Perception parsing coverage:** explain why only 159 of 185 VLM outputs were parsed in the preliminary analysis.
4. **GPS uncertainty:** goal completion is GPS-based and not independently surveyed.
5. **Deployment provenance:** verify the Raspberry Pi's field-tested code matches baseline commit `8693ecf`.
6. **Evidence privacy:** raw log contains precise GPS coordinates; assess repository visibility before publication.

## 8. Follow-up plan

1. Reconcile all 185 VLM cycles with a robust log parser.
2. Reconstruct and classify the 26 reverse decisions chronologically.
3. Diagnose the 19 L3 HOLD events and their downstream effects.
4. Plot GPS distance and heading error against mission time, including accuracy estimates.
5. Verify deployed software revision and record the test configuration.
6. Review and sanitize documentation before committing; revoke any exposed API keys.
7. Finalize the report, commit the evidence documentation separately, create an annotated Git tag, and push after review.

## 9. Evidence handling

The full log is retained separately pending a decision on public versus private publication. Its SHA-256 checksum above enables verification of the exact evidence file. Avoid committing unredacted GPS data, credentials, or camera imagery to a public repository without explicit review.

---

*Draft 0.1 — preliminary analysis. Counts and conclusions marked as preliminary require reproducible validation against the full log before release.*
