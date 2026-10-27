import subprocess
import struct
import json
from pathlib import Path

import cv2


class VisionNN:
    """Persistent local CPU VisionNN worker; JPEG/JSON framing unchanged."""

    def __init__(self):
        project_root = Path(__file__).resolve().parent
        python_bin = (
            project_root
            / "experiments/local_perception/.venv-offseg/bin/python"
        )
        if not python_bin.is_file():
            raise FileNotFoundError(f"VisionNN environment missing: {python_bin}")

        self.process = subprocess.Popen(
            [str(python_bin), "-u", str(project_root / "vision_nn_worker.py")],
            cwd=str(project_root),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
        )

    def _read_exact(self, stream, size):
        data = b""

        while len(data) < size:
            chunk = stream.read(size - len(data))

            if not chunk:
                raise RuntimeError("VisionNN local worker connection closed")

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
