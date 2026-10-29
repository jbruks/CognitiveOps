"""No-network no-device validations for attributed doctrine reasoning."""
import json
import unittest
from types import SimpleNamespace

from doctrine_service import DoctrineService, DoctrinePassage
from llm.llm_service import LLMService
from mf_dod_doctrine_v2 import evaluate, role_sources, rich_plan


class FakeClient:
    def __init__(self, source_id=None, invalid=None):
        self.responses = self
        self.calls = []
        self.source_id = source_id
        self.invalid = invalid

    def create(self, **kwargs):
        data = json.loads(kwargs["input"])
        self.calls.append(data)
        ids = [row["objective_id"] for row in data["approved_objectives"]]
        refs = data["retrieved_sources"]
        cited = [self.source_id or refs[0]["source_id"]] if refs else []
        out = {"objective_ids": ids,
               "reason": "Check uncertain visibility, not direct movement",
               "recommendations": [{"objective_id": ids[0],
                                    "check": "Record terrain visibility",
                                    "limitation": "No sensor verification",
                                    "source_ids": cited}]}
        if self.invalid == "goal":
            out["objective_ids"][0] = "FORGED-GOAL"
        if self.invalid == "citation":
            out["recommendations"][0]["source_ids"] = ["L4-S999"]
        return SimpleNamespace(output_text=json.dumps(out), id="mock")


class DoctrineV2Test(unittest.TestCase):
    def setUp(self):
        self.doctrine = DoctrineService([
            DoctrinePassage("manual.pdf",
                            "inspection planning observation verification access",
                            "PDF page 5", True),
            DoctrinePassage("manual.pdf",
                            "navigation terrain association checkpoint compass uncertainty",
                            "PDF page 9", True)])

    def test_role_specific_retrieval_and_provenance(self):
        l3 = role_sources(self.doctrine, "L3")
        l4 = role_sources(self.doctrine, "L4")
        self.assertTrue(l3 and l4)
        self.assertTrue(all(s["source_id"].startswith("L3-") for s in l3))
        self.assertTrue(all(s["source_id"].startswith("L4-") for s in l4))
        self.assertEqual(l3[0]["locator"], "PDF page 9")
        self.assertEqual(l4[0]["locator"], "PDF page 5")

    def test_baseline_has_no_sources_and_enriched_has_sources(self):
        fake = FakeClient()
        result = evaluate(LLMService(backend="openai", model="mock", client=fake),
                          self.doctrine)
        self.assertEqual(len(fake.calls), 3)
        self.assertEqual(fake.calls[0]["retrieved_sources"], [])
        self.assertTrue(fake.calls[1]["retrieved_sources"])
        self.assertTrue(fake.calls[2]["retrieved_sources"])
        self.assertEqual(fake.calls[0]["constraints"], fake.calls[1]["constraints"])
        self.assertEqual(result["L4_doctrine"]["physical_actions"], 0)
        self.assertEqual(result["L4_doctrine"]["used_source_ids"], ["L4-S1"])

    def test_nonexistent_citation_rejected(self):
        fake = FakeClient(invalid="citation")
        with self.assertRaises(ValueError):
            rich_plan(LLMService(backend="openai", model="mock", client=fake),
                      self.doctrine)

    def test_unapproved_target_rejected(self):
        fake = FakeClient(invalid="goal")
        with self.assertRaises(ValueError):
            rich_plan(LLMService(backend="openai", model="mock", client=fake),
                      self.doctrine)

    def test_stub_never_creates_citations(self):
        result = evaluate(LLMService(), self.doctrine)
        self.assertEqual(result["L4_doctrine"]["used_source_ids"], [])
        self.assertEqual(result["L4_doctrine"]["output"]["recommendations"], [])


if __name__ == "__main__":
    unittest.main()
