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

## 6. What our current field experiments demonstrate

ProjectRover has already exercised an end-to-end physical loop involving camera capture, GPT-based corridor assessment, GPS/heading guidance, GPT tactical action selection, and actuator commands.

In the **2026-10-22 garden test**, recorded observations included:

- A main session of approximately **17 minutes and 15 seconds**.
- **171 perception cycles** and **146 movement decisions**.
- Mean measured GPT latency of approximately **1.31 seconds for perception** and **1.16 seconds for tactical L2**.
- Real movements involving forward, left, right, and backward actions.
- Operator interventions, including manually lifting and repositioning the rover.
- Navigation tested over **home Wi-Fi with a fiber connection**, **not field 4G**.
- No reliable ground-truth distance traveled: phone GPS was noisy, with a reported median horizontal accuracy around **11 meters**.

These results support the feasibility of **an LLM participating in a real rover control loop** under supervised conditions. They do **not** prove autonomous mission completion, superior navigation performance relative to Nav2, or production safety.

The field logs and images are evidence, not a substitute for controlled comparative experiments.

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
