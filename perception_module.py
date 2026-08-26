from dataclasses import dataclass
from typing import List, Optional

from openai import OpenAI
import cv2
import base64
import json
import os

from rover_interfaces import PerceptionState


@dataclass
class SimulatedScenario:
    name: str
    obstacle_ahead: bool
    free_direction: str
    corridor_visible: bool
    summary: str
    confidence: float = 1.0


class PerceptionModule:

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
        self.mode = mode

        # --- SIMULATION SETUP ---
        self.default_scenario = default_scenario
        self.scenario_sequence = scenario_sequence or []
        self.loop_sequence = loop_sequence
        self.sequence_index = 0
        self.current_scenario_name = default_scenario

        # --- CAMERA SETUP ---
        if self.mode == "camera":
            self.cap = cv2.VideoCapture(0)
            
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

    def _observe_camera(self) -> PerceptionState:
        ret, frame = self.cap.read()

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
        if self.mode == "camera":
            return self._observe_camera()
        else:
            return self._observe_simulated()


    

    def observe_llm_OLD(self):
        """
        Nueva función mínima para pipeline LLM.
        No rompe nada existente.
        """
        if self.mode != "camera":
            state = self._observe_simulated()
            return state, None

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
                None,
            )

        frame = cv2.resize(frame, (320, 240))

        # reutilizamos lógica actual (sin tocar nada)
        state = self._observe_camera()

        # convertir imagen a bytes
        ok, buffer = cv2.imencode(".jpg", frame)
        image_bytes = buffer.tobytes() if ok else None

        return state, image_bytes
        
        
        
    #################


    def observe_llm(self):
        """
        LLM-based perception + image output
        """
        if self.mode != "camera":
            state = self._observe_simulated()
            return state, None

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
                None,
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
            )

        # 🔴 fallback si no hay LLM
        if self.llm_client is None:
            state = self._observe_camera()
            return state, image_bytes

        # 🧠 LLM percepción
        perception_prompt = """
    You are the perception layer of an autonomous rover.

    Analyze the image and return ONLY valid JSON:

    {
      "obstacle_ahead": true,
      "free_direction": "left",
      "corridor_visible": false,
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
                max_output_tokens=200,
            )

            text = response.output_text.strip()

            data = json.loads(text)

            state = PerceptionState(
                obstacle_ahead=bool(data.get("obstacle_ahead", False)),
                free_direction=str(data.get("free_direction", "none")),
                corridor_visible=bool(data.get("corridor_visible", False)),
                summary=str(data.get("summary", "")),
                confidence=float(data.get("confidence", 0.0)),
            )

            return state, image_bytes

        except Exception as exc:
            print(f"[PERCEPTION LLM ERROR] {exc}")

            # fallback a visión clásica
            state = self._observe_camera()
            return state, image_bytes
