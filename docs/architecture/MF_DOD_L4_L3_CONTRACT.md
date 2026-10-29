# MF-DoD — L4 ↔ L3 Navigation Contract (POC 1)

**Issue:** [#4 — Cognitive architecture and level contracts](https://github.com/jbruks/CognitiveOps/issues/4)  
**Status:** Agreed conceptual contract; implementation pending  
**Branch:** `feature/mf-dod-cognitive-architecture`  
**Decision:** POC 1 develops L4/L3 and reuses L2, VisionNN, L1 and RA4M1 unchanged.

## 1. Principle

**L4 specifies the navigation objective and its purpose. L3 decides how to pursue it, monitors progress and reports the result.**

- L4 owns mission intent, objective selection, doctrine use, mission progress and mission-level replanning.
- L3 owns navigation strategy and existing deterministic GPS/heading Guidance.
- L3 must not redefine mission intent; L4 must not select motor actions.
- A navigation target must be authorized and evaluated for feasibility before physical execution.
- Navigation completion does **not** imply successful inspection or mission completion.

## 2. Downward contract: NavigationObjective

Proposed **minimal conceptual Python model** (not yet committed as runtime code):

```python
@dataclass
class NavigationObjective:
    objective_id: str
    latitude: float
    longitude: float
    radius_m: float = 5.0
    purpose: str = ""
```

| Field | Meaning |
|---|---|
| `objective_id` | Stable correlation key across multiple execution cycles |
| `latitude` / `longitude` | Approved target location, decimal degrees |
| `radius_m` | Arrival tolerance, not GPS accuracy |
| `purpose` | Human-readable reason for the displacement |

L3 also needs access to **separately enforced navigation constraints**, especially the approved area and excluded zones. These must not be entrusted solely to GPT or assumed from the `purpose` string. Their representation is pending Issue #4 implementation design.

Example (illustrative, **not a surveyed or authorized waypoint**):

```json
{
  "objective_id": "OBJ-001",
  "latitude": 39.299215,
  "longitude": -0.615309,
  "radius_m": 5.0,
  "purpose": "Reach an approved runway observation position"
}
```

## 3. Upward contract: NavigationResult

```python
@dataclass
class NavigationResult:
    objective_id: str
    status: str
    distance_remaining_m: float | None = None
    reason: str | None = None
```

| Status | Semantics |
|---|---|
| `PENDING` | Objective has not started |
| `IN_PROGRESS` | Navigation is underway |
| `COMPLETED` | Navigation arrival conditions have been met |
| `BLOCKED` | Current route/strategy is not making safe progress; higher-level review may be needed |
| `FAILED` | Navigation cannot continue under current constraints |

Example:

```json
{
  "objective_id": "OBJ-001",
  "status": "BLOCKED",
  "distance_remaining_m": 18.0,
  "reason": "Repeated tactical HOLD; no verified progress"
}
```

`reason` is a concise, observable explanation; it is not unrestricted chain-of-thought output. L3 must never fabricate physical completion acknowledgements or sensor measurements.

## 4. Expected control/feedback flow

```text
Operator mission + maps + restrictions
                  |
                  v
           L4 selects objective
                  |
             NavigationObjective
                  |
                  v
          L3 GPS/heading Guidance
                  |
           existing L3 → L2 adapter
                  |
                  v
          L2 (unchanged) → L1 (unchanged)
                  |
          existing action/status signals
                  |
                  v
          L3 NavigationResult
                  |
                  v
          L4 mission assessment
             |         |
        next goal   replan / report
```

L3 maintains a stable `objective_id` across cycles. L3 may continue deterministic Guidance without any GPT request while navigation progresses normally. Significant navigation failures may trigger a bounded cognitive query later; inference must never block safety-critical control.

## 5. Compatibility and change boundary

| Existing component | Agreed treatment |
|---|---|
| `l4_models.py` / `Mission` | Preserve the existing `GO_TO_POINT` path; extend only when required |
| `l4_mission_planner.py` | Produce navigation objectives and evaluate structured navigation feedback |
| `l3_models.py` / `GuidanceTask` | Reuse GuidanceTask; add small contract types if necessary |
| `l3_task_planner.py` | Accept objectives, reuse GPS computations, expose navigation results |
| `l2_tactical_planner.py` | **No changes in POC 1** |
| `vision_nn_worker.py` / perception | **No changes in POC 1** |
| `l1_rover_controler_ra4m1.py` and firmware | **No changes in POC 1** |

In the existing runtime, L3 calls L2 with a dictionary containing `FOLLOW_BEARING`, heading, distance and safety priority. L2 returns action and decision metadata to L3; L3 currently returns an action toward L4. Preserve this internal path and interpret available signals within L3, rather than introducing new L2 or L1 protocols.

## 6. Skeleton verification — no movement

The first executable test must use mock rover hardware, simulated perception and deterministic fixture data. It must not open a serial device, arm motors, access a camera, require GPS or call GPT.

Acceptance scenarios:
1. **Progress:** objective remains identifiable across successive simulated cycles.
2. **Arrival:** L3 reports `COMPLETED` on valid simulated arrival conditions; L4 does not automatically mark an observation mission complete.
3. **Temporary hold:** L3 can represent non-progress without inventing an alternate motor action.
4. **Persistent block:** L3 reports `BLOCKED` with an observable reason for L4.
5. **Invalid position or missing inputs:** safe non-movement outcome and explicit diagnostic status.
6. **Regression:** existing GO_TO_POINT interfaces remain compatible.

## 7. Deferred decisions

- Whether status will be an enum or another validated type in the actual code.
- Exact objective/result validation and lifecycle methods.
- How approved geography and navigation constraints are supplied and enforced.
- How progress and blockage thresholds are determined and tested.
- Whether L4 invokes a separate adapter or extends the existing planner method.
- How L4 represents higher-level *inspection* completion and supporting evidence.

Resolve only when inspecting call sites and designing the smallest executable integration; avoid implementing a generic multi-agent message bus.

## 8. Agreed POC scope

**POC 1:** Mission input → L4 cognitive planning and DoctrineService → L3 navigation strategy/Guidance → unchanged L2 → unchanged L1, with feedback interpreted at L3/L4.

**POC 2:** Optional later L2 cognitive enhancement, tracked separately in [#11](https://github.com/jbruks/CognitiveOps/issues/11).

**Reference:** [Architecture Design Decisions, ADR-011](MF_DOD_DESIGN_DECISIONS.md).
