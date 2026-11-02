# CognitiveOps

### Mission-first cognitive autonomy for unmanned ground vehicles

**From doctrine and mission intent to explainable, supervised robotic decisions.**

CognitiveOps is an experimental cognitive autonomy architecture built around a real unmanned ground vehicle (UGV). Its research question is straightforward:

> **Can an AI system understand a mission, use relevant doctrine and geographic context, decompose intent into objectives, supervise navigation, and adapt when the environment changes—without giving an LLM unchecked control of the motors?**

Rather than using an LLM merely to choose the next steering command, CognitiveOps places reasoning where it can have a greater effect: **L4 mission cognition and L3 task/navigation cognition**. These layers work with structured contracts, map-derived objectives, memory, and feedback from lower-level perception and control.

The project combines a physical rover platform, an experimental **Mission First / MF-DoD** cognitive architecture, and a traceable simulation and non-actuating field-test workflow.

> **Research status:** The L4 → L3 → L4 replanning loop has been demonstrated in simulation with GPT-5.4. The new live *manual shadow* integration has passed software tests but **has not yet been validated on the physical rover**. This is research software, not a field-qualified autonomous system.

---

## The idea: give the rover a mission, not a list of motor commands

A conventional navigation stack may receive a destination and calculate movement towards it. CognitiveOps explores a higher-level problem:

**What should the rover attempt, why does the objective matter, what evidence would establish success, and what should change when the original plan cannot be completed?**

For a representative **civilian airfield visual-inspection experiment**, an operator supplies:

- **Mission intent:** what needs to be observed or inspected.
- **Doctrine and guidance:** relevant reference material, concepts, and operational constraints to inform reasoning.
- **Mission Package:** site documents, WGS84 geospatial data, candidate points of interest (POIs), and declared exclusions.
- **Human approval:** which proposed objectives may proceed in the experiment.

L4 then proposes a mission-level plan. L3 manages the status of individual navigation tasks and can escalate problems back to L4. Lower layers provide navigation calculations, perception, constrained action selection, and—for the legacy physical rover—actuator interfaces.

**The LLM does not invent GPS coordinates or confer site-access permission.** In the current implementation, it selects documented POIs; the Mission Package resolves those POIs into coordinates when an operator approves the proposal.

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
              │ Monitor progress    │
              │ Interpret blockers  │
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
| **L3 — Task / Navigation** | Receive an objective; track navigation feedback; distinguish progress from failure; hold, request operator review, or escalate to L4 | **GPT-assisted exception handling and mission-aware task decisions** |
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

### L3: task cognition and escalation

L3 bridges mission intent and the conditions reported by navigation and perception. In the demonstrated simulation, a blocked navigation objective produced a structured L3 decision:

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
             POI → verified data lookup
                 (lat, lon, radius)
                         │
                 L4 objective order
                         │
                 L3 navigation task
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

**Coordinates and routes are different things.** The package contains map-derived target coordinates. The deterministic guidance layer can compute distance, bearing, and heading error from live GPS/attitude. A complete obstacle-aware route across terrain is **not** demonstrated by the L4/L3 simulation.

Likewise, **navigation arrival is not inspection success**: a candidate arrival must not be reported as verified visual evidence without an appropriate observation and assessment.

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

**Current integration gap:** real sensor observations have not yet been connected to a fully validated automatic L3-escalation / L4-replanning mission lifecycle.

---

## Research roadmap

1. **Validated real-time observation:** verify GPS/heading, camera/VisionNN, ultrasonic telemetry and timing in a stationary, de-energized physical setup.
2. **Sensor-to-cognition integration:** convert meaningful navigation/perception incidents into bounded L3 reviews, and route justified replanning requests to L4.
3. **Supervised manual field walkthrough:** observe real sensor changes while the human physically moves the rover, with **zero motor/servo power** and complete decision logs.
4. **Mission planning research:** test stronger doctrine attribution, mission memory, spatial reasoning, and the distinction between target selection and route planning.
5. **Simulation expansion:** visualize the L4 → L3 → L2/L1 architecture in Gazebo without prematurely replacing the project's control stack.
6. **Safety and deployment gates:** separately review operating permissions, physical interlocks, watchdogs, communications loss, geofence evidence, and emergency stop before **any** actuated cognitive integration.

See [Issue #16](https://github.com/jbruks/CognitiveOps/issues/16) for the current manual-shadow validation and [MF-DoD iteration closeout](docs/architecture/MF_DOD_ITERATION_CLOSEOUT_20261030.md) for prior results and limitations.

---

## Key implementation entry points

| Area | Files |
| --- | --- |
| L4/L3 simulation and replay | `mf_dod_integrated_agent.py`, `mf_dod_event_replay.py`, `mf_dod_telemetry_replay.py` |
| Mission package and geospatial validation | `mission_package.py`, `llombai_sim_package.py` |
| Doctrine and cognitive services | `doctrine_service.py`, `llm/llm_service.py` |
| Live manual shadow | `mf_dod_live_shadow.py`, `mf_dod_shadow_perception.py`, `mf_dod_shadow_sonar.py` |
| Rover perception and tactical layer | `perception_module.py`, `vision_nn_worker.py`, `l2_tactical_planner.py` |
| Existing physical control | `l1_rover_controler_ra4m1.py`, `ra4m1_rover_controller/` |
| Development documentation | `docs/architecture/` and GitHub Issues |

**Development branch:** [`feature/mf-dod-cognitive-architecture`](https://github.com/jbruks/CognitiveOps/tree/feature/mf-dod-cognitive-architecture). The `main` branch is intentionally left unchanged during this research iteration.

---

## Safety, scope, and license

CognitiveOps is an **experimental research demonstrator**. Model outputs, simulated approvals, map overlays, and software tests do not establish a safe or authorized physical operating envelope. A human operator retains authority over mission approval and physical testing. Do not connect experimental LLM outputs directly to actuator commands without independent engineering, testing, and safety controls.

Consult the repository for the applicable license terms; this README does not grant additional rights.
