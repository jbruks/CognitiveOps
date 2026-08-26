from rover_client_ra4m1 import RoverClient
from perception_module import PerceptionModule
from guidance_navigator import GuidanceNavigator

from memory_system import MemorySystem
from l3_task_planner import L3TaskPlanner
from l4_mission_planner import L4MissionPlanner

def main():
    print("[MAIN] Starting full autonomy stack")


    # =========================
    # L1 — Rover (RA4M1)
    # =========================
    rover = RoverClient("/dev/ttyACM0")
    rover.connect_and_prepare()

    # =========================
    # Perception
    # =========================
    perception = PerceptionModule(mode="camera")

    # =========================
    # L2 — Tactical Navigation
    # =========================
    navigator = GuidanceNavigator(
        rover,
        perception,
        llm_enabled=True,
        fallback_enabled=True,
    )

    # =========================
    # Memory System
    # =========================
    memory = MemorySystem()

    # =========================
    # L3 — Task Planner
    # =========================
    l3 = L3TaskPlanner(
        navigator=navigator,
        perception_module=perception,
        memory_system=memory,
    )

    # =========================
    # L4 — Mission Planner
    # =========================
    l4 = L4MissionPlanner(
        rover_client=rover,
        task_planner=l3,
        memory_system=memory,
    )

    print("[MAIN] Stack initialized (L4 → L3 → L2 → L1)")

    # =========================
    # RUN LOOP
    # =========================
    l4.run_loop(steps=25, delay_s=7)


if __name__ == "__main__":
    main()

