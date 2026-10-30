"""Offline tests for visual-candidate simulation package."""
import json
from pathlib import Path
import tempfile
import unittest

from llombai_sim_package import build
from mission_package import MissionPackage


class LlombaiSimulationPackageTest(unittest.TestCase):
    def test_converts_candidates_without_physical_permission(self):
        source = Path(__file__).resolve().parents[1] / "qgis_pr" / "llombai_visual_candidates_review.geojson"
        with tempfile.TemporaryDirectory() as work:
            dest = Path(work) / "package"
            summary = build(source, dest)
            pkg = MissionPackage.load(dest / "manifest.json")
            self.assertTrue(summary["simulation_only"])
            self.assertFalse(summary["physical_permission"])
            self.assertEqual(len(pkg.pois), 4)
            self.assertEqual(len(pkg.authorized), 1)
            self.assertTrue(all(pkg.allowed(xy) for xy in pkg.pois.values()))
            self.assertIn("SIMULATION_ONLY", pkg.site_id)

    def test_refuses_candidate_without_explicit_non_authorizing_flag(self):
        with tempfile.TemporaryDirectory() as work:
            source = Path(__file__).resolve().parents[1] / "qgis_pr" / "llombai_visual_candidates_review.geojson"
            data = json.loads(source.read_text(encoding="utf-8"))
            data["features"][0]["properties"].pop("not_authorized")
            edited = Path(work) / "bad.geojson"
            edited.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                build(edited, Path(work) / "output")


if __name__ == "__main__":
    unittest.main()
