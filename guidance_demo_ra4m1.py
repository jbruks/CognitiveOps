from l1_rover_controler_ra4m1 import L1RoverControler
from perception_module import PerceptionModule
from l2_tactical_planner import L2TacticalPlanner
from memory_system import MemorySystem
from l3_task_planner import L3TaskPlanner
from l4_mission_planner import L4MissionPlanner
from lite_world_model import WorldBuilder
from utils.xlogger import XLogger

def main():
    #print("[MAIN] Starting full autonomy stack")
    #print("___________________________________")
    XLogger.log("MAIN", "Full autonomy stack initialization")

    # =========================
    # L1 — Rover (RA4M1)
    # =========================
    l1_rover_controler = L1RoverControler("/dev/ttyACM0")
    l1_rover_controler.connect_and_prepare()

    # =========================
    # Perception
    # =========================
    perception = PerceptionModule(mode="camera")

    # =========================
    # L2 — Tactical Navigation
    # =========================
    l2_planner = L2TacticalPlanner(
        l1_rover_controler,
        perception,
        WorldBuilder,
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
        l2_planner=l2_planner,
        perception_module=perception,
        memory_system=memory,
    )

    # =========================
    # L4 — Mission Planner
    # =========================
    l4 = L4MissionPlanner(
        l1_rover_controler=l1_rover_controler,
        task_planner=l3,
        memory_system=memory,
    )

    #print("[MAIN] Stack initialized (L4 → L3 → L2 → L1)")
    XLogger.log("MAIN", "Full autonomy stack initialized (L4 → L3 → L2 → L1)")
    
    # =========================
    # RUN LOOP
    # =========================
    l4.run_loop(steps=5, delay_s=7)


if __name__ == "__main__":
    main()

