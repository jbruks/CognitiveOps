from utils.xlogger import XLogger
import os
import base64
import subprocess
import struct
import json
from openai import OpenAI
from config import LLM_BACKEND, OPENAI_MODEL


class TacticalLLMDecisionMaker:

    def __init__(self, backend: str = LLM_BACKEND, model: str = OPENAI_MODEL):
        self.backend = backend
        self.model = model
        self.client = None
        self.ollama_process = None

        if backend == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY not set")

            self.client = OpenAI(api_key=api_key)

        elif backend == "ollama":
            self.ollama_process = subprocess.Popen(
                [
                    "ssh",
                    "devlin@lw232451585.local",
                    "cd ~/CognitiveOps && python3 -u ollama_l2_worker.py",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=None,
            )

    def decide(self, prompt: str) -> str:
        XLogger.log("class TacticalLLMDecisionMaker", "decide")

        if self.backend == "stub":
            return self._stub_response(prompt)

        if self.backend == "openai":
            return self._openai_response(prompt)

        if self.backend == "ollama":
            return self._ollama_response(prompt)

        raise RuntimeError("Unsupported backend")

    def _read_exact(self, stream, size):
        data = b""

        while len(data) < size:
            chunk = stream.read(size - len(data))

            if not chunk:
                raise RuntimeError("Ollama remote connection closed")

            data += chunk

        return data

    def _ollama_response(self, prompt: str):
        XLogger.log(
            "class TacticalLLMDecisionMaker",
            "_ollama_response",
        )

        if self.ollama_process is None:
            raise RuntimeError("Ollama worker not initialized")

        payload = json.dumps(
            {
                "prompt": prompt,
            }
        ).encode("utf-8")

        self.ollama_process.stdin.write(
            struct.pack("!I", len(payload))
        )
        self.ollama_process.stdin.write(payload)
        self.ollama_process.stdin.flush()

        header = self._read_exact(
            self.ollama_process.stdout,
            4,
        )

        response_size = struct.unpack(
            "!I",
            header,
        )[0]

        response_bytes = self._read_exact(
            self.ollama_process.stdout,
            response_size,
        )

        result = json.loads(
            response_bytes.decode("utf-8")
        )

        if not result.get("ok"):
            raise RuntimeError(
                result.get(
                    "error",
                    "Unknown Ollama worker error",
                )
            )

        text = result.get(
            "response",
            "",
        ).strip()

        if not text:
            raise RuntimeError("LLM returned empty response")

        return text

    def _openai_response(self, prompt: str):
        XLogger.log("class TacticalLLMDecisionMaker", "_openai_response")

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
        XLogger.log("class TacticalLLMDecisionMaker", "_stub_response")

        text = prompt.lower()

        if "confidence: 0.4" in text:
            return "ACTION=HOLD"

        if "free_direction: left" in text:
            return "ACTION=FORWARD_LEFT"

        if "free_direction: right" in text:
            return "ACTION=FORWARD_RIGHT"

        if "corridor_visible: true" in text:
            return "ACTION=MOVE_FORWARD"

        return "ACTION=HOLD"

    def decide_with_image(self, prompt: str, image_bytes: bytes) -> str:
        XLogger.log("class TacticalLLMDecisionMaker", "decide_with_image")

        if self.backend == "stub":
            return self._stub_response(prompt)

        if self.backend == "openai":
            return self._openai_response_with_image(prompt, image_bytes)

        raise RuntimeError("Unsupported backend")

    def _openai_response_with_image(self, prompt: str, image_bytes: bytes):
        XLogger.log("class TacticalLLMDecisionMaker", "_openai_response_with_image")

        if not image_bytes:
            raise RuntimeError("Image bytes are required for multimodal decision")

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        XLogger.log("L2", "LLM request START")

        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt,
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{image_b64}",
                        },
                    ],
                }
            ],
            temperature=0,
            max_output_tokens=20,
        )

        XLogger.log("L2", "LLM request END")

        text = response.output_text.strip()

        if not text:
            raise RuntimeError("LLM returned empty response")

        return text

    def close(self):
        if self.ollama_process is not None:
            try:
                self.ollama_process.terminate()
            except Exception:
                pass
