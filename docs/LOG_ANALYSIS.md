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
### Result
### Key observations
### Problems / limitations
### Conclusion


## 4. Overall findings

Resumen de lo aprendido comparando las tres etapas.


## 5. Next development priorities

Cambios que justifican las pruebas realizadas.
