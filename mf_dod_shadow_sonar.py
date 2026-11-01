"""Explicitly opt-in, diagnostic-only RA4M1 sonar query.

Allowlist: GET_DISTANCE only. This interface has NO L1, arming, stop,
movement, or servo methods. Serial opening can reset some controllers,
so motors/servos MUST be physically disconnected beforehand.
"""
import math
import re

DEFAULT_DEVICE = "/dev/serial/by-id/usb-Arduino_UNO_WiFi_R4_CMSIS-DAP_3CDC7544B664-if01"
_PATTERN = re.compile(r"^DISTANCE_CM=([-+]?(?:\d+(?:\.\d*)?|\.\d+))\s+BLOCKED=([01])(?:\s+SENSOR_STATE=\S+)?$")


def parse_distance(line):
    match = _PATTERN.fullmatch(line.strip())
    if not match:
        raise ValueError("Malformed ultrasonic response")
    distance, blocked = float(match.group(1)), match.group(2) == "1"
    if not math.isfinite(distance) or distance <= 0:
        return {"front_distance_cm": None, "front_blocked": None,
                "front_distance_valid": False, "status": "INVALID_NO_CLEARANCE"}
    return {"front_distance_cm": distance, "front_blocked": blocked,
            "front_distance_valid": True, "status": "OBSERVED"}


class ReadOnlySonar:
    def __init__(self, device=DEFAULT_DEVICE, timeout_s=1.0, serial_factory=None):
        self.device = device
        self.timeout_s = timeout_s
        self._factory = serial_factory
        self._port = None

    def open(self):
        if self._port is not None:
            raise RuntimeError("Already open")
        factory = self._factory
        if factory is None:
            from serial import Serial
            factory = Serial
        # No other program may share this controller port.
        self._port = factory(self.device, 115200, timeout=self.timeout_s,
                             write_timeout=self.timeout_s)
        return self

    def read(self):
        if self._port is None:
            raise RuntimeError("Sonar serial port is not open")
        try:
            # The only serial command in this entire module:
            self._port.write(b"GET_DISTANCE\n")
            self._port.flush()
            for _ in range(5):
                raw = self._port.readline()
                if raw.startswith(b"DISTANCE_CM="):
                    return parse_distance(raw.decode("ascii", errors="replace"))
            raise TimeoutError("No valid ultrasonic response")
        except Exception as exc:
            return {"front_distance_cm": None, "front_blocked": None,
                    "front_distance_valid": False,
                    "status": "SENSOR_ERROR", "error": str(exc)}

    def close(self):
        if self._port is not None:
            self._port.close()
            self._port = None
