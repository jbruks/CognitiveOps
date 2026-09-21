# CognitiveOps — Log Analysis

## 1. NAV_OK — Navigation baseline

**Log:** `goto_test_nav_only_20260916_NAV_OK.log`

### Test

Autonomous GO_TO_POINT test without real camera perception.

The rover used phone position and attitude as the navigation source.
Perception was simulated as a clear corridor, allowing the test to focus
primarily on the Navigation → Guidance → Tactical → Control loop.

Target:
- Latitude: 39.424570
- Longitude: -0.319972
- Arrival radius: 5 m
- Mode: AUTONOMOUS

### Result

SUCCESS.

The rover autonomously reached the target area and completed the mission.

Final reported distance to target: **4.24 m**.

L4 detected arrival inside the configured 5 m radius, changed Guidance
to HOLD and commanded STOP.

### Key observations

- At startup, the rover remained stopped while phone navigation data was
  unavailable.

- Once valid phone position and attitude became available, L3 generated
  FOLLOW_BEARING guidance and autonomous movement started.

- L2 used FORWARD_LEFT, FORWARD_RIGHT and MOVE_FORWARD actions to follow
  the requested bearing.

- No MOVE_BACKWARD action was observed during the navigation run.

- The rover repeatedly corrected its heading around the target bearing
  rather than following a perfectly straight trajectory.

- Position estimates showed significant GPS uncertainty and fluctuations,
  particularly during the initial part of the run.

- A temporary stale phone-position condition occurred later in the mission.
  The system responded by entering HOLD and stopping until valid navigation
  information became available again.

- Despite navigation noise and heading corrections, the closed loop
  eventually converged to the target.

### Problems / limitations

- Phone GPS accuracy varied considerably during the test.

- Distance-to-target was therefore not monotonically decreasing and should
  not be interpreted as an exact measurement of physical rover progress.

- Heading correction produced an observable left/right correction pattern
  rather than smooth trajectory control.

- The test used simulated clear perception, so it does not validate obstacle
  detection or obstacle avoidance.

### Conclusion

This test demonstrates that, under an assumed clear local environment, the
current architecture can autonomously close a GO_TO_POINT loop using phone
position and attitude:

Navigation → Guidance → Tactical → Control

The rover was able to acquire navigation data, orient toward the target,
make repeated course corrections, progress toward the destination and
terminate the mission automatically inside the configured 5 m arrival radius.

This test should therefore be considered the navigation baseline for
subsequent experiments involving real visual perception.

## 2. NAV+CAM — Initial camera integration

**Log:** `goto_test_nav_cam_20260917_OK.log`

### Test

Autonomous GO_TO_POINT test with real camera perception enabled.

The purpose of this test was to verify the integration of visual perception
with the existing Navigation → Guidance → Tactical → Control loop.

The test was performed in a relatively constrained garden environment,
with the target located beyond the chalet/building area. Therefore, this
was not intended as a clean point-to-point navigation validation.

### Result

INTEGRATION SUCCESSFUL — MISSION NOT COMPLETED.

The complete autonomous loop operated with real camera perception for
29 cognitive cycles.

Navigation and Guidance remained active while L2 adapted its tactical
actions according to both the requested bearing and the perceived local
environment.

The run ended before reaching the GO_TO_POINT target.

### Key observations

- Real camera perception was successfully incorporated into every
  cognitive cycle.

- L3 continuously generated FOLLOW_BEARING guidance from phone position
  and attitude.

- L2 did not simply follow the global bearing. Its actions changed according
  to the locally perceived environment.

- The rover used all four available movement primitives during the test:
  MOVE_FORWARD, FORWARD_LEFT, FORWARD_RIGHT and MOVE_BACKWARD.

- Tactical action distribution:
  - FORWARD_RIGHT: 8
  - FORWARD_LEFT: 8
  - MOVE_FORWARD: 7
  - MOVE_BACKWARD: 6

- Perception identified both traversable terrain and non-traversable
  obstacles, including walls and other objects.

- Local obstacle avoidance and conservative backward manoeuvres produced
  deviations from the direct route requested by Guidance.

### Problems / limitations

- The environment was relatively constrained and the destination was
  located beyond the chalet/building area.

- L2 only has local visual information and therefore cannot plan a global
  route around a large obstacle such as a building.

- Distance to the target did not decrease consistently. GPS uncertainty
  and local tactical manoeuvres both contributed to this behaviour.

- The mission was not completed, so this test cannot demonstrate autonomous
  point-to-point navigation with perception.

### Conclusion

This test demonstrates successful integration of real visual perception
into the autonomous cognitive loop.

It shows that L2 can combine global Guidance intent with local visual
information and modify the rover's immediate behaviour accordingly.

It also exposes an important architectural limitation: local tactical
avoidance alone is not sufficient to solve navigation around large
environmental structures that require strategic route planning.

This test should therefore be considered an integration milestone rather
than a GO_TO_POINT navigation success.

## 3. NAV+CAM TOLL — Field test

**Logs:**

- `goto_test_nav_cam_toll01.log`
- `goto_test_nav_cam_toll02.log`

### Test

Autonomous GO_TO_POINT field test with real camera perception enabled.

The test was performed along an outdoor tree-lined boulevard, over a
significantly longer and more realistic route than the previous experiments.
The environment included generally traversable terrain together with
vegetation, stones, branches, curbs and locally constrained passages.

The mission was executed in two consecutive runs because the system was
stopped and subsequently resumed. Therefore, TOLL01 and TOLL02 should be
interpreted as two parts of the same field mission rather than as independent
tests.

The test exercised the complete autonomous loop:

Perception → Navigation → Guidance → Tactical → Control

Phone position and attitude provided the navigation state, real camera images
provided local environmental perception, L3 continuously generated guidance
toward the destination, and L2 selected short tactical manoeuvres according
to both global direction and local conditions.

### Result

SUCCESS.

The complete field mission reached the GO_TO_POINT destination and terminated
automatically inside the configured arrival radius.

The mission evolved approximately as follows:

- TOLL01 started at about 69.6 m from the target.
- TOLL01 ended at about 43.5 m from the target.
- TOLL02 resumed at about 41.3 m from the target.
- During the final approach, reported distance fluctuated around 6–10 m.
- The final navigation solution reported approximately 4.73 m to the target.
- Guidance changed to HOLD.
- L4 declared the GO_TO_POINT mission completed.
- L1 stopped the rover.

The mission therefore demonstrated global convergence despite local obstacle
avoidance manoeuvres, significant GPS uncertainty and repeated tactical
deviations from the direct target direction.

### Key observations

- The rover made substantial global progress over the complete mission,
  reducing the reported target distance from approximately 69.6 m to
  approximately 4.7 m.

- TOLL01 was predominantly a progression and orientation-correction phase.
  Across 83 complete tactical cycles it executed approximately:

  - MOVE_FORWARD: 40
  - FORWARD_RIGHT: 35
  - FORWARD_LEFT: 5
  - MOVE_BACKWARD: 3

- TOLL02 contained a more complex local environment and produced a more
  varied tactical behaviour. Across approximately 110 tactical actions:

  - MOVE_FORWARD: 32
  - FORWARD_RIGHT: 37
  - FORWARD_LEFT: 22
  - MOVE_BACKWARD: 19

- Real visual perception materially influenced tactical behaviour. The rover
  did not simply execute the direction requested by Guidance.

- When the local environment was clear and traversable, L2 generally allowed
  forward progress or selected a directional correction consistent with the
  heading error.

- When Perception reported an unsafe immediate environment, L2 could override
  the globally desired direction and choose a conservative manoeuvre.

- A representative case occurred near the beginning of TOLL02. Dense
  vegetation was detected at immediate range, with no safe traversable ground
  visible ahead. Although Guidance continued requesting progress toward the
  target, L2 selected MOVE_BACKWARD.

- After backing away from the vegetation, a subsequent perception cycle
  identified a usable corridor toward the front/right. L2 then selected
  FORWARD_RIGHT and resumed progress.

- This provides evidence of an important closed-loop behaviour:

  detect local obstruction
  → deviate from global guidance
  → re-observe
  → identify a traversable alternative
  → resume progress
  → continue converging toward the global target

- Guidance remained active throughout local tactical deviations. The target
  bearing and heading error were recalculated from the current navigation
  state rather than assuming that the rover remained on a predefined path.

- The rover therefore did not require every tactical action to reduce the
  target distance. Local actions could temporarily prioritize safety while
  later Guidance cycles attempted to recover progress toward the destination.

- Navigation remained a significant source of uncertainty. GPS accuracy
  varied considerably during the mission. In TOLL01 it ranged from a few
  metres to approximately 20 m, while TOLL02 commonly reported uncertainty
  above 10 m.

- Consequently, distance_remaining_m was not monotonic. Some apparent
  increases or decreases in distance are comparable to the GPS uncertainty
  itself and cannot be interpreted directly as physical rover displacement.

- Position freshness and position accuracy behaved as different properties.
  A navigation sample could be fresh while still having poor reported GPS
  accuracy.

- Temporary invalid/stale navigation conditions caused Guidance to enter
  HOLD rather than continuing movement with invalid navigation information.
  Navigation subsequently recovered and the mission continued.

- The final approach showed several fluctuations in reported distance before
  eventually entering the 5 m arrival radius. Given the GPS uncertainty,
  these fluctuations are consistent with the limitations of the navigation
  source used in this experiment.

### Problems / limitations

- Phone GPS accuracy was poor relative to the 5 m arrival radius, especially
  during TOLL02. The final reported distance should therefore be interpreted
  as the navigation system's estimate rather than as a precise physical
  measurement of the rover-to-target distance.

- The current system distinguishes navigation freshness from validity but
  does not yet make full use of GPS accuracy when deciding how much confidence
  to place in Guidance.

- Tactical behaviour is based primarily on the current camera observation.
  The rover does not yet maintain a sufficiently rich spatial representation
  for deliberate route planning around large obstacles.

- MOVE_BACKWARD occurred considerably more often in TOLL02. Some of these
  actions clearly correspond to locally obstructed or uncertain situations,
  but the logs alone are insufficient to determine whether every backward
  manoeuvre was necessary.

- Perception sometimes classified relatively rough terrain, stones,
  vegetation or constrained passages conservatively. Image/log correlation
  is required before deciding whether these classifications were correct or
  unnecessarily restrictive.

- The simplified PerceptionState and the richer perception description are
  not always perfectly consistent. Some cycles contain richer obstacle
  information than is represented by obstacle_ahead/free_direction alone.

- Tactical steering remains based on discrete fixed-duration primitives.
  Heading correction therefore produces repeated left/right/right-forward
  manoeuvres rather than smooth continuous trajectory control.

- The two logs represent a mission that was interrupted and resumed.
  Consequently, the transition between TOLL01 and TOLL02 is not a continuous
  autonomous execution and should not be interpreted as such.

### Conclusion

This is the strongest field validation of the CognitiveOps autonomy
architecture obtained so far.

Unlike NAV_OK, the mission was not performed under simulated clear-perception
conditions. Unlike the initial NAV+CAM experiment, it was performed over a
route where the rover could make meaningful global progress toward the
destination.

The experiment demonstrates that the current architecture can combine:

- real visual perception,
- phone-based position and attitude,
- deterministic global Guidance,
- LLM-based local tactical reasoning,
- deterministic physical execution,

within a closed autonomous GO_TO_POINT loop.

Most importantly, the experiment provides evidence that local tactical
avoidance and global navigation can coexist. L2 was able to temporarily
deviate from the direction requested by L3 when the immediate environment
appeared unsafe, while subsequent Navigation and Guidance cycles continued
to drive the system toward the global destination.

The mission ultimately entered the configured arrival radius and terminated
automatically.

The result should not be interpreted as demonstrating general autonomous
navigation in arbitrary environments. GPS uncertainty remains substantial,
perception decisions still require validation against the recorded images,
and the architecture does not yet provide strategic route planning around
large obstacles.

However, this experiment demonstrates an operational end-to-end autonomous
field loop in which Perception, Navigation, Guidance, Tactical reasoning and
Control interacted successfully during a complete GO_TO_POINT mission.

The next analysis step is to correlate selected tactical cycles with their
saved camera images, especially obstacle encounters, MOVE_BACKWARD actions
and recovery manoeuvres. This will determine whether the observed tactical
behaviour was justified by the physical environment and identify which
limitations belong to Perception, L2 tactical reasoning or Navigation.

## 4. Overall findings

The three experiments show a progressive validation of the CognitiveOps
autonomy architecture.

The first NAV_OK test demonstrated the basic autonomous GO_TO_POINT loop
under an assumed clear environment. Navigation and Guidance were sufficient
to orient the rover, correct its trajectory and terminate the mission inside
the configured arrival radius.

The NAV+CAM integration test introduced real visual perception. It showed
that L2 could combine the global direction requested by Guidance with local
environmental information and modify its actions when the direct route was
not appropriate. It also exposed the limitation of purely local tactical
reasoning when facing larger environmental structures.

The TOLL field test combined both capabilities over a longer and more
realistic outdoor mission. The rover encountered vegetation, stones, branches,
terrain boundaries and constrained passages while continuing to receive a
global GO_TO_POINT objective.

Across the three stages, the main architectural result is that global
Guidance and local Tactical reasoning can operate as distinct but cooperating
functions:

Navigation determines the current state.
Guidance continuously defines the direction toward the mission objective.
Perception describes the immediate environment.
L2 adapts the next local manoeuvre to that environment.
L1 executes the selected physical primitive.

The field test showed that a tactical deviation does not necessarily represent
a navigation failure. L2 can temporarily prioritize local safety, after which
Navigation and Guidance recompute the situation and attempt to recover
progress toward the destination.

This produces the intended closed-loop behaviour:

Perception
→ Navigation
→ Guidance
→ Tactical decision
→ Control
→ physical movement
→ new observation
→ recomputation

The tests also showed that the principal limitations are no longer simply
whether the rover can move autonomously toward a GPS target. The important
remaining questions concern the quality of the information and decisions
inside that loop: navigation uncertainty, perception reliability, tactical
decision quality and recovery from local deviations.

The current system should therefore be considered an operational experimental
autonomy stack rather than a complete general-purpose autonomous navigation
system.
