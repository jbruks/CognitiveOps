from llm.memory_formatter import MemoryFormatter
from llm.l3_task_prompt import L3TaskPromptBuilder
from llm.l3_task_parser import parse_mode, validate_mode
from llm.llm_service import LLMService

class L3TaskPlanner:
    def __init__(self, navigator, perception_module, memory_system, llm_service=None):
        self.navigator = navigator
        self.perception = perception_module
        self.memory = memory_system
        self.llm = llm_service or LLMService()

        self.current_mode = "EXPLORE"

    def step(self, rover_state):
        print("[L3] Step")

        perception_state, image_bytes = self.perception.observe_llm()

        mode = self.decide_mode(rover_state, perception_state)

        action, decision_info, prompt, source = self.navigator.decide_action(
            rover_state,
            perception_state,
            image_bytes,
        )

        self.memory.update_step(rover_state, perception_state, action)

        return action

    def decide_mode(self, rover_state, perception_state):
        print("[L3] decide_mode (LLM)")

        # =========================
        # 1. Construir contexto desde memoria
        # =========================
        context = MemoryFormatter.build_l3_context(
            self.memory,
            rover_state,
            perception_state,
        )

        # =========================
        # 2. Construir prompt
        # =========================
        prompt = L3TaskPromptBuilder().build(context)

        print("[L3] Prompt:\n", prompt)

        # =========================
        # 3. Llamar al LLM
        # =========================
        response = self.llm.decide_task_mode(prompt)

        print("[L3] Raw response:", response)

        # =========================
        # 4. Parsear y validar
        # =========================
        mode = parse_mode(response)
        mode = validate_mode(mode)

        print("[L3] Final mode:", mode)

        return mode

    def call_llm_for_mode(self, context):
        print("[L3] call_llm_for_mode")
        return "EXPLORE"

    def detect_stuck(self):
        print("[L3] detect_stuck")
        return False
