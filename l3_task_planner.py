from llm.memory_formatter import MemoryFormatter
from llm.l3_task_prompt import L3TaskPromptBuilder
from llm.l3_task_parser import parse_mode, validate_mode
from llm.llm_service import LLMService

from perception_module import PerceptionResult

from lite_world_model import WorldBuilder
from lite_world_model import WorldModel
from utils.xlogger import XLogger


class L3TaskPlanner:
    world = WorldModel
    def __init__(self, l2_planner, perception_module, memory_system, llm_service=None):
        self.l2_planner = l2_planner
        self.perception = perception_module
        self.memory = memory_system
        self.llm = llm_service or LLMService()
        self.current_mode = "EXPLORE"

    #def step(self, rover_state, result, mission):
    def step(self, rover_state, result, mission):

        XLogger.log("L3", "step")        
        #mode = self.decide_mode(rover_state, result.perception_state)         NOT NEEDED BY NOW
        
        # DE MOMENTO FIJA
        l3_task = {
            "task_type": "MOVE_IN_CARDINAL_DIRECTION",
            "desired_direction": "W",
            "task_text": "Move generally toward WEST.",
            "priority": "SAFETY_FIRST"
        }


        
        action, decision_info, prompt, source = self.l2_planner.step(
            rover_state,
            result,
            l3_task
        )
        
        self.memory.update_step(rover_state, result.perception_state, action)
        return action


    def decide_mode(self, rover_state, perception_state):
        XLogger.log("L3", "decide_mode (LLM)")
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
        # =========================
        # 3. Llamar al LLM
        # =========================
        response = self.llm.decide_task_mode(prompt)
        # =========================
        # 4. Parsear y validar
        # =========================
        mode = parse_mode(response)
        mode = validate_mode(mode)
        return mode

    def call_llm_for_mode(self, context):
        XLogger.log("L3", "call_llm_for_mode")
        return "EXPLORE"

    def detect_stuck(self):
        XLogger.log("L3", "detect_stuck")
        return False
