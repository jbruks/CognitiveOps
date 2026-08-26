from utils.xlogger import XLogger

class LLMService:
    def decide_tactical(self, prompt, image_bytes=None):
        XLogger.log("class LLMService:", "decide_tactical")
        #print("[LLM] tactical decision")
        return "MOVE_FORWARD"

    def decide_task_mode(self, prompt):
        XLogger.log("class LLMService:", "decide_task_mode")
        #print("[LLM] task mode decision")
        return "EXPLORE"

    def decide_mission(self, prompt):
        XLogger.log("class LLMService:", "decide_mission")
        #print("[LLM] mission decision")
        return "EXPLORE"
