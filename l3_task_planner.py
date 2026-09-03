from llm.memory_formatter import MemoryFormatter
from llm.l3_task_prompt import L3TaskPromptBuilder
from llm.l3_task_parser import parse_mode, validate_mode
from llm.llm_service import LLMService

from perception_module import PerceptionResult

from lite_world_model import WorldBuilder
from lite_world_model import WorldModel
from utils.xlogger import XLogger

import math

from l3_models import GuidanceTask, GuidanceTaskType
from l4_models import MissionTask
from lite_world_model.navigation_state import NavigationState


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

        navigation_state = self.build_navigation_state(
            rover_state,
            result.gps_state,
        )

        guidance_task = self.plan_guidance(
            navigation_state,
            mission,
        )

        self.last_navigation_state = navigation_state
        self.last_guidance_task = guidance_task

        XLogger.log(
            "L3",
            (
                f"Guidance: {guidance_task.task_type.value} "
                f"bearing={guidance_task.desired_heading_deg} "
                f"distance={guidance_task.distance_remaining_m} "
                f"heading_error={guidance_task.heading_error_deg}"
            ),
        )

        if guidance_task.task_type == GuidanceTaskType.HOLD:
            return None

        desired_direction = self._bearing_to_cardinal(
            guidance_task.desired_heading_deg
        )

        # Adapter hacia la interfaz que L2 ya utiliza.
        l3_task = {
            "task_type": "FOLLOW_BEARING",
            "desired_direction": desired_direction,
            "desired_heading_deg": guidance_task.desired_heading_deg,
            "distance_remaining_m": guidance_task.distance_remaining_m,
            "heading_error_deg": guidance_task.heading_error_deg,
            "task_text": (
                f"Move toward bearing "
                f"{guidance_task.desired_heading_deg:.1f} deg "
                f"({desired_direction})."
            ),
            "priority": "SAFETY_FIRST",
        }

        action, decision_info, prompt, source = self.l2_planner.step(
            rover_state,
            result,
            l3_task,
        )

        self.memory.update_step(
            rover_state,
            result.perception_state,
            action,
        )

        return action

    def build_navigation_state(self, rover_state, gps_state):
        gps_state = gps_state or {}

        position = gps_state.get("position") or {}

        if isinstance(position, dict):
            latitude = position.get("latitude", position.get("lat"))
            longitude = position.get("longitude", position.get("lon"))
        else:
            latitude = getattr(
                position,
                "latitude",
                getattr(position, "lat", None),
            )
            longitude = getattr(
                position,
                "longitude",
                getattr(position, "lon", None),
            )

        heading = gps_state.get("estimated_heading_deg")

        if heading is None:
            heading = rover_state.heading_deg

        position_valid = (
            bool(gps_state.get("gps_fix_ok", False))
            and latitude is not None
            and longitude is not None
        )

        return NavigationState(
            latitude=latitude,
            longitude=longitude,
            heading_deg=heading,
            speed_m_s=rover_state.speed_m_s,
            position_valid=position_valid,
            heading_valid=heading is not None,
        )


    def plan_guidance(self, navigation_state, mission):
        if mission.task != MissionTask.GOTO:
            return GuidanceTask(
                task_type=GuidanceTaskType.HOLD,
            )

        if not navigation_state.position_valid:
            XLogger.log("L3", "No valid GPS position -> HOLD")
            return GuidanceTask(
                task_type=GuidanceTaskType.HOLD,
            )

        distance_m = self._distance_m(
            navigation_state.latitude,
            navigation_state.longitude,
            mission.target_lat,
            mission.target_lon,
        )

        bearing_deg = self._bearing_deg(
            navigation_state.latitude,
            navigation_state.longitude,
            mission.target_lat,
            mission.target_lon,
        )

        heading_error_deg = None

        if navigation_state.heading_valid:
            heading_error_deg = self._normalize_angle(
                bearing_deg - navigation_state.heading_deg
            )

        if distance_m <= mission.arrival_radius_m:
            return GuidanceTask(
                task_type=GuidanceTaskType.HOLD,
                desired_heading_deg=bearing_deg,
                distance_remaining_m=distance_m,
                heading_error_deg=heading_error_deg,
            )

        return GuidanceTask(
            task_type=GuidanceTaskType.FOLLOW_BEARING,
            desired_heading_deg=bearing_deg,
            distance_remaining_m=distance_m,
            heading_error_deg=heading_error_deg,
        )


    @staticmethod
    def _distance_m(lat1, lon1, lat2, lon2):
        earth_radius_m = 6371000.0

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)

        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = (
            math.sin(dphi / 2.0) ** 2
            + math.cos(phi1)
            * math.cos(phi2)
            * math.sin(dlambda / 2.0) ** 2
        )

        c = 2.0 * math.atan2(
            math.sqrt(a),
            math.sqrt(1.0 - a),
        )

        return earth_radius_m * c


    @staticmethod
    def _bearing_deg(lat1, lon1, lat2, lon2):
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dlambda = math.radians(lon2 - lon1)

        y = math.sin(dlambda) * math.cos(phi2)

        x = (
            math.cos(phi1) * math.sin(phi2)
            - math.sin(phi1)
            * math.cos(phi2)
            * math.cos(dlambda)
        )

        bearing = math.degrees(math.atan2(y, x))

        return (bearing + 360.0) % 360.0


    @staticmethod
    def _normalize_angle(angle_deg):
        return (angle_deg + 180.0) % 360.0 - 180.0


    @staticmethod
    def _bearing_to_cardinal(bearing_deg):
        directions = [
            "N",
            "NE",
            "E",
            "SE",
            "S",
            "SW",
            "W",
            "NW"
        ]

        index = int((bearing_deg + 22.5) // 45.0) % 8

        return directions[index]


    
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
