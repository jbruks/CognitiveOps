import sys
import json
import struct
import requests

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b"


def read_exact(stream, size):
    data = b""

    while len(data) < size:
        chunk = stream.read(size - len(data))

        if not chunk:
            raise EOFError("stdin closed")

        data += chunk

    return data


def write_response(payload):
    data = json.dumps(payload).encode("utf-8")

    sys.stdout.buffer.write(
        struct.pack("!I", len(data))
    )

    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def main():
    while True:
        try:
            header = read_exact(
                sys.stdin.buffer,
                4,
            )

            request_size = struct.unpack(
                "!I",
                header,
            )[0]

            request_bytes = read_exact(
                sys.stdin.buffer,
                request_size,
            )

            request = json.loads(
                request_bytes.decode("utf-8")
            )

            prompt = request["prompt"]

            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0,
                        "num_predict": 20,
                    },
                },
                timeout=60,
            )

            response.raise_for_status()

            text = response.json().get(
                "response",
                "",
            ).strip()

            if not text:
                raise RuntimeError(
                    "Ollama returned empty response"
                )

            write_response(
                {
                    "ok": True,
                    "response": text,
                }
            )

        except EOFError:
            break

        except Exception as exc:
            write_response(
                {
                    "ok": False,
                    "error": str(exc),
                }
            )


if __name__ == "__main__":
    main()
