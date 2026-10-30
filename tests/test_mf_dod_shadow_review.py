import unittest
from mf_dod_shadow_review import analyze


class ShadowReviewTests(unittest.TestCase):
    def test_unknown_gps_invalid_ultrasonic_recovery(self):
        data = {"format": "COGNITIVEOPS_TEXT_CYCLES_V1", "cycles": [
            {"cycle": 1, "gps_usable": False, "position": None,
             "ultrasonic": [{"valid": False}], "events": []},
            *[{"cycle": i, "gps_usable": True,
             "position": {"accuracy_m": 4.0},
             "ultrasonic": [], "events": [{"type": "RECOVERY_NOTICE"}]}
            for i in (2, 3, 4)]]}
        result = analyze(data)
        self.assertEqual(result["counts"]["GPS_UNAVAILABLE"], 1)
        self.assertEqual(result["counts"]["ULTRASONIC_INVALID"], 1)
        self.assertEqual(result["counts"]["RECOVERY_ATTEMPT_RECORDED"], 3)
        self.assertEqual(result["counts"]["REPEATED_RECOVERY_NOTICES"], 1)
        self.assertEqual(result["physical_actions"], 0)

    def test_nonmatching_format_fails_closed(self):
        with self.assertRaises(ValueError):
            analyze({"format": "UNKNOWN", "cycles": []})


if __name__ == "__main__":
    unittest.main()
