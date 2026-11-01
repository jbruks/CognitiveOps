"""Opt-in shadow camera contract: no actual L1 commands."""
import unittest
from types import SimpleNamespace
from mf_dod_shadow_perception import ShadowCameraObserver


def fake_perception(confidence=0.9):
    state = SimpleNamespace(
        confidence=confidence, obstacle_ahead=False,
        free_direction="center", summary="synthetic camera state",
        regions=[{"name": k, "traversable": True}
                 for k in ("left", "front", "right")],
        objects=[])
    return SimpleNamespace(observe_llm=lambda: SimpleNamespace(
        perception_state=state, image_bytes=None, gps_state=None))


class ShadowCameraTests(unittest.TestCase):
    def test_no_guidance_never_proposes_movement(self):
        obs = ShadowCameraObserver(perception=fake_perception()).observe(
            {"status": "GPS_UNAVAILABLE", "heading_error_deg": None,
             "distance_m": None})
        self.assertEqual(obs.tactical["action"], "HOLD")
        self.assertFalse(obs.tactical["executable"])

    def test_camera_error_proposes_hold(self):
        obs = ShadowCameraObserver(perception=fake_perception(0)).observe(
            {"status": "OBSERVING_MANUAL_MOTION",
             "heading_error_deg": 0, "distance_m": 20})
        self.assertEqual(obs.status, "PERCEPTION_UNAVAILABLE")
        self.assertEqual(obs.tactical["action"], "HOLD")

    def test_pure_l2_proposal_never_executable(self):
        obs = ShadowCameraObserver(perception=fake_perception()).observe(
            {"status": "OBSERVING_MANUAL_MOTION",
             "heading_error_deg": 0, "distance_m": 20})
        self.assertEqual(obs.status, "CAMERA_OBSERVED")
        self.assertEqual(obs.tactical["action"], "MOVE_FORWARD")
        self.assertFalse(obs.tactical["executable"])
        self.assertEqual(obs.tactical["ultrasonic"], "NOT_READ")


if __name__ == "__main__":
    unittest.main()
