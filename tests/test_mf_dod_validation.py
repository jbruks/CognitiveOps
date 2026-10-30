"""No-network validation of memory reuse, explicit observation and doctrine."""
import tempfile
import unittest
from pathlib import Path

from doctrine_service import DoctrinePassage, DoctrineService
from llm.llm_service import LLMService, InferenceResult
from mission_package import MissionPackage
from mf_dod_validation import validate
from mf_dod_integrated_agent import MissionJournal, prepare_proposals


class ReorderingService(LLMService):
    def __init__(self):
        super().__init__()
        self.seen_context = None

    def plan_objectives(self, intent, approved_objectives, context=None):
        self.seen_context = context
        return InferenceResult("L4", {"objective_ids": [
            row["objective_id"] for row in reversed(approved_objectives)],
            "reason": "Review prior blocked POI first"}, "stub", "test")


class CognitiveValidationTest(unittest.TestCase):
    def setUp(self):
        self.package = MissionPackage(
            {"schema_version": "1.0", "site_id": "LAB", "intent": "Inspect",
             "crs": "EPSG:4326", "supporting_documents": []},
            {"type": "FeatureCollection", "features": [
                {"type": "Feature", "properties": {"kind": "authorized"},
                 "geometry": {"type": "Polygon", "coordinates": [
                     [[0,0],[4,0],[4,4],[0,4],[0,0]]]}},
                *[{"type": "Feature", "properties": {"kind": "poi", "poi_id": pid},
                   "geometry": {"type": "Point", "coordinates": point}}
                  for pid, point in [("A",[1,1]),("B",[2,2]),("C",[3,3])]]]})
        self.proposals, _, _ = prepare_proposals(self.package, LLMService())
        self.ids = [p.objective_id for p in self.proposals]

    def test_memory_changes_order_and_records_trace(self):
        service = ReorderingService()
        prior = [{"event": "L3_NAVIGATION_FEEDBACK", "objective_id": self.ids[0],
                  "status": "BLOCKED"}]
        doctrine = DoctrineService([
            DoctrinePassage("manual.pdf", "inspection terrain access observation",
                            "PDF page 3", True)])
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "history.jsonl"
            result = validate(self.package, self.proposals, service, self.ids, prior,
                              {self.ids[1]: {"description": "Visible edge marker",
                                             "observed": True,
                                             "source_ref": "operator:photo-1"}},
                              doctrine, journal=MissionJournal(path))
            self.assertEqual(result["execution_order"], self.ids[::-1])
            self.assertEqual(service.seen_context["prior_blocked_pois"], ["A"])
            self.assertEqual(result["objectives"][1]["status"], "OBSERVED")
            self.assertEqual(result["objectives"][0]["status"], "UNVERIFIED")
            self.assertEqual(result["doctrine_context"][0]["source"], "manual.pdf")
            self.assertTrue(any(e["event"] == "OPERATOR_EVIDENCE"
                                for e in MissionJournal(path).events))
            self.assertEqual(result["physical_actions"], 0)

    def test_rejects_forged_evidence_and_blocked_evidence(self):
        with self.assertRaises(ValueError):
            validate(self.package, self.proposals, LLMService(), self.ids,
                     evidence={"FAKE": {"description": "x", "observed": True,
                                        "source_ref": "op:1"}})
        with self.assertRaises(ValueError):
            validate(self.package, self.proposals, LLMService(), self.ids,
                     evidence={self.ids[0]: {"description": "x", "observed": "yes",
                                             "source_ref": "op:1"}})
        result = validate(self.package, self.proposals, LLMService(), self.ids,
                          evidence={self.ids[0]: {"description": "x", "observed": True,
                                                  "source_ref": "operator:1"}},
                          blocked_poi="A")
        self.assertEqual(result["objectives"][0]["status"], "INACCESSIBLE")
        self.assertFalse(any(e["event"] == "OPERATOR_EVIDENCE"
                             for e in result["events"]))


if __name__ == "__main__":
    unittest.main()
