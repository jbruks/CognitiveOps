"""Tests for historical, read-only telemetry normalization."""
import unittest
from mf_dod_telemetry_replay import normalize_log, summary


class TextLogReplayTests(unittest.TestCase):
    def test_unavailable_gps_then_arrival(self):
        raw = """[L4] step
[L3] Phone attitude: heading=None fresh=False available=False age=None
[L3] Phone position: lat=None lon=None accuracy=Nonem status=None fresh=False available=False age=None
[L3] No valid GPS position -> HOLD
[L3] Guidance: HOLD bearing=None distance=None heading_error=None
[L1] Executing tactical action via RA4M1: STOP
[MAIN] Inter-cycle STOP
[L1] Executing tactical action via RA4M1: STOP
[L4] step
[L3] Phone attitude: heading=118.8 fresh=True available=True age=0.0
[L3] Phone position: lat=39.42458 lon=-0.32001 accuracy=6.23m status=1 fresh=True available=True age=0.0
[L3] Guidance: HOLD bearing=116.3 distance=4.23 heading_error=-2.5
[L4] GO_TO_POINT completed: distance=4.24 m
"""
        result = normalize_log(raw)
        self.assertEqual(len(result["cycles"]), 2)
        self.assertFalse(result["cycles"][0]["gps_usable"])
        self.assertTrue(result["cycles"][1]["gps_usable"])
        self.assertEqual(result["cycles"][1]["position"]["accuracy_m"], 6.23)
        self.assertEqual(summary(result)["reported_arrivals"], 1)
        self.assertFalse(result["cycles"][0]["actions"][0]["intercycle"])
        self.assertTrue(result["cycles"][0]["actions"][1]["intercycle"])

    def test_invalid_ultrasonic_not_clear_and_recovery_not_arrival(self):
        raw = """[2026-10-29 11:56:03.858] [L4] step
[2026-10-29 11:56:03.858] [L1-ULTRASONIC] Distance=-1.0 cm | Blocked=False | Valid=False
[2026-10-29 11:56:31.213] [L1] Executing tactical action via RA4M1: HOLD
[2026-10-29 11:56:40.832] [L2] [RECOVERY] Visual blockage -> reverse once
"""
        result = normalize_log(raw)
        self.assertEqual(summary(result)["invalid_ultrasonic_samples"], 1)
        self.assertIsNone(result["cycles"][0]["ultrasonic"][0]["distance_cm"])
        self.assertEqual(summary(result)["recovery_notices"], 1)
        self.assertEqual(summary(result)["reported_arrivals"], 0)
        self.assertEqual(result["objective_attribution"],
                         "UNKNOWN_NOT_MATCHED_TO_MISSION_PACKAGE")


if __name__ == "__main__":
    unittest.main()
