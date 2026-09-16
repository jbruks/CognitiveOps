import argparse
import select
import sys
import termios
import tty
import time

from l1_rover_controler_ra4m1 import L1RoverControler
from perception_module import PerceptionModule
from l2_tactical_planner import L2TacticalPlanner
from memory_system import MemorySystem
from l3_task_planner import L3TaskPlanner
from l4_mission_planner import L4MissionPlanner
from lite_world_model import WorldBuilder
from utils.xlogger import XLogger
from l4_models import Mission, MissionTask, MissionStatus

def key_pressed():
    readable, _, _ = select.select([sys.stdin], [], [], 0)

    if readable:
        return sys.stdin.read(1).lower()

    return None

def main():
    parser = argparse.ArgumentParser(
        description="Run a GO_TO_POINT rover mission"
    )

    parser.add_argument(
        "target_lat",
        type=float,
        help="Target latitude in decimal degrees",
    )

    parser.add_argument(
        "target_lon",
        type=float,
        help="Target longitude in decimal degrees",
    )

    parser.add_argument(
        "--radius",
        type=float,
        default=2.0,
        help="Arrival radius in meters (default: 2.0)",
        
    )
    
    parser.add_argument(
        "--no-camera",
        action="store_true",
        help="Disable camera perception and assume a clear corridor",
    )
    
    parser.add_argument(
        "--autonomous",
        action="store_true",
        help="Execute tactical actions without operator approval",
    )

    args = parser.parse_args()
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
    if args.no_camera:
        perception = PerceptionModule(
            mode="simulated",
            default_scenario="corridor_forward",
        )
    else:
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
        human_on_loop=not args.autonomous,
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
        target_lat=args.target_lat,
        target_lon=args.target_lon,
        arrival_radius_m=args.radius,
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
    # GO_TO_POINT MISSION LOOP
    # =========================
    try:
        execution_mode = "AUTONOMOUS" if args.autonomous else "SUPERVISED"

        XLogger.log(
            "MAIN",
            f"GO_TO_POINT mission started. Mode={execution_mode}",
        )

        while mission.status != MissionStatus.COMPLETED:

            # 1. Cognitive cycle:
            #    Navigation -> L3 -> L2 -> [operator approval] -> L1
            l4.step()

            if mission.status == MissionStatus.COMPLETED:
                break

            # 2. In supervised mode, operator rejection aborts the mission.
            #    L2 has already commanded HOLD.
            if not args.autonomous and not l2_planner.last_action_approved:
                mission.status = MissionStatus.ABORTED
                XLogger.log(
                    "MAIN",
                    "Mission aborted by operator",
                )
                break

            # 3. Tactical action executes for a controlled interval.
            XLogger.log(
                "MAIN",
                f"Executing tactical action for 3 seconds. Mode={execution_mode}",
            )
            time.sleep(3.0)

            # 4. Physical STOP before starting a new cognitive cycle.
            XLogger.log("MAIN", "Inter-cycle STOP")
            l1_rover_controler.stop()
        

    except KeyboardInterrupt:
        mission.status = MissionStatus.ABORTED
        XLogger.log("MAIN", "Mission aborted by Ctrl+C")

    finally:
        XLogger.log("MAIN", "Stopping rover")
        l1_rover_controler.stop()

if __name__ == "__main__":
    main()

