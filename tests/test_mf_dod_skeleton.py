"""No-hardware first smoke test for existing L4 orchestration.

This increment verifies L4 with stub L3 and mock L1. Real L3 and L2
integration is the next step of Issue #5. No device or API calls occur.
"""
from dataclasses import dataclass
from types import SimpleNamespace
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
from rover_interfaces import RoverState, PerceptionState, TacticalAction
from memory_system import MemorySystem


@dataclass
class FakeObservation:
    perception_state: object = None
    image_bytes: bytes | None = None


class MockL1:
    def __init__(self):
        self.stop_calls = 0
        self.commands = []

    def get_state(self):
        return RoverState(armed=False, mode="MOCK")

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


    def test_real_l3_guidance_with_simulated_phone_and_stub_l2(self):
        """Exercise real L3 GPS math through real L4; no hardware or GPT."""
        from lite_world_model.navigation_state import NavigationState

        # L3 depends on the perception/world-model and phone imports, but
        # receives synthetic readings. Avoid device discovery/network access.
        import importlib
        position_module = types.ModuleType("sensors.phone_position_service")
        attitude_module = types.ModuleType("sensors.phone_attitude_service")
        position_module.PhonePositionService = lambda: None
        attitude_module.PhoneAttitudeService = lambda: None
        with patch.dict(sys.modules, {
            "sensors.phone_position_service": position_module,
            "sensors.phone_attitude_service": attitude_module,
        }):
            from l3_task_planner import L3TaskPlanner

        class PhoneFeed:
            def __init__(self, samples):
                self.samples = iter(samples)

            def read(self):
                return next(self.samples)

        class StubL2:
            def __init__(self):
                self.tasks = []

            def step(self, rover_state, result, l3_task, observability=None):
                self.tasks.append(l3_task)
                return TacticalAction.MOVE_FORWARD, "SIMULATED_PROGRESS", None, "stub"

        def position(lat):
            return SimpleNamespace(latitude=lat, longitude=-0.6,
                                   horizontal_accuracy_m=1.0, gps_status=1,
                                   fresh=True, available=True, age_s=0.0)

        attitude = SimpleNamespace(heading_deg=0.0, fresh=True,
                                   available=True, age_s=0.0)
        l1 = MockL1()
        l2 = StubL2()
        memory = MemorySystem()
        l3 = L3TaskPlanner(l2_planner=l2, perception_module=object(),
                           memory_system=memory)
        l3.phone_position = PhoneFeed([position(38.9998), position(39.0)])
        l3.phone_attitude = PhoneFeed([attitude, attitude])
        mission = Mission(task=MissionTask.GOTO, target_lat=39.0,
                          target_lon=-0.6, arrival_radius_m=5.0)
        observation = FakeObservation(
            perception_state=PerceptionState(
                obstacle_ahead=False, free_direction="center",
                corridor_visible=True, confidence=1.0,
            )
        )

        class ConstantPerception:
            def observe_llm(self):
                return observation

        with patch.object(L4MissionPlanner.__init__.__globals__["os"], "makedirs"):
            l4 = L4MissionPlanner(
                perception_module=ConstantPerception(),
                l1_rover_controler=l1, task_planner=l3,
                memory_system=memory, mission=mission,
            )
        l4.step()
        self.assertEqual(mission.status, MissionStatus.ACTIVE)
        self.assertEqual(l3.last_guidance_task.task_type,
                         GuidanceTaskType.FOLLOW_BEARING)
        self.assertGreater(l3.last_guidance_task.distance_remaining_m, 15)
        self.assertEqual(len(l2.tasks), 1)
        self.assertEqual(l2.tasks[0]["task_type"], "FOLLOW_BEARING")
        self.assertEqual(l1.commands, [])

        l4.step()
        self.assertEqual(l3.last_guidance_task.task_type, GuidanceTaskType.HOLD)
        self.assertEqual(mission.status, MissionStatus.COMPLETED)
        self.assertEqual(len(l2.tasks), 1)
        self.assertEqual(l1.stop_calls, 1)
        self.assertEqual(l1.commands, [])



    def test_real_l2_forward_and_front_block_hold_without_hardware(self):
        """Real L4→L3→L2, with a strict fake actuation boundary."""
        # Import real L2 without importing the legacy OpenAI/Ollama client.
        # It is not used in deterministic step(), but imported at module load.
        llm_stub = types.ModuleType("llm_decision")
        llm_stub.TacticalLLMDecisionMaker = lambda: object()
        with patch.dict(sys.modules, {"llm_decision": llm_stub}):
            from l2_tactical_planner import L2TacticalPlanner
        from l3_task_planner import L3TaskPlanner

        class RecordingRover(MockL1):
            def __init__(self):
                super().__init__()
                self.front_blocked = False

            def get_front_sensor_state(self):
                return {
                    "front_distance_cm": 90.0 if not self.front_blocked else 20.0,
                    "front_distance_valid": True,
                    "front_blocked": self.front_blocked,
                }

            def execute_tactical_action(self, action):
                # In-memory log only. This object has no physical control method.
                self.commands.append(action)

        class PhoneFeed:
            def read(self):
                return SimpleNamespace(
                    latitude=38.9998, longitude=-0.6,
                    horizontal_accuracy_m=1.0, gps_status=1,
                    heading_deg=0.0, fresh=True, available=True, age_s=0.0,
                )

        class StaticPerception:
            llm_client = None

            def observe_llm(self):
                return FakeObservation(
                    perception_state=PerceptionState(
                        obstacle_ahead=False,
                        free_direction="center",
                        corridor_visible=True,
                        confidence=1.0,
                        summary="Synthetic three-sector clear corridor",
                        regions=[
                            {"name": "left", "traversable": True},
                            {"name": "front", "traversable": True},
                            {"name": "right", "traversable": True},
                        ],
                    )
                )

        rover = RecordingRover()
        perception = StaticPerception()
        # Prevent L2's legacy inference client from opening API/SSH channels
        # at construction, even though step() uses deterministic navigation.
        l2 = L2TacticalPlanner(
            rover_client=rover,
            perception_module=perception,
            world_builder=None,
            llm_enabled=False,
            human_on_loop=False,
        )
        memory = MemorySystem()
        l3 = L3TaskPlanner(l2_planner=l2, perception_module=perception,
                           memory_system=memory)
        l3.phone_position = PhoneFeed()
        l3.phone_attitude = PhoneFeed()
        mission = Mission(
            task=MissionTask.GOTO, target_lat=39.0, target_lon=-0.6,
            arrival_radius_m=5.0,
        )
        with patch.object(L4MissionPlanner.__init__.__globals__["os"], "makedirs"):
            l4 = L4MissionPlanner(
                perception_module=perception, l1_rover_controler=rover,
                task_planner=l3, memory_system=memory, mission=mission,
            )

        # Clear corridor: real L2 chooses MOVE_FORWARD, mock only records it.
        l4.step()
        self.assertEqual(l3.last_guidance_task.task_type,
                         GuidanceTaskType.FOLLOW_BEARING)
        self.assertEqual(rover.commands, [TacticalAction.MOVE_FORWARD])
        self.assertEqual(mission.status, MissionStatus.ACTIVE)

        # Front obstacle: existing L2 must return HOLD. This is one blocked
        # cycle only; do not exercise its autonomous-reverse recovery policy.
        rover.front_blocked = True
        l4.step()
        self.assertEqual(rover.commands,
                         [TacticalAction.MOVE_FORWARD, TacticalAction.HOLD])
        self.assertEqual(mission.status, MissionStatus.ACTIVE)
        self.assertEqual(l2._blocked_cycles, 1)
        self.assertEqual(rover.stop_calls, 0)


if __name__ == "__main__":
    unittest.main()
