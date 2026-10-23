# Why CognitiveOps Is LLM-First Rather Than ROS 2 / Nav2-First

**Project:** CognitiveOps / ProjectRover  
**Status:** Architecture rationale and research direction  
**Date:** 2026-10-23

## 1. Our target is the LLM

CognitiveOps is not an attempt to build another conventional autonomous navigation stack. Its primary objective is to **demonstrate how far a general-purpose multimodal large language model can take a physical robot when the model is responsible for perception-informed decisions and tactical navigation**.

This distinction drives the architecture.

ROS 2 and Nav2 are established robotics technologies. They offer valuable infrastructure and proven navigation components. But adopting a complete conventional navigation stack as the centerpiece of CognitiveOps would change the question we are trying to answer.

We are **not** asking:

> How can we make a rover navigate using the most mature conventional robotics software stack?

We are asking:

> How much robot behavior can be driven by an LLM, with minimal application-specific navigation code, while preserving necessary deterministic control and safety?

**The LLM is the subject of the experiment, not an optional interface layered on top of an already autonomous robot.**

## 2. What ROS 2 and Nav2 solve

These technologies should not be treated as interchangeable:

- **ROS 2** is a robotics middleware and software ecosystem. It facilitates communication between nodes, sensor integration, tooling, logging, and modular deployment.
- **Nav2** is a navigation framework built on ROS 2. It provides components for localization integration, planning, path following, costmaps, recovery behaviors, and task orchestration.

Neither is inherently incompatible with LLMs. The architectural concern is where the actual decisions happen.

If Nav2 performs obstacle avoidance, chooses local trajectories, and manages recovery while GPT merely supplies a destination, the resulting demonstration is primarily **Nav2-based navigation with an LLM interface**.

That is a valid product architecture, but **it is not our research target**.

## 3. The CognitiveOps approach

CognitiveOps deliberately retains a compact, comprehensible L1–L4 architecture:

| Layer | Responsibility | Current approach |
|---|---|---|
| **L4 — Mission** | Interpret goals and coordinate the mission | Mission orchestration, with scope for business-level LLM reasoning |
| **L3 — Guidance** | Translate destination coordinates into desired bearing, distance, and heading error | Deterministic GPS/compass geometry |
| **L2 — Tactical intelligence** | Select an action given local traversability and navigation intent | **GPT multimodal-informed tactical decisions** |
| **Perception** | Interpret camera images as local navigation opportunities and constraints | **GPT vision: LEFT / FRONT / RIGHT passability and confidence** |
| **L1 — Physical control** | Issue bounded actuator commands and enforce independent safety constraints | Deterministic controller and Arduino |

The model selects among a small set of actions—currently `MOVE_FORWARD`, `FORWARD_LEFT`, `FORWARD_RIGHT`, and `MOVE_BACKWARD`—using the output of perception and the guidance context.

This keeps the experimental question visible: **what can the model decide from vision and mission context, and where does it fail?**

The design is intentionally hybrid. Deterministic components remain appropriate for GPS geometry, motor control, validation, timeouts, and emergency stopping. LLM-first does **not** mean LLM-only.

## 4. Why not start with a full Nav2 stack?

### A. It would obscure the experimental contribution

A sophisticated costmap, classical local planner, and recovery manager could navigate around obstacles before GPT needs to make a meaningful decision. We would then struggle to attribute success—or failure—to the LLM.

### B. It increases integration overhead before we need it

A complete Nav2 deployment typically involves robot frames and transforms, a motion model, odometry, localization, controller configuration, obstacle representations, and tuning. These are reasonable investments for a production navigation stack, but they are not prerequisites for investigating our present LLM-based decision loop.

### C. It shifts effort away from the central hypothesis

Our scarce engineering time is better spent measuring perception quality, tactical decisions, latency, recovery behavior, navigation progress, and failure modes than configuring a second, largely independent autonomous navigation system.

### D. It risks turning GPT into a superficial add-on

A robot that accepts a natural-language mission while Nav2 performs all the navigation demonstrates a useful interface. CognitiveOps aims to demonstrate **cognition participating directly in physical action selection**.

## 5. The business connection

The longer-term value proposition is not merely simpler movement. It is the potential to connect **business intent directly to physical tasks**:

```text
Business objective
       |
       v
L4: Mission interpretation and task reasoning
       |
       v
L3: Navigation goals and guidance
       |
       v
L2: LLM tactical decision-making
       ^
       |
Multimodal perception and environmental context
       |
       v
L1: Deterministic execution and safety
       |
       v
Physical robot
```

Potential workflows include inspecting a site and reporting anomalies, surveying a crop area, or examining infrastructure against a checklist.

The hypothesis is that a reusable reasoning architecture could reduce some domain-specific programming: the same robot could receive different missions, context, and inspection criteria without a new hand-coded navigation strategy for every task.

This remains a **hypothesis to evaluate**, not a demonstrated reduction in total engineering cost. Hardware, safety, connectivity, validation, and domain-specific sensing still matter.

## 6. Evidence from demos and field experiments

CognitiveOps has evolved through **simulated experiments, incremental physical-robot demos, and instrumented outdoor tests**. The evidence is not limited to the October 22 garden run.

### 6.1 Development demonstrations: camera, multimodal decisions, hierarchy, and GPS

The repository's [main README](../../README.md#development-evolution) documents a sequence of experimental *Lunar Rover* revisions. These are **recorded implementation milestones**, rather than independently benchmarked navigation-success results:

| Recorded milestone | What was demonstrated or introduced |
|---|---|
| **LR014–LR015** | Real OpenCV camera perception, followed by multimodal image + LLM tactical reasoning |
| **LR016–LR017** | Reverse driving and autonomous execution-loop diagnostics |
| **LR018–LR021** | L3/L4 hierarchical planning, cognitive memory, recovery/task experiments, and per-run image/execution traces |
| **LR027–LR037** | Layered L1/L2 integration, Lite World Model, and broader instrumentation |
| **LR042–LR045** | Shared perception/cognitive context, GPS integrated into perception, and GPS target handoff between mission layers |

The [README's physical test launcher section](../../README.md#physical-test-launchers) also describes short (`i5`) and longer (`i50`) real-rover iteration tests. Together, these stages show an experimental progression from camera input to an LLM-influenced physical control loop and mission context.

**Evidence scope:** The README documents capabilities and revision history; it does not establish collision-free mileage or benchmark superiority over conventional navigation.

### 6.2 October 21, 2026 — Outdoor runs with local Qwen L2

The repository contains a dedicated, quantitative report: **[Field test — Local Qwen L2 — 2026-10-21](https://github.com/jbruks/CognitiveOps/blob/main/FIELD_TEST_20261021_QWEN_L2.md)**.

The report covers four autonomous runs using **Qwen 2.5 7B via Ollama**, connected through a persistent worker on a ZBook, and a fast local VisionNN perception stage. Motor commands were active.

| Reported measurement | Result |
|---|---:|
| Recorded cycles/images | **318** |
| Tactical decisions | **297** |
| Forward / forward-left / forward-right / backward | **118 / 69 / 47 / 63** |
| VisionNN mean / median | **0.313 s / 0.311 s** |
| VisionNN observed range | **0.298–0.425 s** |
| GPS/navigation HOLD cycles | **20** |

The report documents several substantive findings:

- **Field conditions mattered:** low frontal sunlight, shadows, gravel, vegetation, and nearby objects complicated perception.
- **GPS loss was handled conservatively:** stale phone position/heading resulted in HOLD/STOP, rather than unrestricted movement.
- **Backward action was not always an LLM decision:** 48 of 63 backward actions coincided with LOW perception confidence and were forced by the then-current deterministic policy.
- **A useful negative result:** a Qwen heading micro-task agreed with a numeric ±8° rule in **189/217 cases (87.1%)**. Heading thresholding was subsequently moved to deterministic code.

**Architectural relevance:** This test illustrates why LLM-first does not mean using an LLM for every operation. Semantic obstacle reasoning is a research target; simple numeric heading thresholds may be better implemented deterministically.

**Configuration caution:** This was a **different experimental stack** from the following day's GPT-based garden run. Qwen/VisionNN inference figures must not be compared directly with GPT API latency as though they measured identical tasks.

### 6.3 October 22, 2026 — Physical garden test with GPT tactical navigation

A subsequent garden test exercised camera capture, **GPT-based LEFT / FRONT / RIGHT corridor assessment**, GPS/heading guidance, GPT tactical action selection, and physical rover movements.

Recorded observations from the analysed session included:

- Approximately **17 minutes and 15 seconds** of activity.
- **171 perception cycles** and **146 movement decisions**.
- Mean GPT response times of approximately **1.31 s for perception** and **1.16 s for L2 tactical decisions**.
- Executed forward, left, right, and backward maneuvers.
- Human interventions, including lifting and repositioning the rover.
- **Home Wi-Fi connected through fiber**, *not* field 4G; cloud-model latency under cellular conditions remains untested by this run.
- No reliable ground-truth distance travelled: phone GPS was noisy, with a reported median horizontal accuracy of approximately **11 m**.

**Evidence scope:** This supports feasibility of GPT participating in a sustained supervised physical control loop. It does **not** establish independent mission completion, verified obstacle-avoidance accuracy, reliable odometric distance, or safety equivalence to Nav2.

### 6.4 What the broader experimental history tells us

Taken together, these records support **an engineering and research trajectory**, not a claim that one model or architecture has already won:

1. **System integration:** camera, perception, hierarchical mission context, guidance, LLM action selection, and RA4M1 commands were progressively connected to a physical platform.
2. **Model/backend flexibility:** tests used both local Qwen-based reasoning and cloud GPT, exposing different deployment and connectivity trade-offs.
3. **Measured rather than anecdotal behavior:** at least two field-test records report cycle counts, decisions, and inference timing, including failure cases.
4. **Selective determinism:** observed errors in numeric heading decisions motivated moving that subproblem out of the LLM path, while keeping the cognition experiment centered on perception and tactical behavior.
5. **Open research gaps:** localization, temporal reasoning, avoiding repeated recoveries, robustness to lighting, and cellular-network performance remain unresolved.

This is precisely why a **Nav2-first replacement would answer a different question**: we want to measure and improve the LLM's contribution to physical navigation, rather than conceal it behind an established autonomous planner.

**Primary repository evidence**

- [CognitiveOps README — architecture, physical launchers, and development evolution](../../README.md)
- [Field test: Local Qwen L2, October 21, 2026](https://github.com/jbruks/CognitiveOps/blob/main/FIELD_TEST_20261021_QWEN_L2.md)
- October 22, 2026 garden-test analysis and operator-provided log; quantitative values above are from that session, not from the earlier Qwen report.

## 7. Known limits and why they matter

An LLM-driven navigation loop has meaningful constraints:

- **Depth and free-space uncertainty:** A monocular image does not provide reliable metric obstacle clearance. Distant objects can be mistaken for immediate blockers.
- **Limited temporal context:** Repeated local decisions can lead to oscillation, repeated reversing, or dead ends without memory and progress tracking.
- **Network dependence:** Cloud inference latency and availability can vary. Results on fiber-backed Wi-Fi cannot be assumed to hold on 4G.
- **Localization quality:** Several-meter GPS errors can overwhelm short rover movements and make apparent progress unreliable.
- **Rear visibility:** Forward vision does not establish that backing up is safe.
- **Safety:** Motor stop, command expiry/watchdogs, manual override, and motion limits must not depend on a model response.

These are essential research questions for CognitiveOps, not reasons to hide the LLM behind a conventional autonomous stack.

## 8. Where ROS 2 could still help

Rejecting a **Nav2-first architecture** does **not** mean rejecting ROS 2 forever.

ROS 2 may add value as infrastructure for sensor topics, component isolation, timestamped messaging, bag recording, diagnostics, and interchangeable drivers—without changing who makes tactical decisions.

Nav2 could also serve as a **baseline** or an optional separate navigation mode:

| Experimental mode | Tactical navigation authority | Purpose |
|---|---|---|
| **CognitiveOps GPT-first** | GPT L2, with deterministic safety | Main research configuration |
| **Nav2 baseline** | Conventional planner/controller | Quantitative comparison |
| **Hybrid** | GPT selects higher-level subgoals or maneuvers; conventional control executes | Explore division of labor |

A fair comparison should measure mission completion, collision/near-miss events, human interventions, progress toward the target, latency, integration effort, operating cost, and robustness across terrain and connectivity conditions.

## 9. Architectural decision

**For the current proof of concept, CognitiveOps will remain LLM-first and will not adopt ROS 2/Nav2 as its core navigation decision engine.**

We will prioritize:

1. **Perception validity:** Does GPT distinguish traversable terrain from obstacles at the movement horizon?
2. **Tactical reasoning:** Does GPT choose useful, safe maneuvers given a target and local alternatives?
3. **Temporal reasoning:** What minimal memory or progress representation prevents repeated failures?
4. **Real-world evaluation:** How does the same architecture behave outdoors, including on 4G?
5. **Independent physical safety:** Can the deterministic control layer bound motion and stop the rover regardless of GPT behavior?
6. **Business-task integration:** Can missions be expressed and evaluated at the level of real operational outcomes?

ROS 2 and Nav2 remain possible **supporting technologies or comparison baselines**, not the definition of the project.

## 10. One-sentence positioning

> **CognitiveOps is an LLM-first robotics research architecture designed to move from business intent to physical action, keeping multimodal reasoning at the center of navigation decisions while retaining deterministic execution and safety.**

The goal is not to claim that conventional robotics is obsolete. The goal is to discover **which pieces of specialized robotics software general-purpose models can meaningfully simplify—and which pieces must remain deterministic, measurable, and engineered.**
