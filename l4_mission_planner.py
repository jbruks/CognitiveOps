import time
from utils.xlogger import XLogger


class L4MissionPlanner:
    def __init__(self, l1_rover_controler, task_planner, memory_system, llm_service=None):
        self.l1_rover_controler = l1_rover_controler
        self.task_planner = task_planner
        self.memory = memory_system
        self.llm = llm_service

        self.current_task = "EXPLORE"

    def run_loop(self, steps=10, delay_s=1.0):
        #print("[L4] Starting mission loop")
        XLogger.log("L4", "Starting mission loop")
        for i in range(steps):
            #print(f"\n[L4] Step {i+1}/{steps}")
            XLogger.log("L4", f"\n[L4] Step {i+1}/{steps}")
            self.step()
            time.sleep(delay_s)

    def step(self):
        #print("[L4] step")
        XLogger.log("L4", "step")

        rover_state = self.l1_rover_controler.get_state()

        task = self.decide_task(rover_state)

        action = self.task_planner.step(rover_state)

        #self.l1_rover_controler.execute_tactical_action(action)

    def decide_task(self, rover_state):
        #print("[L4] decide_task")
        XLogger.log("L4", "decide_task")
        return "EXPLORE"

    def call_llm_for_task(self, context):
        #print("[L4] call_llm_for_task")
        XLogger.log("L4", "call_llm_for_task")
        return "EXPLORE"
