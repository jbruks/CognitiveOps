## Architectural reference — CognitiveOps, CLARAty and Perseverance

CognitiveOps does not attempt to reproduce a NASA/JPL architecture directly.
However, its separation of mission reasoning, navigation/guidance, tactical
reasoning and physical control can be compared with concepts used in CLARAty
and the Perseverance rover autonomy stack.

The correspondence below is therefore conceptual rather than a strict
one-to-one implementation mapping.

| Function / abstraction | CognitiveOps | NASA/JPL CLARAty | Perseverance / AutoNav |
|---|---|---|---|
| **Mission intent** | **L4 — Mission**. Understands mission objectives, progress, completion, failure and future replanning. | **Decision Layer**, upper planning region. High-level goals are decomposed into plans and activities. | **Mission / science team** defines scientific objectives, destinations and general route intent. |
| **Strategic navigation** | **L3 — Navigation + Guidance**. Determines current navigation state and how the rover should progress toward the mission objective. Future responsibility includes intermediate objectives and strategic recovery. | **Decision Layer**. Planning and executive functions elaborate goals and coordinate Functional Layer capabilities. | Rover planners define general routes, destinations, waypoints and constraints. Increasingly, onboard autonomy can contribute to route planning. |
| **Local tactical autonomy** | **L2 — Tactical**. Combines Guidance with immediate Perception and chooses the next safe local manoeuvre. Can temporarily deviate from the global direction. | Boundary between **Decision Layer** and higher-level capabilities of the **Functional Layer**, depending on abstraction and implementation. | **AutoNav / ENav** builds local terrain representations, evaluates hazards and autonomously replans around obstacles toward the destination. |
| **Perception** | Camera/VLM perception provides semantic environmental information to the cognitive loop. Future sensors will expand this representation. | Primarily represented through capabilities and state exposed by the **Functional Layer** to decision-making components. | Navigation cameras and onboard terrain processing generate 3D terrain information used for hazard detection and path evaluation. |
| **Vehicle control** | **L1 — Control**. Deterministic execution of tactical commands and physical movement primitives. | **Functional Layer**. Provides low- and mid-level robotic capabilities and encapsulates physical-system functionality. | Mobility/control software converts navigation decisions into rover motion and actuator commands. |
| **Hardware / autopilot** | Current **RA4M1**, potentially **Pixhawk 6** in the future. | Hardware and low-level subsystems represented and controlled through the Functional Layer. | Rover flight computers, motor-control electronics, sensors and actuators. |
| **Decision vs execution boundary** | Approximately between **L2 and L1**, although some future deterministic navigation functionality may exist on either side. | Explicit conceptual boundary between **Decision Layer** and **Functional Layer**, known as **"The Line"**. | Separation between higher-level route/navigation decisions and lower-level mobility/control execution. |
| **Global vs local navigation** | **L3** maintains global Guidance while **L2** handles local environmental constraints. | Decision Layer can reason at different planning horizons while Functional capabilities can provide robust local behaviours. | Human/planning systems provide general route intent while AutoNav handles many of the local path and obstacle decisions. |
| **Reaction to obstacles** | L2 may override the requested Guidance direction for safety, re-observe and later recover progress toward the target. | Execution is monitored and plans can be modified when system state or conditions change. | AutoNav detects hazards and replans locally around rocks and other obstacles while progressing toward a pre-established destination. |
| **Role of AI** | LLM/VLM reasoning is intended mainly for Mission, strategic and Tactical cognition; deterministic computation remains appropriate for geometry and control. | The Decision Layer is explicitly the home of AI/planning components; the Functional Layer provides reusable robotic capabilities. | Classical onboard autonomy currently performs much of navigation; recent NASA experiments have also demonstrated generative-AI-assisted waypoint planning. |
| **Human role** | Future operator provides mission intent and interacts mainly with L4 rather than continuously controlling movement. | Mission-level goals may originate outside the robot planning space and are elaborated by the Decision Layer. | Ground teams define science objectives, routes and activities while onboard autonomy executes significant portions of navigation. |
| **Design philosophy** | Explicit hierarchy of cognitive authority: **Mission → Strategic Guidance → Tactical → Control**. | Separation of **decision-making** from **functional robotic capabilities**, with variable granularity inside both layers. | Combination of human mission planning, onboard autonomous navigation and deterministic vehicle control. |

### Interpretation for CognitiveOps

The comparison suggests that CognitiveOps can preserve its four-level model
without attempting to reproduce either CLARAty or Perseverance internally.

CLARAty provides a useful architectural principle:

**Decision-making should be separated from robust functional execution.**

Perseverance provides a complementary operational principle:

**Global mission and route intent can coexist with autonomous local navigation
and obstacle avoidance.**

CognitiveOps extends these ideas with an explicit cognitive hierarchy:

**L4 Mission**
→ what must be achieved

**L3 Navigation / Guidance**
→ where and how the system should make strategic progress

**L2 Tactical**
→ what should be done locally given the immediate environment

**L1 Control**
→ how the selected physical action is executed

This separation should become one of the foundations of the future
CognitiveOps Doctrine Framework.

The Doctrine Framework should therefore define not only the behaviour of each
level, but also the boundaries of authority between levels: what information
a level receives, what decisions it owns, what it may delegate, what it may
override, and under what conditions a problem must be escalated to a higher
cognitive level.
