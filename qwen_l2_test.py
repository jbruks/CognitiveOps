import subprocess
import time

prompt = """
You are the tactical navigation module of an autonomous rover.

Current tactical task from L3:
- task_type: FOLLOW_BEARING
- desired_direction: RIGHT
- heading_error_deg: 10.714829601042936

Perception summary:
- obstacle_ahead: False
- free_direction: center
- confidence: 0.9
- summary: Suggested direction: center.

Allowed actions:
- MOVE_FORWARD, MOVE_BACKWARD, FORWARD_LEFT, FORWARD_RIGHT, STOP

Direction following rules:
- A positive heading_error_deg means the target direction is to the rover's right
- A negative heading_error_deg means the target direction is to the rover's left
- Safety always overrides direction following

Action heuristics:
- If heading_error_deg is known and significantly positive, prefer FORWARD_RIGHT when right/front-right is safe
- If heading_error_deg is known and significantly negative, prefer FORWARD_LEFT when left/front-left is safe
- If heading_error_deg is close to zero and the path ahead is clear, prefer MOVE_FORWARD
- If obstacle_ahead is true, do not choose MOVE_FORWARD
- If no safe path is visible -> MOVE_BACKWARD
- If perception confidence is low -> MOVE_BACKWARD

Output format:
ACTION=<one allowed action>
""".strip()

start = time.perf_counter()

result = subprocess.run(
    ["ollama", "run", "qwen2.5:7b", prompt],
    capture_output=True,
    text=True,
)

elapsed = time.perf_counter() - start

print("Qwen:", result.stdout.strip())
print(f"Time: {elapsed:.3f} s")
