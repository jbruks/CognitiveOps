class LLMService:
    def decide_tactical(self, prompt, image_bytes=None):
        print("[LLM] tactical decision")
        return "MOVE_FORWARD"

    def decide_task_mode(self, prompt):
        print("[LLM] task mode decision")
        return "EXPLORE"

    def decide_mission(self, prompt):
        print("[LLM] mission decision")
        return "EXPLORE"
