from dataclasses import dataclass
from typing import List, Optional
from openai import OpenAI
import cv2
import base64
import json
import os
from rover_interfaces import PerceptionState

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

        # 🔴 fallback si no hay LLM
        if self.llm_client is None:
            state = self._observe_camera(frame)
            return PerceptionResult(
                perception_state=state,
                image_bytes=image_bytes,
                gps_state=gps_state,
            )

        # 🧠 LLM percepción

        perception_prompt = """
You are the visual perception system of an Axial SCX10 II
4x4 rock crawler, approximately 0.30 m wide, with standard
axles and approximately 0.07 m minimum ground clearance.

This rover is designed to traverse gravel, loose dirt,
small stones, grass, and moderately uneven terrain.

Camera perspective can make small stones near the camera
appear much larger than they really are.

Analyze the image only for immediate local navigation.

Evaluate exactly these five rover-relative regions:
left, front-left, front, front-right, right.

For each region determine:
- traversable: true or false
- risk: low, medium, or high

Report only obstacles that meaningfully restrict or endanger
the movement of this specific rover.

Gravel, scattered small stones, loose dirt, sparse grass,
and minor surface irregularities are traversable terrain.
Do not report them as individual obstacles.

A stone is not a blocking obstacle merely because it appears
large in the foreground of the image.

Report rocks, rigid objects, dense vegetation, holes, drops,
water, and other hazards when they could prevent safe passage.

Do not assume that an uncertain obstacle is safely passable.

Do NOT report sparse grass, isolated grass stems, flexible weeds,
or light vegetation as obstacles when the rover can reasonably
push through or pass over them.

Treat such vegetation as part of the traversable terrain,
even if it is tall enough to appear prominently in the image.

Report dense or rigid vegetation as an obstacle when it forms
a physical barrier.

Also report solid obstacles, large rocks, trunks, walls, holes,
drops, water, and other hazards that could prevent safe passage.

An obstacle must represent a real restriction on rover movement,
not merely something visible in the camera image.

For each obstacle estimate:
- region
- distance_m

The rover can traverse grass, dirt, gravel, small rocks, pavement,
and moderately uneven continuous terrain.

Dense vegetation, walls, large obstacles, drops, water, and blocked
areas are not traversable.

Do not identify or describe objects.
Do not infer anything not visible.
Do not choose a rover action.

Return ONLY valid JSON:

{
  "regions": [
    {"name":"left","traversable":true,"risk":"low"},
    {"name":"front-left","traversable":true,"risk":"low"},
    {"name":"front","traversable":true,"risk":"low"},
    {"name":"front-right","traversable":true,"risk":"low"},
    {"name":"right","traversable":true,"risk":"low"}
  ],
  "obstacles": [],
  "confidence":0.8
}

All five regions must always be present.
obstacles may be empty.
confidence must be between 0.0 and 1.0.
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
                max_output_tokens=self.max_output_tokens,
            )
            
            XLogger.log("Perception", "LLM request END")
                
            text = response.output_text.strip()
            
            XLogger.log("Perception - Observe_llm - Prompt Result:", text)
            
            data = json.loads(text)
            
            
            ##########################################
            objects = data.get("objects", [])
            obstacles = data.get("obstacles", [])
            regions = data.get("regions", [])
            confidence = float(data.get("confidence", 0.0))
            
            # Convert compact VLM obstacles to the existing internal object format
            objects = [
                {
                    "type": "obstacle",
                    "position": {
                        "region": obstacle.get("region", "unknown")
                    },
                    "distance_m": obstacle.get("distance_m"),
                    "traversable": False,
                }
                for obstacle in obstacles
            ]

            regions_by_name = {
                region.get("name"): region
                for region in regions
            }

            front = regions_by_name.get("front", {})
            front_left = regions_by_name.get("front-left", {})
            front_right = regions_by_name.get("front-right", {})
            left = regions_by_name.get("left", {})
            right = regions_by_name.get("right", {})

            # Visual traversability reported by the VLM
            front_visual = bool(front.get("traversable", False))

            left_visual = bool(
                front_left.get("traversable", False)
                or left.get("traversable", False)
            )

            right_visual = bool(
                front_right.get("traversable", False)
                or right.get("traversable", False)
            )


            # Nearby obstacles block the corresponding movement corridor
            MIN_CLEARANCE_M = 1

            blocked_regions = set()

            for obstacle in obstacles:
                distance = obstacle.get("distance_m")
                region = obstacle.get("region")

                if (
                    distance is not None
                    and region is not None
                    and distance <= MIN_CLEARANCE_M
                ):
                    blocked_regions.add(region)


            # Clearance for each possible movement direction
            front_clear = not any(
                region in blocked_regions
                for region in ("front-left", "front", "front-right")
            )

            left_clear = not any(
                region in blocked_regions
                for region in ("left", "front-left")
            )

            right_clear = not any(
                region in blocked_regions
                for region in ("front-right", "right")
            )


            # Final traversability = visual perception + geometric clearance
            front_traversable = front_visual and front_clear
            left_traversable = left_visual and left_clear
            right_traversable = right_visual and right_clear

            obstacle_ahead = not front_traversable

            if front_traversable:
                free_direction = "center"
            elif left_traversable:
                free_direction = "left"
            elif right_traversable:
                free_direction = "right"
            else:
                free_direction = "none"

            state = PerceptionState(
                obstacle_ahead=obstacle_ahead,
                free_direction=free_direction,
                corridor_visible=front_traversable,
                summary=str(data.get("summary", "")),
                #confidence=float(data.get("overall_confidence", 0.0)),
                confidence=confidence,
                objects=objects,
                regions=regions,
                perception_prompt_result=response.output_text.strip(),
            )
            ##########################################
            

            #state = PerceptionState(
            #    obstacle_ahead=bool(data.get("obstacle_ahead", False)),
            #    free_direction=str(data.get("free_direction", "none")),
            #    corridor_visible=bool(data.get("corridor_visible", False)),
            #    summary=str(data.get("summary", "")),
            #    confidence=float(data.get("confidence", 0.0)),
            #)
            
            world = self.worldbuilder.update(rover_state=None, perception_state=state)
            
            return PerceptionResult(
                perception_state=state,
                world_model=world,
                image_bytes=image_bytes,
                gps_state=gps_state)

        except Exception as exc:
            XLogger.log("Perception", "After ERROR" + f"[PERCEPTION LLM ERROR] {exc}")
            # fallback a visión clásica
            state = self._observe_camera()
            world = self.worldbuilder.update(rover_state=None, perception_state=state)
            
            return PerceptionResult(
                perception_state=state,
                world_model=world,
                image_bytes=image_bytes,
                gps_state=gps_state
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
