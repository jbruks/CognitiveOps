class L3TaskPlanner:
    def __init__(self, navigator, perception_module, memory_system, llm_service=None):
        self.navigator = navigator
        self.perception = perception_module
        self.memory = memory_system
        self.llm = llm_service

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
        print("[L3] decide_mode")
        return "EXPLORE"

    def call_llm_for_mode(self, context):
        print("[L3] call_llm_for_mode")
        return "EXPLORE"

    def detect_stuck(self):
        print("[L3] detect_stuck")
        return False
