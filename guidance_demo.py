from rover_client import RoverClient
from perception_module import PerceptionModule
from guidance_navigator import GuidanceNavigator


def main():
    rover = RoverClient("udp:127.0.0.1:14551")
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

    navigator = GuidanceNavigator(rover, perception)
    #navigator.run_loop(steps=12, delay_s=2.0)
    navigator.run_loop(steps=500, delay_s=25)


if __name__ == "__main__":
    main()
