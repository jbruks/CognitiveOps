from config import LLM_BACKEND


class TacticalLLMDecisionMaker:
    """
    Minimal LLM decision wrapper.

    Current behavior:
    - uses a deterministic stub backend so you can integrate the module now
    - later you can replace _call_backend() with a real LLM API call
    """

    def __init__(self, backend: str = LLM_BACKEND):
        self.backend = backend

    def decide(self, prompt: str) -> str:
        return self._call_backend(prompt)

    def _call_backend(self, prompt: str) -> str:
        if self.backend == "stub":
            return self._stub_response(prompt)

        raise RuntimeError(f"Unsupported LLM backend: {self.backend}")

    def _stub_response(self, prompt: str) -> str:
        text = prompt.lower()

        if "confidence: 0.4" in text or "confidence: 0.3" in text or "confidence: 0.2" in text:
            return "ACTION=HOLD"

        if "obstacle_ahead: true" in text and "free_direction: left" in text:
            return "ACTION=TURN_LEFT"

        if "obstacle_ahead: true" in text and "free_direction: right" in text:
            return "ACTION=TURN_RIGHT"

        if "obstacle_ahead: true" in text and "free_direction: none" in text:
            return "ACTION=STOP"

        if "corridor_visible: true" in text and "free_direction: center" in text:
            return "ACTION=MOVE_FORWARD"

        return "ACTION=HOLD"
