# MF-DoD — Current Runtime Baseline and Integration Inventory

**Issue:** [#3 — Baseline and development workflow](https://github.com/jbruks/CognitiveOps/issues/3)  
**Date:** 2026-10-29  
**Status:** Code inspection completed; runtime smoke tests and device checks **not executed**  
**Working branch:** `feature/mf-dod-cognitive-architecture`  
**Inspection basis:** repository code on the feature branch derived from `main` at `24e84cd` (physical baseline parent `fe09e70`)

## 1. Scope and constraints

This document inventories the current implementation and identifies reuse points and integration risks for a future mission-driven cognitive skeleton. It is **not** a redesign or an implementation. No rover movement or hardware test was performed as part of this review.

References:
- [MF-DoD Iteration 3 — RC Airfield Inspection](../MF_DOD_ITERATION_03_AIRFIELD_USE_CASE.md)
- [MF-DoD Architecture Design Decisions](MF_DOD_DESIGN_DECISIONS.md)
- [EPIC #2](https://github.com/jbruks/CognitiveOps/issues/2)

## 2. Version control baseline

| Reference | Revision / path | Meaning |
|---|---|---|
| Validated physical code | `fe09e70` | US05-integrated hardware and L1/L2 stack |
| Cognitive planning starting commit | `24e84cd` | Same runtime with MF-DoD use-case documentation |
| Permanent physical tag | `baseline/rover-functional-20261029` | Recovery reference |
| Permanent planning tag | `baseline/mf-dod-start-20261029` | Recovery reference |
| Development branch | `feature/mf-dod-cognitive-architecture` | All new cognitive work |
| Primary worktree | `~/RoverGit` | Local `main`; observed at `fe09e70` |
| Development worktree | `~/RoverGit-mf-dod` | Feature branch |

**Note:** at the time of worktree verification, local `main` remained at `fe09e70` although `origin/main` had advanced to `24e84cd`. This is not a runtime regression; synchronize intentionally when required. The documentation commit on the feature branch will advance it beyond the starting commit.

## 3. Confirmed entrypoint and call graph

**Field-test entrypoint:** `guidance_demo_goto_point.py`.

The entrypoint accepts `target_lat`, `target_lon`, `--radius`, `--autonomous`, `--perception-max-tokens`, `--no-camera`, and `--ultrasonic-only`. It creates the real RA4M1 controller and prepares it **before** it builds the perception, planners and mission. Consequently this entrypoint is **not safe for no-movement skeleton tests** without an explicit mock/adaptation.

Actual construction path:

```text
guidance_demo_goto_point.py
  L1RoverControler(serial device) → connect_and_prepare()
  PerceptionModule(camera | simulated)
  L2TacticalPlanner(L1, PerceptionModule, WorldBuilder, ...)
  MemorySystem()
  L3TaskPlanner(L2, PerceptionModule, MemorySystem)
  Mission(task=GOTO, GPS target, arrival radius)
  L4MissionPlanner(L1, PerceptionModule, L3, MemorySystem, Mission)
  while mission not completed:
      L4.step()
      wait 3 seconds
      L1.stop()
  finally: L1.stop()
```

Observed in `L4MissionPlanner.step()`:

```text
L1.get_state()
L1.get_front_sensor_state()            # diagnostic sample
PerceptionModule.observe_llm()
Mission.status = ACTIVE
L3TaskPlanner.step(state, perception, mission)
  PhoneAttitudeService.read()
  PhonePositionService.read()
  build_navigation_state()
  plan_guidance()                     # deterministic GPS/heading
  if guidance HOLD: return
  adapt GuidanceTask → existing L2 task dict
  L2TacticalPlanner.step(...)
    L1.get_front_sensor_state()         # pre-action safety data
    sensor fusion / tactical decision
    L1.execute_tactical_action(...)
  MemorySystem.update_step(...)
  possible L3 blockage advice
L4 checks GuidanceTask for arrival
L4 optionally stores image from current cycle
```

**Important coupling:** L2 currently issues physical actions directly through the injected rover client. L4 also calls L1 directly for state, diagnostic sampling and STOP. The next skeleton must mock at the **physical controller boundary**, preserving existing call paths where possible.

**Important feedback gap:** L3 returns an action, while L4's completion logic primarily checks Guidance HOLD and remaining distance. This is not yet a general mission-objective lifecycle or rich upward result contract.

## 4. Component inventory and reuse decisions

| Module | Verified responsibility / behavior | Plan for skeleton |
|---|---|---|
| `guidance_demo_goto_point.py` | CLI and end-to-end physical GO_TO_POINT loop; connects real RA4M1 | Preserve as physical baseline; add isolated no-movement test harness later |
| `l4_mission_planner.py` | Reads L1 state/perception, dispatches L3, checks GPS arrival, records images; `call_llm_for_task` returns `EXPLORE` | Reuse planner; evolve mission/feedback interfaces in Issue #4/#9 |
| `l4_models.py` | Small dataclasses/enums for mission task/status | Extend minimally for mission intent/objective state |
| `l3_task_planner.py` | Phone GPS and attitude; deterministic Guidance; L2 adapter; navigation history; repeated-block advice | Preserve guidance; expose clearer navigation result contract |
| `l3_models.py` | Task and Guidance types | Reuse; add explicit statuses only as needed |
| `l2_tactical_planner.py` | Sensors, tactical actions, recovery, optional human approval, direct L1 execution | Preserve tested deterministic behavior initially; mock rover client |
| `l1_rover_controler_ra4m1.py` | Serial RA4M1 transport, state, arming, motor commands, front sensor | No behavior changes during skeleton; mock the interface |
| `perception_module.py` | Camera/simulated perception; VisionNN integration; results; OpenAI client path | Reuse simulated perception for lab, avoiding hardware initialization |
| `vision_nn_worker.py` | Neural perception worker, including depth/terrain analysis | Leave unchanged during skeleton |
| `memory_system.py` | Recent steps plus task and mission contexts | Extend rather than replace |
| `llm/memory_formatter.py` | Builds level-specific memory context | Reuse where compatible |
| `llm/prompt_framework.py` | Small base prompt builder | Evolve generic contracts |
| `llm/llm_service.py` | **Stub** responses for tactical/task/mission | Do not mistake for production GPT adapter |
| `llm_decision.py` | `TacticalLLMDecisionMaker`, OpenAI / Ollama / stub backends | Review before consolidating under one service |
| `decision_validator.py` | Tactical response parsing/validation | Preserve safeguards; inspect where invoked |
| `config.py` | LLM toggles, backend `openai`, model `gpt-5.4` in inspected revision | Treat as configuration, not proof of active provider path |

## 5. Current GPT/inference reality

There is **not yet one unified inference implementation**.

- `llm/llm_service.py` returns constant responses and is effectively a placeholder.
- `llm_decision.py` contains a real provider adapter (`openai`, `ollama`, or `stub`).
- `perception_module.py` imports the OpenAI SDK and exposes a client used by current perception paths.
- `l3_task_planner.py` invokes `self.perception.llm_client.responses.create(...)` directly for blockage advice (one request after three blocked cycles), rather than using `LLMService`.
- `l4_mission_planner.py` has a placeholder `call_llm_for_task` returning `EXPLORE`.
- `l2_tactical_planner.py` contains a GPT decision method, but the inspected active `decide_action` path is documented as deterministic.

**Design implication:** Issue #6 should consolidate provider access behind one service **without rewriting the functioning perception or control path prematurely**. Check the exact runtime paths and dependencies first.

## 6. Field-tested behavior and integration hazards

The supplied status summary identifies field test **US05** on 2026-10-29: 95 cycles; 36 `HOLD` actions, 9 reversals, 14 consecutive late `HOLD` actions, and manual termination without confirmed GPS arrival. This is evidence of physically functioning components, **not** proven end-to-end autonomy.

### Risks requiring explicit attention

| Risk | Evidence in inspected code | Recommended treatment |
|---|---|---|
| Real hardware initialization | Entrypoint creates/arms L1 on startup | Never use it for skeleton lab tests; mock L1 at construction |
| Unsafe/unverified reverse clearance | L2 can command one automatic `MOVE_BACKWARD` after repeated front/visual block | Keep unchanged for inventory; flag for Issue #11; no blind reverse in offline acceptance |
| Safety validation boundaries | L2 calls controller from several branches, including early recovery | Inspect every action path before allowing GPT-generated proposals |
| GPS/heading uncertainty | L3 depends on phone position/attitude quality | Inject synthetic position/heading for tests; fail safely when unavailable |
| Block handling not fully escalated | L3 GPT advice is logged but not a navigation strategy transition | Define structured escalation in Issue #4 |
| Model/service duplication | Placeholder `LLMService`, tactical provider adapter, perception client, direct L3 SDK call | Centralize only after mapping live uses |
| Missing mission semantics | L4 accepts a structured GOTO mission and checks arrival | Build explicit distinction between location reached and inspection completed |
| Runtime sleep and physical actuation coupling | CLI sleeps 3 s and stops motors each cycle | Lab harness must run deterministically without device and timing dependency |

## 7. Intended skeleton boundary (proposal, not implementation)

```text
Structured mock mission
          |
          v
Existing L4 / extended mission contract
          |
          v
Existing L3 / deterministic Guidance
          |
          v
Existing L2 / synthetic PerceptionResult
          |
          v
Mock L1 rover client (records actions, never opens serial)
          |
          v
Structured simulated feedback → L2 → L3 → L4
```

DoctrineService, shared GPT and mission reasoning will initially return controlled responses. The **first skeleton test should require no API key, camera, phone, serial port or motor controller**.

## 8. Validation checklist — Issue #3

| Check | State |
|---|---|
| Git baseline and worktree strategy documented | Documented from prior Git verification |
| Existing field entrypoint located | Verified by code inspection |
| Existing L4 → L3 → L2 → L1 call graph mapped | Verified by code inspection |
| Current memory/prompt infrastructure inventoried | Verified by code inspection |
| Existing GPT paths distinguished from stub | Verified by code inspection |
| Safety and integration risks recorded | Verified by code inspection |
| Active hardware/device-independent smoke test | **Not run** |
| Baseline regression commands and test environment verified | **Not yet verified** |
| Full device-side behavior of RA4M1 sketch | **Not reviewed in this inspection** |

## 9. Recommended next actions

1. Agree on the **minimum structured contracts** in [Issue #4](https://github.com/jbruks/CognitiveOps/issues/4).
2. Create a no-motion, no-network test seam around the existing planner chain (Issue #5).
3. Run explicit tests and record evidence before claiming Issue #3 completed.
4. Preserve the validated field entrypoint and avoid changing L1 during skeleton work.

**No source code changes are authorized by this document.**
