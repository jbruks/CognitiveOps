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
from rover_interfaces import TacticalAction


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
        
    def decide_action_with_llm(self, rover_state, perception_state, image_bytes):
        print("[LLM] Building prompt...")
        prompt = build_tactical_prompt(rover_state, perception_state)
        raw_response = self.llm.decide_with_image(prompt, image_bytes)
        parsed_action = parse_llm_response(raw_response)
        validated_action = validate_action(parsed_action, rover_state, perception_state)
        print(f"[LLM] Prompt:\n{prompt}")
        print(f"[LLM] Raw response: {raw_response}")
        print(f"[LLM] Parsed action: {parsed_action}")
        return validated_action, raw_response, prompt

    def decide_action_with_llm_OLD(self, rover_state, perception_state):
        prompt = build_tactical_prompt(rover_state, perception_state)
        raw_response = self.llm.decide(prompt)
        parsed_action = parse_llm_response(raw_response)
        validated_action = validate_action(parsed_action, rover_state, perception_state)
        return validated_action, raw_response, prompt
        
    def decide_action(self, rover_state, perception_state, image_bytes):
        if not self.llm_enabled:
            fallback_action = self.fallback.decide_action(rover_state, perception_state)
            return fallback_action, "FALLBACK_ONLY", None, "fallback"

        try:
            action, raw_response, prompt = self.decide_action_with_llm(
                rover_state,
                perception_state,
                image_bytes,
            )

            
            return action, raw_response, prompt, "llm"

        except (DecisionValidationError, RuntimeError, ValueError) as exc:
            print(f"[GUIDANCE] LLM decision failed: {exc}")

            if self.fallback_enabled:
                fallback_action = self.fallback.decide_action(rover_state, perception_state)
                return fallback_action, f"FALLBACK_AFTER_ERROR: {exc}", None, "fallback"

            raise

    def decide_action_OLD(self, rover_state, perception_state):
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
        print("[STEP] New Step")
        print("[STEP] Getting rover state...")
        rover_state = self.rover_client.get_state()
        print("[STEP] Getting perception state...")
        perception_state, image_bytes = self.perception_module.observe_llm()
        
        print("[STEP] Deciding action...")
        action, decision_info, prompt, source = self.decide_action(
            rover_state,
            perception_state,
            image_bytes,
        )
        if LLM_DEBUG:
            print("\n=== Guidance Step ===")
            print(f"Rover state: {rover_state}")
            print(f"Perception: {perception_state}")
            print(f"Decision source: {source}")
            print(f"Decision info: {decision_info}")
            print(f"Chosen action: {action.value}")

        # 🔐 APPROVAL STEP
        #approved = self._request_user_approval(action)
        approved = True
        if approved:
            self.rover_client.execute_tactical_action(action)
        else:
            print("[USER] Action rejected → HOLD")
            action = TacticalAction.HOLD
            self.rover_client.execute_tactical_action(action)
            
            
            
    def _request_user_approval(self, action):
        try:
            user_input = input(f"\nApprove action {action.value}? [y/n]: ").strip().lower()
            return user_input in ("y", "yes")
        except KeyboardInterrupt:
            print("\n[USER] Interrupted → rejecting action")
            return False
        

    def step_OLD(self):
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
        i=0
        for _ in range(steps):
            print(f"\n[LOOP] Step {i+1}/{steps}")
            i=i+1
            self.step()
            time.sleep(delay_s)
