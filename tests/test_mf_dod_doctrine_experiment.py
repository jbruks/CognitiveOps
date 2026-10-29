"""Offline tests for attributed doctrine A/B comparison."""
import json
import unittest
from types import SimpleNamespace

from doctrine_service import DoctrinePassage, DoctrineService
from llm.llm_service import LLMService
from mf_dod_doctrine_experiment import evaluate


class DoctrineABTest(unittest.TestCase):
    def test_no_document_is_not_faked(self):
        result = evaluate(LLMService(), DoctrineService())
        self.assertEqual(result["doctrine_status"], "NO_MATCHES_OR_SOURCES")
        self.assertIsNone(result["with_doctrine"])
        self.assertEqual(result["retrieved_sources"], [])
        self.assertEqual(result["physical_actions"], 0)

    def test_two_arms_have_same_mission_and_approved_goals(self):
        class FakeClient:
            def __init__(self):
                self.responses = self
                self.calls = []
            def create(self, **kwargs):
                self.calls.append(json.loads(kwargs["input"]))
                ids = [o["objective_id"] for o in self.calls[-1]["approved_objectives"]]
                if self.calls[-1]["context"]["doctrine"]:
                    ids = list(reversed(ids))
                return SimpleNamespace(output_text=json.dumps({
                    "objective_ids": ids, "reason": "Mock source-conditioned order"
                }), id="mock")
        client = FakeClient()
        service = LLMService(backend="openai", model="mock", client=client)
        docs = DoctrineService([DoctrinePassage(
            "real-source.pdf", "Inspection access safety and observations",
            "PDF page 11", verified=True)])
        report = evaluate(service, docs)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[0]["intent"], client.calls[1]["intent"])
        self.assertEqual(client.calls[0]["approved_objectives"],
                         client.calls[1]["approved_objectives"])
        self.assertEqual(client.calls[0]["context"]["constraints"],
                         client.calls[1]["context"]["constraints"])
        self.assertEqual(client.calls[0]["context"]["doctrine"], [])
        self.assertEqual(len(client.calls[1]["context"]["doctrine"]), 1)
        self.assertTrue(report["order_changed"])
        self.assertEqual(report["retrieved_sources"][0]["locator"], "PDF page 11")

    def test_no_match_skips_enriched_arm(self):
        docs = DoctrineService([DoctrinePassage(
            "source.pdf", "Unrelated terminology entirely", "PDF page 2")])
        report = evaluate(LLMService(), docs)
        self.assertIsNone(report["with_doctrine"])


if __name__ == "__main__":
    unittest.main()
