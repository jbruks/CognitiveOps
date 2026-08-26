LLM_ENABLED = True
USE_FALLBACK_ON_ERROR = True

# For now this is a local stub selector.
# Later you can replace the implementation behind llm_decision.py
# with OpenAI / Ollama / local model inference.
LLM_BACKEND = "stub"

#LOOP_DELAY_S = 2.0
#DEFAULT_STEPS = 12

LOOP_DELAY_S = 20
DEFAULT_STEPS = 500

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
