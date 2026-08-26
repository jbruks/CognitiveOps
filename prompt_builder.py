from config import ALLOWED_ACTIONS, SYSTEM_GOAL
from utils.xlogger import XLogger


def build_tactical_prompt(rover_state, perception_state) -> str:
    allowed_actions_str = ", ".join(ALLOWED_ACTIONS)

    XLogger.log("prompt_builder.py", "build_tactical_prompt")


    return f"""
        You are the tactical navigation module of an autonomous rover.

        You are given:
        1. A camera image of the environment
        2. A perception summary (may be incomplete or approximate)
        3. The current rover state

        Use BOTH the image and the perception summary to decide.

        If there is any conflict:
        - prioritize safety
        - prefer conservative actions

        Mission goal:
        {SYSTEM_GOAL}

        Current rover state:
        - mode: {rover_state.mode}
        - armed: {rover_state.armed}
        - heading_deg: {rover_state.heading_deg}
        - speed_m_s: {rover_state.speed_m_s}
        - x: {rover_state.x}
        - y: {rover_state.y}

        Perception summary:
        - obstacle_ahead: {perception_state.obstacle_ahead}
        - free_direction: {perception_state.free_direction}
        - corridor_visible: {perception_state.corridor_visible}
        - confidence: {perception_state.confidence}
        - summary: {perception_state.summary}

        Allowed actions:
        - {allowed_actions_str}

        Robot constraints and capabilities:
        - The rover is an off-road crawler (~35 cm, Axial SCX10 III)
        - It can traverse uneven outdoor terrain

        Traversable terrain includes:
        - Grass
        - Sand
        - Small rocks and gravel
        - Slightly uneven ground

        Constraints:
        - Avoid tight or narrow spaces that may not fit a 35 cm rover
        - Avoid large obstacles or steep drops
        - Avoid areas that look blocked or highly cluttered

        Interpretation guidelines:
        - Do not assume grass or rough terrain is unsafe
        - Prefer moving forward even if terrain is slightly uneven
        - If terrain looks moderately rough but continuous → it is safe to proceed

        Decision principles:
        - Avoid collisions and entanglement
        - Prefer open and traversable space
        - Avoid uncertain or risky areas
        - If unsure, act conservatively

        Heuristics (use as guidance, not strict rules):
        - If obstacle ahead and left is clearer → FORWARD_LEFT
        - If obstacle ahead and right is clearer → FORWARD_RIGHT
        - If path ahead is clear → MOVE_FORWARD
        - If blocked and no safe path → MOVE_BACKWARD
        - If perception confidence is low → MOVE_BACKWARD

        Output format:
        ACTION=<one allowed action>
        """.strip()



