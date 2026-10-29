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

    def record_mission_event(self, objective_id, event_type, details):
        """Append an attributable high-level event without replacing legacy memory."""
        from datetime import datetime, timezone
        if not objective_id or not event_type or not isinstance(details, dict):
            raise ValueError("Valid objective_id, event_type and details are required")
        self.mission_context.setdefault("events", []).append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "objective_id": objective_id,
            "type": event_type,
            "details": details.copy(),
        })

    def get_mission_events(self, n=None):
        events = self.mission_context.get("events", [])
        return list(events if n is None else events[-n:])

    def record_navigation_event(self, objective_id, status, reason=None,
                                distance_remaining_m=None):
        if not objective_id or not status:
            raise ValueError("Navigation event needs an objective and status")
        events = self.task_context.setdefault("navigation_events", [])
        events.append({
            "objective_id": objective_id, "status": status,
            "reason": reason, "distance_remaining_m": distance_remaining_m,
        })

    def get_navigation_events(self, n=10):
        return list(self.task_context.get("navigation_events", [])[-n:])
