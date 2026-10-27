from dataclasses import dataclass
from typing import List, Optional
from openai import OpenAI
import cv2
import base64
import json
import os
from rover_interfaces import PerceptionState
from vision_nn import VisionNN

# Restore tested local neural perception; the worker remains on the ZBook via SSH.
USE_VISION_NN = True

from lite_world_model import WorldBuilder
from lite_world_model import WorldModel

from sensors.gps_service import GPSService


from utils.xlogger import XLogger



@dataclass
class SimulatedScenario:
    name: str
    obstacle_ahead: bool
    free_direction: str
    corridor_visible: bool
    summary: str
    confidence: float = 1.0
    
@dataclass
class PerceptionResult:
    perception_state: PerceptionState
    world_model: object | None = None
    semantic_summary: str = ""
    image_bytes: bytes | None = None
    gps_state: dict | None = None
    front_sensor: dict | None = None


def fuse_front_sensor(result: PerceptionResult, sensor: dict) -> PerceptionResult:
    """Augment existing vision perception without mistaking ultrasonic clearance for vision clearance."""
    result.front_sensor = dict(sensor)
    blocked = sensor["front_blocked"]
    valid = sensor["front_distance_valid"]
    if blocked or not valid:
        state = result.perception_state
        state.obstacle_ahead = True
        state.corridor_visible = False
        state.summary = (state.summary + " | FRONT_ULTRASONIC_BLOCKED").strip()
        # Do not rewrite LEFT/RIGHT regions: a narrow sonar cone cannot assess them.
        for region in (state.regions or []):
            if isinstance(region, dict) and region.get("name") == "front":
                region["traversable"] = False
        if state.free_direction == "center":
            state.free_direction = "none"
    return result


class PerceptionModule:
    #world = WorldModel
    
    BUILTIN_SCENARIOS = {
        "corridor_forward": SimulatedScenario(
            name="corridor_forward",
            obstacle_ahead=False,
            free_direction="center",
            corridor_visible=True,
            summary="Clear corridor ahead."
        ),
        "obstacle_left_open": SimulatedScenario(
            name="obstacle_left_open",
            obstacle_ahead=True,
            free_direction="left",
            corridor_visible=False,
            summary="Obstacle ahead. Left side looks traversable."
        ),
        "obstacle_right_open": SimulatedScenario(
            name="obstacle_right_open",
            obstacle_ahead=True,
            free_direction="right",
            corridor_visible=False,
            summary="Obstacle ahead. Right side looks traversable."
        ),
        "blocked": SimulatedScenario(
            name="blocked",
            obstacle_ahead=True,
            free_direction="none",
            corridor_visible=False,
            summary="Obstacle ahead and no safe path detected."
        ),
        "uncertain": SimulatedScenario(
            name="uncertain",
            obstacle_ahead=False,
            free_direction="none",
            corridor_visible=False,
            summary="Environment unclear.",
            confidence=0.4
        ),
    }

    def __init__(
        self,
        mode: str = "camera",  # 🔥 NEW
        default_scenario: str = "corridor_forward",
        scenario_sequence: Optional[List[str]] = None,
        loop_sequence: bool = True,
        gps_enabled=True,
        max_output_tokens: int = 500,
        
    ):
        XLogger.log("PerceptionModule", "__init__")
        self.mode = mode
        self.max_output_tokens = max_output_tokens
        self.worldbuilder = WorldBuilder()
        self.vision_nn = VisionNN() if USE_VISION_NN else None

        # --- GPS SETUP ---
        # Perception only reads GPS state. It does not interpret mission, target,
        # route, progress, or tactical meaning.
        self.gps_enabled = gps_enabled
        self.gps = None

        if self.gps_enabled:
            try:
                #self.gps = GPSService()
                self.gps = GPSService(
                        history_size=120,
                        min_heading_distance_m=3.0,
                    )
                self.gps.start()
                XLogger.log("PerceptionModule", "GPSService started")
            except Exception as exc:
                self.gps = None
                self.gps_enabled = False
                XLogger.log("PerceptionModule", f"GPSService disabled: {exc}")

        # --- SIMULATION SETUP ---
        self.default_scenario = default_scenario
        self.scenario_sequence = scenario_sequence or []
        self.loop_sequence = loop_sequence
        self.sequence_index = 0
        self.current_scenario_name = default_scenario

        # --- CAMERA SETUP ---
        
        


        #if self.mode == "camera":
        #    self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        #    self.cap.set( cv2.CAP_PROP_BUFFERSIZE,1)
            
        
        CAMERA_DEVICE = ("/dev/v4l/by-id/usb-046d_0825_E88EE230-video-index0")

        if self.mode == "camera":
            self.cap = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)    
            
            
            
        self.llm_client = None
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.llm_client = OpenAI(api_key=api_key)

    # =========================
    # SIMULATION LOGIC (UNCHANGED)
    # =========================

    def _get_next_scenario_name(self) -> str:
        if not self.scenario_sequence:
            return self.current_scenario_name

        if self.sequence_index >= len(self.scenario_sequence):
            if self.loop_sequence:
                self.sequence_index = 0
            else:
                return self.scenario_sequence[-1]

        scenario_name = self.scenario_sequence[self.sequence_index]
        self.sequence_index += 1
        return scenario_name

    def _observe_simulated(self) -> PerceptionState:
        scenario_name = self._get_next_scenario_name()
        scenario = self.BUILTIN_SCENARIOS[scenario_name]

        return PerceptionState(
            obstacle_ahead=scenario.obstacle_ahead,
            free_direction=scenario.free_direction,
            corridor_visible=scenario.corridor_visible,
            summary=scenario.summary,
            confidence=scenario.confidence,
        )

    # =========================
    # CAMERA LOGIC (NEW)
    # =========================

    def _observe_camera(self, frame) -> PerceptionState:
        XLogger.log("Perception", "_observe_camera")
        #ret, frame = self.cap.read()

        if not ret:
            return PerceptionState(
                obstacle_ahead=False,
                free_direction="none",
                corridor_visible=False,
                summary="Camera error",
                confidence=0.0,
            )
        frame = cv2.resize(frame, (320, 240))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        h, w = edges.shape

        left = edges[:, :w//3].sum()
        center = edges[:, w//3:2*w//3].sum()
        right = edges[:, 2*w//3:].sum()

        #threshold = 50000
        threshold = 5000
        obstacle = center > threshold

        if obstacle:
            free = "left" if left < right else "right"
        else:
            free = "center"

        print(f"[VISION] L:{left} C:{center} R:{right} → {free}")

        return PerceptionState(
            obstacle_ahead=obstacle,
            free_direction=free,
            corridor_visible=not obstacle,
            summary=f"L:{left} C:{center} R:{right}",
            confidence=0.8,
        )

    # =========================
    # GPS LOGIC
    # =========================

    def _observe_gps(self) -> dict | None:
        """Read pure GPS state, if GPS is enabled.

        This method does not interpret destination, mission progress, route,
        or tactical decisions. It only exposes raw/normalized GPS sensor state.
        """
        if not self.gps_enabled or self.gps is None:
            return None

        try:
            return self.gps.get_state()
        except Exception as exc:
            XLogger.log("Perception", f"GPS read error: {exc}")
            return {
                "gps_fix_ok": False,
                "position": None,
                "reason": f"GPS read error: {exc}",
            }


    # =========================
    # MAIN ENTRY POINT
    # =========================

    def observe(self) -> PerceptionState:
        XLogger.log("Perception", "Observe")
        if self.mode == "camera":
            return self._observe_camera()
        else:
            return self._observe_simulated()


    def observe_llm(self):
        XLogger.log("Perception", "Observe_llm")
        """
        LLM-based perception + image output
        """
        gps_state = self._observe_gps()
        

        
        if self.mode != "camera":
            state = self._observe_simulated()
            world = self.worldbuilder.update(
                rover_state=None,
                perception_state=state,
            )

            return PerceptionResult(
                perception_state=state,
                world_model=world,
                gps_state=gps_state,
            )
            
        XLogger.log("Perception", "Camera capture START") 
        
        for _ in range(3):
            self.cap.grab()
            
        ret, frame = self.cap.read()

        XLogger.log("Perception", "Camera capture END")

        if not ret:
            return PerceptionResult(
                perception_state=PerceptionState(
                    obstacle_ahead=False,
                    free_direction="none",
                    corridor_visible=False,
                    summary="Camera error",
                    confidence=0.0,
                ),
                gps_state=gps_state,
            )
        
        XLogger.log("Perception", "Image preprocessing START")
        
        frame = cv2.resize(frame, (320, 240))

        vision_nn_result = self.vision_nn.analyze(frame) if USE_VISION_NN else {}
        
        ##############
        
        
        XLogger.log(
            "Perception",
            "VisionNN " + json.dumps(
                vision_nn_result,
                separators=(",", ":"),
            ),
        )

        ok, buffer = cv2.imencode(".jpg", frame)
        image_bytes = buffer.tobytes() if ok else None

        if image_bytes is None:
            return PerceptionResult(
                perception_state=PerceptionState(
                    obstacle_ahead=False,
                    free_direction="none",
                    corridor_visible=False,
                    summary="Encoding error",
                    confidence=0.0,
                ),
                gps_state=gps_state,
            )

        # =====================================================
        # VisionNN-only perception
        # =====================================================

        if vision_nn_result.get("source") == "vision_nn_fusion":

            nn_regions = vision_nn_result.get("regions", {})
            geometry_confidence = vision_nn_result.get(
                "geometry_confidence",
                "LOW",
            )
            temporal_stability = vision_nn_result.get(
                "temporal_stability",
                "UNKNOWN",
            )

            MIN_CANDIDATE_FRACTION = 0.02
            MIN_NONTRAVERSABLE_FRACTION = 0.50
            MIN_CLEARANCE_M = 1.0

            regions = []
            objects = []

            region_traversable = {}

            for name in ("left", "front", "right"):

                r = nn_regions.get(name, {})

                candidate_fraction = float(
                    r.get("candidate_fraction", 0.0) or 0.0
                )

                traversable_fraction = float(
                    r.get("traversable_fraction", 0.0) or 0.0
                )

                candidate_nontrav = r.get(
                    "candidate_nontraversable_fraction"
                )

                distance = r.get("distance_p25_m")

                blocking = (
                    candidate_nontrav is not None
                    and distance is not None
                    and candidate_fraction >= MIN_CANDIDATE_FRACTION
                    and candidate_nontrav >= MIN_NONTRAVERSABLE_FRACTION
                    and distance <= MIN_CLEARANCE_M
                )

                traversable = not blocking
                
                region_traversable[name] = traversable

                regions.append({
                    "name": name,
                    "traversable": traversable,
                    "candidate_fraction": candidate_fraction,
                    "traversable_fraction": traversable_fraction,
                    "candidate_traversable_fraction":
                        r.get("candidate_traversable_fraction"),
                    "candidate_nontraversable_fraction":
                        candidate_nontrav,
                    "distance_p25_m": distance,
                })

                if blocking:
                    objects.append({
                        "type": "obstacle",
                        "position": {
                            "region": name,
                        },
                        "distance_m": distance,
                        "traversable": False,
                    })

            front_traversable = region_traversable.get(
                "front",
                False,
            )

            left_traversable = region_traversable.get(
                "left",
                False,
            )

            right_traversable = region_traversable.get(
                "right",
                False,
            )

            obstacle_ahead = not front_traversable

            if front_traversable:
                free_direction = "center"
            elif left_traversable:
                free_direction = "left"
            elif right_traversable:
                free_direction = "right"
            else:
                free_direction = "none"

            if geometry_confidence == "HIGH":
                confidence = 0.9
            elif geometry_confidence == "MEDIUM":
                confidence = 0.7
            else:
                confidence = 0.3

            summary = (
                f"VisionNN geometry={geometry_confidence} "
                f"temporal={temporal_stability} "
                f"free={free_direction}"
            )

            state = PerceptionState(
                obstacle_ahead=obstacle_ahead,
                free_direction=free_direction,
                corridor_visible=front_traversable,
                summary=summary,
                confidence=confidence,
                objects=objects,
                regions=regions,
                perception_prompt_result=json.dumps(
                    vision_nn_result,
                    separators=(",", ":"),
                ),
            )

            world = self.worldbuilder.update(
                rover_state=None,
                perception_state=state,
            )

            return PerceptionResult(
                perception_state=state,
                world_model=world,
                image_bytes=image_bytes,
                gps_state=gps_state,
            )
        
        
        ##############
        
        

        ok, buffer = cv2.imencode(".jpg", frame)
        image_bytes = buffer.tobytes() if ok else None
        if image_bytes is None:
            return PerceptionResult(
                perception_state=PerceptionState(
                    obstacle_ahead=False,
                    free_direction="none",
                    corridor_visible=False,
                    summary="Encoding error",
                    confidence=0.0,
                ),
                gps_state=gps_state,
            )

        # GPT-only experiment: missing credentials/network must not select classic vision.
        if self.llm_client is None:
            state = PerceptionState(
                obstacle_ahead=True,
                free_direction="none",
                corridor_visible=False,
                summary="GPT unavailable: OPENAI_API_KEY not configured",
                confidence=0.0,
                regions=[
                    {"name": name, "traversable": False}
                    for name in ("left", "front", "right")
                ],
            )
            world = self.worldbuilder.update(rover_state=None, perception_state=state)
            return PerceptionResult(
                perception_state=state,
                world_model=world,
                image_bytes=image_bytes,
                gps_state=gps_state,
            )

        # 🧠 LLM percepción

        perception_prompt = """
You are the visual perception system of an Axial SCX10 II 4x4 rover,
0.30 m wide, with approximately 0.07 m minimum ground clearance.

For immediate local navigation, assess three rover-relative corridors:
LEFT, FRONT, RIGHT. Each corridor is a possible path for the full rover,
not merely a patch of drivable ground. A corridor is passable only when
there is clearance for the rover's entire 0.30 m width without colliding
with a visible rigid obstacle in its immediate path.

The rover can traverse gravel, dirt, grass, scattered small stones,
flexible weeds and moderately uneven continuous terrain. Camera
perspective may exaggerate the size of nearby stones. Do not block a
corridor solely because of small loose stones, light vegetation or
moderately uneven ground that this off-road rover can cross.

Posts, fences, gates, walls, trunks, rigid branches, dense vegetation,
large rocks, holes, drops and water may physically block a corridor.
A drivable-looking surface underneath or beside a rigid barrier does
NOT make the corridor passable. Pay particular attention to thin posts,
horizontal fence bars, branches and barriers crossing the rover's path.
If an obstacle intersects the immediate corridor, mark it false even
when the ground itself is traversable. Do not treat an obstacle outside
the corridor as blocking it; do not assume a gap is wide enough without
visual evidence. If a possible physical collision or drop cannot be
resolved from the image, mark that corridor false and lower confidence.
Do not invent precise distances. Do not choose an action.

Return ONLY valid JSON with exactly these keys, in LEFT, FRONT, RIGHT order:
{"passable":[true,false,true],"confidence":0.85}
Confidence is a global number from 0 to 1.
"""


        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        
        XLogger.log("Perception", "Image preprocessing END")
        
        try:
            XLogger.log("Perception", "LLM request START")
            
            response = self.llm_client.responses.create(
                model="gpt-5.4",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": perception_prompt},
                            {"type": "input_image", "image_url": f"data:image/jpeg;base64,{image_b64}"},
                        ],
                    }
                ],
                temperature=0,
                max_output_tokens=min(self.max_output_tokens, 100),
            )
            
            XLogger.log("Perception", "LLM request END")
                
            text = response.output_text.strip()
            
            XLogger.log("Perception - Observe_llm - Prompt Result:", text)
            
            data = json.loads(text)
            if not isinstance(data, dict) or set(data) != {"passable", "confidence"}:
                raise ValueError("Invalid V3.2 fields")
            passable = data["passable"]
            if (not isinstance(passable, list) or len(passable) != 3
                    or any(type(v) is not bool for v in passable)):
                raise ValueError("V3.2 passable must contain 3 booleans")
            confidence = data["confidence"]
            if (type(confidence) not in (int, float)
                    or not 0.0 <= confidence <= 1.0):
                raise ValueError("Invalid V3.2 confidence")

            left_clear, front_clear, right_clear = passable
            if front_clear:
                free_direction = "center"
            elif left_clear:
                free_direction = "left"
            elif right_clear:
                free_direction = "right"
            else:
                free_direction = "none"

            # Preserve the legacy PerceptionState contract consumed by L2/world model.
            regions = [
                {"name": name, "traversable": clear}
                for name, clear in zip(("left", "front", "right"), passable)
            ]
            state = PerceptionState(
                obstacle_ahead=not front_clear,
                free_direction=free_direction,
                corridor_visible=front_clear,
                summary=f"GPT V3.2 passable L/F/R={passable}",
                confidence=float(confidence),
                objects=[],
                regions=regions,
                perception_prompt_result=text,
            )

            world = self.worldbuilder.update(rover_state=None, perception_state=state)
            
            return PerceptionResult(
                perception_state=state,
                world_model=world,
                image_bytes=image_bytes,
                gps_state=gps_state)

        except Exception as exc:
            XLogger.log("Perception", f"[PERCEPTION GPT ERROR] {exc}")
            # Fail closed: never substitute unvalidated geometric guesses for GPT.
            state = PerceptionState(
                obstacle_ahead=True,
                free_direction="none",
                corridor_visible=False,
                summary=f"GPT unavailable or invalid: {exc}",
                confidence=0.0,
                regions=[
                    {"name": name, "traversable": False}
                    for name in ("left", "front", "right")
                ],
            )
            world = self.worldbuilder.update(rover_state=None, perception_state=state)
            return PerceptionResult(
                perception_state=state,
                world_model=world,
                image_bytes=image_bytes,
                gps_state=gps_state,
            )


    def close(self):
        """Release optional sensor resources owned by PerceptionModule."""
        if self.gps is not None:
            try:
                self.gps.stop()
            except Exception:
                pass

        if hasattr(self, "cap") and self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
