# CognitiveOps — Log Analysis

## 1. Purpose

This document records the systematic analysis of rover execution logs.

The objective is to reconstruct rover behaviour from experimental evidence
and understand the interaction between:

Perception → Navigation → Guidance → Tactical → Control

The document separates:
- observed evidence,
- interpretation,
- identified limitations,
- and proposed improvements.

---

## 2. Reference Logs

### 2.1 NAV_OK — Navigation baseline

Log:
`goto_test_nav_only_20260916_NAV_OK.log`

Purpose:
Establish the baseline behaviour of autonomous GO_TO_POINT navigation
without camera perception.

---

### 2.2 NAV+CAM — Initial camera integration

Log:
`goto_test_nav_cam_5.log`

Purpose:
Study the first integration of real visual perception with autonomous
navigation and tactical control.

---

### 2.3 NAV+CAM TOLL — Field navigation test

Logs:
`goto_test_nav_cam_toll01.log`
`goto_test_nav_cam_toll02.log`

These two logs correspond to the same field mission, interrupted and
subsequently resumed.

This is the current primary reference experiment.

---

## 3. Analysis Method

### 3.1 Cognitive cycle

For each relevant cycle:

PERCEPTION
→ NAVIGATION
→ GUIDANCE
→ TACTICAL
→ L1 EXECUTION

### 3.2 Navigation variables

- Position
- GPS accuracy
- Heading
- Position freshness
- Heading freshness

### 3.3 Guidance variables

- Target bearing
- Heading error
- Distance remaining

### 3.4 Perception variables

- Obstacle ahead
- Free direction
- Confidence
- Semantic summary
- Relevant detected objects / regions

### 3.5 Tactical variables

- L2 proposed action
- Safety-envelope intervention, if any
- Final executed action

---

## 4. NAV_OK Analysis

### 4.1 Mission overview
### 4.2 Navigation behaviour
### 4.3 Guidance behaviour
### 4.4 Tactical behaviour
### 4.5 Mission convergence
### 4.6 Relevant observations
### 4.7 Conclusions

---

## 5. NAV+CAM Analysis

### 5.1 Mission overview
### 5.2 Navigation behaviour
### 5.3 Perception behaviour
### 5.4 Guidance behaviour
### 5.5 Tactical behaviour
### 5.6 Interaction between perception and guidance
### 5.7 Relevant observations
### 5.8 Conclusions

---

## 6. TOLL Field Test Analysis

### 6.1 Mission overview
### 6.2 Reconstruction of the complete mission
### 6.3 Navigation behaviour
### 6.4 Guidance behaviour
### 6.5 Visual perception behaviour
### 6.6 Tactical decisions
### 6.7 Obstacle encounters
### 6.8 Tactical deviations from global guidance
### 6.9 Recovery toward the target
### 6.10 Final approach and mission completion
### 6.11 Relevant observations
### 6.12 Conclusions

---

## 7. Image / Log Correlation

For selected cognitive cycles:

Image
↔ Perception interpretation
↔ Navigation state
↔ Guidance request
↔ Tactical decision
↔ Physical rover behaviour

---

## 8. Cross-Test Comparison

### 8.1 NAV_OK vs NAV+CAM
### 8.2 NAV+CAM vs TOLL
### 8.3 Effect of visual perception
### 8.4 Effect of GPS uncertainty
### 8.5 Evolution of tactical behaviour

---

## 9. Observed Behaviours

### 9.1 Global convergence
### 9.2 Heading correction / zigzag
### 9.3 Obstacle avoidance
### 9.4 Backward manoeuvres
### 9.5 Recovery after tactical deviation
### 9.6 Oscillations or repeated actions
### 9.7 Unexpected behaviours

---

## 10. Architecture Findings

### 10.1 Perception
### 10.2 Navigation
### 10.3 L3 Guidance
### 10.4 L2 Tactical
### 10.5 L1 / RA4M1
### 10.6 Interaction between cognitive levels

---

## 11. Demonstrated Capabilities

Capabilities supported directly by experimental evidence.

---

## 12. Limitations and Open Questions

Issues or behaviours identified by the logs that require further evidence
or investigation.

---

## 13. Candidate Improvements

Potential changes derived from experimental evidence.

No modification should be considered necessary solely because it appears
in this section.

---

## 14. Conclusions

Current assessment of the autonomous navigation architecture based on
the analysed experimental evidence.
