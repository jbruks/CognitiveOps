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

---

## Implementation work plan (proposed; not implemented)

**Development baseline:** `main`. This document is copied from the analysis branch as the reviewed functional baseline; the original is preserved there. Follow-up code work should use short-lived branches based on `main` and merge through reviewed pull requests.

### WP0 — Establish the verified baseline
- Compare `main` with current field-tested entrypoint and actual GPT provider.
- Identify the active L4, L3, L2, L1, perception, memory, logging and prompt paths; separate historical stubs from the active runtime.
- Record smoke tests and avoid altering the validated movement/safety loop.
- **Done when:** dependencies, entrypoint and baseline tests are documented.

### WP1 — Minimal mission contract and L4 reasoning (no movement)
- Accept a natural-language **civil inspection** objective together with site constraints and capabilities.
- Represent mission intent, observation subjects (Z1–Z5), evidence requirements and progress state.
- Produce a human-reviewable plan without hard-coded inspection-specific prompts.
- **Done when:** an offline test produces a coherent bounded plan and identifies missing inputs.

### WP2 — DoctrineService: on-demand, source-grounded retrieval
- Use the **DoctrineService** name consistently; it is a retrieval/reference service, not a mission authority.
- Start with the two existing manuals in `main/docs/references`, using a simple local text index and exact page/source metadata.
- L4 formulates its own questions; DoctrineService returns a small set of relevant excerpts and provenance.
- Treat document contents as untrusted reference data; do not execute embedded instructions.
- **Done when:** a lab run shows relevant citations and distinguishes source statements from system interpretation.

### WP3 — Reuse mission memory and prompt framework
- Inspect and extend `memory_system.py` and `llm/memory_formatter.py` rather than replacing them.
- Store mission state, consulted citations, observations, uncertainties and decisions; add simple persistence only if necessary.
- Extend `llm/prompt_framework.py` and L4 prompt composition to combine stable interfaces with mission + state + memory + doctrine.
- **Done when:** L4 can revisit a partially completed inspection without losing its documented state.

### WP4 — Plan/report validation in a laboratory
- Compare the same inspection brief **with versus without** DoctrineService retrieval.
- Check provenance, site-constraint compliance, uncertainty handling, token usage and latency.
- Produce a structured per-zone report, even when observations are simulated or unavailable.
- **Done when:** outputs are reproducible, inspectable, and do not invent measurements.

### WP5 — Optional supervised field integration
- Only after WP0–WP4: connect approved inspection tasks to the existing navigation interface.
- Validate permitted areas, observation positions, routes, physical stop capability and club flying restrictions **on site**.
- Keep L1 safety behavior and operator authority unchanged.
- **Done when:** limited supervised trials produce useful evidence and can terminate safely.

### Priorities and non-goals

**Minimum POC:** WP0–WP4. WP5 is a separate validation decision.  
**No-go for first POC:** multi-agent orchestration, vector database by default, continual model training, autonomous authority changes, weapon-related behaviors, or rewriting L1–L3.

### Source and branch note

The original analysis branch `analysis/doctrine-use-cases-20261022` contains a broader collection of 13 PDFs and earlier MF-DoD iterations; **`main` currently contains four doctrine PDFs**, including MCTP 3-01A and FM 3-25.26. Do not assume the additional references are available on `main` until selectively copied and reviewed.

### Next decision

Begin with **WP0**: inspect the actual code paths on `main` and agree on the smallest L4 ↔ DoctrineService interface *before* writing application code.
