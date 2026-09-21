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

**Log:** `goto_test_nav_cam_5.log`

### Test
### Result
### Key observations
### Problems / limitations
### Conclusion


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
