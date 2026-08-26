from config import DEFAULT_STEPS, LOOP_DELAY_S
from rover_client_ra4m1 import RoverClient
from perception_module import PerceptionModule
from guidance_navigator import GuidanceNavigator


def main():
    rover = RoverClient("/dev/ttyACM4")
    rover.connect_and_prepare()

    perception = PerceptionModule(
        scenario_sequence=[
            "corridor_forward",
            "corridor_forward",
            "obstacle_left_open",
            "corridor_forward",
            "obstacle_right_open",
            "blocked",
            "uncertain",
        ],
        loop_sequence=True,
    )

    navigator = GuidanceNavigator(
        rover,
        perception,
        llm_enabled=True,
        fallback_enabled=True,
    )
    navigator.run_loop(steps=DEFAULT_STEPS, delay_s=LOOP_DELAY_S)


if __name__ == "__main__":
    main()
