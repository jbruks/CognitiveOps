from l1_rover_controler_ra4m1 import L1RoverControler
from rover_interfaces import TacticalAction
import time


PORT = "/dev/serial/by-id/usb-Arduino_UNO_WiFi_R4_CMSIS-DAP_3CDC7544B664-if01"


def main():
    rover = L1RoverControler(PORT)
    rover.connect_and_prepare()

    try:
        print("\nFORWARD_LEFT durante 2 s")
        rover.execute_tactical_action(TacticalAction.FORWARD_LEFT)
        time.sleep(2)

        print("STOP")
        rover.execute_tactical_action(TacticalAction.STOP)
        time.sleep(1)

        print("\nFORWARD_RIGHT durante 2 s")
        rover.execute_tactical_action(TacticalAction.FORWARD_RIGHT)
        time.sleep(2)

        print("STOP")
        rover.execute_tactical_action(TacticalAction.STOP)

    finally:
        try:
            rover.execute_tactical_action(TacticalAction.STOP)
        except Exception:
            pass


if __name__ == "__main__":
    main()
