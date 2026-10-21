import json
import math
import time
import urllib.request
from dataclasses import dataclass
from typing import Optional

from sensors.phyphox_discovery import discover_phyphox_attitude


@dataclass
class PhoneAttitudeReading:
    heading_deg: Optional[float]
    phyphox_time_s: Optional[float]

    available: bool
    fresh: bool
    measuring: bool

    age_s: Optional[float]


class PhoneAttitudeService:
    def __init__(
        self,
        stale_after_s: float = 1.0,
        timeout_s: float = 2.0,
    ):
        self.stale_after_s = stale_after_s
        self.timeout_s = timeout_s

        self._endpoint = None

        self._last_phyphox_time = None
        self._last_update_monotonic = None
        self._last_heading_deg = None

    def _ensure_endpoint(self):
        if self._endpoint is None:
            self._endpoint = discover_phyphox_attitude()

        return self._endpoint

    def read(self) -> PhoneAttitudeReading:
        endpoint = self._ensure_endpoint()

        if endpoint is None:
            return self._unavailable_reading(False)

        url = (
            f"{endpoint}/get?"
            "attT&attW&attX&attY&attZ"
        )

        try:
            with urllib.request.urlopen(
                url,
                timeout=self.timeout_s,
            ) as response:
                data = json.load(response)

            measuring = bool(
                data.get("status", {}).get("measuring", False)
            )

            buffers = data["buffer"]

            t = self._last_value(buffers, "attT")
            w = self._last_value(buffers, "attW")
            x = self._last_value(buffers, "attX")
            y = self._last_value(buffers, "attY")
            z = self._last_value(buffers, "attZ")

            if None in (t, w, x, y, z):
                return self._unavailable_reading(measuring)

            heading = self._heading_from_quaternion(
                w, x, y, z
            )

            now = time.monotonic()

            if (
                self._last_phyphox_time is None
                or t != self._last_phyphox_time
            ):
                self._last_phyphox_time = t
                self._last_update_monotonic = now
                self._last_heading_deg = heading

            if self._last_update_monotonic is None:
                age_s = None
            else:
                age_s = now - self._last_update_monotonic

            fresh = (
                measuring
                and age_s is not None
                and age_s <= self.stale_after_s
            )

            return PhoneAttitudeReading(
                heading_deg=self._last_heading_deg,
                phyphox_time_s=self._last_phyphox_time,
                available=self._last_heading_deg is not None,
                fresh=fresh,
                measuring=measuring,
                age_s=age_s,
            )

        except Exception:
            self._endpoint = None
            return self._unavailable_reading(False)

    def _unavailable_reading(
        self,
        measuring: bool,
    ) -> PhoneAttitudeReading:
        now = time.monotonic()

        if self._last_update_monotonic is None:
            age_s = None
        else:
            age_s = now - self._last_update_monotonic

        return PhoneAttitudeReading(
            heading_deg=self._last_heading_deg,
            phyphox_time_s=self._last_phyphox_time,
            available=self._last_heading_deg is not None,
            fresh=False,
            measuring=measuring,
            age_s=age_s,
        )

    @staticmethod
    def _last_value(buffers, name):
        values = buffers.get(name, {}).get("buffer", [])

        if not values:
            return None

        return float(values[-1])

    @staticmethod
    def _heading_from_quaternion(w, x, y, z):
        vx = 2.0 * (x * y - w * z)
        vy = 1.0 - 2.0 * (x * x + z * z)

        return math.degrees(
            math.atan2(vx, vy)
        ) % 360.0


if __name__ == "__main__":
    service = PhoneAttitudeService()

    try:
        while True:
            r = service.read()

            heading = (
                "UNKNOWN"
                if r.heading_deg is None
                else f"{r.heading_deg:7.2f}°"
            )

            age = (
                "UNKNOWN"
                if r.age_s is None
                else f"{r.age_s:.2f}s"
            )

            print(
                f"HEADING={heading}  "
                f"fresh={r.fresh}  "
                f"available={r.available}  "
                f"measuring={r.measuring}  "
                f"age={age}"
            )

            time.sleep(0.2)

    except KeyboardInterrupt:
        print()
