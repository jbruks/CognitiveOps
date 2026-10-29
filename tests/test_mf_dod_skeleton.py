"""No-hardware first smoke test for existing L4 orchestration.

This increment verifies L4 with stub L3 and mock L1. Real L3 and L2
integration is the next step of Issue #5. No device or API calls occur.
"""
from dataclasses import dataclass
import sys
import types
import unittest
from unittest.mock import patch

# Prevent importing the camera/OpenAI-heavy perception module. The current
# L4 planner imports only the PerceptionResult type from that module.
perception_stub = types.ModuleType("perception_module")
perception_stub.PerceptionResult = type("PerceptionResult", (), {})
sys.modules["perception_module"] = perception_stub

from l4_mission_planner import L4MissionPlanner
from l3_models import GuidanceTask, GuidanceTaskType
from l4_models import Mission, MissionTask, MissionStatus


@dataclass
class FakeObservation:
    perception_state: object = None
    image_bytes: bytes | None = None


class MockL1:
    def __init__(self):
        self.stop_calls = 0
        self.commands = []

    def get_state(self):
        return {"mock": True}

    def get_front_sensor_state(self):
        return {"front_distance_cm": None, "front_blocked": False}

    def stop(self):
        self.stop_calls += 1


class FakePerception:
    def observe_llm(self):
        return FakeObservation()


class StubL3:
    def __init__(self, distances):
        self.distances = iter(distances)
        self.calls = 0
        self.last_guidance_task = None

    def step(self, rover_state, result, mission):
        self.calls += 1
        distance = next(self.distances)
        self.last_guidance_task = GuidanceTask(
            task_type=(GuidanceTaskType.HOLD if distance <= mission.arrival_radius_m
                       else GuidanceTaskType.FOLLOW_BEARING),
            desired_heading_deg=90.0,
            distance_remaining_m=distance,
            heading_error_deg=0.0,
        )
        return None


class SkeletonL4SmokeTest(unittest.TestCase):
    def test_one_objective_completes_without_hardware(self):
        l1 = MockL1()
        l3 = StubL3([18.0, 3.0])
        mission = Mission(task=MissionTask.GOTO, target_lat=39.0,
                          target_lon=-0.6, arrival_radius_m=5.0)
        with patch.object(L4MissionPlanner.__init__.__globals__["os"], "makedirs"):
            l4 = L4MissionPlanner(
                perception_module=FakePerception(),
                l1_rover_controler=l1,
                task_planner=l3,
                memory_system=object(),
                mission=mission,
            )
        l4.step()
        self.assertEqual(mission.status, MissionStatus.ACTIVE)
        l4.step()
        self.assertEqual(mission.status, MissionStatus.COMPLETED)
        self.assertEqual(l3.calls, 2)
        self.assertEqual(l1.stop_calls, 1)
        self.assertEqual(l1.commands, [])


if __name__ == "__main__":
    unittest.main()
