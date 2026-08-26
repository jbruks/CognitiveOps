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
        
    ):
        XLogger.log("PerceptionModule", "__init__")
        self.mode = mode
        self.worldbuilder = WorldBuilder()

        # --- SIMULATION SETUP ---
        self.default_scenario = default_scenario
        self.scenario_sequence = scenario_sequence or []
        self.loop_sequence = loop_sequence
        self.sequence_index = 0
        self.current_scenario_name = default_scenario

        # --- CAMERA SETUP ---
        if self.mode == "camera":
            self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
            self.cap.set( cv2.CAP_PROP_BUFFERSIZE,1)
            
            
            
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
        if self.mode != "camera":
            state = self._observe_simulated()
            return state, None, None, None
            #return state, None
            
        for _ in range(3):
            self.cap.grab()
            
        ret, frame = self.cap.read()

        if not ret:
            return (
                PerceptionState(
                    obstacle_ahead=False,
                    free_direction="none",
                    corridor_visible=False,
                    summary="Camera error",
                    confidence=0.0,
                ),
                None, None, None
            )
        frame = cv2.resize(frame, (320, 240))
        ok, buffer = cv2.imencode(".jpg", frame)
        image_bytes = buffer.tobytes() if ok else None
        if image_bytes is None:
            return (
                PerceptionState(
                    obstacle_ahead=False,
                    free_direction="none",
                    corridor_visible=False,
                    summary="Encoding error",
                    confidence=0.0,
                ),
                None,
                None, None
            )

        # 🔴 fallback si no hay LLM
        if self.llm_client is None:
            state = self._observe_camera()
            return state, None, None, image_bytes

        # 🧠 LLM percepción
        
        perception_prompt = """
You are the perception and navigation layer of an autonomous ground rover using a low-resolution monocular RGB web camera.

Your task is to analyze a single camera frame and generate ONLY valid JSON describing:

* terrain
* traversability
* obstacles
* visibility
* navigation

The rover platform is:

* AXIAL SCX III 1:10 crawler
* 4x4 traction
* Length: 0.50 meters
* Width: 0.30 meters
* Height: 0.30 meters
* Speed: 3 km/h
* Navigation step size: 1 meter
* Camera mounted 25cm from ground level

The rover operates outdoors on:

* grass
* dirt
* stone
* pavement
* uneven terrain

==================================================
PERCEPTION RULES
================

* Be conservative and safety-oriented
* NEVER hallucinate unseen objects
* Infer ONLY what is visually observable
* If uncertain, reduce confidence
* Monocular depth estimation is approximate
* Small obstacles may be partially hidden by grass
* Assume the rover moves on the ground plane
* Use rover-centric coordinates and directions
* Focus on immediate traversability
* Prefer false negatives over false positives
* Do not invent terrain behind obstacles
* Avoid overestimating visibility range
* Distances are approximate
* Terrain beyond visibility range is unknown

==================================================
FIELD OF VIEW MODEL
===================

Assume camera field of view:

* Horizontal FOV: 70 degrees
* Vertical FOV: 50 degrees

Divide image horizontally into:

* LEFT: 30° to 60°
* FRONT-LEFT: 60° to 85°
* FRONT: 85° to 95°
* FRONT-RIGHT: 95° to 120°
* RIGHT: 120° to 150°

Distance bands:

* IMMEDIATE: 0.0m to 0.5m
* NEAR: 0.5m to 2.0m
* MID: 2.0m to 5.0m
* FAR: 5.0m to visibility limit

==================================================
TRAVERSABILITY RULES
====================

Terrain is traversable when:

* slope is low
* no large obstacle is visible
* terrain roughness is acceptable
* estimated obstacle height is below wheel capability

Terrain is NOT traversable when:

* wall
* deep hole
* large rock
* water
* dense vegetation
* obstacle larger than wheel clearance
* unknown unsafe region

Grass is usually traversable.
Tile edges smaller than 5 cm are traversable.
Small grass clumps are traversable.
Dense bushes and walls are not traversable.

==================================================
OBJECT SIZE RULES
=================

Object size is estimated radius in centimeters.

Examples:

* small stone: 20
* grass clump: 5
* plant pot: 20
* chair: 35
* bush: 100

==================================================
CONFIDENCE RULES
================

Confidence range:

* 0.90 to 1.00 = very clear
* 0.70 to 0.89 = probable
* 0.40 to 0.69 = uncertain
* below 0.40 = weak evidence

Low-resolution or distant objects must reduce confidence.

==================================================
OUTPUT RULES
============

* Output ONLY valid JSON
* No markdown
* No explanations
* No comments
* No extra text
* Use meters
* Use decimal numbers
* Use null when estimation is unreliable
* Keep summary concise and technical
* All JSON keys must always exist
* Arrays must exist even if empty

==================================================
RETURN EXACTLY THIS JSON SCHEMA
===============================

{
"frame_context": 
{
"camera_height_m": 0.12,
"estimated_pitch_deg": -5,
"horizontal_fov_deg": 70,
"vertical_fov_deg": 50
},

"regions": 
[
{
"name": "front",
"azimuth_range_deg": [85, 95],
"distance_range_m": [0.5, 5.0],
"surface_type": "grass",
"terrain_roughness": "low",
"estimated_friction": "medium",
"slope": "0 degrees",
"traversable": true,
"risk_level": "low",
"confidence": 0.82
}
],

"objects": 
[
{
  "type": "chair",
  "category": "static_obstacle",
  "position": 
  {
    "region": "left",
    "azimuth_deg": 42
  },
  "distance_m": 5.8,
  "size_radius_m": 0.35,
  "estimated_height_m": 0.8,
  "traversable": false,
  "risk_level": "low",
  "confidence": 0.84
}
],


"visibility": 
{
"lighting": "good",
"image_quality": "medium",
"visible_range_m": 8.0
},

"navigation":
{
"recommended_action": "forward | stop | turn_left | turn_right | avoid_obstacle",
"recommended_direction":
{
  "region": "front",
  "azimuth_deg": 90
},
"safe_corridor":
{
  "available": true,
  "center_azimuth_deg": 90,
  "width_deg": 25,
  "estimated_clear_distance_m": 3.0
},
}

"summary": "Flat paved terrain ahead with sparse grass. Central region is traversable with low collision risk.",

"overall_confidence": 0.84
}   

"""     
        
        
        
        perception_prompt_2 = """
    You are the perception layer of an autonomous rover.

    Analyze the image and return ONLY valid JSON:

    {
  "navigation": {
    "free_direction": "left",
    "corridor_visible": true,
    "risk_level": "moderate"
  },

  "objects": [
    {
      "type": "obstacle",
      "position": "front-left",
      "distance_m": 1.5
    }
  ],

  "regions": [
    {
      "name": "ahead",
      "terrain": "rough"
    }
  ],

  "summary": "short navigation summary",

  "confidence": 0.8
}

    Rules:
    - Be conservative
    - Focus on obstacles and traversability
    """
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        try:
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
                max_output_tokens=2000,
            )
            text = response.output_text.strip()
            
            XLogger.log("Perception - Observe_llm - Prompt Result:", text)
            
            data = json.loads(text)
            navigation = data.get("navigation", {})
            objects = data.get("objects", [])
            regions = data.get("regions", [])
            state = PerceptionState(
                obstacle_ahead=len(objects) > 0,
                free_direction=str(navigation.get("free_direction", "none")),
                corridor_visible=bool(navigation.get("corridor_visible", False)),
                summary=str(data.get("summary", "")),
                confidence=float(data.get("confidence", 0.0)),
                objects=objects,
                regions=regions,
                perception_prompt_result = response.output_text.strip()
            )

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
                image_bytes=image_bytes)

        except Exception as exc:
            XLogger.log("Perception", "After ERROR" + f"[PERCEPTION LLM ERROR] {exc}")
            # fallback a visión clásica
            state = self._observe_camera()
            world = self.worldbuilder.update(rover_state=None, perception_state=state)
            
            return PerceptionResult(
                perception_state=state,
                image_bytes=image_bytes)
            
