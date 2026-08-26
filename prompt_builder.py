from config import ALLOWED_ACTIONS, SYSTEM_GOAL


def build_tactical_prompt(rover_state, perception_state) -> str:
    allowed = ", ".join(ALLOWED_ACTIONS)

    return f"""
You are the tactical guidance module for an autonomous rover.

Goal:
{SYSTEM_GOAL}

Current rover state:
- mode: {rover_state.mode}
- armed: {rover_state.armed}
- heading_deg: {rover_state.heading_deg}
- speed_m_s: {rover_state.speed_m_s}
- x: {rover_state.x}
- y: {rover_state.y}

Current perception state:
- obstacle_ahead: {perception_state.obstacle_ahead}
- free_direction: {perception_state.free_direction}
- corridor_visible: {perception_state.corridor_visible}
- confidence: {perception_state.confidence}
- summary: {perception_state.summary}

Rules:
- Output exactly one action.
- Allowed actions: {allowed}
- If confidence is low, prefer HOLD.
- If obstacle ahead and left is free, prefer TURN_LEFT.
- If obstacle ahead and right is free, prefer TURN_RIGHT.
- If obstacle ahead and no safe path is visible, prefer STOP.
- If corridor is visible and center is free, prefer MOVE_FORWARD.

Response format:
ACTION=<one allowed action>
""".strip()
