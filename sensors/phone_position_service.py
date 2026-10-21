import json
import time
import urllib.request
from dataclasses import dataclass
from typing import Optional

from sensors.phyphox_discovery import discover_phyphox_attitude


@dataclass
class PhonePositionReading:
    latitude: Optional[float]
    longitude: Optional[float]
    horizontal_accuracy_m: Optional[float]
    phyphox_time_s: Optional[float]

    gps_status: Optional[int]

    available: bool
    fresh: bool
    measuring: bool

    age_s: Optional[float]


class PhonePositionService:
    def __init__(
        self,
        stale_after_s: float = 2.5,
        timeout_s: float = 2.0,
    ):
        self.stale_after_s = stale_after_s
        self.timeout_s = timeout_s

        self._endpoint = None

        self._last_phyphox_time = None
        self._last_update_monotonic = None

        self._last_latitude = None
        self._last_longitude = None
        self._last_accuracy_m = None
        self._last_gps_status = None

    def _ensure_endpoint(self):
        if self._endpoint is None:
            self._endpoint = discover_phyphox_attitude()

        return self._endpoint

    def read(self) -> PhonePositionReading:
        endpoint = self._ensure_endpoint()

        if endpoint is None:
            return self._unavailable_reading(False)

        url = (
            f"{endpoint}/get?"
            "gps_time&gpsLat&gpsLon&gpsAccuracy&gpsStatus"
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

            t = self._last_value(buffers, "gps_time")
            lat = self._last_value(buffers, "gpsLat")
            lon = self._last_value(buffers, "gpsLon")
            accuracy = self._last_value(buffers, "gpsAccuracy")
            gps_status = self._last_value(buffers, "gpsStatus")

            if None in (t, lat, lon):
                return self._unavailable_reading(measuring)

            now = time.monotonic()

            if (
                self._last_phyphox_time is None
                or t != self._last_phyphox_time
            ):
                self._last_phyphox_time = t
                self._last_update_monotonic = now

                self._last_latitude = lat
                self._last_longitude = lon
                self._last_accuracy_m = accuracy

                self._last_gps_status = (
                    None
                    if gps_status is None
                    else int(gps_status)
                )

            if self._last_update_monotonic is None:
                age_s = None
            else:
                age_s = now - self._last_update_monotonic

            fresh = (
                measuring
                and age_s is not None
                and age_s <= self.stale_after_s
            )

            return PhonePositionReading(
                latitude=self._last_latitude,
                longitude=self._last_longitude,
                horizontal_accuracy_m=self._last_accuracy_m,
                phyphox_time_s=self._last_phyphox_time,
                gps_status=self._last_gps_status,
                available=(
                    self._last_latitude is not None
                    and self._last_longitude is not None
                ),
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
    ) -> PhonePositionReading:
        now = time.monotonic()

        if self._last_update_monotonic is None:
            age_s = None
        else:
            age_s = now - self._last_update_monotonic

        return PhonePositionReading(
            latitude=self._last_latitude,
            longitude=self._last_longitude,
            horizontal_accuracy_m=self._last_accuracy_m,
            phyphox_time_s=self._last_phyphox_time,
            gps_status=self._last_gps_status,
            available=(
                self._last_latitude is not None
                and self._last_longitude is not None
            ),
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


if __name__ == "__main__":
    service = PhonePositionService()

    try:
        while True:
            r = service.read()

            print(
                f"LAT={r.latitude}  "
                f"LON={r.longitude}  "
                f"accuracy={r.horizontal_accuracy_m}m  "
                f"status={r.gps_status}  "
                f"fresh={r.fresh}  "
                f"available={r.available}  "
                f"measuring={r.measuring}  "
                f"age={r.age_s}"
            )

            time.sleep(0.5)

    except KeyboardInterrupt:
        print()
