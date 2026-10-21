import subprocess
import struct
import json

import cv2


class VisionNN:
    """
    Lightweight remote VisionNN client.

    Keeps a persistent SSH session open to the ZBook and sends
    JPEG frames to vision_nn_worker.py.

    The remote worker currently returns accepted=False, so
    PerceptionModule will continue using the existing GPT path.
    """

    def __init__(self):
        self.process = subprocess.Popen(
            [
                "ssh",
                "devlin@lw232451585.local",
                "cd ~/CognitiveOps && ~/depth-env/bin/python -u vision_nn_worker.py",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
        )

    def _read_exact(self, stream, size):
        data = b""

        while len(data) < size:
            chunk = stream.read(size - len(data))

            if not chunk:
                raise RuntimeError("VisionNN remote connection closed")

            data += chunk

        return data

    def analyze(self, frame):
        try:
            ok, buffer = cv2.imencode(".jpg", frame)

            if not ok:
                return {
                    "accepted": False,
                    "source": "vision_nn_encode_error",
                }

            image_bytes = buffer.tobytes()

            # Send: 4-byte length + JPEG
            self.process.stdin.write(
                struct.pack("!I", len(image_bytes))
            )
            self.process.stdin.write(image_bytes)
            self.process.stdin.flush()

            # Receive: 4-byte length + JSON
            header = self._read_exact(
                self.process.stdout,
                4,
            )

            response_size = struct.unpack(
                "!I",
                header,
            )[0]

            payload = self._read_exact(
                self.process.stdout,
                response_size,
            )

            return json.loads(
                payload.decode("utf-8")
            )

        except Exception as exc:
            return {
                "accepted": False,
                "source": "vision_nn_error",
                "error": str(exc),
            }

    def close(self):
        if self.process is not None:
            try:
                self.process.terminate()
            except Exception:
                pass
