import os
import time
import datetime

from lite_world_model import WorldBuilder

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

from utils.xlogger import XLogger



class L2TacticalPlanner:
    def __init__(
        self,
        rover_client,
        perception_module,
        world_builder,
        llm_enabled: bool = LLM_ENABLED,
        fallback_enabled: bool = USE_FALLBACK_ON_ERROR,
    ):
        self.rover_client = rover_client
        self.perception_module = perception_module
        self.world_builder = WorldBuilder()

        self.llm_enabled = llm_enabled
        self.fallback_enabled = fallback_enabled

        self.llm = TacticalLLMDecisionMaker()
        self.fallback = FallbackGuidance()

    
         # 📁 carpeta única por ejecución
        run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = f"simulaciones/{run_id}"
        os.makedirs(self.output_dir, exist_ok=True)

        # 🔢 contador global
        self.sim_counter = 0
        
    def decide_action_with_llm(self, rover_state, perception_state, image_bytes):
        #print("[L2] Decide action with llm ...")
        #print("[LLM] Building prompt...")
        XLogger.log("L2", "Decide action with llm ...")
        

        prompt = build_tactical_prompt(rover_state, perception_state)
        raw_response = self.llm.decide_with_image(prompt, image_bytes)
        parsed_action = parse_llm_response(raw_response)
        validated_action = validate_action(parsed_action, rover_state, perception_state)
        #print(f"[LLM] Prompt:\n{prompt}")
        #print(f"[LLM] Raw response: {raw_response}")
        #print(f"[LLM] Parsed action: {parsed_action}")
        
        XLogger.log("L2", "_________________________________________________________________________")
        
        return validated_action, raw_response, prompt

    
        
    def decide_action(self, rover_state, perception_state, image_bytes):
        XLogger.log("L2", "Decide_action...")
        # 🔢 contador
        self.sim_counter += 1
        sim_id = self.sim_counter

        #print(f"\n[SIM {sim_id:04d}] =========================")
        XLogger.log("L2", f"\n[SIM {sim_id:04d}] =========================")

        # 💾 guardar imagen
        if image_bytes is not None:
            filename = f"{sim_id:04d}.jpg"
            filepath = os.path.join(self.output_dir, filename)

            with open(filepath, "wb") as f:
                f.write(image_bytes)

            #print(f"[SIM {sim_id:04d}] Image saved → {filepath}")
            XLogger.log("L2", f"[SIM {sim_id:04d}] Image saved → {filepath}")
        else:
            #print(f"[SIM {sim_id:04d}] No image captured")
            XLogger.log("L2", f"[SIM {sim_id:04d}] No image captured")
        
        if not self.llm_enabled:
            fallback_action = self.fallback.decide_action(rover_state, perception_state)
            return fallback_action, "FALLBACK_ONLY", None, "fallback"
        
        world_model = self.world_builder.update(rover_state, perception_state)
        #print('\n === WORLD MODEL SUMMARY=== ')
        #print(world_model.semantic_summary()) 
        #print('\n === WORLD MODEL FULL === ')
        #print(world_model) 
        
        
        try:
            action, raw_response, prompt = self.decide_action_with_llm(
                rover_state,
                perception_state,
                image_bytes,
            )

            
            return action, raw_response, prompt, "llm"

        except (DecisionValidationError, RuntimeError, ValueError) as exc:
            #print(f"[GUIDANCE] LLM decision failed: {exc}")
            XLogger.log("L2", f"[GUIDANCE] LLM decision failed: {exc}")

            if self.fallback_enabled:
                fallback_action = self.fallback.decide_action(rover_state, perception_state)
                return fallback_action, f"FALLBACK_AFTER_ERROR: {exc}", None, "fallback"

            raise

    

    def step(self, rover_state, perception_state, image_bytes):
        # 🔢 incrementar contador global
        self.sim_counter += 1
        sim_id = self.sim_counter
        #print(f"\n\nooooooooooooooooooooooooooooooooooooooooooooooooooooooooo\nooooooooooooooooooooooooooooooooooooooooooooooooooooooooo")
        #print(f"\n==============================")
        #print(f"[SIM {sim_id:04d}] NEW STEP")
        XLogger.log("L2", f"[SIM {sim_id:04d}] NEW STEP") 
        #print(f"==============================")
        #print("[STEP] Getting rover state...")
        #rover_state = self.rover_client.get_state()
        #print("[STEP] Getting perception state...")
        #perception_state, image_bytes = self.perception_module.observe_llm()
        #print('\nooooooooooooooooooooooooooooooooooooooooooooooooooooooooo')
        world_model = self.world_builder.update(rover_state, perception_state)
        #print('\n === WORLD MODEL SUMMARY=== ')
        #print(world_model.semantic_summary()) 
        #print('\n === WORLD MODEL SUMMARY=== ')
        #print('\n === WORLD MODEL FULL === ')
        #print(world_model) 
        #print('\n === WORLD MODEL FULL=== ')
        
        # 💾 guardar imagen
        if image_bytes is not None:
            filename = f"{sim_id:04d}.jpg"
            filepath = os.path.join(self.output_dir, filename)


        with open(filepath, "wb") as f:
            f.write(image_bytes)
        
        #print(f"[SIM {sim_id:04d}] Image saved → {filepath}")

        XLogger.log("L2", f"[SIM {sim_id:04d}] Image saved → {filepath}")
        
        ##print("[STEP] Deciding action...")
        #XLogger.log("L2", f"[SIM {sim_id:04d}] Image saved → {filepath}")
        
        action, decision_info, prompt, source = self.decide_action(
            rover_state,
            perception_state,
            image_bytes,
        )
        
        
        #if LLM_DEBUG:
        #    print("\n=== Guidance Step ===")
        #    print(f"Rover state: {rover_state}")
        #    print(f"Perception: {perception_state}")
        #    print(f"Decision source: {source}")
        #    print(f"Decision info: {decision_info}")
        #    print(f"Chosen action: {action.value}")

        # 🔐 APPROVAL STEP
        #approved = self._request_user_approval(action)
        approved = True
        if approved:
            self.rover_client.execute_tactical_action(action)
        else:
            #print("[USER] Action rejected → HOLD")
            XLogger.log("L2", "[USER] Action rejected → HOLD")
            action = TacticalAction.HOLD
            self.rover_client.execute_tactical_action(action)
            
        return action, decision_info, prompt, source   
            
    def _request_user_approval(self, action):
        try:
            user_input = input(f"\nApprove action {action.value}? [y/n]: ").strip().lower()
            return user_input in ("y", "yes")
        except KeyboardInterrupt:
            #print("\n[USER] Interrupted → rejecting action")
            XLogger.log("L2", "\n[USER] Interrupted → rejecting action")
            
            return False
        


    def run_loop(self, steps=10, delay_s=1.0):
        i=0
        for _ in range(steps):
            #print(f"\n[LOOP] Step {i+1}/{steps}")
            XLogger.log("L2", f"\n[LOOP] Step {i+1}/{steps}")
            
            i=i+1
            self.step()
            time.sleep(delay_s)
