"""No-network shared inference service tests (Issue #6)."""
import json
import unittest
from types import SimpleNamespace

from llm.llm_service import LLMService


class SharedInferenceTest(unittest.TestCase):
    def test_stub_is_deterministic_and_role_limited(self):
        service = LLMService()
        a = service.infer("L4", "Choose strategy", {"mission": "inspect"},
                          ("INSPECT", "HOLD"))
        b = service.infer("L3", "Choose navigation strategy",
                          {"blocked": True}, ("HOLD", "REQUEST_REPLAN"))
        self.assertEqual(a.output["decision"], "INSPECT")
        self.assertEqual(b.output["decision"], "HOLD")
        self.assertEqual(a.provider, "stub")
        with self.assertRaises(ValueError):
            service.infer("L2", "Choose", {}, ("HOLD",))
        with self.assertRaises(ValueError):
            service.infer("L3", "Choose", {}, ("MOVE_FORWARD",))

    def test_structured_provider_response_is_validated(self):
        class FakeClient:
            def __init__(self, text):
                self.text = text
                self.calls = []
                self.responses = self

            def create(self, **kwargs):
                self.calls.append(kwargs)
                return SimpleNamespace(output_text=self.text, id="offline-1")

        client = FakeClient('{"decision":"HOLD","reason":"Obstacle ahead"}')
        svc = LLMService(backend="openai", model="mock-model", client=client)
        result = svc.infer("L3", "Decide safe strategy",
                           {"front_obstacle": True}, ("HOLD", "REQUEST_REPLAN"))
        self.assertEqual(result.output["decision"], "HOLD")
        self.assertEqual(result.request_id, "offline-1")
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(json.loads(client.calls[0]["input"])["level"], "L3")

        client.text = '{"decision":"MOVE_BACKWARD","reason":"Unsafe"}'
        with self.assertRaises(ValueError):
            svc.infer("L3", "Decide", {}, ("HOLD",))
        client.text = "not json"
        with self.assertRaises(ValueError):
            svc.infer("L4", "Decide", {}, ("INSPECT",))

    def test_legacy_methods_do_not_change_behavior(self):
        svc = LLMService()
        self.assertEqual(svc.decide_task_mode("test"), "EXPLORE")
        self.assertEqual(svc.decide_mission("test"), "EXPLORE")
        self.assertEqual(svc.decide_tactical("test"), "MOVE_FORWARD")


    def test_plan_orders_all_approved_objectives(self):
        ids = [{"objective_id": "A", "purpose": "Surface"},
               {"objective_id": "B", "purpose": "Access"}]
        stub = LLMService()
        result = stub.plan_objectives("Inspect all areas", ids)
        self.assertEqual(result.output["objective_ids"], ["A", "B"])

        class Client:
            responses = None
            def __init__(self):
                self.responses = self
                self.text = '{"objective_ids":["B","A"],"reason":"Access first"}'
            def create(self, **kwargs):
                return SimpleNamespace(output_text=self.text, id="mock-plan")

        fake = Client()
        service = LLMService(backend="openai", model="mock", client=fake)
        reordered = service.plan_objectives("Inspect all", ids)
        self.assertEqual(reordered.output["objective_ids"], ["B", "A"])
        fake.text = '{"objective_ids":["B","C"],"reason":"Unauthorized target"}'
        with self.assertRaises(ValueError):
            service.plan_objectives("Inspect all", ids)


if __name__ == "__main__":
    unittest.main()
