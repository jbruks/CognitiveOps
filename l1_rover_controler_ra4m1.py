import time
from typing import Dict

import serial

from rover_interfaces import RoverState, TacticalAction
from utils.xlogger import XLogger


class L1RoverControler:
    """
    Drop-in tactical rover client for a temporary RA4M1 backend.

    Expected line-based serial protocol on the controller side:
      PING                 -> PONG
      ARM                  -> ACK ARM
      DISARM               -> ACK DISARM
      STOP                 -> ACK STOP
      HOLD                 -> ACK HOLD
      MOVE_FORWARD         -> ACK MOVE_FORWARD
      FORWARD_LEFT            -> ACK FORWARD_LEFT
      FORWARD_RIGHT           -> ACK FORWARD_RIGHT
      MOVE_BACKWARD           -> ACK MOVE_BACKWARD
      GET_STATE            -> STATE armed=1 mode=GUIDED speed_m_s=0 heading_deg=0 x=0 y=0

    Notes:
    - The controller only needs to execute short, discrete actions.
    - If GET_STATE is not implemented yet, the cached state is still updated locally
      after connect/arm/commands so the rest of the guidance stack can run.
    """

    def __init__(
        self,
        connection_string: str,
        baudrate: int = 115200,
        timeout_s: float = 1.0,
        command_delay_s: float = 0.05,
    ):
        self.connection_string = connection_string
        self.baudrate = baudrate
        self.timeout_s = timeout_s
        self.command_delay_s = command_delay_s
        self.serial_conn = None
        self.state = RoverState(armed=False, mode="UNKNOWN")

    def connect(self):
        XLogger.log("L1", f"Connecting to RA4M1 rover controller on {self.connection_string} ...")
        self.serial_conn = serial.Serial(
            self.connection_string,
            self.baudrate,
            timeout=self.timeout_s,
            write_timeout=self.timeout_s,
        )
        time.sleep(2.0)
        self._drain_input()
        response = self._request("PING", expected_prefixes=("PONG",), required=True)
        if response:
            XLogger.log("L1", f"Controller ping OK: {response}")
        else:
            XLogger.log("L1", "Controller ping not implemented yet; continuing in local-state mode")

    def arm(self):
        response = self._request("ARM", expected_prefixes=("ACK ARM",), required=False)
        if response:
            XLogger.log("L1", "Rover armed")
        else:
            XLogger.log("L1", "ARM command sent without ACK; assuming armed for temporary backend")
        self.state.armed = True
        self.state.mode = "GUIDED"

    def disarm(self):
        response = self._request("DISARM", expected_prefixes=("ACK DISARM",), required=False)
        if response:
            XLogger.log("L1", "Rover disarmed")
        else:
            XLogger.log("L1", "DISARM command sent without ACK; updating local state")
        self.state.armed = False
        self.state.speed_m_s = 0.0
        self.state.mode = "STANDBY"

    def connect_and_prepare(self):
        self.connect()
        self.arm()

    def get_state(self) -> RoverState:
        response = self._request("GET_STATE", expected_prefixes=("STATE",), required=False)
        if response and response.startswith("STATE"):
            parsed = self._parse_state_line(response)
            self.state = RoverState(
                x=float(parsed.get("x", self.state.x)),
                y=float(parsed.get("y", self.state.y)),
                heading_deg=float(parsed.get("heading_deg", self.state.heading_deg)),
                speed_m_s=float(parsed.get("speed_m_s", self.state.speed_m_s)),
                armed=self._parse_bool(parsed.get("armed", self.state.armed)),
                mode=str(parsed.get("mode", self.state.mode)),
            )
        return self.state

    def execute_tactical_action(self, action: TacticalAction):
        #print(f"Executing tactical action via RA4M1: {action.value}")
        XLogger.log("L1", f"Executing tactical action via RA4M1: {action.value}")


        command_map = {
            TacticalAction.MOVE_FORWARD: "MOVE_FORWARD",
            TacticalAction.FORWARD_LEFT: "FORWARD_LEFT",
            TacticalAction.FORWARD_RIGHT: "FORWARD_RIGHT",
            TacticalAction.MOVE_BACKWARD: "MOVE_BACKWARD",
            TacticalAction.STOP: "STOP",
            TacticalAction.HOLD: "HOLD",
        }
        command = command_map[action]

        expected = (f"ACK {command}",)
        self._request(command, expected_prefixes=expected, required=False)

        if action in (TacticalAction.STOP, TacticalAction.HOLD):
            self.state.speed_m_s = 0.0
        elif action == TacticalAction.MOVE_FORWARD:
            self.state.speed_m_s = max(self.state.speed_m_s, 0.1)
        self.state.mode = "GUIDED"

    def stop(self):
        self.execute_tactical_action(TacticalAction.STOP)

    def _request(self, line: str, expected_prefixes=(), required: bool = True):
        self._ensure_connected()
        self._write_line(line)
        if not expected_prefixes:
            time.sleep(self.command_delay_s)
            return None

        deadline = time.time() + self.timeout_s
        while time.time() < deadline:
            response = self._read_line()
            if not response:
                continue
            if any(response.startswith(prefix) for prefix in expected_prefixes):
                return response
            if response.startswith("ERR"):
                if required:
                    raise RuntimeError(f"Controller returned error for '{line}': {response}")
                XLogger.log("L1", f"Controller error for '{line}': {response}")
                return None

        if required:
            raise TimeoutError(f"Timeout waiting for response to '{line}'")
        return None

    def _ensure_connected(self):
        if self.serial_conn is None or not self.serial_conn.is_open:
            raise RuntimeError("Rover serial connection is not open")

    def _write_line(self, line: str):
        payload = (line.strip() + "\n").encode("utf-8")
        
        print(f"[L1 SERIAL TX] {payload!r}")
        
        self.serial_conn.write(payload)
        self.serial_conn.flush()

    def _read_line(self):
        raw = self.serial_conn.readline()

        if not raw:
            print("[L1 SERIAL RX] <timeout / no data>")
            return None

        print(f"[L1 SERIAL RX RAW] {raw!r}")

        response = raw.decode("utf-8", errors="replace").strip()
        print(f"[L1 SERIAL RX] {response}")

        return response

    def _drain_input(self):
        if self.serial_conn is None:
            return
        while self.serial_conn.in_waiting:
            self.serial_conn.readline()

    @staticmethod
    def _parse_state_line(line: str) -> Dict[str, str]:
        parts = line.split()
        fields: Dict[str, str] = {}
        for token in parts[1:]:
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            fields[key] = value
        return fields

    @staticmethod
    def _parse_bool(value) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
