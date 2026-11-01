"""Optional camera/VisionNN + existing deterministic L2 action advisory.

Does NOT instantiate L1, send serial commands or call L2.step().
No ultrasonic source exists in this stage: advisory is NOT safe to execute.
"""
from dataclasses import dataclass


@dataclass
class ShadowPerceptionReading:
    status: str
    visual: dict
    tactical: dict


class ShadowCameraObserver:
    def __init__(self, perception=None):
        if perception is None:
            from perception_module import PerceptionModule
            perception = PerceptionModule(mode="camera", gps_enabled=False)
        self.perception = perception

    def observe(self, guidance):
        try:
            result = self.perception.observe_llm()
            state = result.perception_state
            if state is None or state.confidence is None or state.confidence <= 0:
                raise ValueError("Camera or perception unavailable")
            regions = state.regions or []
            visual = {"confidence": state.confidence,
                      "obstacle_ahead": state.obstacle_ahead,
                      "free_direction": state.free_direction,
                      "summary": state.summary,
                      "regions": regions}
            if guidance["status"] != "OBSERVING_MANUAL_MOTION":
                return ShadowPerceptionReading("NAVIGATION_UNCERTAIN", visual,
                    {"action": "HOLD", "reason": guidance["status"],
                     "source": "SHADOW_GUARD", "executable": False})
            # Reuse ONLY the pure deterministic L2 policy; never call L2.step()
            # which accesses L1, triggers physical reverse/recovery and sends actions.
            from l2_tactical_planner import L2TacticalPlanner
            from rover_interfaces import RoverState
            policy = object.__new__(L2TacticalPlanner)
            policy._reverse_attempted = False
            action, reason, _, source = policy.decide_action(
                RoverState(armed=False, mode="SHADOW"),
                state, result.image_bytes,
                {"heading_error_deg": guidance["heading_error_deg"],
                 "distance_remaining_m": guidance["distance_m"]},
                result.gps_state)
            return ShadowPerceptionReading("CAMERA_OBSERVED", visual,
                {"action": action.value, "reason": reason, "source": source,
                 "executable": False, "ultrasonic": "NOT_READ"})
        except Exception as exc:
            return ShadowPerceptionReading("PERCEPTION_UNAVAILABLE",
                {"error": str(exc)}, {"action": "HOLD",
                "reason": "PERCEPTION_UNAVAILABLE",
                "source": "SHADOW_GUARD", "executable": False})

    def close(self):
        cap = getattr(self.perception, "cap", None)
        if cap is not None:
            cap.release()
