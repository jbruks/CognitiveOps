from rover_interfaces import RoverState
from perception_module import PerceptionModule
from guidance_navigator import GuidanceNavigator


class DummyRoverClient:
    def get_state(self):
        return RoverState(armed=True, mode="GUIDED")

    def execute_tactical_action(self, action):
        print(f"EXECUTE -> {action.value}")


def main():
    rover = DummyRoverClient()
    perception = PerceptionModule(
        scenario_sequence=[
            "corridor_forward",
            "obstacle_left_open",
            "obstacle_right_open",
            "blocked",
            "uncertain",
        ],
        loop_sequence=False,
    )
    navigator = GuidanceNavigator(
        rover,
        perception,
        llm_enabled=True,
        fallback_enabled=True,
    )

    for _ in range(5):
        navigator.step()


if __name__ == "__main__":
    main()
