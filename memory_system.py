from utils.xlogger import XLogger

class MemorySystem:
    def __init__(self):
        self.short_term = []
        self.task_context = {}
        self.mission_context = {}

    def update_step(self, rover_state, perception_state, action):
        XLogger.log("class MemorySystem:", "update_step")

        #print("[MEMORY] update_step")
        self.short_term.append({
            "rover": rover_state,
            "perception": perception_state,
            "action": action,
        })

    def get_recent_history(self, n=5):
        XLogger.log("class MemorySystem:", "get_recent_history")

        return self.short_term[-n:]

    def get_task_context(self):
        XLogger.log("class MemorySystem:", "get_task_context")
        
        return self.task_context

    def set_task_context(self, context):
        XLogger.log("class MemorySystem:", "set_task_context")
        
        self.task_context = context

    def get_mission_context(self):
        XLogger.log("class MemorySystem:", "get_mission_context")
        
        return self.mission_context

    def set_mission_context(self, context):
        XLogger.log("class MemorySystem:", "set_mission_context")
        
        self.mission_context = context
