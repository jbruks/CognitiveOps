# CognitiveOps — RECON-1KM
## Doctrine-Guided Autonomous Terrain Reconnaissance
*Map-assisted mission planning, autonomous execution, and evidence-based terrain reporting*

| Field | Value |
|---|---|
| Document | Experimental Mission Proposal |
| Version | **0.2 — October 15, 2026** |
| Status | **Proposed; the new mission-planning and reconnaissance workflow has not been implemented or field-validated** |
| Preparation window | Approximately three weeks |
| Platform | Axial SCX10 II 4×4, Raspberry Pi, front camera, GPS |
| Repository | https://github.com/jbruks/CognitiveOps |
| Proven baseline | `fieldtest-2026-10-15-goto-point-success` |

> **Mission concept:** Provide CognitiveOps with a start point **A**, a destination **B** approximately 1 km away, and a **georeferenced map**. L4 uses a small, source-traceable set of doctrine-derived planning and observation guidelines to propose a few navigation segments. The rover executes them using existing navigation and perception capabilities, collects terrain observations, and produces a report grounded in recorded evidence.

## 1. Executive Summary

CognitiveOps is an experimental cognitive-autonomy system for a small unmanned ground vehicle. Its four-layer architecture separates mission management (L4), guidance (L3), tactical maneuver selection (L2), and actuator control (L1), with visual perception and a world model providing environmental context.

On October 15, 2026, CognitiveOps completed a `GO_TO_POINT` field trial according to its GPS arrival criterion [E1]. **RECON-1KM** extends that baseline into a more complete, realistic mission workflow:

1. **PLAN:** L4 interprets the goal and map, applies concise doctrine-derived guidelines, and creates a small set of executable segments.
2. **EXECUTE:** L4 runs those segments sequentially through the existing `GO_TO_POINT` mechanism; L3–L1 and perception handle local navigation.
3. **OBSERVE:** The system records terrain information relevant to reconnaissance, using categories derived from the referenced publications and adapted to rover sensors.
4. **REPORT:** An evidence-based post-mission report summarizes the route actually traveled, observations, outcomes, and uncertainty.

The purpose is to demonstrate **knowledge-informed mission decomposition and physical execution** without building a general Cognitive Runtime, full-document RAG, SLAM, or dynamic global replanning. This is an **unarmed, civilian-safe, supervised field-robotics experiment**. A 1 km completion is the target, **not an established capability**.

## 2. CognitiveOps: Current Status

### 2.1. Physical Platform and Architecture

The rover uses an Axial SCX10 II 4×4, Raspberry Pi, low-mounted front-facing camera, and GPS. Front-facing perception evaluates visible terrain; GPS estimates position and direction toward a destination. Both are uncertain and neither guarantees route traversability.

| Component | Existing role |
|---|---|
| **L4 — Mission Management** | Receives and supervises the mission objective |
| **L3 — Guidance & Navigation** | Computes guidance toward the active GPS target |
| **L2 — Tactical Planning** | Selects local movements based on guidance and perception |
| **L1 — Actuator Control** | Executes actuator commands |
| **Perception / World Model** | Interprets images and maintains available environmental context |

### 2.2. Demonstrated Field Baseline — October 15, 2026

| Metric | Observed result |
|---|---:|
| Mission | `GO_TO_POINT` |
| Initial GPS distance to destination | 45.24 m |
| Final GPS distance to destination | 4.86 m |
| Reported final GPS accuracy | ~2.39 m |
| Execution cycles | 185 |
| Duration | ~30 min 6 s |
| Forward movements | 134 |
| Reverse movements | **26, without rearward perception** |
| Result | Arrival according to the configured GPS criterion |

This demonstrates successful integration in one field test, **not** validated map-based planning, autonomous route discovery, comprehensive terrain reporting, or 1 km endurance. Slow effective progress, GPS variability, temporary unavailable guidance, and blind reversing require attention. Preserve the baseline tag and make any changes separately and traceably [E1–E2].

## 3. Operational and Doctrinal Rationale

Reconnaissance of a route or terrain corridor is a real-world information-gathering task: determine conditions affecting movement, identify visible restrictions, and communicate observations. **Reaching a destination alone is not a reconnaissance result.**

| Publication | Role in RECON-1KM | Scope of adaptation |
|---|---|---|
| **ATP 3-20.98 — *Reconnaissance Platoon*** [D1] | Mission purpose and reporting of route conditions | Reconnaissance concepts, **not** replication of a military unit |
| **ATP 3-34.81 / MCRP 3-34.3 — *Engineer Reconnaissance*** [D2] | Mobility restrictions, visible obstacles, and terrain-condition observations | Visual, rover-relative assessment, **not** certified route classification |
| **FM 3-25.26 — *Map Reading and Land Navigation*** [D3] | Positions, direction, route context, and navigation references | GPS/map-based adaptation, **not** implementation of all manual techniques |

**Doctrinal boundary:** The manuals provide concepts for route reconnaissance, land navigation, and observation. **The three-segment mission structure, L4 orchestration, JSON schemas, and sensor-specific categories are CognitiveOps engineering choices.** They must not be presented as prescriptions from those publications. Exact passages, editions, and page references will be verified against the locally archived PDFs before formal attribution.

The map gives L4 prior geographical context; **the actual condition and traversability of the route remain to be checked in the field**. This is a map-assisted reconnaissance mission, not pure exploration from two coordinates alone.

## 4. Scientific and Technical Foundation

Terrain traversability assessment, autonomous ground navigation, and perception in unstructured environments are established field-robotics research areas [S1–S3]. RECON-1KM combines these problems with a deliberately small knowledge-to-action workflow.

A front-facing camera cannot reliably establish soil bearing capacity, hidden obstacles, exact slopes, or conditions beyond its field of view. GPS observations have finite accuracy. Reports must therefore distinguish **observed**, **inferred**, **actually traversed**, and **unknown** conditions; no visual assessment should be represented as a certified engineering measurement.

## 5. Mission Definition

### 5.1. Inputs and Environment

**Required inputs:** starting position **A**, destination **B** (approximately 1 km away), and a **georeferenced map** containing sufficient information to locate proposed intermediate objectives. Mission limits and the authorized operating area are safety inputs.

The experiment takes place in relatively simple, authorized, supervised rural terrain with mild slopes, manageable obstacles, good GPS reception, and no traffic. The test team may know the area for safety purposes, but **the rover receives no manually prepared waypoint sequence**.

The map may be a georeferenced raster or geographic route data. **An unreferenced screenshot alone is insufficient to safely generate GPS waypoints.** Any model-proposed waypoint must be converted using valid map coordinates and checked deterministically.

### 5.2. Mission Order

> Plan and attempt a terrain reconnaissance mission from A to B using the supplied map and approved doctrine-derived guidelines. Divide the mission into a small number of executable navigation segments (initial target: **up to three**). Execute the segments sequentially, observe terrain conditions throughout the journey, preserve supporting evidence, and produce a report. Stop safely if navigation, sensing, or operating conditions become unacceptable.

### 5.3. Mission Objectives

| ID | Objective | Evidence |
|---|---|---|
| **OBJ-01** | L4 generates a segment plan from A, B, and the map | Saved plan and map provenance |
| **OBJ-02** | Planning uses verified doctrine-derived guidance | Guideline IDs and planning trace |
| **OBJ-03** | L4 executes segments sequentially using existing navigation | Segment state transitions and control logs |
| **OBJ-04** | Terrain observations follow a defined reconnaissance schema | Timestamped observations and supporting images/logs |
| **OBJ-05** | Rover makes autonomous progress or stops safely | GPS trajectory, safety and intervention log |
| **OBJ-06** | Produce a traceable final reconnaissance report | Report linked to raw evidence |

**Excluded:** guaranteed 1 km arrival; autonomous discovery of complex road networks; global optimal routing; automatic replanning after blocked routes; SLAM; certified engineering assessment; surveillance of persons; armed operations; unsupervised testing.

## 6. Doctrine-Guided Planning, Execution, and Observation

### 6.1. End-to-End Workflow

```text
             MISSION REQUEST
         Start A + Goal B + Map
                    |
                    v
          L4 MISSION PLANNER <---- Verified doctrine-derived guidelines
                    |             (planning + observation requirements)
                    v
            VALIDATED PLAN
         S1: A -> P1
         S2: P1 -> P2
         S3: P2 -> B
                    |
                    v
          L4 SEGMENT EXECUTOR
                    |
          Existing GO_TO_POINT
                    |
        L3 guidance -> L2 tactics -> L1 control
                    ^                 |
                    |                 v
             Front perception <- Rover movement
                    |
                    v
           RECON OBSERVATION LOG
                    |
                    v
          OFFLINE MISSION REPORT
```

**The planner may propose fewer than three segments.** Three is a demonstration configuration, not a universal rule. Intermediate objectives are generated by L4, not supplied by the operator. The plan must be validated **before any movement**.

### 6.2. Minimal Doctrine Knowledge Profile

A short, version-controlled **reconnaissance knowledge profile** will be prepared from verified passages of [D1–D3]. It will contain two types of guidance:

**Planning guidance:** use identifiable, geographically valid intermediate objectives; relate segment goals to available map information; retain a clear final destination; consider rover limitations; define explicit completion and abort conditions.

**Observation guidance:** observe and report surface characteristics, visible obstacles, possible mobility restrictions, route continuity, and location uncertainty. Maintain the same core categories throughout all segments.

The profile will identify **source document, edition, page/section once checked, principle, and CognitiveOps adaptation**. A source label in a prompt or JSON field **is not sufficient proof** that a model applied that source. Preserve the actual guideline text given to L4 and the resulting planning decisions.

**Minimal implementation:** a curated Markdown or structured profile loaded into the L4 planning context. **No PDF retrieval at runtime is required.**

### 6.3. Structured Mission Plan

Illustrative output (**P1/P2 are placeholders, not coordinates**):

```json
{
  "mission_id": "RECON-1KM",
  "planning_mode": "map_assisted_doctrine_guided",
  "map_reference": "<verified-georeferenced-map-id>",
  "guideline_profile": "<versioned-profile-id>",
  "segments": [
    {"id": "S1", "from": "A",  "to": "P1", "task": "GO_TO_POINT"},
    {"id": "S2", "from": "P1", "to": "P2", "task": "GO_TO_POINT"},
    {"id": "S3", "from": "P2", "to": "B",  "task": "GO_TO_POINT"}
  ],
  "observation_profile": "terrain_recon_v1",
  "doctrine_guideline_ids": ["<verified-guideline-id>"]
}
```

Before execution, deterministic checks must confirm valid coordinates, correct map projection/georeferencing, allowed-area boundaries, segment count, supported task type, and **B as the final objective**. An LLM must not invent or directly execute unchecked geographic coordinates.

### 6.4. Reconnaissance Observation Requirements

The following is a **proposed rover-specific schema inspired by the manuals**, not a verbatim doctrinal reporting form:

| Field | Intended observation | Limits |
|---|---|---|
| `surface` | Visible gravel, compact soil, grass, mud-like appearance, etc. | Visual appearance only |
| `traversability` | `PASSABLE`, `RESTRICTED`, `BLOCKED`, `UNKNOWN` | Relative to rover and available evidence |
| `visible_obstacles` | Stones, branches, vegetation, apparent ruts/ditches | Only if visible and reasonably supported |
| `terrain_condition` | Unevenness, apparent erosion, loose surface | No unmeasured physical properties |
| `route_continuity` | Visible continuation, interruption, unknown | Limited to observed field of view |
| `position` | GPS position and accuracy when available | Approximate, not exact obstacle geolocation |
| `evidence` | Image/log reference, timestamp, segment ID | Must resolve to an actual record |
| `confidence` | Supported confidence/uncertainty marker | Use `UNKNOWN` where evidence is insufficient |

Navigation and reconnaissance should preferably share **the existing perception result**. Preserve the current L2 input contract; first inspect the VLM output and parser, then add non-breaking logging or post-processing. **Do not promise observations that the present logs cannot support.**

A minimal JSONL observation record could look like this (illustrative, with no fabricated coordinates):

```json
{
  "mission_id": "RECON-1KM",
  "segment_id": "S2",
  "timestamp": "<recorded-time>",
  "gps": {"latitude": null, "longitude": null, "accuracy_m": null},
  "surface": "gravel",
  "traversability": "UNKNOWN",
  "visible_obstacles": ["small_stones"],
  "route_continuity": "VISIBLE",
  "confidence": "MEDIUM",
  "image_ref": "<actual-image-reference>"
}
```

### 6.5. Segment Execution and Mission Reporting

L4 activates S1, waits for its actual `GO_TO_POINT` outcome, records the segment result, and proceeds to S2 only when S1 meets the validated completion criterion. On failure, unsafe conditions, or loss of essential sensing, **stop and preserve partial results**. No automatic global replanning is included in this phase.

An **offline** report generator will assemble:

1. Mission inputs, map provenance, knowledge-profile version, and generated plan.
2. Planned versus executed segments, with status and human interventions.
3. GPS trajectory, duration, progress, and uncertainty.
4. Terrain observations linked to timestamps, approximate positions, and evidence.
5. Obstacles, restrictions, unknown areas, and sensor limitations.
6. Final outcome: `COMPLETED`, `PARTIAL`, or `ABORTED`.

The report must cover **the path actually observed**, not claim that the full map corridor or untraveled route was inspected.

## 7. Minimal Implementation Scope

**Engineering rule:** inspect the actual L4 runner and perception interfaces first; preserve the proven baseline; implement small, testable changes; dry-run with motors disconnected before field deployment.

| Item | Plan | Priority |
|---|---|---|
| Existing L3/L2/L1, GPS, `GO_TO_POINT` | Reuse unchanged if interfaces allow | Essential |
| Georeferenced map input | Choose one simple, verifiable format | Essential |
| Curated doctrine knowledge profile | Verify relevant manual passages; store source links | Essential |
| L4 plan generation | Generate at most three segments from A/B/map/profile | Essential |
| Deterministic plan validation | Reject invalid, unsafe, or unsupported waypoints | Essential |
| Sequential segment executor | Reuse `GO_TO_POINT`, track outcomes | Essential |
| Reconnaissance observation capture | Reuse existing perception/logs; minimal extension only if needed | Essential |
| Offline report generator | Assemble evidence and limitations | Essential |
| Blind reversing and emergency stop | Review and address safety risks | Essential |
| Stagnation/time limits | Add only if not already covered | Conditional |
| Cognitive Runtime, full RAG, memory, SLAM, replanning | Defer | Out of scope |

**Effort warning:** Segment sequencing may be small; **map interpretation, valid coordinate extraction, and VLM/log compatibility are the uncertain parts**. They must be scoped after inspecting the code and chosen map format. This document is a proposal, not a claim that these features already exist.

## 8. Experimental Validation and Success Criteria

### 8.1. Hypothesis

> CognitiveOps can use a compact, traceable doctrine-derived knowledge profile to generate and validate a short map-assisted reconnaissance plan, execute its segments with existing navigation capabilities, and produce an evidence-based terrain report in a simple, supervised rural environment.

### 8.2. Test Progression

| Stage | Distance | Primary validation |
|---|---:|---|
| P0 | No vehicle motion | Profile, plan generation, coordinate validation, sequential state-machine dry run |
| P1 | 50 m | One-segment baseline and observation logging |
| P2 | 100–150 m | Multi-segment handoff and report generation |
| P3 | 300 m | Sustained progress and segment completion |
| P4 | 500 m | Time, power, sensing, and reliability |
| P5 | 1,000 m | Full target demonstration, if earlier stages permit |

The prior 45 m destination test took approximately 30 minutes. **Feasibility of a 1 km trial within practical time and energy limits remains unproven.**

### 8.3. Evaluation Metrics

**Planning:** valid plan generated; segment count; waypoint/map consistency; guideline-profile provenance; rejected plans; operator corrections.

**Execution:** completed segments; GPS distance and accuracy; elapsed time; progress rate; stops/reverses; perception and guidance availability; interventions; termination reason.

**Reconnaissance:** count and coverage of evidence-backed observations; missing/unknown values; image/log traceability; report completeness; observed versus inferred classifications.

**Outcomes:**

- **Completed:** validated segments executed and final GPS criterion reached, with a report linked to evidence and no unacceptable safety event.
- **Partial:** some valid segments/progress/observations obtained, but B not reached.
- **Aborted:** terminated due to safety, technical failure, or operator intervention; partial evidence retained.

A generated plan alone is **not proof of doctrinal reasoning**; an arrival fix alone is **not proof of systematic reconnaissance**. Both require inspectable records.

### 8.4. Safety and Boundaries

Operate only in authorized areas under human supervision, with a reliable emergency stop, communications, defined operating boundaries, and a recovery plan. Avoid traffic, people, water, drop-offs, and terrain with unacceptable uncertainty. Do not rely on a front camera for rearward clearance. If essential perception/guidance is unavailable or progress cannot be established safely, stop rather than improvise an unvalidated maneuver.

## 9. Three-Week Plan and Deliverables

| Period | Focus | Output |
|---|---|---|
| **Week 1** | Inspect existing code/logs; select map format; verify relevant doctrine passages; create profile and dry-run plan | Minimal valid plan and traceable guidelines |
| **Week 2** | Add segment sequencing and observation logging/reporting with minimal changes; test 50–300 m | Verified plan-to-execution-to-report chain |
| **Week 3** | Extend distance if safe; run best achievable trial; capture video and evidence | Demonstration, metrics, report, limitations |

**Deliverables:** versioned knowledge profile; mission request and map reference; generated/validated mission plan; software commit/tag; segment execution logs; GPS trajectory; perception/evidence records; reconnaissance report; video; list of limitations and interventions.

**Fallback demonstration:** If 1 km is not feasible, show a shorter **fully evidenced end-to-end mission**, rather than claiming unverified range.

## 10. Future Evolution: Cognitive Runtime

The mission is a stepping stone toward general cognitive resources: working/episodic/spatial/procedural memory, task management, capability registry, retrieval from complete technical publications, and adaptive replanning. None is required for this experiment. Deterministic safety and capability validation must remain independent of model-generated plans.

## 11. References and Traceability

### Doctrine

- **[D1]** Department of the Army. *ATP 3-20.98 — Reconnaissance Platoon* (2013). Verify local edition and page references before detailed attribution.
- **[D2]** *ATP 3-34.81 / MCRP 3-34.3 — Engineer Reconnaissance*, with Change 1. Local reference: `docs/references/MCRP 3-34.3 (W CH 1) (SECURED).pdf`. Verify cover, revision, and relevant passages.
- **[D3]** Department of the Army. *FM 3-25.26 — Map Reading and Land Navigation*. Verify local edition and relevant passages.

### Field Robotics

- **[S1]** Borges et al. (2022). *A Survey on Terrain Traversability Analysis for Autonomous Ground Vehicles*. *Field Robotics*. https://doi.org/10.55417/fr.2022049
- **[S2]** Beycimen, Ignatyev, and Zolotas (2023). *A Comprehensive Survey of Unmanned Ground Vehicle Terrain Traversability for Unstructured Environments and Sensor Technology Insights*. https://doi.org/10.1016/j.jestch.2023.101457
- **[S3]** *Terrain Traversability Analysis Methods for Unmanned Ground Vehicles: A Survey* (2013). https://doi.org/10.1016/j.engappai.2013.01.006

### CognitiveOps Evidence

- **[E1]** October 15, 2026, `GO_TO_POINT` field trial: `goto_test_nav_cam_sol11_500tokens.log`; `docs/field_tests/2026-10-15_goto_point_success/REPORT.md`.
- **[E2]** https://github.com/jbruks/CognitiveOps — tag `fieldtest-2026-10-15-goto-point-success`.

**Source-integrity note:** This proposal identifies **conceptual links**, not verified verbatim quotations or specific paragraph citations. The knowledge profile must not be labeled doctrine-derived until the exact relevant passages in the archived manuals have been reviewed and referenced. Bibliographic metadata should be checked before external distribution.

---

## Conclusion

**RECON-1KM now tests an end-to-end cognitive mission workflow:** **receive objective and map → apply verified doctrine-derived guidelines → plan and validate segments → execute with existing autonomy → collect reconnaissance observations → produce an evidence-based report**.

The intended innovation is modest in code but meaningful in system behavior. The experiment remains constrained by proven rover capabilities, safe operation, transparent evidence, and a three-week development window.
