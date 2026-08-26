import os
import time
import datetime
from utils.xlogger import XLogger

from perception_module import PerceptionResult

class L4MissionPlanner:
    def __init__(self, perception_module, l1_rover_controler, task_planner, memory_system, llm_service=None):
        self.l1_rover_controler = l1_rover_controler
        self.task_planner = task_planner
        self.memory = memory_system
        self.llm = llm_service
        self.current_task = "EXPLORE"
        self.perception = perception_module
        
        run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = f"simulaciones/{run_id}"
        os.makedirs(self.output_dir, exist_ok=True)
        # 🔢 contador global
        self.sim_counter = 0

    def run_loop(self, steps=10, delay_s=1.0):
        XLogger.log("L4", "Starting mission loop ")
        
        for i in range(steps):
            XLogger.log("L4", f"begin run loop {i+1}/{steps}" + "       ------------------------------------")
            self.step()
            time.sleep(delay_s)
            XLogger.log("L4", f"end run loop {i+1}/{steps}" + "     ------------------------------------")


    def step(self):
        XLogger.log("L4", "step")
        rover_state = self.l1_rover_controler.get_state()
        
        #task = self.decide_task(rover_state)
        mission = self.decide_task(rover_state)

        
        result = self.perception.observe_llm()
        perception_state=result.perception_state
        image_bytes=result.image_bytes
        
        self.sim_counter += 1
        sim_id = self.sim_counter        
        # 💾 guardar imagen
        if image_bytes is not None:
            filename = f"{sim_id:04d}.jpg"
            filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)   
            
        XLogger.log("L4", f"step [SIM {sim_id:04d}] Image saved → {filepath}")
        world = result.world_model
        #action = self.task_planner.step(rover_state, result)
        action = self.task_planner.step(
            rover_state,
            result,
            mission
        )        

    def decide_task(self, rover_state):
        XLogger.log("L4", "decide_task")
        return {
            "mission_type": "GO_TO_GPS",
            "target_position": {
                "lat": 39.470000,
                "lon": -0.500000
            },
            "mission_text": "Reach target GPS position."
    }

    def call_llm_for_task(self, context):
        XLogger.log("L4", "call_llm_for_task")
        return "EXPLORE"
