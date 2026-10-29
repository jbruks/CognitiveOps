"""Offline adaptation/replanning tests; no devices or external network."""
import unittest
from types import SimpleNamespace
import json

from llm.llm_service import LLMService
from mf_dod_experiments_ab import compare_scenarios, run_replanning, authorized_targets


class FakeResponses:
    def __init__(self, invalid_replan=False, hold=False):
        self.responses = self
        self.calls = []
        self.invalid_replan = invalid_replan
        self.hold = hold

    def create(self, **kwargs):
        self.calls.append(kwargs)
        payload = json.loads(kwargs["input"])
        if "approved_objectives" in payload:
            ids = [x["objective_id"] for x in payload["approved_objectives"]]
            if self.invalid_replan and len(self.calls) == 3:
                ids.append("UNAUTHORIZED")
            else:
                ids.reverse()
            result = {"objective_ids": ids, "reason": "Synthetic preference"}
        else:
            result = {"decision": "HOLD" if self.hold else "REQUEST_L4_REPLAN",
                      "reason": "Keep rover stopped"}
        return SimpleNamespace(output_text=json.dumps(result),
                               id=f"fake-{len(self.calls)}")


class ExperimentsABTest(unittest.TestCase):
    def test_scenarios_keep_approved_ids_and_distinct_context(self):
        fake = FakeResponses()
        service = LLMService(backend="openai", model="mock", client=fake)
        comparison = compare_scenarios(service)
        expected = {x.objective_id for x in authorized_targets()}
        for result in comparison:
            self.assertEqual(set(result["order"]), expected)
        first = json.loads(fake.calls[0]["input"])["context"]["restrictions"]
        second = json.loads(fake.calls[1]["input"])["context"]["restrictions"]
        self.assertNotEqual(first, second)

    def test_replan_excludes_blocked_and_does_not_move(self):
        fake = FakeResponses()
        service = LLMService(backend="openai", model="mock", client=fake)
        report = run_replanning(service)
        events = [d.get("event") for d in report["decision_log"]]
        self.assertIn("L4_REPLAN", events)
        replan = next(d for d in report["decision_log"]
                      if d.get("event") == "L4_REPLAN")
        self.assertNotIn(report["blocked_id"], replan["order"])
        self.assertEqual(len(replan["order"]), 3)
        self.assertEqual(report["physical_actions"], 0)
        self.assertEqual(sum(o["status"] == "INACCESSIBLE"
                             for o in report["objectives"]), 1)
        self.assertEqual(sum(o["status"] == "UNVERIFIED"
                             for o in report["objectives"]), 3)
        self.assertEqual(len(fake.calls), 3)

    def test_hold_avoids_replanning(self):
        fake = FakeResponses(hold=True)
        report = run_replanning(
            LLMService(backend="openai", model="mock", client=fake))
        self.assertIn("L4_REPLAN_SKIPPED",
                      [d.get("event") for d in report["decision_log"]])
        self.assertEqual(len(fake.calls), 2)

    def test_invented_replan_target_is_rejected(self):
        fake = FakeResponses(invalid_replan=True)
        with self.assertRaises(ValueError):
            run_replanning(LLMService(backend="openai", model="mock", client=fake))

    def test_stub_stays_offline(self):
        service = LLMService()
        comparison = compare_scenarios(service)
        self.assertEqual(len(comparison), 2)
        report = run_replanning(service)
        self.assertEqual(report["physical_actions"], 0)
        self.assertIn("L4_REPLAN_SKIPPED",
                      [d.get("event") for d in report["decision_log"]])


if __name__ == "__main__":
    unittest.main()
