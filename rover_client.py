from rover_interfaces import RoverState, TacticalAction


class RoverClient:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.master = None

    def connect(self):
        print(f"Connecting to rover on {self.connection_string} ...")
        # your existing MAVLink connection code here
        print("Connected.")

    def get_state(self) -> RoverState:
        # replace with your real telemetry read
        return RoverState(
            x=0.0,
            y=0.0,
            heading_deg=0.0,
            speed_m_s=0.0,
            armed=True,
            mode="GUIDED"
        )

    def execute_tactical_action(self, action: TacticalAction):
        print(f"Executing tactical action: {action.value}")

        if action == TacticalAction.MOVE_FORWARD:
            self.move_forward(distance_m=1.0)
        elif action == TacticalAction.TURN_LEFT:
            self.turn_relative(angle_deg=-20)
        elif action == TacticalAction.TURN_RIGHT:
            self.turn_relative(angle_deg=20)
        elif action == TacticalAction.STOP:
            self.stop()
        elif action == TacticalAction.HOLD:
            self.hold_position()

    def move_forward(self, distance_m: float):
        print(f"[ROVER] Move forward {distance_m:.1f} m")
        # call your existing primitive here

    def turn_relative(self, angle_deg: float):
        print(f"[ROVER] Turn relative {angle_deg:.1f} deg")
        # call your existing primitive here

    def stop(self):
        print("[ROVER] Stop")
        # call your existing stop primitive here

    def hold_position(self):
        print("[ROVER] Hold / reassess")
        # for now this can be same as stop()
        self.stop()
