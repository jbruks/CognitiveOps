import math
import time
import random

from pymavlink import mavutil

from rover_interfaces import RoverState, TacticalAction


class RoverClient:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.master = None

    def connect(self):
        print(f"Connecting to rover on {self.connection_string} ...")
        self.master = mavutil.mavlink_connection(self.connection_string)
        self.master.wait_heartbeat()
        print(
            f"Heartbeat received: "
            f"sys={self.master.target_system} comp={self.master.target_component}"
        )

    def set_guided_mode(self):
        mode = "GUIDED"
        mode_id = self.master.mode_mapping().get(mode)
        if mode_id is None:
            raise RuntimeError("GUIDED mode not available in mode mapping")

        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_MODE,
            0,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id,
            0,
            0,
            0,
            0,
            0,
        )

        ack = self.master.recv_match(type="COMMAND_ACK", blocking=True, timeout=3)
        print(f"Set mode ACK: {ack}")

    def arm(self):
        self.master.arducopter_arm()
        self.master.motors_armed_wait()
        print("Rover armed")

    def connect_and_prepare(self):
        self.connect()
        self.set_guided_mode()
        self.arm()

    def get_state(self) -> RoverState:
        hb = self.master.recv_match(type="HEARTBEAT", blocking=False)
        vfr = self.master.recv_match(type="VFR_HUD", blocking=False)
        gps = self.master.recv_match(type="GLOBAL_POSITION_INT", blocking=False)

        mode_name = "UNKNOWN"
        armed = False
        speed = 0.0
        heading_deg = 0.0
        x = 0.0
        y = 0.0

        if hb is not None:
            mode_name = mavutil.mode_string_v10(hb)
            armed = bool(hb.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)

        if vfr is not None:
            speed = float(getattr(vfr, "groundspeed", 0.0))
            heading_deg = float(getattr(vfr, "heading", 0.0))

        if gps is not None:
            x = gps.lat / 1e7
            y = gps.lon / 1e7

        return RoverState(
            x=x,
            y=y,
            heading_deg=heading_deg,
            speed_m_s=speed,
            armed=armed,
            mode=mode_name,
        )

    def execute_tactical_action(self, action: TacticalAction):
        print(f"Executing tactical action: {action.value}")

        if action == TacticalAction.MOVE_FORWARD:
            self.move_forward(distance_m=900, speed_m_s=12)
        elif action == TacticalAction.TURN_LEFT:
            #self.turn_relative(angle_deg=-90.0)
            self.turn_relative(angle_deg=random.randint(-90,90))

        elif action == TacticalAction.TURN_RIGHT:
            #self.turn_relative(angle_deg=90.0)
            self.turn_relative(angle_deg=random.randint(-90,90))

        elif action == TacticalAction.STOP:
            self.stop()

        elif action == TacticalAction.HOLD:
            self.stop()

    def move_forward(self, distance_m: float, speed_m_s: float = 0.5):
        """
        Move forward relative to the rover body frame.
        Uses BODY_OFFSET_NED position target: x=forward meters, y=0.
        """
        type_mask_use_position = 3580  # official ArduPilot Rover docs

        self.master.mav.set_position_target_local_ned_send(
            0,  # time_boot_ms
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_FRAME_BODY_OFFSET_NED,
            type_mask_use_position,
            distance_m,   # x forward
            0.0,          # y right
            0.0,          # z down
            0.0, 0.0, 0.0,
            0.0, 0.0, 0.0,
            0.0, 0.0,
        )
        print(f"[ROVER] move forward {distance_m:.2f} m")

    def turn_relative(self, angle_deg: float):
        """
        Turn in place by commanding a target yaw relative to the body frame.
        Positive yaw is to the right in this usage pattern.
        """
        yaw_rad = math.radians(abs(angle_deg))
        if angle_deg < 0:
            yaw_rad = -yaw_rad

        type_mask_use_yaw = 2559  # official ArduPilot Rover docs

        self.master.mav.set_position_target_local_ned_send(
            0,
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_FRAME_BODY_OFFSET_NED,
            type_mask_use_yaw,
            0.0, 0.0, 0.0,
            0.0, 0.0, 0.0,
            0.0, 0.0, 0.0,
            yaw_rad,
            0.0,
        )
        print(f"[ROVER] turn relative {angle_deg:.1f} deg")
        time.sleep(1.5)

    def stop(self):
        """
        Stop by sending zero forward speed in body frame.
        Velocity commands should be refreshed periodically if used continuously.
        """
        type_mask_use_velocity = 3559  # official ArduPilot Rover docs

        self.master.mav.set_position_target_local_ned_send(
            0,
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_FRAME_BODY_OFFSET_NED,
            type_mask_use_velocity,
            0.0, 0.0, 0.0,
            0.0, 0.0, 0.0,   # vx, vy, vz
            0.0, 0.0, 0.0,
            0.0, 0.0,
        )
        print("[ROVER] stop")
