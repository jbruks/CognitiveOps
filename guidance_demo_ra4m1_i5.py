from l1_rover_controler_ra4m1 import L1RoverControler
from perception_module import PerceptionModule
from l2_tactical_planner import L2TacticalPlanner
from memory_system import MemorySystem
from l3_task_planner import L3TaskPlanner
from l4_mission_planner import L4MissionPlanner
from lite_world_model import WorldBuilder
from utils.xlogger import XLogger

from l4_models import Mission, MissionTask

def main():
    #print("[MAIN] Starting full autonomy stack")
    #print("___________________________________")
    XLogger.log("MAIN", "Full autonomy stack initialization")

    # =========================
    # L1 — Rover (RA4M1)
    # =========================
    l1_rover_controler = L1RoverControler("/dev/serial/by-id/usb-Arduino_UNO_WiFi_R4_CMSIS-DAP_3CDC7544B664-if01")
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
    # Mission — GO_TO_POINT
    # =========================
    mission = Mission(
        task=MissionTask.GOTO,
        target_lat=39.470000,
        target_lon=-0.500000,
        arrival_radius_m=2.0,
    )

    # =========================
    # L4 — Mission Planner
    # =========================
    l4 = L4MissionPlanner(
        l1_rover_controler=l1_rover_controler,
        perception_module=perception,
        task_planner=l3,
        memory_system=memory,
        mission=mission,
    )
    
   

    XLogger.log("MAIN", "Full autonomy stack initialized (L4 → L3 → L2 → L1)")
    
    # =========================
    # RUN LOOP
    # =========================
    l4.run_loop(steps=5, delay_s=0)


if __name__ == "__main__":
    main()

