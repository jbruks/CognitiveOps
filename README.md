# CognitiveOps

### Mission-first cognitive autonomy for unmanned ground vehicles

**From mission intent and operational doctrine to dynamically composed LLM reasoning, explainable objectives, and supervised robotic decisions.**

CognitiveOps is an experimental cognitive autonomy architecture built around a real unmanned ground vehicle (UGV). Its research question is straightforward:

> **Can an AI system understand a mission, use relevant doctrine and geographic context, decompose intent into objectives, supervise navigation, and adapt when the environment changes?**

Rather than using an LLM merely to choose the next steering command, CognitiveOps places reasoning where it can have a greater effect: **L4 mission cognition and L3 task/navigation cognition**. These layers work with structured contracts, map-derived objectives, memory, and feedback from lower-level perception and control.

The project combines a physical rover platform, an experimental **Mission First / MF-DoD** cognitive architecture, and a traceable simulation and non-actuating field-test workflow.

> **Research status:** The L4 → L3 → L4 replanning loop has been demonstrated in simulation with GPT-5.4. The new live *manual shadow* integration has passed software tests but **has not yet been validated on the physical rover**. This is research software, not a field-qualified autonomous system.

---

## The core differentiator: doctrine-driven cognition and prompts generated on the fly

**CognitiveOps is not primarily a waypoint follower with an LLM attached. Its central research proposition is that mission intent and doctrine can be turned into *situational, level-specific reasoning prompts* at runtime.** The rover should not need a separately hard-coded decision script for every site, mission, or unexpected event.

Two complementary ideas define the approach:

1. **Doctrine as operational reasoning context.** Mission-relevant manuals, principles, constraints, priorities and procedures are selected and supplied to the appropriate cognitive agent. Doctrine should influence *what matters*, *which evidence to seek*, *how to assess uncertainty*, and *when to escalate*—not act as an unchecked actuator command.
2. **Dynamic prompt composition.** Instead of treating one static prompt as the entire intelligence of the rover, CognitiveOps builds each L4/L3 request from the **current mission, relevant doctrine where wired in, site/map context, approved objectives, recent events, sensor/navigation feedback, and an explicit output contract**. The context changes when the mission or situation changes; a new prompt can therefore ask a different question at the correct cognitive level, without rewriting the navigation software.

This is the intended **Mission First → Doctrine → Context → Prompt → L4/L3 Decision → Feedback → Next Prompt** cycle:

```text
            MISSION INTENT + MISSION PACKAGE
                          │
      DOCTRINE / GUIDANCE + SITE / MAP CONTEXT
                          │
                          ▼
                CONTEXT ASSEMBLY
          objectives · constraints · memory
          GPS/heading · perception · incidents
                          │
                          ▼
                DYNAMIC L4 / L3 PROMPT
         level-specific task + allowed decisions
           relevant evidence + JSON contract
                          │
                          ▼
                   GPT REASONING
         L4: objectives / priorities / replanning
         L3: observation targets / incident review
                          │
                          ▼
           VALIDATION + HUMAN SUPERVISION
                          │
                          ▼
                   EVENT JOURNAL
                          │
                     new feedback
                          └──────────► next context
```

**Why this matters:** changing the mission, doctrine, or observed conditions should change the *reasoning context* and potentially the proposed plan, while the deterministic geospatial calculations, authorization boundaries and physical-control software remain stable. This separation is the core architectural hypothesis to test—not a claim that any prompt guarantees correct behavior.

### What is implemented, and what remains research

- **Implemented:** `DoctrineService` retrieves attributable excerpts from supplied references, including optional PDFs; `prepare_proposals` can pass retrieved doctrine/site/map evidence into L4 proposal generation. `PromptBuilderBase.compose_cognitive_context` supplies a bounded L3/L4 context structure for mission, constraints, recent events and L4 doctrine hits.
- **Implemented:** the map reconnaissance experiment constructs L4 and L3 requests at runtime using the **mission, site description, current image and current approved objective**; structured instructions and output schemas remain deliberately stable.
- **Implemented and tested:** the optional cognitive mission supervisor assembles fresh **incident-specific** L3 requests from the active objective, navigation/tactical state and remaining approved IDs; on escalation, it constructs an L4 replan request using the blocked objective, reason and approved remaining objectives. On 3 November 2026, GPT-5.4 returned `REQUEST_L4_REPLAN` and a valid L4 ordering for the synthetic Rural Crossroads incident.
- **Not yet demonstrated end-to-end:** automatic retrieval and injection of *mission-specific doctrinal passages into every live L3/L4 prompt*, measured causal influence of doctrine on decisions, and field-tested sensor-driven adaptive prompting. Some current experiments use fixed instruction scaffolds with **dynamic contextual inputs**, rather than synthesizing every instruction from scratch.

**Design principle:** *fixed safety/contract boundaries, adaptable reasoning context*. Prompts, doctrine retrieval and mission decisions must be auditable; operator authorization and motor control must never be inferred from LLM text.

---

## The idea: give the rover a mission and a doctrine (not a list of motor commands)

A conventional navigation stack may receive a destination and calculate movement towards it. CognitiveOps explores a higher-level problem:

**What should the rover attempt, why does the objective matter, what evidence would establish success, and what should change when the original plan cannot be completed?**

For a representative **civilian airfield visual-inspection experiment**, an operator supplies:

- **Mission intent:** what needs to be observed or inspected.
- **Doctrine and guidance:** relevant reference material, concepts, and operational constraints to inform reasoning.
- **Mission Package:** site documents, WGS84 geospatial data, candidate points of interest (POIs), and declared exclusions.
- **Human approval:** which proposed objectives may proceed in the experiment.

L4 then proposes a mission-level plan. L3 manages the status of individual navigation tasks and can escalate problems back to L4. Lower layers provide navigation calculations, perception, constrained action selection, and—for the legacy physical rover—actuator interfaces.

**Geospatial PoC status:** The separate map reconnaissance experiment now demonstrates L4-generated inspection objectives and L3-selected image observation points converted to WGS84 using deterministic georeferencing (Llombai and synthetic Rural Crossroads). These remain **offline, unverified proposals**, not permitted or traversability-checked physical destinations. The Mission Package POI-based path also remains available.

---

## Real doctrinal publications: from established practice to a usable product

**CognitiveOps already works with concrete, published doctrine—not invented rules or generic LLM prompts.** The repository includes local PDF reference material in [`docs/references/`](docs/references/) and a source catalogue in [`docs/references/readme.md`](docs/references/readme.md). These are *professional manuals and doctrinal publications*, not books authored by the CognitiveOps team.

| Real reference | Publisher / documented title | Practical CognitiveOps translation | Main level |
| --- | --- | --- | --- |
| **MCTP 3-01A — *Scouting and Patrolling*** | U.S. Marine Corps | Convert a reconnaissance mission into information requirements, observations and an ordered set of inspection objectives. | **L4** mission cognition |
| **FM 3-25.26 — *Map Reading and Land Navigation*** | U.S. Army | Interpret terrain and position, reason about direction, routes, navigation uncertainty and terrain association; translate mission objectives into geospatial tasks. | **L3** navigation, with L2 feedback |
| **ATP 3-20.98 — *Scout Platoon*** | U.S. Army | Connect reconnaissance purpose, collection priorities, terrain, observation and movement across the mission and task layers. | **L4 ↔ L3 ↔ L2** |

The local library also contains `MCRP 3-34.3 (W CH 1) (SECURED).pdf`. Its exact content and architectural contribution should be reviewed before presenting it as a validated doctrinal input. The broader [Reconnaissance Doctrine and Cognitive Framework](docs/CognitiveOps%20%E2%80%94%20Reconnaissance%20Doctrine%20and%20Cognitive%20Framework.md) additionally discusses *Ground Reconnaissance Operations*; that framework-level reference is not evidence that the exact publication is present in the local PDF library.

### Why this matters for a business-facing demonstrator

The link to real operational practice is **traceable**:

```text
PUBLISHED RECONNAISSANCE / NAVIGATION DOCTRINE
                        │
                        ▼
          MISSION AND INFORMATION NEED
                        │
                        ▼
           CONTEXT RETRIEVAL FROM PDFs
                        │
                        ▼
           L4 / L3 CONTEXTUAL PROMPTS
                        │
                        ▼
        SUPERVISED RECONNAISSANCE PLAN
                        │
                        ▼
         OBSERVATIONS / LOGGED REPLAN
```

For example, an operator can ask the system to **reconnoitre an area** rather than manually define every GPS destination. L4 can derive relevant observation objectives, while L3 selects candidate observation positions and reviews impediments. The doctrinal publications give the experiment a vocabulary and task structure already recognizable to professional users. That makes the prototype relevant to concrete **inspection, reconnaissance, terrain assessment and route-survey workflows**, rather than a generic AI robotics demo.

**Real software hooks exist:** `DoctrineService.from_pdf_paths()` extracts page-attributed passages from operator-supplied PDFs; `DoctrineService.retrieve()` selects relevant excerpts. `mf_dod_doctrine_experiment.py` compares L4 planning with and without retrieved doctrine, and `mf_dod_doctrine_v2.py` evaluates level-specific L4/L3 doctrinal advice and source-ID attribution. Both can use the PDFs checked into `docs/references/`. Source references and model outputs can be inspected; this is a *working research integration*, not merely a conceptual slide.

To reproduce the **non-actuating doctrine experiment** with the local PDF library (requires `pypdf`):

```bash
python -m mf_dod_doctrine_v2 --backend stub
# With a configured OPENAI_API_KEY, to test real LLM responses:
python -m mf_dod_doctrine_v2 --backend openai --model gpt-5.4 --allow-api
```

**Business-readiness boundary:** these references support domain relevance and a realistic demonstration story; they do **not** establish commercial maturity, compliance with doctrine, field reliability, or customer validation. The current live incident-replanning path has been tested with GPT-5.4 using dynamic situation context, but it does **not yet automatically retrieve and apply doctrinal passages on every L3/L4 decision**. Demonstrating measurable improvements attributable to doctrine and validating performance with end users are the next steps toward a deployable offering.

---

## Doctrine-grounded decision-making

**Doctrine is a first-class input to the cognitive architecture—not optional background reading or a decorative citation.** Mission intent defines *what* should be achieved; doctrine provides the principles, procedures, priorities and constraints that can guide *how* objectives are selected, interpreted and revised. A major research question is whether retrieving the right passages and placing them in the *right dynamically assembled prompt* materially improves L4/L3 decisions. The current system is instrumented to investigate this; such improvement has not yet been established empirically. The operator defines *what must be achieved*; doctrine provides the reference principles, procedures, priorities, and constraints that inform *how the mission should be approached*. This is central to the research value of the L4/L3 agents.

The reasoning flow is deliberately explicit:

```text
    OPERATOR MISSION              DOCTRINE / MANUALS
     (intent, goals)          (principles, procedures)
              \                    /
               \                  /
                MISSION PACKAGE + MAP
                         |
                         v
                  GPT L4 REASONING
              Objectives, priorities, plan
                         |
                         v
                  GPT L3 REASONING
            Navigation choices, exceptions
                         |
                         v
                L2 / L1 + FEEDBACK
                         |
                         v
               LOGGED DECISION CYCLE
```

**For example**, a manual may emphasize checking terrain accessibility and observation conditions before attempting an inspection. L4 can use relevant retrieved passages to justify mission objectives and priorities; L3 can use the applicable guidance, together with the map and live observations, when evaluating a route or requesting replanning. The doctrine is **context for decisions**, not a direct motor command or permission to operate.

The existing **DoctrineService** can retrieve excerpts from reference material, including operator-supplied PDFs, and make them available to mission planning with source identifiers. Structured traces let an experimenter inspect the mission input, reference material, model response, and resulting event. **The current PoC has demonstrated doctrine retrieval and L4/L3 replanning separately; it has not yet established that retrieved passages consistently influence decisions correctly or that citations prove doctrinal compliance.** Testing the quality and causal contribution of doctrine-grounded reasoning is an explicit research objective.

The architecture retains **one sequential, discrete decision loop** so the doctrinal context, LLM decisions, and sensor/control feedback can be examined cycle by cycle—without introducing a production-scale multi-agent framework.

---

## Cognitive architecture

```text
                   MISSION FIRST
     Operator intent · doctrine · site documents
            maps / GeoJSON · constraints
                         │
                         ▼
              ┌─────────────────────┐
              │ L4 — MISSION AGENT  │
              │ Interpret intent    │
              │ Propose objectives  │
              │ Sequence / replan   │
              └──────────┬──────────┘
                         │ approved, typed objectives
                         ▼
              ┌─────────────────────┐
              │ L3 — TASK AGENT     │
              │ Map / GPS targets   │
              │ Monitor progress    │
              │ Hold / escalate     │
              └──────────┬──────────┘
                         │ guidance + task context
                         ▼
              ┌─────────────────────┐
              │ L2 — TACTICAL       │
              │ Perception-informed │
              │ action proposals    │
              └──────────┬──────────┘
                         │ validated commands
                         ▼
              ┌─────────────────────┐
              │ L1 — CONTROL        │
              │ RA4M1 interface     │
              │ Physical actuation  │
              └──────────┬──────────┘
                         ▼
                      UGV / ROVER

      TRANSVERSAL: camera · VisionNN · GPS/heading
        ultrasonic · world model · memory · traces

      SUPERVISION: human approval · explicit limits
      SIMULATION / SHADOW: no physical actuation
```

**Four levels, different responsibilities.** Perception, memory, mission context, and traceability support the hierarchy; they are not an additional control level.

| Layer | Responsibility | Current research focus |
| --- | --- | --- |
| **L4 — Mission** | Interpret mission intent; propose goals linked to sources and mapped POIs; prioritize and replan within approved objectives | **GPT reasoning, doctrine/context retrieval, Mission Package, explainable replanning** |
| **L3 — Task / Navigation** | Receive an L4 objective; select destinations using georeferenced map data; calculate/validate GPS, bearing, distance and optional waypoints; monitor feedback and escalate exceptions | **Next PoC step: L3-generated destinations; synthetic GPT exception handling already tested** |
| **L2 — Tactical** | Combine navigation guidance with perception and propose constrained local actions | Existing deterministic tactical logic and camera/VisionNN integration; non-actuating shadow proposals |
| **L1 — Control** | Interface with the rover's low-level controller and actuators | Existing Raspberry Pi → Renesas RA4M1 physical stack; **not connected to the new cognitive shadow agent** |

### L4: mission reasoning grounded in supplied context

L4 is more than a GPS target selector. Its intended role is to transform a human mission into a **reviewable, evidence-linked set of objectives**, then adapt the plan when L3 reports an obstacle or other significant limitation.

The current experimental implementation can:

1. Read mission intent and site context from a **Mission Package**.
2. Retrieve excerpts from **DoctrineService**, including optional operator-supplied PDF references.
3. Present eligible georeferenced POIs and supporting source identifiers to the model.
4. Obtain structured **proposals**, including objective ID, POI, purpose, inspection question, and source references.
5. Validate proposals against known POIs and package geometry, then require **explicit operator approval**.
6. Sequence approved objectives and, after an L3 escalation, replan the **remaining approved objectives**.

**Important boundary:** Doctrine excerpts are contextual input, not independent authority. Source IDs and retrieved excerpts provide traceability, but they do **not** prove that a doctrinal citation substantively supports a specific decision. The usefulness of doctrine grounding is still being evaluated.

### L3: map reading, destination calculation, and task cognition

**Minimal planned extension:** L4 hands L3 a mission-level task, such as “find an observation position for the facilities.” L3 reasons over the existing georeferenced map and optional operator POIs, proposes a position or intermediate waypoints, and uses a small set of deterministic calculations to obtain WGS84 GPS coordinates, distance, and bearing. The calculated output, source map position, model decision, and validation result will be logged against the same sequential cycle. L3 should reuse its chosen destination across cycles unless there is a relevant event; no continuous LLM calls are required.

This is deliberately **not** a new agent hierarchy, service platform, or production route planner. A correctly converted coordinate does not establish terrain traversability; the map and live sensors may leave substantial uncertainty.

In the existing implementation, L3 bridges mission intent and the conditions reported by navigation and perception. In the demonstrated simulation, a blocked navigation objective produced a structured L3 decision:

```text
L3: REQUEST_L4_REPLAN
Reason: objective blocked by synthetic obstruction
```

This triggered an L4 request to reconsider the remaining objectives. L3 did not autonomously create a new destination or issue an unchecked motor command.

**Current boundary:** The completed L3 → L4 loop uses **synthetic navigation feedback**. The live manual-shadow runner currently handles uncertainty with advisory L3 calls; full sensor-event-driven L3/L4 replanning is the next integration step, not an already validated physical capability.

---

## What happens in a mission?

```text
Mission order + doctrine + site context + mapped POIs
                         │
                  L4 proposes goals
                         │
                 OPERATOR APPROVAL
                         │
                 L4 objective order
                         │
                 L3 navigation task
              Map reading / target proposal
              GPS conversion + validation
              Bearing / distance / waypoints
                         │
        navigation/perception feedback
                   ┌─────┴─────┐
               Progress      Blocked
                  │             │
                  ▼             ▼
             Next task    L3 requests L4
                               │
                          L4 replans
                         approved goals
                               │
                               ▼
                     Journal + report
```

**Coordinates and routes are different things.** Currently, the Mission Package resolves map-derived POI coordinates. The next PoC iteration moves target selection and coordinate calculation to L3, using the existing georeferenced map. Basic deterministic navigation computes distance, bearing, and heading error from live GPS/attitude; a complete obstacle-aware route across terrain is **not** demonstrated by the L4/L3 simulation.

Likewise, **navigation arrival is not inspection success**: a candidate arrival must not be reported as verified visual evidence without an appropriate observation and assessment.

---

## Experimental map reconnaissance: L4 recognizes, L3 locates (new lab PoC)

A separate **non-actuating experiment** (`mf_dod_map_recon_poc.py`) tests the minimal extension:

1. **L4** receives the short mission **“Reconnoitre the area”**, an aerial map preview and optional site context. GPT proposes up to four high-level observation goals based on *visible* features (possible runway, buildings, tracks). These remain hypotheses, not verified land-use classifications.
2. An **operator approves the objectives for offline analysis**.
3. **L3** examines the same map and proposes **pixel locations for observation points** for each objective.
4. Deterministic raster georeferencing converts the selected pixels to **WGS84 GPS coordinates**, with bounds and coordinate-system checks.
5. An append-only **JSONL journal** records inputs, L4 output, approval, each L3 output, GPS result and provider request IDs. **No physical actuation occurs.**

This is intentionally a **small, separate lab demonstrator**; it does not replace the existing sequential physical rover loop, wire the new destinations into the motor controller, estimate traversability, or establish reliable image interpretation. L4 feature recognition and L3 destination quality need real evaluation.

With `OPENAI_API_KEY` configured, Python packages `rasterio`, `numpy`, `Pillow`, and `openai` available, and a **correctly georeferenced** local GeoTIFF:

```bash
python -m unittest -v tests.test_mf_dod_map_recon_poc
python -m mf_dod_map_recon_poc \
  --map qgis_pr/llombai_airfield.tif \
  --context mission_packages/llombai_sim/site_context.txt \
  --mission "Reconnoitre the area" \
  --journal /tmp/cognitiveops_map_recon.jsonl
```

The local QGIS image is not tracked in the repository and must exist on the operator's workstation. GeoTIFF spatial reference and pixel transform must be verified independently; a calculated WGS84 value is **not** a safe or authorized navigation goal.

---

## Demonstration: Llombai mission replanning

The repo includes tooling for an experimental Llombai airfield inspection scenario. The local Mission Package consists of a manifest, site context, and GeoJSON candidate geometry.

A recorded **2 November 2026** workstation replay with GPT-5.4 produced:

| Event | Observed outcome |
| --- | --- |
| L4 mission proposal | Four candidate objectives based on supplied POIs |
| Operator gate | Four objectives approved **for simulation** |
| Synthetic event | `OBJ-001` blocked |
| L3 reasoning | `REQUEST_L4_REPLAN` |
| L4 replanning | Proceed with `OBJ-002 → OBJ-003 → OBJ-004`; exclude blocked `OBJ-001` |
| Final status | `FINISHED_WITH_LIMITATIONS` |
| Physical actuator actions | **0** |

Final objective states: `OBJ-001: INACCESSIBLE`; `OBJ-002`, `OBJ-003`, and `OBJ-004: UNVERIFIED`.

This demonstrates **structured cognitive handoff, escalation, replanning, and honest accounting of incomplete evidence**. It does **not** demonstrate obstacle detection by a physical sensor, autonomous terrain traversal, or successful real-world inspection. The replan retained the existing relative order of the three remaining objectives; it should not be described as optimized routing.

The Llombai map geometry is **approximate research/simulation data**, **not** a real authorization boundary, validated geofence, or permission to operate on the airfield.

### Reproduce the synthetic cognitive loop

With the Python environment and a locally prepared `mission_packages/llombai_sim/` directory:

```bash
python -m mf_dod_integrated_agent \
  mission_packages/llombai_sim/manifest.json \
  --backend openai \
  --model gpt-5.4 \
  --allow-api \
  --approve OBJ-001 OBJ-002 OBJ-003 OBJ-004 \
  --block-first \
  --journal /tmp/cognitiveops_llombai_events.jsonl \
  > /tmp/cognitiveops_llombai_report.json
```

Requires a configured API key and makes billable API calls. Proposal IDs may differ between runs, so **inspect proposed IDs first** rather than assuming the example IDs are always valid. The operator's `--approve` flag authorizes only the synthetic experiment, not physical movement.

To inspect results:

```bash
python -m json.tool /tmp/cognitiveops_llombai_report.json
```

The local `mission_packages/` and QGIS products may be untracked research assets; they are **not guaranteed to exist in a fresh clone**.

---

## Doctrine, memory, and evidence

The ambition of CognitiveOps is **mission-aware behavior**, not merely a chatbot attached to a robot.

- **DoctrineService** offers retrieved doctrine excerpts as context for agent proposals. Optional PDF ingestion enables controlled document experiments.
- **Mission Package** binds mission intent to site documents, structured geometry, eligible POIs, and explicit exclusions.
- **Typed L3/L4 contracts** separate proposed goals from navigation objectives and task results.
- **Memory and replay experiments** make historical mission events available for subsequent reasoning; their operational benefit is still under investigation.
- **Event journals and traces** expose proposal, approval, navigation feedback, escalation, and replanning decisions.
- **Validation and human gates** reject unknown POIs and unapproved objectives and keep the simulated cognitive workflow separate from actuator control.

External documents are treated as reference material, not commands. Provenance tracking supports audits; **factual grounding and appropriateness of cited doctrine still require review**.

---

## Physical rover and live shadow mode

CognitiveOps originated in a functioning rover stack and is not only a language-model simulation.

**Research hardware and software include:** an Axial SCX6 1/6 crawler, Raspberry Pi, Renesas RA4M1 controller, camera, GPS/phone-based positioning and heading, ultrasonic ranging, OpenCV, and a VisionNN perception worker.

Two distinct execution paths matter:

| Path | What it does | Status |
| --- | --- | --- |
| **Existing physical rover stack** | Legacy L1/L2 guidance and RA4M1 motor/steering interface | Historical physical tests and logs exist; unchanged by this cognitive iteration |
| **MF-DoD integrated agent** | L4/L3 mission experiments with synthetic navigation outcomes | Workstation-tested; no physical actions |
| **Manual live shadow** | Observe phone GPS/heading and optionally camera/VisionNN, tactical proposals, and sonar; operator moves rover by hand | **14/14 software tests passed; physical integration pending** |

The live shadow entry point is `mf_dod_live_shadow.py`. It never calls the existing L1 actuation interface. Optional sonar sends only `GET_DISTANCE` over serial; **opening a serial connection may reset a microcontroller**, so motor and servo power must be **physically isolated** before use. The shadow mode is observational and must not be treated as a safety-certified actuator interlock.

### RC-guided field test (planned, no software changes)

For the next physical field test, **the operator drives the rover using its existing RC transmitter**, following the navigation information displayed on the laptop. This replaces carrying the rover by hand during a manual-shadow walkthrough; it is **not** autonomous driving.

- **RC operator:** retains exclusive physical control of throttle and steering. Confirm the RC receiver/transmitter control path works as intended before driving; do not assume the shadow software provides an actuator interlock.
- **CognitiveOps:** runs `mf_dod_mission_runner.py` in its existing `--mode shadow`, reading phone GPS and heading and, when enabled, camera/VisionNN observations. The screen reports the current objective, navigation status, distance to target, target bearing, and tactical advice as available. These are **advisory**, not RC or motor commands.
- **Cognitive review:** the existing optional `--allow-api` mode can request GPT L3 review after persistent HOLD/uncertainty and GPT L4 replanning of remaining approved targets. Live GPS/perception-driven behavior has **not** yet been verified on the physical rover.
- **Logging:** per-cycle GPS, heading, navigation, perception, and available cognitive decisions go into the runner's JSONL output. Reaching a destination still requires explicit operator confirmation (`REACHED`); this does not verify an inspection.
- **No software-controlled actuation:** do **not** select `--mode motor` or `--motor-enable`. For a straightforward RC-driven test, omit `--ultrasonic` unless its read-only serial connection and the physical power/isolation arrangement have been checked separately; opening serial can reset the RA4M1.

The rover's motors **must be powered for RC driving**, unlike the earlier *hand-carried/de-energized* observation procedure. This is therefore a distinct supervised test: check RC authority, a clear authorized test area, and a reliable physical stop procedure before operation. Never use synthetic Rural Crossroads coordinates for a physical test; only separately verified, approved real-world destinations.

Existing console cycle output has the form:

```text
[1] OBJ-1 OBSERVING_MANUAL_MOTION distance=42.3 bearing=135.0 tactical=HOLD (motor=OFF)
```

The current console displays **target bearing**, not an explicit turn-angle instruction or graphical dashboard. No display or control changes are required for this test.

**Current integration boundary:** the event-triggered L3 → L4 path has passed mocked software tests and a live GPT-5.4 **synthetic incident replay**; it has not yet been demonstrated with real sensor feedback during RC-guided operation.

---

## Research roadmap

1. **Small L3 geospatial extension:** give L3 the georeferenced map and minimal coordinate/bearing calculations; allow model-proposed destinations beyond preset POIs, validate proposals, and record each input, LLM decision, and output in the existing **sequential, discrete debugging loop**. Keep L4 responsible for mission objectives and replanning; avoid new agents or production architecture.
2. **Validated real-time observation:** verify GPS/heading, camera/VisionNN, ultrasonic telemetry and timing in a stationary, de-energized physical setup.
3. **Sensor-to-cognition integration:** convert meaningful navigation/perception incidents into bounded L3 reviews, and route justified replanning requests to L4.
4. **RC-guided shadow field test:** operator drives using the original RC transmitter while the laptop displays the existing GPS, bearing, distance and advisory output; CognitiveOps remains in non-actuating shadow mode and records the cycles. Validate control separation and physical stopping before driving.
5. **Mission planning research:** test stronger doctrine attribution, mission memory, spatial reasoning, and the distinction between target selection and route planning.
6. **Simulation expansion:** visualize the L4 → L3 → L2/L1 architecture in Gazebo without prematurely replacing the project's control stack.
7. **Supervised powered rover trial:** only after stationary sensor checks, verified operating permissions, actuator/STOP behavior, watchdog and emergency-stop review; begin with a bounded single-goal test.

See [Issue #16](https://github.com/jbruks/CognitiveOps/issues/16) for the current manual-shadow validation and [MF-DoD iteration closeout](docs/architecture/MF_DOD_ITERATION_CLOSEOUT_20261030.md) for prior results and limitations.

---

## Key implementation entry points

| Area | Files |
| --- | --- |
| L4/L3 simulation and replay | `mf_dod_integrated_agent.py`, `mf_dod_event_replay.py`, `mf_dod_telemetry_replay.py` |
| Mission package and geospatial validation | `mission_package.py`, `llombai_sim_package.py` |
| Doctrine and cognitive services | `doctrine_service.py`, `llm/llm_service.py` |
| Live manual shadow and RC-guided display | `mf_dod_live_shadow.py`, `mf_dod_mission_runner.py`, `mf_dod_shadow_perception.py`, `mf_dod_shadow_sonar.py` |
| Event-triggered L3/L4 cognition and lab replay | `mf_dod_cognitive_supervisor.py`, `experiments/mf_dod_live_gpt_incident_replay.py` |
| Rover perception and tactical layer | `perception_module.py`, `vision_nn_worker.py`, `l2_tactical_planner.py` |
| Existing physical control | `l1_rover_controler_ra4m1.py`, `ra4m1_rover_controller/` |
| Development documentation | `docs/architecture/` and GitHub Issues |

**Development branch:** [`feature/mf-dod-cognitive-architecture`](https://github.com/jbruks/CognitiveOps/tree/feature/mf-dod-cognitive-architecture). The `main` branch is intentionally left unchanged during this research iteration.

---

## Safety, scope, and license

CognitiveOps is an **experimental research demonstrator**. Model outputs, simulated approvals, map overlays, and software tests do not establish a safe or authorized physical operating envelope. A human operator retains authority over mission approval and physical testing. Do not connect experimental LLM outputs directly to actuator commands without independent engineering, testing, and safety controls.

Consult the repository for the applicable license terms; this README does not grant additional rights.
