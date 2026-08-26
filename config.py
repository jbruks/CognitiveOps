LLM_ENABLED = True
USE_FALLBACK_ON_ERROR = True

LLM_BACKEND = "openai"
OPENAI_MODEL = "gpt-5.4"
LLM_DEBUG = True

LOOP_DELAY_S = 7
DEFAULT_STEPS = 25

SYSTEM_GOAL = (
    "Navigate the rover safely using short tactical actions. "
    "Prefer forward motion when the corridor is clear. "
    "Turn only when needed to avoid obstacles. "
    "Move backward when uncertain."
)

ALLOWED_ACTIONS = [
    "MOVE_FORWARD",
    "FORWARD_LEFT",
    "FORWARD_RIGHT",
    "MOVE_BACKWARD",
    #"STOP",
    #"HOLD",
]
