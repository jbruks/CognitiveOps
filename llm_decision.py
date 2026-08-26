import os
from openai import OpenAI
from config import LLM_BACKEND, OPENAI_MODEL


class TacticalLLMDecisionMaker:

    def __init__(self, backend: str = LLM_BACKEND, model: str = OPENAI_MODEL):
        self.backend = backend
        self.model = model
        self.client = None

        if backend == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY not set")

            self.client = OpenAI(api_key=api_key)

    def decide(self, prompt: str) -> str:
        if self.backend == "stub":
            return self._stub_response(prompt)

        if self.backend == "openai":
            return self._openai_response(prompt)

        raise RuntimeError("Unsupported backend")

    def _openai_response(self, prompt: str):

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=0,
            max_output_tokens=20,
        )

        text = response.output_text.strip()

        if not text:
            raise RuntimeError("LLM returned empty response")

        return text

    def _stub_response(self, prompt: str):

        text = prompt.lower()

        if "confidence: 0.4" in text:
            return "ACTION=HOLD"

        if "free_direction: left" in text:
            return "ACTION=FORWARD_LEFT"
            #return "ACTION=FORWARD_LEFT"

        if "free_direction: right" in text:
            return "ACTION=FORWARD_RIGHT"
            #return "ACTION=FORWARD_RIGHT"

        if "corridor_visible: true" in text:
            return "ACTION=MOVE_FORWARD"

        return "ACTION=HOLD"
