import os
import time
import datetime
from utils.xlogger import XLogger

from perception_module import PerceptionResult

from l3_models import GuidanceTaskType, NavigationObjective, NavigationStatus
from l4_models import MissionStatus

class L4MissionPlanner:
    def __init__(
        self,
        perception_module,
        l1_rover_controler,
        task_planner,
        memory_system,
        mission,
        llm_service=None,
    ):
        self.mission = mission
        self.l1_rover_controler = l1_rover_controler
        self.task_planner = task_planner
        self.memory = memory_system
        # By default use the very same inference service injected into L3.
        # Do not invoke inference automatically during the control cycle.
        self.llm = llm_service if llm_service is not None else getattr(
            task_planner, "llm", None
        )
        self.current_task = "EXPLORE"
        self.last_navigation_result = None
        self.navigation_objective = (
            NavigationObjective("GOTO-001", mission.target_lat,
                                mission.target_lon, mission.arrival_radius_m,
                                "Reach authorized destination")
            if mission.task.value == "GOTO"
            and mission.target_lat is not None
            and mission.target_lon is not None else None
        )
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
            if self.mission.status == MissionStatus.COMPLETED:
                XLogger.log("L4", "Mission completed")
                break
            time.sleep(delay_s)
            XLogger.log("L4", f"end run loop {i+1}/{steps}" + "     ------------------------------------")


    def step(self):
        XLogger.log("L4", "step")
        rover_state = self.l1_rover_controler.get_state()

        # Diagnostic-only sample every L4 cycle, even when phone GPS is unavailable.
        # L2 remains the authority for the safety read immediately before a maneuver.
        try:
            sensor_diag = self.l1_rover_controler.get_front_sensor_state()
            XLogger.log("L4-ULTRASONIC", f"Cycle sample: {sensor_diag}")
        except Exception as exc:
            XLogger.log("L4-ULTRASONIC", f"Cycle sample ERROR: {exc}")
       
        result = self.perception.observe_llm()
        
        self.mission.status = MissionStatus.ACTIVE

        if (self.navigation_objective is not None
                and callable(getattr(self.task_planner, "step_objective", None))):
            self.last_navigation_result = self.task_planner.step_objective(
                rover_state, result, self.navigation_objective
            )
            if self.last_navigation_result.status == NavigationStatus.COMPLETED:
                self.mission.status = MissionStatus.COMPLETED
                self.l1_rover_controler.stop()
                XLogger.log("L4", "Navigation objective completed")
            elif self.last_navigation_result.status in (
                    NavigationStatus.BLOCKED, NavigationStatus.FAILED):
                self.l1_rover_controler.stop()
                XLogger.log("L4", "Navigation requires review: "
                            + str(self.last_navigation_result.reason))
        else:
            self.task_planner.step(
                rover_state,
                result,
                self.mission,
            )

            guidance = self.task_planner.last_guidance_task

            if guidance.task_type == GuidanceTaskType.HOLD:
                if (
                    guidance.distance_remaining_m is not None
                    and guidance.distance_remaining_m <= self.mission.arrival_radius_m
                ):
                    self.mission.status = MissionStatus.COMPLETED

                    XLogger.log(
                        "L4",
                        (
                            "GO_TO_POINT completed: "
                            f"distance={guidance.distance_remaining_m:.2f} m"
                        ),
                    )
                else:
                    XLogger.log(
                        "L4",
                        "Guidance HOLD: navigation state not valid",
                    )

                self.l1_rover_controler.stop()
        
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
        

   
    

    def plan_from_intent(self, intent: str, approved_objectives):
        """Explicit non-actuating L4 selection from operator-approved destinations."""
        if not isinstance(intent, str) or not intent.strip():
            raise ValueError("Mission intent is required")
        objectives = list(approved_objectives)
        if not objectives or any(not isinstance(item, NavigationObjective)
                                 for item in objectives):
            raise ValueError("Provide approved NavigationObjective instances")
        ids = [item.objective_id for item in objectives]
        if len(ids) != len(set(ids)) or any(not value for value in ids):
            raise ValueError("Objective identifiers must be unique and nonempty")
        if self.llm is None:
            raise RuntimeError("Shared inference service unavailable")
        advice = self.llm.infer(
            level="L4",
            instructions=("Select one approved destination for the mission intent. "
                          "Do not invent coordinates or motor commands."),
            context={"intent": intent, "approved_objectives": [
                {"objective_id": item.objective_id, "purpose": item.purpose}
                for item in objectives]},
            allowed_decisions=ids,
        )
        chosen = next(item for item in objectives
                      if item.objective_id == advice.output["decision"])
        # Do not activate the objective or move the rover here.
        return chosen, advice

    def prepare_inspection_plan(self, intent, approved_objectives,
                                observation_questions, doctrine_service=None):
        """Prepare an inert inspection plan; no GPS target is activated here.

        LLM may choose a first approved objective, but cannot invent coordinates.
        Doctrine excerpts are recorded as attributed references, not commands.
        """
        from mf_dod_mission import InspectionObjective, InspectionPlan
        approved = list(approved_objectives)
        if not approved:
            raise ValueError("No approved observation points")
        if any(o.objective_id not in observation_questions for o in approved):
            raise ValueError("Missing observation question for objective")
        hits = (doctrine_service.retrieve(intent) if doctrine_service else [])
        citations = ([doctrine_service.provenance(hit) for hit in hits]
                     if doctrine_service else [])
        from llm.prompt_framework import PromptBuilderBase
        context = PromptBuilderBase.compose_cognitive_context(
            "L4", intent, None, {"approved_only": True},
            self.memory.get_mission_events() if hasattr(
                self.memory, "get_mission_events") else (),
            citations,
        )
        advice = self.llm.plan_objectives(
            intent,
            [{"objective_id": item.objective_id, "purpose": item.purpose,
              "question": observation_questions[item.objective_id]}
             for item in approved],
            context=context,
        )
        approved_by_id = {item.objective_id: item for item in approved}
        ordered = [approved_by_id[oid] for oid in advice.output["objective_ids"]]
        first = ordered[0]
        plan = InspectionPlan(
            intent=intent,
            objectives=[
                InspectionObjective(o, observation_questions[o.objective_id])
                for o in ordered
            ],
            doctrine=citations,
            decisions=[{"event": "PLAN_CREATED", "selected_first": first.objective_id,
                        "provider": advice.provider,
                        "reason": advice.output["reason"]}],
        )
        return plan

    def call_llm_for_task(self, context):
        XLogger.log("L4", "call_llm_for_task")
        return "EXPLORE"
