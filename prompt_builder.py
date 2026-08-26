from config import ALLOWED_ACTIONS, SYSTEM_GOAL

def build_tactical_prompt(rover_state, perception_state) -> str:
    allowed_actions_str = ", ".join(ALLOWED_ACTIONS)

    return f"""
You are the tactical navigation module of an autonomous rover.

Mission goal:
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

Allowed actions:
- {allowed_actions_str}

Decision rules:
- Output exactly one allowed action.
- If confidence is low, prefer HOLD.
- If obstacle_ahead is true and free_direction is left, prefer FORWARD_LEFT.
- If obstacle_ahead is true and free_direction is right, prefer FORWARD_RIGHT.
- If obstacle_ahead is true and no safe path is visible, prefer STOP.
- If corridor_visible is true and free_direction is center, prefer MOVE_FORWARD.

Output format:
ACTION=<one allowed action>
""".strip()
