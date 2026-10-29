"""Memory, prompt and strategic review checks without GPT network or hardware."""
import unittest

from tests import test_mf_dod_skeleton  # safe camera/import boundary
from l3_models import NavigationObjective
from l3_task_planner import L3TaskPlanner
from llm.llm_service import LLMService
from llm.prompt_framework import PromptBuilderBase
from memory_system import MemorySystem


class MemoryAndReasoningTest(unittest.TestCase):
    def test_event_memory_additive_to_legacy_fields(self):
        memory = MemorySystem()
        memory.record_mission_event("A", "EVIDENCE", {"observed": True})
        memory.record_navigation_event("A", "BLOCKED", "OBSTACLE", 12.0)
        self.assertEqual(memory.get_mission_events()[0]["type"], "EVIDENCE")
        self.assertEqual(memory.get_navigation_events()[0]["distance_remaining_m"], 12.0)
        self.assertEqual(memory.short_term, [])

    def test_cognitive_context_excludes_doctrine_for_l3(self):
        l3 = PromptBuilderBase.compose_cognitive_context(
            "L3", "inspect", {"id": "A"}, {"authorized": True},
            [{"action": "HOLD"}], [{"source": "test"}])
        self.assertEqual(l3["doctrine"], [])
        l4 = PromptBuilderBase.compose_cognitive_context(
            "L4", "inspect", {"id": "A"}, {}, [], [{"source": "test"}])
        self.assertEqual(l4["doctrine"][0]["source"], "test")

    def test_l3_block_review_is_explicit_and_non_actuating(self):
        class NoMovement:
            def step(self, *args, **kwargs):
                raise AssertionError("L2 must not be invoked during review")

        memory = MemorySystem()
        memory.record_navigation_event("A", "BLOCKED", "OBSTACLE", 12.0)
        l3 = L3TaskPlanner(NoMovement(), object(), memory,
                           llm_service=LLMService(backend="stub"))
        result = l3.review_navigation_block(
            NavigationObjective("A", 39.0, -0.6, purpose="Inspect access"),
            "PERSISTENT_TACTICAL_HOLD", {"operator_authorized": False})
        self.assertEqual(result.level, "L3")
        self.assertEqual(result.output["decision"], "HOLD")


if __name__ == "__main__":
    unittest.main()
