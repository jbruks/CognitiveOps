# CognitiveOps — Reconnaissance Doctrine and Cognitive Framework

## 1. Purpose

This document defines the operational and cognitive framework for the continued development of CognitiveOps.

The framework is derived from three doctrinal references:

1. **MCTP 3-01A — Scouting and Patrolling**
2. **MCRP 2-10A.6 / MCWP 2-25 — Ground Reconnaissance Operations**
3. **FM 3-25.26 — Map Reading and Land Navigation**

These publications are not treated as software specifications.

Instead, they provide mature descriptions of reconnaissance missions, information-collection tasks, land-navigation problems, terrain reasoning and movement that can be translated into autonomous robotic capabilities.

The design direction is therefore:

**Doctrine → Mission Use Cases → Cognitive Responsibilities → Capabilities → Implementation → Field Validation**

rather than:

**Existing Software → Possible Use Cases**

This distinction is fundamental to the future development of CognitiveOps.

---

## 2. Scope

CognitiveOps is treated in this document as an autonomous or supervised ground reconnaissance platform.

The relevant doctrinal functions are:

* Reconnaissance.
* Observation.
* Information collection.
* Terrain assessment.
* Route assessment.
* Search.
* Detection.
* Identification.
* Localization.
* Land navigation.
* Reporting.
* Confirmation or denial of observations.

Functions involving weapons employment, attack, target engagement or fire control are outside the scope of this architecture.

The objective is an autonomous system capable of answering questions about an environment while navigating through it.

---

# 3. From Navigation to Reconnaissance

The current CognitiveOps implementation has primarily demonstrated:

> GO_TO_POINT

This has been useful as an experimental mission because it exercises the complete cognitive-control loop.

However, GO_TO_POINT should not define the future mission architecture.

In the mature architecture:

> **GO_TO_POINT is a navigation capability used by missions, not the mission model itself.**

For example:

```
RECONNOITRE ROUTE A → B
           │
           ▼
          L4
    Mission reasoning
           │
           ▼
          L3
  Navigation / Guidance
           │
    GO_TO_POINT
    checkpoints
    route progress
           │
           ▼
          L2
    Local tactical
       movement
           │
           ▼
          L1
    Physical control
```

A reconnaissance mission may require many navigation objectives, observations, inspections and changes of plan before the mission can be considered complete.

---

# 4. Reconnaissance Mission Model

The reconnaissance doctrine provides a richer set of mission-level use cases than point-to-point navigation.

The following mission families form the initial CognitiveOps L4 mission model.

| Mission                          | Mission intent                                                     | L4 completion concept                                                           |
| -------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| **Route Reconnaissance**         | Collect information about a route and relevant adjacent terrain    | Required route has been covered and relevant observations reported              |
| **Area Reconnaissance**          | Collect information within a designated area                       | Required area has been sufficiently observed                                    |
| **Zone Reconnaissance**          | Systematically collect information across a larger designated zone | Required portions of the zone have been covered according to mission priorities |
| **Point Reconnaissance**         | Collect information about a specific location, feature or object   | Required information about the point has been obtained                          |
| **Terrain Reconnaissance**       | Characterize terrain relevant to movement or observation           | Required terrain characteristics have been assessed                             |
| **Route Feasibility Assessment** | Determine whether a route is usable by the platform                | Traversability and significant restrictions have been characterized             |
| **Object Search**                | Search a defined space for a specified object or class of object   | Search criteria or coverage criteria have been satisfied                        |
| **Observation / Monitoring**     | Observe a location or feature and report relevant changes          | Observation requirement or monitoring period has been satisfied                 |

These are mission-level concepts.

They should not prescribe how the rover physically moves.

---

# 5. Reconnaissance Tasks

Ground reconnaissance doctrine describes reconnaissance in terms of information tasks such as:

* Observe.
* Locate.
* Detect.
* Determine.
* Identify.
* Evaluate.
* Report.
* Confirm.
* Deny.

These concepts are useful for robotics because they separate the **mission objective** from the **navigation required to achieve it**.

For example:

```
MISSION
Reconnoitre Area A

      ↓

INFORMATION REQUIREMENTS
Detect obstacles
Identify route conditions
Locate relevant objects
Evaluate terrain
Confirm expected features
Report observations

      ↓

NAVIGATION REQUIREMENTS
Reach observation locations
Cover the area
Revisit uncertain locations

      ↓

PHYSICAL MOVEMENT
```

This distinction should remain explicit throughout the CognitiveOps architecture.

---

# 6. Cognitive Architecture

CognitiveOps divides autonomy into four levels of authority and abstraction.

| Level                          | Primary question                                          | Responsibility                                     |
| ------------------------------ | --------------------------------------------------------- | -------------------------------------------------- |
| **L4 — Mission**               | What must be achieved and what information is required?   | Mission reasoning and reconnaissance objectives    |
| **L3 — Navigation / Guidance** | Where should the rover go to accomplish it?               | Strategic navigation, route reasoning and progress |
| **L2 — Tactical**              | What should the rover do locally now?                     | Local terrain reasoning and manoeuvre selection    |
| **L1 — Control**               | How should the requested movement be physically executed? | Deterministic vehicle control                      |

The levels represent different decision horizons.

They do **not** imply that every level must use an LLM.

---

# 7. Doctrine-to-Architecture Mapping

## 7.1 Mission and reconnaissance mapping

| Reconnaissance function             | L4                         | L3                          | L2                               | L1                     |
| ----------------------------------- | -------------------------- | --------------------------- | -------------------------------- | ---------------------- |
| Define reconnaissance objective     | **Primary**                | Consume                     | —                                | —                      |
| Define information requirements     | **Primary**                | Consume                     | Consume                          | —                      |
| Route reconnaissance                | **Own mission**            | Plan/progress route         | Inspect locally                  | Execute                |
| Area reconnaissance                 | **Own mission**            | Coverage strategy           | Local exploration                | Execute                |
| Zone reconnaissance                 | **Own mission**            | Coverage / sequencing       | Local exploration                | Execute                |
| Point reconnaissance                | **Own mission**            | Reach observation position  | Inspect point                    | Position rover         |
| Search for specified object         | **Own search objective**   | Manage search coverage      | Detect / inspect                 | Move / orient          |
| Observe                             | Determine relevance        | Select observation position | **Perform local observation**    | Hold / orient          |
| Locate                              | Mission relevance          | **Georeference / position** | Detect locally                   | —                      |
| Detect                              | Evaluate against mission   | —                           | **Primary local detection**      | —                      |
| Identify                            | Evaluate mission relevance | —                           | **Primary local interpretation** | —                      |
| Evaluate terrain                    | Mission implications       | Route implications          | **Local assessment**             | Physical feasibility   |
| Confirm / deny expected observation | **Mission interpretation** | Spatial context             | Observation evidence             | —                      |
| Report findings                     | **Primary**                | Supply navigation context   | Supply observations              | Supply execution state |

---

# 8. L4 — Mission Cognition

## Primary question

> **What must be discovered, observed or achieved?**

L4 owns the purpose of the reconnaissance mission.

L4 should not normally decide individual steering manoeuvres or calculate physical actuator commands.

Its responsibilities include:

* Interpret mission intent.
* Define reconnaissance objectives.
* Define information requirements.
* Establish priorities.
* Determine mission constraints.
* Track mission progress.
* Determine what remains unknown.
* Decide whether additional observation is required.
* Determine when reconnaissance is sufficiently complete.
* Handle mission-level failure or abort conditions.
* Reprioritize objectives when new information is discovered.
* Produce the final reconnaissance result or report.

A future L4 should therefore be capable of reasoning about states such as:

```
REQUIRED
OBSERVED
CONFIRMED
UNKNOWN
NOT YET INSPECTED
INCONCLUSIVE
```

This is significantly richer than the current GO_TO_POINT completion model.

---

# 9. L3 — Navigation and Guidance

## Primary question

> **Where should the rover progress in order to accomplish the mission?**

FM 3-25.26 provides much of the doctrinal foundation for this level.

L3 owns strategic spatial progress.

Its responsibilities may include:

* Determine or consume current position.
* Determine orientation.
* Determine distance and direction.
* Select routes.
* Generate intermediate navigation objectives.
* Manage checkpoints.
* Monitor route progress.
* Detect significant route deviation.
* Perform strategic recovery.
* Support dead reckoning.
* Use terrain association.
* Reason about expected terrain.
* Select observation positions requested by L4.
* Support systematic area coverage.
* Determine which locations remain unvisited.
* Generate GO_TO_POINT objectives when appropriate.

GO_TO_POINT therefore belongs primarily here.

A future L3 might receive:

```
L4:
"Reconnoitre this route."
```

and transform it into:

```
checkpoint A
      ↓
checkpoint B
      ↓
observation point C
      ↓
checkpoint D
      ↓
destination
```

The individual navigation objectives are implementation details of the reconnaissance mission.

---

# 10. L2 — Tactical Cognition

## Primary question

> **Given the strategic intent and immediate environment, what is the best safe local action now?**

L2 connects strategic Guidance with the terrain actually observed by the rover.

Its responsibilities include:

* Interpret immediate terrain.
* Determine local traversability.
* Detect local obstacles.
* Interpret local environmental features.
* Select a safe local passage.
* Select tactical manoeuvres.
* Temporarily deviate from strategic Guidance when required.
* Recover the requested direction when possible.
* Select local observation opportunities.
* Determine whether something locally observed deserves further inspection.
* Distinguish obstacles from difficult but traversable terrain.
* Express uncertainty when perception is insufficient.

L2 therefore performs both:

**movement reasoning**

and

**local reconnaissance reasoning**.

This distinction will become increasingly important as CognitiveOps evolves beyond navigation experiments.

---

# 11. L1 — Physical Control

## Primary question

> **How is the requested physical action executed safely and deterministically?**

L1 owns vehicle execution.

Its responsibilities include:

* Steering.
* Speed.
* Forward and reverse movement.
* Physical stopping.
* Low-level movement primitives.
* Actuator commands.
* Execution monitoring.
* Terrain-specific control behaviour.
* Vehicle protection constraints.
* Reporting completion or failure of physical actions.

Future crawler capabilities may allow L1 to expose more meaningful physical primitives such as:

```
DRIVE_FORWARD
TURN
PRECISE_APPROACH
CROSS_ROUGH_TERRAIN
CLIMB_SLOPE
DESCEND_SLOPE
HOLD_POSITION
```

These should remain deterministic physical capabilities rather than mission-level decisions.

---

# 12. Traversability Doctrine

Reconnaissance requires movement through real terrain.

CognitiveOps should therefore avoid reducing the environment to:

```
FREE
or
OBSTACLE
```

Instead, the architecture should progressively reason about:

```
SAFE AND EASY
      │
SAFE BUT DIFFICULT
      │
UNCERTAIN
      │
NON-TRAVERSABLE
      │
DANGEROUS
```

This distinction spans multiple levels.

L3 asks:

> Is this terrain appropriate for the route?

L2 asks:

> Can I safely traverse this specific terrain now?

L1 answers:

> What can the physical rover actually execute?

The crawler's mobility capabilities therefore become part of the autonomy model.

---

# 13. Terrain Association

FM 3-25.26 introduces an important concept for future CognitiveOps development:

**terrain association**.

Navigation should eventually be capable of comparing what is expected with what is observed.

Conceptually:

```
MAP / ROUTE / PRIOR KNOWLEDGE
             │
             ▼
      EXPECTED WORLD
             │
             ▼
          MEMORY
             ▲
             │
      OBSERVED WORLD
             ▲
             │
        PERCEPTION
```

A correspondence can strengthen confidence in the navigation hypothesis.

A mismatch may indicate:

* Position uncertainty.
* Route deviation.
* Incorrect prior information.
* Environmental change.
* Perception uncertainty.

This creates a future connection between Perception, Memory and Navigation.

---

# 14. Memory

Reconnaissance is inherently temporal.

A rover cannot perform meaningful reconnaissance if every cognitive cycle is treated as an entirely new world.

Memory should therefore be investigated as a transversal CognitiveOps capability.

Potential memory horizons include:

| Memory horizon            | Main use                                                                 |
| ------------------------- | ------------------------------------------------------------------------ |
| **Tactical memory**       | Recent obstacles, manoeuvres and local observations                      |
| **Navigation memory**     | Route progress, checkpoints, deviations and previously traversed terrain |
| **Mission memory**        | Completed objectives, unresolved requirements and inspected areas        |
| **Reconnaissance memory** | Observations, objects, locations and environmental findings              |

Examples:

L2 may need to know:

> "I already attempted this passage and had to reverse."

L3 may need to know:

> "The rover has been locally avoiding obstacles for several cycles without recovering route progress."

L4 may need to know:

> "The eastern portion of the area has been inspected, but the western portion remains unknown."

The precise Memory architecture should not yet be assumed.

It should be derived from future field tests.

---

# 15. Perception

Perception is a transversal capability rather than a cognitive level.

Its role expands substantially under the reconnaissance model.

Current perception primarily supports:

> Where can I move safely?

Future reconnaissance perception must also support:

> What am I observing?

Potential perception products include:

* Terrain.
* Traversability.
* Obstacles.
* Paths.
* Vegetation.
* Infrastructure.
* Landmarks.
* Objects.
* Environmental conditions.
* Changes.
* Mission-relevant observations.

Perception provides evidence.

The cognitive levels determine what that evidence means for the mission.

---

# 16. Navigation

Navigation is also transversal.

Its fundamental question remains:

> **Where am I, how am I oriented, and how am I moving?**

Future Navigation may combine:

* GNSS.
* RTK GNSS.
* IMU.
* Odometry.
* Visual localization.
* Terrain association.
* Map information.
* Other localization sources.

Navigation should also represent uncertainty.

A fresh position is not necessarily an accurate position.

This distinction has already been observed during CognitiveOps field testing and should remain an architectural principle.

---

# 17. Safety

Safety constrains all cognitive levels.

A higher cognitive level may request an objective.

It may not override a hard lower-level safety constraint.

Conceptually:

```
L4 Mission intent
      ↓
L3 Strategic Guidance
      ↓
L2 Tactical decision
      ↓
   SAFETY
      ↓
L1 execution
```

Safety mechanisms may exist at several layers, including physical control, tactical constraints and mission abort logic.

Safety should not depend exclusively on LLM reasoning.

---

# 18. Authority and Escalation

Each level should solve problems within its own authority.

Example:

```
L3:
"Progress east."

      ↓

L2:
"East is locally blocked.
 I will move around the obstacle."

      ↓

obstacle persists

      ↓

L2 → L3:
"Local avoidance is not restoring progress."

      ↓

L3:
strategic route recovery

      ↓

route cannot be recovered

      ↓

L3 → L4:
"Mission objective cannot currently
 be reached through available routes."
```

This gives CognitiveOps an explicit escalation model:

**L1**
→ execution failure.

**L2**
→ local/tactical failure.

**L3**
→ navigation/route failure.

**L4**
→ mission consequence.

---

# 19. Doctrine Framework

Each cognitive level should eventually have a formal doctrine describing:

**ROLE**

What the level represents.

**OBJECTIVE**

What it is trying to achieve.

**CONTEXT**

What information it receives.

**RESPONSIBILITIES**

What problems it owns.

**AUTHORITY**

What it may decide independently.

**RESTRICTIONS**

What it must never decide or execute.

**UNCERTAINTY**

How it behaves when information is incomplete.

**MEMORY**

What historical information it may use.

**DELEGATION**

What decisions belong to lower levels.

**ESCALATION**

When a problem must be passed upward.

**OUTPUT**

What contract it provides to the next level.

This doctrine must remain conceptually independent of implementation technology.

A level may eventually be implemented using:

* Deterministic algorithms.
* State machines.
* Classical planners.
* Optimization.
* LLMs.
* VLMs.
* Learned perception.
* Hybrid systems.

**The architecture defines responsibilities, not implementation technologies.**

---

# 20. Development Use Cases

The doctrinal missions provide a natural progression for CognitiveOps field development.

## Navigation baseline

```
GO_TO_POINT
```

Validates basic Navigation, Guidance, Tactical and Control integration.

This capability has already been demonstrated experimentally.

## Route reconnaissance

```
RECONNOITRE ROUTE A → B
```

Adds:

* Route progress.
* Observations along movement.
* Obstacle reporting.
* Terrain characterization.
* Mission-level information collection.

This is a natural evolution of the current system.

## Point reconnaissance

```
INSPECT POINT P
```

Adds:

* Approach planning.
* Observation positioning.
* Inspection.
* Mission-relevant perception.
* Reporting.

## Area reconnaissance

```
RECONNOITRE AREA A
```

Adds:

* Coverage reasoning.
* Spatial memory.
* Visited/unvisited representation.
* Multiple navigation objectives.
* Mission completeness reasoning.

## Object search

```
SEARCH AREA A FOR OBJECT CLASS X
```

Adds:

* Search strategy.
* Mission-directed perception.
* Observation confidence.
* Reinspection.
* Spatial memory.
* Reporting.

## Zone reconnaissance

```
RECONNOITRE ZONE Z
```

Adds:

* Larger-scale planning.
* Mission prioritization.
* Multiple areas/routes.
* Resource awareness.
* Long-term memory.
* Dynamic replanning.

This progression should be treated as capability development rather than as a fixed implementation schedule.

---

# 21. Implications for Field Testing

Future field tests should not ask only:

> Did the rover reach the GPS coordinate?

They should progressively ask:

> Did the rover obtain the information required by the mission?

This changes the definition of success.

For route reconnaissance, success may require:

```
route traversed
      +
significant terrain observed
      +
obstacles recorded
      +
findings spatially associated
      +
reconnaissance result produced
```

For area reconnaissance:

```
adequate coverage
      +
observations collected
      +
unresolved areas identified
      +
mission completion justified
```

This will require future tests to evaluate not only movement but also:

* Perception.
* Memory.
* Navigation.
* Coverage.
* Information quality.
* Uncertainty.
* Reporting.
* Mission reasoning.

---

# 22. Relationship to the Current CognitiveOps System

The existing implementation should be considered the first experimental subset of this architecture.

Current approximate mapping:

```
L4
GO_TO_POINT mission
completion / stop
      ↓
L3
NavigationState
bearing
distance
heading error
Guidance
      ↓
L2
visual environment
+
Guidance
→
tactical manoeuvre
      ↓
L1
deterministic movement command
      ↓
RA4M1
      ↓
crawler
```

This is not a competing architecture.

It is the first implemented slice of the larger reconnaissance architecture.

The objective is therefore not to discard the current GO_TO_POINT work.

The objective is to **generalize upward from a validated navigation primitive into a reconnaissance system**.

---

# 23. Development Principle

Future CognitiveOps development should follow this sequence:

```
RECONNAISSANCE DOCTRINE
          ↓
    MISSION USE CASE
          ↓
INFORMATION REQUIREMENTS
          ↓
COGNITIVE RESPONSIBILITIES
          ↓
   CAPABILITY GAPS
          ↓
   IMPLEMENTATION
          ↓
    FIELD TEST
          ↓
     EVIDENCE
          ↓
  DOCTRINE REFINEMENT
```

New technologies should enter the project only when they solve a capability requirement identified through this process.

Therefore:

* Jetson is not a goal.
* Pixhawk is not a goal.
* RTK is not a goal.
* LiDAR is not a goal.
* An LLM is not a goal.

They are possible implementation technologies.

The goal is increasingly capable autonomous reconnaissance.

---

# 24. Architectural Direction

The long-term CognitiveOps model can therefore be summarized as:

```
HUMAN / OPERATOR
       │
       ▼
MISSION INTENT
       │
       ▼
      L4
Mission Cognition
"What must be discovered?"
       │
       ▼
      L3
Navigation / Guidance
"Where should I go?"
       │
       ▼
      L2
Tactical Cognition
"What should I do here?"
       │
       ▼
      L1
Physical Control
"How do I execute it?"
       │
       ▼
    VEHICLE
```

while:

```
PERCEPTION
NAVIGATION
MEMORY
SAFETY
```

provide transversal capabilities supporting the cognitive hierarchy.

The fundamental system loop becomes:

```
Mission intent
     ↓
Determine information required
     ↓
Determine where to obtain it
     ↓
Navigate
     ↓
Observe
     ↓
Interpret
     ↓
Remember
     ↓
Evaluate mission progress
     ↓
Continue / replan / complete
     ↓
Report
```

This is the proposed doctrinal foundation for the continued development of CognitiveOps.

---

# 25. Reference Doctrine

## MCTP 3-01A — Scouting and Patrolling

Primary contribution to CognitiveOps:

* Reconnaissance patrol concepts.
* Route reconnaissance.
* Area reconnaissance.
* Zone reconnaissance.
* Point reconnaissance.
* Information collection during reconnaissance.
* Planning and execution of reconnaissance patrols.

## MCRP 2-10A.6 / MCWP 2-25 — Ground Reconnaissance Operations

Primary contribution to CognitiveOps:

* Ground reconnaissance mission framework.
* Observation and surveillance concepts.
* Reconnaissance information tasks.
* Detection, location, identification, evaluation, confirmation and reporting.
* Mission purpose and information collection.

Only reconnaissance, observation and information-collection concepts are used by this framework. Weapons employment and engagement functions are outside CognitiveOps scope.

## FM 3-25.26 — Map Reading and Land Navigation

Primary contribution to CognitiveOps:

* Land-navigation fundamentals.
* Position and direction.
* Route selection.
* Terrain interpretation.
* Terrain association.
* Dead reckoning.
* Mounted land navigation.
* Navigation under different terrain conditions.

Together, these references provide three complementary perspectives:

```
RECONNAISSANCE DOCTRINE
What information must be obtained?
             │
             ▼
            L4

LAND NAVIGATION
Where must the rover go?
             │
             ▼
            L3

TERRAIN / LOCAL OBSERVATION
What does the immediate environment permit?
             │
             ▼
            L2

VEHICLE EXECUTION
How can the crawler physically do it?
             │
             ▼
            L1
```

This mapping should be refined as CognitiveOps accumulates field evidence.
