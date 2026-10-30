"""Offline tests for identical-goal A/B/C comparisons; zero network calls."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from doctrine_service import DoctrinePassage, DoctrineService
from llombai_sim_package import build
from mission_package import MissionPackage
from mf_dod_integrated_agent import prepare_proposals
from llm.llm_service import LLMService
from mf_dod_abc_experiment import run_abc


class FakeService:
    def __init__(self):
        self.contexts = []

    def plan_objectives(self, intent, approved_objectives, context):
        self.contexts.append(context)
        ids = [o["objective_id"] for o in approved_objectives]
        if context["prior_blocked_pois"]:
            ids = ids[::-1]
        return SimpleNamespace(output={
            "objective_ids": ids, "reason": "Received context " + context["experiment"]})


class ABCExperimentTest(unittest.TestCase):
    def setUp(self):
        source = (Path(__file__).resolve().parents[1] / "qgis_pr" /
                  "llombai_visual_candidates_review.geojson")
        self.tmp = tempfile.TemporaryDirectory()
        path = Path(self.tmp.name)
        build(source, path / "pkg")
        self.package = MissionPackage.load(path / "pkg" / "manifest.json")
        self.proposals, _, _ = prepare_proposals(self.package, LLMService())
        self.output = path / "out"

    def tearDown(self):
        self.tmp.cleanup()

    def test_three_variants_keep_same_goals_and_isolate_context(self):
        service = FakeService()
        result = run_abc(self.package, self.proposals, service, [
            {"event": "L3_NAVIGATION_FEEDBACK", "status": "BLOCKED",
             "objective_id": self.proposals[0].objective_id}],
            DoctrineService([DoctrinePassage(
                "safety.pdf", "inspection terrain access uncertainty", "PDF page 2", True)]),
            self.output)
        self.assertEqual(set(result["variants"]), {"A", "B", "C"})
        self.assertEqual(service.contexts[0]["prior_blocked_pois"], [])
        self.assertEqual(service.contexts[1]["doctrine_excerpts"], [])
        self.assertTrue(service.contexts[2]["doctrine_excerpts"])
        self.assertTrue(result["comparison"]["A_B_order_changed"])
        self.assertEqual(result["doctrine_matches"], 1)
        self.assertTrue((self.output / "report.md").is_file())
        self.assertTrue((self.output / "results.json").is_file())
        with self.assertRaises(FileExistsError):
            run_abc(self.package, self.proposals, service, [], DoctrineService(), self.output)

    def test_no_doctrine_fails_openly_in_report_and_no_fake_claims(self):
        result = run_abc(self.package, self.proposals, FakeService(), [],
                         DoctrineService(), self.output)
        self.assertFalse(result["variants"]["C"]["doctrine_available"])
        self.assertEqual(result["doctrine_matches"], 0)
        self.assertFalse(result["comparison"]["A_B_order_changed"])


if __name__ == "__main__":
    unittest.main()
