"""No-hardware, no-network cognitive demo integration tests."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from doctrine_service import DoctrineService, DoctrinePassage
from llm.llm_service import LLMService
from mf_dod_cognitive_demo import execute_cognitive_demo, main


class CognitiveDemoTest(unittest.TestCase):
    def test_stub_full_flow_and_attributed_sources(self):
        sources = DoctrineService([
            DoctrinePassage("test-manual.pdf",
                            "Inspection observation safety report uncertainty",
                            "PDF page 8", verified=True)
        ])
        report = execute_cognitive_demo(LLMService(), sources)
        self.assertTrue(report["simulation_only"])
        self.assertEqual(len(report["objectives"]), 3)
        self.assertEqual(
            {row["id"]: row["status"] for row in report["objectives"]},
            {"LAB-RUNWAY": "OBSERVED", "LAB-ACCESS": "INACCESSIBLE",
             "LAB-FACILITIES": "UNVERIFIED"},
        )
        self.assertEqual(report["doctrine_sources"][0]["locator"], "PDF page 8")
        l3 = [d for d in report["decision_log"] if d.get("event") == "L3_REVIEW"]
        self.assertEqual(len(l3), 1)
        self.assertEqual(l3[0]["decision"], "HOLD")
        self.assertFalse(l3[0]["action_executed"])

    def test_mocked_openai_can_change_order_and_review(self):
        class FakeClient:
            def __init__(self):
                self.responses = self
                self.calls = []
            def create(self, **kwargs):
                self.calls.append(kwargs)
                if len(self.calls) == 1:
                    out = {"objective_ids": ["LAB-FACILITIES", "LAB-ACCESS",
                                             "LAB-RUNWAY"],
                           "reason": "Prioritize exterior review"}
                else:
                    out = {"decision": "REQUEST_L4_REPLAN",
                           "reason": "Obstacle blocks approach"}
                import json
                return SimpleNamespace(output_text=json.dumps(out),
                                       id=f"mock-{len(self.calls)}")
        client = FakeClient()
        svc = LLMService(backend="openai", model="fake", client=client)
        report = execute_cognitive_demo(svc)
        self.assertEqual([x["id"] for x in report["objectives"]],
                         ["LAB-FACILITIES", "LAB-ACCESS", "LAB-RUNWAY"])
        self.assertEqual(len(client.calls), 2)
        review = next(d for d in report["decision_log"] if d["event"] == "L3_REVIEW")
        self.assertEqual(review["decision"], "REQUEST_L4_REPLAN")
        self.assertFalse(review["action_executed"])

    def test_api_requires_explicit_opt_in(self):
        with self.assertRaises(SystemExit):
            main(["--backend", "openai", "--model", "fake"])
        with self.assertRaises(SystemExit):
            main(["--backend", "openai", "--allow-api"])

    def test_pdf_ingestion_missing_file_rejected(self):
        with self.assertRaises((RuntimeError, ValueError)):
            # Missing pypdf or source PDF must fail, not fake attribution.
            DoctrineService.from_pdf_paths(["/missing/source.pdf"])


if __name__ == "__main__":
    unittest.main()
