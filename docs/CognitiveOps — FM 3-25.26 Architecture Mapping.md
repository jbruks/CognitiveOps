# CognitiveOps — FM 3-25.26 Architecture Mapping

## 1. Purpose

This document maps land-navigation functions and use cases described in
FM 3-25.26, *Map Reading and Land Navigation*, to the four-level
CognitiveOps architecture.

The purpose is not to reproduce the manual or its procedures directly.

Instead, the manual is used as a reference source for identifying mature
land-navigation functions and determining which CognitiveOps level should
own, support, or execute each capability.

The mapping is architectural and doctrinal rather than implementation-specific.

---

## 2. CognitiveOps levels

The CognitiveOps hierarchy is based on four levels of authority and
abstraction:

| Level | Primary question | Main responsibility |
|---|---|---|
| **L4 — Mission** | What must be achieved? | Mission objectives, priorities, progress and completion |
| **L3 — Navigation / Guidance** | Where should the rover progress? | Position, route, guidance and strategic navigation |
| **L2 — Tactical** | What should the rover do locally? | Terrain interpretation, local manoeuvre selection and obstacle avoidance |
| **L1 — Control** | How should the physical movement be executed? | Deterministic vehicle and actuator control |

Perception, Navigation, Memory and Safety may provide transversal services
to more than one cognitive level.

---

## 3. FM 3-25.26 functional mapping

| Land-navigation function | L4 — Mission | L3 — Navigation / Guidance | L2 — Tactical | L1 — Control |
|---|---|---|---|---|
| Determine movement objective | **Primary** | Support | — | — |
| Determine current position | — | **Primary** | Consume | — |
| Determine orientation / direction | — | **Primary** | Consume | — |
| Determine distance to destination | — | **Primary** | Consume | — |
| Select general route | Supervise | **Primary** | — | — |
| Select checkpoints / intermediate points | — | **Primary** | — | — |
| Point navigation | Define destination | **Primary** | Local execution | Physical execution |
| Dead reckoning | — | **Primary** | Local support | Odometry / movement execution |
| Terrain association | — | **Strategic use** | **Local use** | — |
| Recognize landmarks | — | Use for localization | **Observe / identify** | — |
| Compare expected terrain with observed terrain | — | **Primary strategic reasoning** | **Local interpretation** | — |
| Confirm / correct estimated position | — | **Primary** | Provide observations | — |
| Detect route deviation | Monitor mission progress | **Primary** | May detect local deviation | — |
| Correct route deviation | — | **Replan Guidance** | Execute local correction | Execute |
| Evaluate terrain traversability | — | Strategic consideration | **Primary** | Physical capability |
| Avoid difficult / non-traversable terrain | — | May modify route | **Primary locally** | Execute |
| Exploit traversable terrain | — | Provide Guidance | **Select local path** | Execute movement |
| Negotiate immediate obstacle | — | Maintain strategic intent | **Primary** | Execute |
| Navigate with degraded visibility | Mission constraints | Adapt navigation strategy | Adapt tactical behaviour | Execute |
| Adapt to terrain type | Mission constraints | Strategic adaptation | **Local adaptation** | Vehicle-specific execution |
| Determine arrival at destination | **Declare mission success** | Detect arrival condition | — | Stop / hold |

---

## 4. Dead reckoning

FM 3-25.26 treats dead reckoning as a fundamental land-navigation technique.

Architecturally, dead reckoning belongs primarily to L3 and the Navigation
system.

A CognitiveOps implementation could progressively combine:

- Previous known position.
- Heading.
- Distance travelled.
- Vehicle odometry.
- IMU measurements.
- Wheel motion.
- GNSS updates.

Conceptually:

    Known position
          ↓
    heading + movement
          ↓
     dead reckoning
          ↓
    estimated position
          ↓
     external position fix
          ↓
    corrected position

L1 may provide movement and odometry information, but L1 should not own the
navigation estimate.

The resulting state belongs to Navigation and is primarily consumed by L3.

---

## 5. Terrain association

Terrain association is particularly relevant to the future CognitiveOps
architecture.

The rover should eventually be capable of comparing:

    EXPECTED WORLD
          ↕
        MEMORY
          ↕
    OBSERVED WORLD

For example:

    L3 expects:
    "A path intersection should appear ahead."

                 ↓

    Perception observes:
    "A path intersection is visible."

                 ↓

    Terrain association:
    observation is consistent with expected position

                 ↓

    Navigation confidence increases

The opposite case is equally important:

    expected terrain
          ≠
    observed terrain

                 ↓

    reassess position
    or
    reassess route

This capability would allow visual and semantic perception to contribute
directly to Navigation rather than being used exclusively for obstacle
avoidance.

---

## 6. Terrain association across cognitive levels

Terrain association should not belong exclusively to a single level.

### L3 — Strategic terrain association

L3 reasons about terrain in relation to the route and navigation state.

Examples:

- Expected landmarks.
- Route features.
- Terrain sequence.
- Checkpoints.
- Position confirmation.
- Route deviation.
- Strategic recovery.

Primary question:

**Does the terrain I am observing correspond to where I expect to be?**

### L2 — Local terrain association

L2 reasons about terrain in relation to immediate movement.

Examples:

- Which local region is traversable?
- Is the expected path locally accessible?
- Is vegetation blocking the requested direction?
- Can the rover move around this rock?
- Is an apparent obstacle actually traversable terrain?

Primary question:

**Given the terrain immediately around me, what manoeuvre should I execute?**

---

## 7. Mounted navigation and the crawler platform

Mounted land navigation provides a particularly useful reference for
CognitiveOps because the system operates a physical ground vehicle.

The architecture can separate route selection, terrain assessment and
physical execution:

    L3
    Strategic route
    "Progress through this area toward the objective."
              │
              ▼
    L2
    Tactical terrain assessment
    "The right side is the best local passage."
              │
              ▼
    L1
    Vehicle execution
    "Apply the appropriate physical control."
              │
              ▼
          CRAWLER

This distinction becomes increasingly important as the physical capabilities
of the crawler improve.

---

## 8. Traversability versus obstacles

Future CognitiveOps perception should distinguish between at least two
fundamentally different situations:

### Non-traversable obstacle

Examples may include:

- Large blocking objects.
- Dangerous drops.
- Terrain beyond vehicle limits.
- Impassable vegetation.
- Physical barriers.

Expected behaviour:

    detect
      ↓
    avoid
      ↓
    recover route

### Difficult but traversable terrain

Examples may include:

- Loose soil.
- Gravel.
- Small rocks.
- Moderate uneven terrain.
- Vegetation the crawler can safely cross.
- Slopes inside vehicle limits.

Expected behaviour:

    identify terrain
          ↓
    evaluate vehicle capability
          ↓
    select appropriate manoeuvre
          ↓
    traverse

This distinction connects L2 terrain reasoning directly with future L1
mobility capabilities.

A crawler should not treat every difficult surface as an obstacle if the
vehicle is physically capable of crossing it safely.

---

## 9. Route deviation and recovery

The manual's navigation concepts reinforce an important CognitiveOps
architectural boundary.

A temporary deviation from the desired direction does not necessarily
represent navigation failure.

Example:

    L3
    target direction
          ↓
    L2
    local obstacle detected
          ↓
    tactical deviation
          ↓
    L1
    execute manoeuvre
          ↓
    new observation
          ↓
    L3
    recompute Guidance

L2 owns the immediate tactical deviation.

L3 owns strategic recovery toward the route or objective.

If repeated tactical actions fail to restore progress, the problem should
eventually be escalated from L2 to L3.

If strategic recovery is no longer possible or conflicts with mission
constraints, L3 should escalate the situation to L4.

Therefore:

**L2 handles local avoidance.**

**L3 handles strategic navigation and recovery.**

**L4 handles mission consequences.**

---

## 10. Memory implications

Several land-navigation capabilities require temporal context.

Terrain association cannot rely only on the current observation.

The system may need to remember:

- Previously observed landmarks.
- Expected landmarks.
- Previous position estimates.
- Previous route decisions.
- Terrain already traversed.
- Recent tactical deviations.
- Whether progress toward the objective is being recovered.
- Areas already inspected during reconnaissance.

This suggests several possible memory horizons:

| Memory horizon | Primary consumer | Example |
|---|---|---|
| Immediate / tactical | L2 | "I backed away from vegetation in the previous cycle." |
| Navigation / route | L3 | "I have been deviating from the route for several cycles." |
| Mission | L4 | "This area has already been inspected." |
| Reconnaissance knowledge | L4 / mission systems | "An object of interest was observed at this location." |

The final CognitiveOps Memory architecture should be derived from field
experiments rather than assumed prematurely.

---

## 11. Implications for the Doctrine Framework

FM 3-25.26 provides useful real-world navigation problems that can be used
to develop and test the CognitiveOps Doctrine Framework.

The resulting responsibilities can be summarized as:

### L4 — WHY / WHAT

Mission purpose and desired outcome.

Owns:

- Mission objectives.
- Mission priorities.
- Mission constraints.
- Completion criteria.
- Mission-level consequences of navigation failure.

### L3 — WHERE / ROUTE

Strategic navigation and progress.

Owns:

- Position and orientation interpretation.
- Route selection.
- Guidance.
- Checkpoints.
- Terrain association at route level.
- Progress monitoring.
- Strategic recovery.

### L2 — WHAT LOCAL MANOEUVRE

Immediate interaction with the environment.

Owns:

- Local traversability.
- Immediate obstacles.
- Terrain interpretation.
- Tactical deviations.
- Local recovery.
- Selection of the next manoeuvre.

### L1 — HOW PHYSICALLY

Deterministic physical execution.

Owns:

- Vehicle movement.
- Steering.
- Speed.
- Traction.
- Actuator execution.
- Terrain-specific physical control.
- Low-level execution safety.

---

## 12. Architectural conclusion

FM 3-25.26 reinforces the separation already emerging from CognitiveOps:

    Mission
       ↓
      L4
       ↓
    strategic intent
       ↓
      L3
       ↓
    Guidance
       ↓
      L2
       ↓
    tactical manoeuvre
       ↓
      L1
       ↓
    physical movement

Perception provides observations of the environment.

Navigation estimates the state of the vehicle.

Memory provides temporal continuity.

Safety constrains what actions may be executed.

The important architectural lesson is that autonomous land navigation is
not a single capability.

It is the interaction of mission intent, localization, route reasoning,
terrain interpretation, tactical adaptation, memory and physical vehicle
control.

FM 3-25.26 therefore provides a useful source of navigation use cases for
developing and validating the CognitiveOps Doctrine Framework.
