# CognitiveOps — MF-DoD Iteration 3: RC Airfield Inspection Use Case

**Status:** Functional analysis; no implementation  
**Framework:** Mission First, Doctrine on Demand (MF-DoD)  
**Use case:** CU-01 — Civilian RC Airfield Inspection

## Goal

Demonstrate that a general-purpose rover can interpret an unfamiliar civilian site-inspection mission, identify needed procedural knowledge, and produce an evidence-based inspection plan and report without a mission-specific prompt.

**Mission brief:** “Inspect the authorized RC airfield facilities, surface conditions and accesses. Report visible obstructions, uncertainties and areas that could not be inspected.”

The operator supplies site information, an approved boundary, operating constraints and the map. The rover must not infer authorization from a satellite image.

## Actors and responsibilities

| Actor | Responsibility |
|---|---|
| Site representative | Approves areas and operating window |
| Operator | Assigns and supervises inspection; approves robot movements |
| CognitiveOps | Plans observations, records findings and reports uncertainty |
| DoctrineService (future) | Retrieves attributed procedural guidance, not commands |

## Reference sources

- **MCTP 3-01A — Scouting and Patrolling**: a source for general observation, information collection and reporting concepts, adapted strictly to a non-weaponized civil inspection.
- **FM 3-25.26 — Map Reading and Land Navigation**: a source for general map interpretation and terrain awareness.

**Citation status:** Exact paragraphs/pages have not yet been verified. Source-based requirements must not be claimed as direct quotations until checked.

## Areas identified in supplied satellite images

| Zone | Feature | Inspection interest |
|---|---|---|
| Z1 | RC runway | Surface condition and visible obstructions |
| Z2 | Club facilities | Visible condition and accessibility |
| Z3 | Southern apron | Ground condition and local surface irregularities |
| Z4 | Western access | General access condition |
| Z5 | Eastern access | General access condition |

These are image-derived functional labels, **not surveyed polygons**. Photos and annotated maps remain in the conversation and are not yet committed as repository image assets.

## Inspection approach

1. Validate club permission, exclusions and supervision arrangements.
2. Use the aerial image to distinguish the five inspection subjects.
3. Define evidence required for each subject.
4. Observe from approved safe locations before considering any closer inspection.
5. Record georeferenced photographs, date/time, confidence and visibility problems.
6. Mark any inaccessible or unobserved zone explicitly.
7. Compile a final report and request human review.

The operator supplied an annotated sequence of areas for discussion. It is a **functional inspection order**, not an approved robotic route. Physical navigation and waypoint selection must be checked separately at the site.

### Morning light

The inspection is planned in low morning light, with the sun to the east (right of the reference map). Eastward views may be affected by glare; lateral light and long shadows may also distort obstacle interpretation. Uncertain findings require a better observation or an uncertainty flag.

## Traceability: rationale versus adaptation

| Decision | Basis |
|---|---|
| Analyze imagery before the inspection | General map-reading/reconnaissance preparation |
| Divide the site into meaningful areas | Functional adaptation for systematic civilian inspection |
| Define information required in each area | General observation and reporting principles |
| Prefer safe observation before closer inspection | Civil robot-safety adaptation |
| Record time, position, photos and limitations | Evidence-quality requirement for this POC |
| Re-observe when glare reduces confidence | Environment-specific adaptation |

**Rule for the future DoctrineService:** distinguish the retrieved excerpt, exact source/page, interpretation, operator constraints and the resulting decision.

## Outputs

The final inspection report should identify, for each zone: coverage, findings, photographic evidence, available location accuracy, confidence and unresolved questions. It must distinguish observation from inference.

## MF-DoD implications

- **L4** interprets mission intent, identifies information gaps, tracks coverage and produces the report.
- **DoctrineService** returns relevant sourced excerpts when L4 requests them.
- **Existing memory** should retain mission goals, inspected areas, evidence and consulted sources.
- **Existing prompt framework** should compose stable level contracts with live mission context and doctrine; no site-specific prompt templates.
- **L3, L2 and L1** remain responsible for navigation guidance, local safety decisions and hardware control respectively.

## Open issues before implementation

- Verify the exact doctrine citations from the repository PDFs.
- Agree on the authorized site boundary and no-go areas.
- Confirm which entrypoint and GPT backend are active.
- Define the smallest L4 ↔ DoctrineService request/response contract.
- Specify minimal mission-memory records.
- Compare document-informed planning with a baseline in a **no-movement laboratory test**.

**Next:** technical design and minimum software implementation plan, using this manual walkthrough as input.
