"""Integrated agent acceptance tests. No network or physical actuation."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from doctrine_service import DoctrineService, DoctrinePassage
from llm.llm_service import LLMService
from mission_package import MissionPackage
from mf_dod_integrated_agent import (MissionJournal, prepare_proposals,
                                     execute_agent, site_documents)


class FakeClient:
    def __init__(self, invalid=False):
        self.responses = self
        self.calls = []
        self.invalid = invalid

    def create(self, **kwargs):
        self.calls.append(kwargs)
        input_data = json.loads(kwargs["input"])
        if "pois" in input_data:
            goal = {"objective_id": "A", "poi_id": "SAFE",
                    "purpose": "Inspect access", "question": "Visible obstructions?",
                    "source_ids": ["map:poi:SAFE"]}
            if self.invalid:
                goal["source_ids"] = ["map:poi:FORGED"]
            data = {"goals": [goal], "reason": "Mapped POI"}
        elif "allowed_decisions" in input_data:
            data = {"decision": "REQUEST_L4_REPLAN",
                    "reason": "Synthetic obstruction"}
        else:
            ids = [x["objective_id"] for x in input_data["approved_objectives"]]
            data = {"objective_ids": list(reversed(ids)), "reason": "Try remaining"}
        return SimpleNamespace(output_text=json.dumps(data), id="mock")


class IntegratedAgentTest(unittest.TestCase):
    def setUp(self):
        polygon = {"type": "Feature", "properties": {"kind": "authorized"},
                   "geometry": {"type": "Polygon", "coordinates": [
                       [[0,0],[2,0],[2,2],[0,2],[0,0]]]}}
        pois = [{"type": "Feature",
                 "properties": {"kind": "poi", "poi_id": pid},
                 "geometry": {"type": "Point", "coordinates": xy}}
                for pid, xy in [("SAFE", [0.5,0.5]), ("OTHER", [1.5,1.5])]]
        self.package = MissionPackage(
            {"schema_version": "1.0", "intent": "Inspect authorized points",
             "site_id": "LAB", "crs": "EPSG:4326", "supporting_documents": []},
            {"type": "FeatureCollection", "features": [polygon, *pois]})

    def test_without_operator_approval_never_dispatches(self):
        goals, _, _ = prepare_proposals(self.package, LLMService())
        result = execute_agent(self.package, goals, [], LLMService())
        self.assertEqual(result["state"], "AWAITING_OPERATOR_APPROVAL")
        self.assertEqual(result["physical_actions"], 0)

    def test_integrated_replanning_and_memory_reload(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "journal.jsonl"
            svc = LLMService(backend="openai", model="mock", client=FakeClient())
            goals, sources, reason = prepare_proposals(self.package, svc)
            self.assertEqual(len(goals), 1)
            report = execute_agent(self.package, goals, ["A"], svc,
                                   MissionJournal(path), simulate_block=True)
            self.assertEqual(report["physical_actions"], 0)
            self.assertEqual(report["objectives"][0]["status"], "INACCESSIBLE")
            self.assertEqual(len(MissionJournal(path).events), len(report["events"]))
            self.assertIn("L3_REVIEW", [e["event"] for e in report["events"]])

    def test_replanning_with_remaining_approved_goals(self):
        svc = LLMService(backend="openai", model="mock", client=FakeClient())
        goals, _, _ = prepare_proposals(self.package, LLMService())
        report = execute_agent(self.package, goals,
                               [g.objective_id for g in goals], svc,
                               simulate_block=True)
        self.assertEqual(report["replans"], 1)
        self.assertIn("L4_REPLAN", [e["event"] for e in report["events"]])
        statuses = {r["status"] for r in report["objectives"]}
        self.assertIn("INACCESSIBLE", statuses)
        self.assertIn("UNVERIFIED", statuses)

    def test_forged_source_fails(self):
        svc = LLMService(backend="openai", model="mock",
                         client=FakeClient(invalid=True))
        with self.assertRaises(ValueError):
            prepare_proposals(self.package, svc)

    def test_site_document_must_be_local_text(self):
        with tempfile.TemporaryDirectory() as root:
            manifest = Path(root) / "manifest.json"
            (Path(root) / "notes.txt").write_text("Site constraints are unverified")
            self.package.document_sources = ["notes.txt"]
            self.assertEqual(site_documents(manifest, self.package)[0]["type"], "site")
            self.package.document_sources = ["../outside.txt"]
            with self.assertRaises(ValueError):
                site_documents(manifest, self.package)

    def test_doctrine_and_site_sources_separate(self):
        docs = [{"source_id": "site:notes.txt", "type": "site", "text": "Site note"}]
        doctrine = DoctrineService([DoctrinePassage("manual.pdf",
                    "inspection observation terrain access", "PDF page 3", True)])
        _, sources, _ = prepare_proposals(self.package, LLMService(),
                                          docs, doctrine)
        self.assertEqual(sources["site:notes.txt"]["type"], "site")
        self.assertEqual(sources["doctrine:1"]["type"], "doctrine")


if __name__ == "__main__":
    unittest.main()
