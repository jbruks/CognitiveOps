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

**Recorded image sets:**

- TOLL01: 83 images
- TOLL02: 118 images
- Total: 201 images

### Test

Autonomous GO_TO_POINT field test with real camera perception enabled.

The test was performed along an outdoor tree-lined boulevard, over a
significantly longer and more realistic route than the previous experiments.
The environment included generally traversable terrain together with
vegetation, stones, branches, tree trunks, curbs and locally constrained
passages.

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

After the initial log analysis, the complete recorded camera datasets were
also inspected and correlated with the corresponding navigation, perception
and tactical events.

This made it possible to evaluate not only what the software reported, but
also whether important tactical decisions were consistent with the physical
scene observed by the rover.

### Result

SUCCESS.

The complete field mission reached the GO_TO_POINT destination according to
the implemented navigation criterion and terminated automatically inside the
configured 5 m arrival radius.

The mission evolved approximately as follows:

- TOLL01 started at about 69.6 m from the target.
- TOLL01 ended at about 43.5 m from the target.
- TOLL02 resumed at about 41.3 m from the target.
- During the final approach, reported distance fluctuated around 6–10 m.
- The final navigation solution reported approximately 4.73 m to the target.
- Guidance changed to HOLD.
- L4 declared the GO_TO_POINT mission completed.
- L1 stopped the rover.

The final GPS sample reported an accuracy of approximately 6.37 m. Therefore,
the 4.73 m final distance must be interpreted as the navigation system's
estimate rather than as a precise physical measurement.

The mission demonstrated global convergence according to the implemented
navigation criterion despite local obstacle avoidance manoeuvres, substantial
GPS uncertainty and repeated tactical deviations from the direct target
direction.

### Experimental data and timing

The complete mission produced 201 recorded camera observations:

- TOLL01: 83 images
- TOLL02: 118 images

All recorded images have a resolution of 320 × 240 pixels, corresponding to
76,800 pixels per observation, and were stored as JPEG files.

TOLL01 generated approximately 3.10 MiB of recorded image data, while TOLL02
generated approximately 4.28 MiB.

The complete mission therefore produced approximately 7.38 MiB of recorded
camera data.

Typical JPEG size was approximately 38–39 KB per image, with individual files
ranging approximately from 22 KB to 55 KB.

Image storage was consequently not a significant resource cost in this
experiment.

The relatively low 320 × 240 resolution was nevertheless sufficient for the
system to identify operationally relevant environmental structures including
vegetation, tree trunks, stones, branches, terrain boundaries and traversable
corridors.

This does not establish that 320 × 240 is an optimal perception resolution.
It only establishes that this resolution contained sufficient visual
information to support the behaviours observed during this field test.

The complete two-part field experiment required at least approximately one
hour of real elapsed time.

This wall-clock duration was observed during the field experiment rather than
reconstructed from log timestamps, because the current logs do not contain
sufficiently granular timing information for each processing stage.

During the experiment, a complete cognitive analysis cycle typically required
at least approximately 15 seconds before physical execution.

With 201 recorded observation cycles, this gives a lower-bound estimate of:

201 cycles × ~15 s ≈ 3,015 s ≈ 50 minutes

The logs additionally contain approximately 200 explicit physical execution
windows of approximately 3 seconds:

200 actions × 3 s ≈ 600 s ≈ 10 minutes

The combination is therefore already approximately:

~50 min cognitive processing
+ ~10 min physical execution
= ~60 min

before accounting for communication, STOP commands, transitions,
startup, interruption/resume overhead and other delays.

These values should be interpreted as approximate timing evidence rather than
a precise performance benchmark. The ~15 s cognitive-cycle value is a field
observation, while the ~3 s action windows are explicitly represented in the
execution logs.

The effective execution pattern was approximately:

observe
→ reason for ~15 s or more
→ execute short primitive for ~3 s
→ stop
→ observe again

The rover was therefore operating as a relatively slow sense–reason–act system
rather than as a high-frequency continuous motion planner.

This timing was acceptable for the slow rover and mostly static environment
used in the experiment, but represents an important limitation for faster
motion or dynamic environments.

### Key observations

#### Guidance and Tactical reasoning operated as distinct functions

Real visual perception materially influenced tactical behaviour. The rover
did not simply execute the direction requested by Guidance.

When the local environment was clear and traversable, L2 generally allowed
forward progress or selected a directional correction consistent with the
heading error.

When the immediate environment appeared unsafe, L2 could reject the direct
implementation of the Guidance direction and select a conservative manoeuvre
instead.

The image/log correlation provides particularly strong evidence that L3 and
L2 were performing different functions.

In one TOLL02 episode, the rover was almost perfectly aligned with the global
target:

- rover heading: approximately 136.38°
- target bearing: approximately 137.20°
- heading error: approximately +0.82°
- distance remaining: approximately 30.25 m

However, the camera showed a large tree trunk blocking the central path at
immediate range.

From the Guidance perspective, the rover was correctly oriented toward the
objective. From the Tactical perspective, continuing directly forward was
not safe.

This provides a clear experimental distinction:

global alignment does not imply local traversability.

L3 should therefore continue to express where progress is desired, while L2
is responsible for deciding whether and how that progress can be executed in
the immediate physical environment.

#### TOLL01 tactical recovery

TOLL01 was predominantly a progression and orientation-correction phase.
Across 83 tactical cycles it executed approximately:

- MOVE_FORWARD: 40
- FORWARD_RIGHT: 35
- FORWARD_LEFT: 5
- MOVE_BACKWARD: 3

Image correlation confirmed that important MOVE_BACKWARD actions were
consistent with the observed physical environment.

A representative sequence occurred around images 0024–0025.

At image 0024, the rover was facing dense vegetation with very little useful
forward corridor. Detailed perception described non-traversable vegetation
across the frontal sectors and no clear forward route.

Guidance still required a substantial correction toward the right, but L2
selected MOVE_BACKWARD instead of attempting to force progress into the
vegetation.

The following observation showed that backing away had changed the available
geometry. Space for manoeuvring became visible again and L2 selected
FORWARD_RIGHT, returning to progress consistent with Guidance.

A stronger sequence occurred around images 0070–0073.

The rover again approached dense vegetation that effectively blocked the
forward field of view. L2 selected MOVE_BACKWARD.

After further observation the environment remained constrained, resulting in
another backward manoeuvre. Once additional space and a central corridor
became visible, L2 changed to FORWARD_RIGHT and resumed progress toward the
global objective.

The observed pattern was:

local obstruction
→ MOVE_BACKWARD
→ re-observation
→ obstruction still present
→ additional recovery
→ traversable corridor becomes visible
→ directional forward movement resumes

This provides visual evidence that MOVE_BACKWARD sometimes acted as a useful
tactical recovery manoeuvre rather than simply representing failed progress.

#### TOLL02 tactical behaviour and recovery

TOLL02 contained a more complex local environment and produced more varied
tactical behaviour. Across approximately 110 tactical actions:

- MOVE_FORWARD: 32
- FORWARD_RIGHT: 37
- FORWARD_LEFT: 22
- MOVE_BACKWARD: 19

The beginning of TOLL02 exposed both a questionable tactical decision and a
successful subsequent recovery.

Guidance initially requested a correction toward the right, with a heading
error of approximately +34°. The scene already contained a stump and
significant vegetation, but L2 selected FORWARD_LEFT.

The following image showed the rover at immediate range from dense vegetation,
with essentially no safe frontal corridor.

Perception then reported an obstacle ahead, no free direction and no visible
corridor. L2 correctly selected MOVE_BACKWARD.

After backing away, subsequent observation exposed usable terrain toward the
front/right. Guidance continued requesting a rightward correction and L2
selected FORWARD_RIGHT.

The sequence can therefore be interpreted as:

Guidance requests rightward progress
→ questionable FORWARD_LEFT action
→ rover reaches dense vegetation
→ MOVE_BACKWARD
→ new observation exposes usable space
→ FORWARD_RIGHT
→ progress resumes

This demonstrates both the capability and the current limitation of L2.

The rover can recover from an undesirable local state, but it does not yet
explicitly reason about the fact that its previous action contributed to that
state.

#### Recovery emerges from the closed loop

Across TOLL01 and TOLL02, image/log correlation confirms a recurring behaviour:

detect local obstruction
→ temporarily deviate from global Guidance
→ execute a short manoeuvre
→ observe the new physical situation
→ reassess traversability
→ select another tactical action
→ eventually resume progress toward the global objective

This behaviour does not yet constitute deliberate local path planning.

Each tactical decision is still primarily based on the current observation.

Nevertheless, recovery can emerge from repeated execution of the complete
Perception–Navigation–Guidance–Tactical–Control loop.

A backward action should therefore not automatically be interpreted as a
navigation failure. In several recorded cases it created a new viewpoint and
additional manoeuvring space from which forward progress became possible.

#### Evidence for Tactical and Navigation Memory

The visual sequences expose a limitation that was less obvious from the logs
alone: L2 reacts to successive situations but does not explicitly represent
the temporal relationship between them.

The current behaviour is approximately:

observation → decision
→ observation → decision
→ observation → decision

The field evidence suggests that future tactical reasoning could benefit from
representing information such as:

- a passage was already attempted,
- the previous manoeuvre increased or reduced obstruction,
- the rover has already backed away from the same local situation,
- a previously blocked direction has become available,
- several tactical cycles have occurred without useful progress.

Repeated local recovery without restored global progress may also be
information that should eventually be visible to L3.

This provides experimental motivation for Tactical Memory and Navigation
Memory.

It does not yet determine how Memory should be implemented. The field test
supports the requirement for temporal context, not a particular memory
architecture.

#### Rich perception versus simplified PerceptionState

Image/log correlation confirmed that the simplified PerceptionState can lose
information that exists in the richer perception output.

During at least one TOLL01 vegetation encounter, the detailed perception
described frontal vegetation as non-traversable and reported that no clear
forward route was available, while the simplified representation indicated a
more optimistic local state.

L2 nevertheless selected MOVE_BACKWARD because its decision also had access
to the camera image and richer perception context.

This indicates that the transformation from rich environmental interpretation
to simplified world representation is not currently information-preserving.

The simplified state remains useful as a compact interface, but its semantics
and reduction rules require further validation before it can be treated as
the complete representation of local traversability.

#### Perception was useful but sometimes conservative

The recorded images confirm that Perception was not merely producing
decorative information.

Vegetation, trunks, stones, branches, rough ground, terrain boundaries and
visible corridors materially affected tactical decisions.

At the same time, some scenes suggest conservative interpretation of terrain
that the crawler may physically be capable of traversing, including small
stones, gravel and moderately irregular ground.

The present evidence identifies this as an area for further testing but does
not justify defining new traversability thresholds yet.

A future representation may need to distinguish more than simply traversable
versus non-traversable, for example:

SAFE AND EASY
→ SAFE BUT DIFFICULT
→ UNCERTAIN
→ NON-TRAVERSABLE
→ DANGEROUS

Such categories should be validated experimentally against the physical
capabilities of the rover.

#### Navigation uncertainty became dominant near the target

Navigation remained a significant source of uncertainty throughout the
mission.

GPS samples could be fresh while still having poor positional accuracy,
demonstrating that freshness and accuracy are different properties.

This became particularly important during the final approach.

When the reported distance to the target was approximately 9.77 m, one GPS
sample reported an accuracy of approximately 13.49 m.

During the final cycle:

- distance_remaining_m ≈ 4.73 m
- configured arrival radius = 5 m
- reported GPS accuracy ≈ 6.37 m

The implemented logic correctly followed its current rule:

distance_remaining < arrival_radius
→ Guidance HOLD
→ mission completed
→ STOP

However, the experiment does not establish that the rover was physically
4.73 m from the target with that precision.

It establishes that the current navigation estimate entered the configured
arrival radius.

The experiment therefore identifies two independent navigation questions:

1. Is this navigation information recent enough to use?
2. Is this navigation information accurate enough for the decision currently
   being made?

The current system handles the first question more explicitly than the
second.

### Problems / limitations

- Phone GPS accuracy was poor relative to the 5 m arrival radius. Mission
  completion therefore represents satisfaction of the implemented navigation
  estimate, not independently verified physical proximity to the target.
- GPS accuracy is observed and logged but is not yet fully incorporated into
  the confidence placed in Guidance or the mission-completion criterion.
- Cognitive latency was high relative to physical action duration. A
  cognitive cycle typically required at least approximately 15 seconds,
  while a movement primitive lasted approximately 3 seconds.
- The rover therefore operated using a stop-and-reason pattern suitable for
  slow movement in a mostly static environment, but this timing would be a
  significant limitation for faster vehicles or dynamic scenes.
- The current logs do not provide sufficiently granular timestamps to
  determine Perception, L2, L3 and communication latency independently.
- L2 remains primarily reactive. It does not explicitly remember recently
  attempted passages, unsuccessful manoeuvres or repeated recovery attempts.
- The rover does not yet maintain a sufficiently rich persistent spatial
  representation for deliberate route planning around large obstacles.
- Some tactical decisions were questionable. In particular, the initial
  FORWARD_LEFT action in TOLL02 was followed by an immediate vegetation
  encounter.
- MOVE_BACKWARD is sometimes clearly justified and useful, as confirmed by
  the images, but this does not establish that every backward manoeuvre in
  the complete mission was necessary or optimal.
- Perception sometimes appears conservative when evaluating rough but
  potentially traversable terrain.
- The simplified PerceptionState can omit or distort information present in
  the richer perception output.
- Tactical steering remains based on discrete fixed-duration primitives
  rather than smooth continuous trajectory control.
- The transition between TOLL01 and TOLL02 was interrupted and should not be
  interpreted as continuous autonomous execution.
- The test demonstrates local reactive recovery, but not persistent local
  planning, global obstacle-aware route planning or general navigation in
  arbitrary environments.

### Architectural implications

The field evidence supports the current separation between Navigation,
Guidance and Tactical reasoning.

Navigation estimates the rover state.

Guidance determines where progress should be made relative to the global
objective.

Tactical reasoning determines whether and how that requested progress can be
executed safely in the immediate environment.

Therefore:

correct Guidance ≠ safe local action

and:

temporary tactical deviation ≠ navigation failure

The experiments also provide direct field evidence for introducing temporal
reasoning into the architecture.

The requirement should initially be expressed as a capability rather than an
implementation:

Tactical Memory:
retain recent local attempts, obstacles, manoeuvres and their consequences.

Navigation Memory:
retain route progress, deviations and whether local recovery is restoring
progress toward the global objective.

Mission Memory is expected to become important for richer reconnaissance
missions, but GO_TO_POINT alone does not yet provide sufficient evidence to
define its detailed requirements.

The experiment also establishes an approximate performance baseline for the
current cognitive implementation:

- cognitive cycle: approximately 15 seconds or more,
- physical primitive: approximately 3 seconds,
- recorded image resolution: 320 × 240,
- complete image dataset: approximately 7.38 MiB.

Future changes such as onboard inference should be compared quantitatively
against this baseline rather than assumed to improve performance.

Future field tests should therefore instrument explicit timestamps around
camera acquisition, Perception inference, WorldModel update, Navigation,
Guidance, Tactical inference, command transmission and physical execution.

### Conclusion

This is the strongest field validation of the CognitiveOps autonomy
architecture obtained so far.

The experiment demonstrates that the current architecture can combine:

- real visual perception,
- phone-based position and attitude,
- deterministic global Guidance,
- LLM-based local tactical reasoning,
- deterministic physical execution,

within a closed autonomous GO_TO_POINT loop.

The image/log correlation strengthens the original result.

It confirms that several conservative tactical actions were physically
justified by vegetation or obstacles visible in the recorded scene. It also
shows cases where backing away changed the rover's viewpoint, exposed a new
traversable corridor and allowed progress to resume.

The strongest architectural result is therefore not simply that the rover
reached a GPS objective.

The experiment demonstrates a closed loop in which global Guidance and local
visual Tactical reasoning remained distinct:

global objective
→ Guidance
→ local visual interpretation
→ tactical manoeuvre
→ physical movement
→ new observation
→ recomputation

The rover maintained a geographic objective while locally adapting its
movement to real obstacles, temporarily rejecting direct progress when the
scene appeared unsafe and subsequently resuming progress when a traversable
alternative became available.

At the same time, the experiment clearly exposes the present frontier of the
system:

- tactical reasoning lacks explicit temporal history,
- perception and the simplified world representation are imperfect,
- local recovery is reactive rather than deliberately planned,
- navigation accuracy is not yet fully represented in decision confidence,
- terminal mission completion can occur at a scale comparable to GPS
  uncertainty,
- cognitive processing is slow relative to physical action execution.

The result should therefore not be interpreted as demonstrating general
autonomous navigation in arbitrary environments.

A more precise statement is:

CognitiveOps demonstrated an operational end-to-end autonomous field loop in
which global Guidance and visual Tactical reasoning remained separate and
cooperating functions. The rover maintained a geographic objective, adapted
locally to real obstacles, performed observable recovery manoeuvres and
resumed progress until the implemented navigation criterion for mission
completion was satisfied.

The image-correlated analysis also converts several previously theoretical
architecture questions into experimentally motivated requirements,
particularly Tactical Memory, Navigation Memory, explicit treatment of
navigation uncertainty and improved timing instrumentation.

These requirements should be investigated through further field experiments
before committing to specific implementations.
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
