"""Offline mission package tests. Coordinates are intentionally synthetic."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mission_package import MissionPackage
from mf_dod_mission_package_demo import propose
from llm.llm_service import LLMService


def polygon(kind, coords):
    return {"type": "Feature", "properties": {"kind": kind},
            "geometry": {"type": "Polygon", "coordinates": [coords]}}


def point(pid, xy):
    return {"type": "Feature", "properties": {"kind": "poi", "poi_id": pid},
            "geometry": {"type": "Point", "coordinates": xy}}


class PackageTest(unittest.TestCase):
    def setUp(self):
        self.manifest = {"schema_version": "1.0", "intent": "Inspect site",
                         "site_id": "TEST", "crs": "EPSG:4326",
                         "supporting_documents": []}
        self.geo = {"type": "FeatureCollection", "features": [
            polygon("authorized", [[0,0], [2,0], [2,2], [0,2], [0,0]]),
            polygon("excluded", [[1,1], [1.5,1], [1.5,1.5], [1,1.5], [1,1]]),
            point("safe", [0.5,0.5]), point("forbidden", [1.2,1.2]),
            point("outside", [3,3]), point("boundary", [0,1])]}

    def test_geofence_and_conservative_boundaries(self):
        pkg = MissionPackage(self.manifest, self.geo)
        self.assertTrue(pkg.allowed([0.5,0.5]))
        for pid in ("forbidden", "outside", "boundary"):
            self.assertFalse(pkg.allowed(pkg.pois[pid]))
            with self.assertRaises(ValueError):
                pkg.candidate("OBS-" + pid, pid, "Inspect", "What is visible?")

    def test_operator_gate_revalidates_and_preserves_coords(self):
        pkg = MissionPackage(self.manifest, self.geo)
        c = pkg.candidate("GOAL-1", "safe", "Inspection", "Visible condition?")
        self.assertFalse(c.approved)
        result = pkg.approve([c], ["GOAL-1"])
        self.assertEqual((result[0].longitude, result[0].latitude), (0.5, 0.5))
        with self.assertRaises(ValueError):
            pkg.approve([c], ["NOT-PROPOSED"])

    def test_missing_map_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "manifest.json"
            p.write_text(json.dumps({**self.manifest, "geojson": "absent.geojson"}))
            with self.assertRaises(FileNotFoundError):
                MissionPackage.load(p)
        with self.assertRaises(ValueError):
            MissionPackage({**self.manifest, "crs": "EPSG:3857"}, self.geo)

    def test_stub_only_proposes_safe_operator_points(self):
        pkg = MissionPackage(self.manifest, self.geo)
        report = propose(pkg, LLMService())
        self.assertEqual([p["poi_id"] for p in report["proposals"]], ["safe"])
        self.assertFalse(report["proposals"][0]["approved"])
        self.assertEqual(report["physical_actions"], 0)

    def test_gpt_cannot_create_unlisted_poi(self):
        class Fake:
            def __init__(self):
                self.responses = self
            def create(self, **kwargs):
                return SimpleNamespace(output_text=json.dumps({
                    "goals": [{"objective_id": "BAD", "poi_id": "invented",
                               "purpose": "Inspect", "question": "Visible?"}],
                    "reason": "Fake"}))
        pkg = MissionPackage(self.manifest, self.geo)
        with self.assertRaises(ValueError):
            propose(pkg, LLMService(backend="openai", model="mock", client=Fake()))


if __name__ == "__main__":
    unittest.main()
