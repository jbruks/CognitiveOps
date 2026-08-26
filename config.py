LLM_ENABLED = True
USE_FALLBACK_ON_ERROR = True

LLM_BACKEND = "openai"
OPENAI_MODEL = "gpt-5.4"
LLM_DEBUG = True

LOOP_DELAY_S = 5
DEFAULT_STEPS = 25

SYSTEM_GOAL = (
    "Navigate the rover safely using short tactical actions. "
    "Prefer forward motion when the corridor is clear. "
    "Turn only when needed to avoid obstacles. "
    "Stop or hold when uncertain."
)

ALLOWED_ACTIONS = [
    "MOVE_FORWARD",
    "TURN_LEFT",
    "TURN_RIGHT",
    "STOP",
    "HOLD",
]
