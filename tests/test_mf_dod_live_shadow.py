"""First-stage manual-shadow safety and navigation diagnostics."""
import ast
from pathlib import Path
import unittest
from types import SimpleNamespace

from mf_dod_live_shadow import (ActuationForbidden, NoActuation,
                                evaluate_position, distance_m)


def position(lat=None, lon=None, accuracy=None, fresh=False, available=False):
    return SimpleNamespace(latitude=lat, longitude=lon,
                           horizontal_accuracy_m=accuracy,
                           fresh=fresh, available=available)


def heading(value=None, fresh=False, available=False):
    return SimpleNamespace(heading_deg=value, fresh=fresh, available=available)


class ManualShadowTests(unittest.TestCase):
    def setUp(self):
        self.goal = SimpleNamespace(latitude=39.0, longitude=-0.6)

    def test_no_actuator_surface_or_serial_imports(self):
        for method in ("connect", "connect_and_prepare", "arm", "stop",
                       "execute_tactical_action", "get_state",
                       "get_front_sensor_state"):
            with self.assertRaises(ActuationForbidden):
                getattr(NoActuation(), method)
        src = Path(__file__).resolve().parents[1] / "mf_dod_live_shadow.py"
        tree = ast.parse(src.read_text(encoding="utf-8"))
        modules = [x.module for x in ast.walk(tree) if isinstance(x, ast.ImportFrom)]
        modules.extend(alias.name for x in ast.walk(tree)
                       if isinstance(x, ast.Import) for alias in x.names)
        for forbidden in ("serial", "l1_rover_controler_ra4m1",
                          "l2_tactical_planner", "perception_module"):
            self.assertNotIn(forbidden, modules)

    def test_missing_gps_fails_closed(self):
        result = evaluate_position(position(), heading(), self.goal)
        self.assertEqual(result["status"], "GPS_UNAVAILABLE")
        self.assertIsNone(result["distance_m"])

    def test_inaccurate_gps_fails_closed(self):
        result = evaluate_position(
            position(39.0, -0.6, 40, True, True),
            heading(0, True, True), self.goal)
        self.assertEqual(result["status"], "GPS_ACCURACY_UNCERTAIN")
        self.assertIsNone(result["distance_m"])

    def test_valid_manual_progress_and_heading(self):
        result = evaluate_position(
            position(38.9998, -0.6, 3, True, True),
            heading(0, True, True), self.goal)
        self.assertEqual(result["status"], "OBSERVING_MANUAL_MOTION")
        self.assertAlmostEqual(result["distance_m"], 22.24, places=1)
        self.assertAlmostEqual(result["heading_error_deg"], 0, places=1)

    def test_heading_unavailable_prevents_full_observation(self):
        result = evaluate_position(
            position(39.0, -0.6, 3, True, True), heading(), self.goal)
        self.assertEqual(result["status"], "HEADING_UNAVAILABLE")

    def test_zero_distance(self):
        self.assertAlmostEqual(distance_m(39, -0.6, 39, -0.6), 0.0)


if __name__ == "__main__":
    unittest.main()
