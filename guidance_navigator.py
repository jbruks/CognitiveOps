import time

from config import LLM_ENABLED, USE_FALLBACK_ON_ERROR
from config import LLM_DEBUG
from decision_validator import (
    DecisionValidationError,
    parse_llm_response,
    validate_action,
)
from fallback_guidance import FallbackGuidance
from llm_decision import TacticalLLMDecisionMaker
from prompt_builder import build_tactical_prompt


class GuidanceNavigator:
    def __init__(
        self,
        rover_client,
        perception_module,
        llm_enabled: bool = LLM_ENABLED,
        fallback_enabled: bool = USE_FALLBACK_ON_ERROR,
    ):
        self.rover_client = rover_client
        self.perception_module = perception_module
        self.llm_enabled = llm_enabled
        self.fallback_enabled = fallback_enabled

        self.llm = TacticalLLMDecisionMaker()
        self.fallback = FallbackGuidance()

    def decide_action_with_llm(self, rover_state, perception_state):
        prompt = build_tactical_prompt(rover_state, perception_state)
        raw_response = self.llm.decide(prompt)
        parsed_action = parse_llm_response(raw_response)
        validated_action = validate_action(parsed_action, rover_state, perception_state)
        return validated_action, raw_response, prompt

    def decide_action(self, rover_state, perception_state):
        if not self.llm_enabled:
            fallback_action = self.fallback.decide_action(rover_state, perception_state)
            return fallback_action, "FALLBACK_ONLY", None, "fallback"

        try:
            action, raw_response, prompt = self.decide_action_with_llm(
                rover_state,
                perception_state,
            )
            return action, raw_response, prompt, "llm"

        except (DecisionValidationError, RuntimeError, ValueError) as exc:
            print(f"[GUIDANCE] LLM decision failed: {exc}")

            if self.fallback_enabled:
                fallback_action = self.fallback.decide_action(rover_state, perception_state)
                return fallback_action, f"FALLBACK_AFTER_ERROR: {exc}", None, "fallback"

            raise

    def step(self):
        rover_state = self.rover_client.get_state()
        perception_state = self.perception_module.observe()

        action, decision_info, prompt, source = self.decide_action(
            rover_state,
            perception_state,
        )
        
        if LLM_DEBUG and prompt is not None:
            print("\n--- PROMPT ---")
            print(prompt)

        if LLM_DEBUG:
            print("\n--- LLM RESPONSE ---")
            print(decision_info)

        print("\n=== Guidance Step ===")
        print(f"Rover state: {rover_state}")
        print(f"Perception: {perception_state}")
        print(f"Decision source: {source}")
        print(f"Decision info: {decision_info}")
        print(f"Chosen action: {action.value}")

        if prompt is not None:
            print("--- LLM Prompt ---")
            print(prompt)
        

        self.rover_client.execute_tactical_action(action)

    def run_loop(self, steps=10, delay_s=1.0):
        for _ in range(steps):
            self.step()
            time.sleep(delay_s)
