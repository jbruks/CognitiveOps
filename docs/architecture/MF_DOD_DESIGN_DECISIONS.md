# MF-DoD — Architecture Design Decisions

**Project:** CognitiveOps  
**Status:** Accepted principles; detailed contracts pending review  
**Date:** 2026-10-29  
**Development branch:** `feature/mf-dod-cognitive-architecture`  
**Parent tracking issue:** [#2 — MF-DoD Cognitive Architecture](https://github.com/jbruks/CognitiveOps/issues/2)  
**Functional reference:** [Iteration 3 — RC Airfield Inspection](../MF_DOD_ITERATION_03_AIRFIELD_USE_CASE.md)

## Context and goal

CognitiveOps already has a working physical rover stack: L1 motor control on RA4M1, L2 perception and tactical actions, L3 GPS guidance, and an initial L4 mission layer. The next iteration moves from GPS-target execution to **Mission First, Doctrine on Demand (MF-DoD)** while retaining the validated physical stack.

A mission begins with operator intent and available context (maps, GPS references, imagery, operating constraints, capabilities, and available source documents). The system derives inspection objectives, executes permitted tasks, evaluates evidence, revises plans, and reports results. The RC airfield is the **validation case**, not a hard-coded mission type.

## Decision register

### ADR-001 — Preserve the functional baseline and develop on a separate branch

**Status:** Accepted.

- Physical baseline: `fe09e70`, tagged `baseline/rover-functional-20261029`.
- MF-DoD starting point: `24e84cd`, tagged `baseline/mf-dod-start-20261029`.
- Development branch: `feature/mf-dod-cognitive-architecture`.
- Keep `main` stable and integrate only after tests and review.
- Existing local worktrees: `~/RoverGit` and `~/RoverGit-mf-dod`.

**Rationale:** avoid destabilizing the validated US05 rover baseline.  
**Tracked by:** [#3](https://github.com/jbruks/CognitiveOps/issues/3).

### ADR-002 — Skeleton first, intelligence later

**Status:** Accepted.

Build a **minimal executable vertical slice** connecting mission input → L4 → L3 → L2 → mock L1 and ascending feedback. Use deterministic stubs initially; prove contracts, lifecycle and safe failure before enabling actual inference. Do not create a parallel robot-control architecture or a large collection of unused placeholder classes.

**Rationale:** integration defects should be isolated before cognitive behavior is introduced.  
**Tracked by:** [#4](https://github.com/jbruks/CognitiveOps/issues/4), [#5](https://github.com/jbruks/CognitiveOps/issues/5).

### ADR-003 — One shared GPT inference service

**Status:** Accepted.

L4, L3 and L2 use a **single configurable inference service**, with separate role-specific context, schemas and decision validation. Centralize provider configuration, timeout/error handling and observability. The service may be stubbed for offline tests.

**Constraint:** never block deterministic safety or the physical control loop while waiting for GPT.

**Rationale:** reduce duplication, manage latency and enable incremental adoption.  
**Tracked by:** [#6](https://github.com/jbruks/CognitiveOps/issues/6).

### ADR-004 — Strict responsibility boundaries for L4, L3, L2 and L1

**Status:** Accepted.

| Layer | Owns | Must not own |
|---|---|---|
| **L4 — Mission** | Interpret intent; information needs; doctrine questions; inspection objectives; completion and reporting; mission-level replanning | Raw motor commands |
| **L3 — Navigation** | Translate authorized objectives into navigation goals; intermediate stages; GPS/heading guidance; monitor progress and navigation failure | Mission authority or motor safety overrides |
| **L2 — Tactical** | Fuse current perception with guidance and recent history; propose local actions; recover within safety bounds; escalate persistent blocks | Reinterpret mission objectives or bypass validation |
| **L1 — RA4M1** | Deterministic physical actuation, feedback and hardware safeguards | LLM inference |

Use **structured downward objectives** and **structured upward status/feedback**. A successful navigation arrival does **not** by itself prove that an inspection objective is complete.

**Rationale:** clear ownership enables compositional tests and prevents unrestricted agent-to-agent control.  
**Tracked by:** [#4](https://github.com/jbruks/CognitiveOps/issues/4), [#9](https://github.com/jbruks/CognitiveOps/issues/9), [#10](https://github.com/jbruks/CognitiveOps/issues/10), [#11](https://github.com/jbruks/CognitiveOps/issues/11).

### ADR-005 — Doctrine on demand, with provenance and without authority transfer

**Status:** Accepted.

Introduce **`DoctrineService`**, queried by L4 when procedural knowledge is useful. Initially favor simple local retrieval over complex infrastructure. Each usable result should identify source and verified location (page/section when available), and the system must distinguish:

1. Material returned from a document.
2. LLM interpretation or adaptation.
3. Operator constraints and permissions.
4. Resulting mission-level recommendation.

Documents are reference data, **not higher-priority operational commands**. For the initial civil inspection example, MCTP 3-01A and FM 3-25.26 are conceptual sources; exact doctrinal citations remain to be verified before claiming direct textual support.

**Rationale:** generalize across unforeseen missions while retaining traceability.  
**Tracked by:** [#8](https://github.com/jbruks/CognitiveOps/issues/8).

### ADR-006 — Reuse existing memory and prompt infrastructure

**Status:** Accepted.

Review and evolve `memory_system.py`, `llm/memory_formatter.py`, `llm/prompt_framework.py`, and existing level models rather than building duplicate stores or per-mission prompt scripts.

Maintain logically distinct contexts:
- **Mission (L4):** objectives, evidence, consulted sources, progress and unresolved uncertainty.
- **Navigation (L3):** goals, progress, GPS quality, attempted strategies and block conditions.
- **Tactical (L2):** recent perceptions/actions, uncertainty and bounded recovery attempts.

Use generic prompts assembled from current mission, level role, constraints, observations, memory and retrieved knowledge. Do not encode the RC airfield as a dedicated behavioral prompt.

**Rationale:** keep changes minimal and avoid losing context between cycles.  
**Tracked by:** [#7](https://github.com/jbruks/CognitiveOps/issues/7).

### ADR-007 — Preserve deterministic control, guidance and safety

**Status:** Accepted.

- Retain deterministic L1 and motor safety mechanisms.
- Retain deterministic GPS, distance, heading and angular computations in L3.
- Validate all L2-generated action proposals before actuation.
- Handle degraded perception, unavailable GPS, GPT timeout and conflicting sensor data by bounded safe behavior and escalation.
- An ultrasonic no-echo reading does **not** establish free space.
- Review reverse-motion safety and action-completion synchronization before field trials.
- No unattended motor activation in early development stages.

**Rationale:** reasoning quality must not weaken physical safety.  
**Tracked by:** [#10](https://github.com/jbruks/CognitiveOps/issues/10), [#11](https://github.com/jbruks/CognitiveOps/issues/11), [#12](https://github.com/jbruks/CognitiveOps/issues/12).

### ADR-008 — Event-driven reasoning and bounded escalation

**Status:** Accepted as a design principle; exact triggers pending.

Use the normal fast deterministic tactical cycle when sufficient. Trigger costly GPT deliberation for meaningful decisions, ambiguity or persistent failure. Escalate problems through the responsibility chain:

`L2 local uncertainty/block → L3 navigation problem → L4 mission-level reconsideration → operator when necessary`.

Prevent repeated `HOLD`/recovery loops without progress, as highlighted by the US05 field run. Thresholds and retry policies must be measured and reviewed, not guessed in this document.

**Rationale:** control latency, reduce token use and avoid indefinite loops.  
**Tracked by:** [#6](https://github.com/jbruks/CognitiveOps/issues/6), [#10](https://github.com/jbruks/CognitiveOps/issues/10), [#11](https://github.com/jbruks/CognitiveOps/issues/11).

### ADR-009 — Validate top-down intelligence after the skeleton

**Status:** Accepted.

After the skeleton and common services work, enable intelligence in this order:

1. **L4:** mission understanding, doctrine-informed planning, evidence/status and reporting.
2. **L3:** navigation strategy and progress/replanning while preserving deterministic Guidance.
3. **L2:** tactical reasoning and bounded recovery, with deterministic action validation.
4. **End-to-end:** simulated mission, regression testing and only then an approved supervised field demonstration.

**Rationale:** the higher-level mission contract defines the information lower layers actually need.  
**Tracked by:** [#9](https://github.com/jbruks/CognitiveOps/issues/9), [#10](https://github.com/jbruks/CognitiveOps/issues/10), [#11](https://github.com/jbruks/CognitiveOps/issues/11), [#12](https://github.com/jbruks/CognitiveOps/issues/12).

### ADR-010 — Observable results and evidence, not ungrounded conclusions

**Status:** Accepted.

Record structured events sufficient to replay and assess decisions: mission objective, level, chosen action/status, timestamp, available evidence, uncertainty, model/provider metadata where relevant, and doctrinal source identifiers when consulted. Do not rely on raw hidden model reasoning.

For the RC airfield, report each zone as observed, partially observed, unvisited or inaccessible. Distinguish measurement, model inference, source material and missing information.

**Rationale:** demonstrate what cognition contributes and why outcomes can be trusted.  
**Tracked by:** [#7](https://github.com/jbruks/CognitiveOps/issues/7), [#12](https://github.com/jbruks/CognitiveOps/issues/12).

## End-to-end conceptual flow

```text
Operator mission + map + restrictions + capabilities
                        |
                        v
               L4 Mission Intelligence
                  |             |
                  v             v
          DoctrineService   Mission memory
                        |
             mission-level objective
                        v
               L3 Navigation Intelligence
             goals + deterministic Guidance
                        v
               L2 Tactical Intelligence
             perception + bounded reasoning
                        v
             Deterministic safety validator
                        v
                 L1 RA4M1 control
                        |
              sensors, action outcomes
                        |
              upward feedback to L2
               / L3 / L4 as needed
```

The **GPT service** is shared by L4/L3/L2, and must not sit on the immediate actuation safety path.

## Open design decisions (not yet accepted)

- Exact mission, objective, navigation and feedback types, and their minimum required fields.
- Active runtime entrypoint and which GPT client/backend actually runs on current `main`.
- Whether doctrine retrieval starts as keyword/section index or another smallest viable approach.
- Exact model invocation triggers, budgets, latency thresholds and fail-safe defaults.
- Persistence requirements beyond existing memory structures.
- Field-test approval conditions and quantitative acceptance thresholds.

These should be resolved through the linked issues following code inspection, **not guessed here**.

## Delivery checkpoints

| Checkpoint | Related issues | Acceptance summary |
|---|---|---|
| Baseline and contracts | #3–#4 | Actual runtime documented; minimal contracts agreed |
| Executable shell | #5 | No-movement end-to-end flow and feedback pass |
| Shared cognitive services | #6–#8 | GPT stubs/real interface, memory and doctrine retrieval verified |
| L4 reasoning | #9 | Mission-to-inspection-plan lab demonstration |
| L3 reasoning | #10 | Navigation progress/block/replan scenarios verified |
| L2 reasoning | #11 | Ambiguity and repeated-HOLD replay with safe escalation |
| Integration | #12 | Reproducible simulated demonstration and regression pass |

**Non-goals:** agent orchestration frameworks, separate GPT clients per level, mission-specific prompt scripts, new hardware by default, redesigning L1 or replacing deterministic GPS Guidance.

---

**Change control:** Update this register when a decision changes; include rationale and link to the relevant issue/PR. The implementation should reflect the accepted decisions, not the other way around.
