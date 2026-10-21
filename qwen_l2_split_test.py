import time
from llm_decision import TacticalLLMDecisionMaker


CASES = [
    {
        "name": "aligned_clear",
        "obstacle_ahead": False,
        "free_direction": "center",
        "confidence": 0.9,
        "heading_error": 3.6,
        "expected": "MOVE_FORWARD",
    },
    {
        "name": "right_small",
        "obstacle_ahead": False,
        "free_direction": "center",
        "confidence": 0.9,
        "heading_error": 10.7,
        "expected": "FORWARD_RIGHT",
    },
    {
        "name": "right_large",
        "obstacle_ahead": False,
        "free_direction": "center",
        "confidence": 0.9,
        "heading_error": 51.5,
        "expected": "FORWARD_RIGHT",
    },
    {
        "name": "left_small",
        "obstacle_ahead": False,
        "free_direction": "center",
        "confidence": 0.9,
        "heading_error": -8.6,
        "expected": "FORWARD_LEFT",
    },
    {
        "name": "left_large",
        "obstacle_ahead": False,
        "free_direction": "center",
        "confidence": 0.9,
        "heading_error": -15.0,
        "expected": "FORWARD_LEFT",
    },
    {
        "name": "low_confidence",
        "obstacle_ahead": False,
        "free_direction": "center",
        "confidence": 0.3,
        "heading_error": -6.2,
        "expected": "MOVE_BACKWARD",
    },
    {
        "name": "obstacle_left_free",
        "obstacle_ahead": True,
        "free_direction": "left",
        "confidence": 0.9,
        "heading_error": 5.0,
        "expected": "FORWARD_LEFT",
    },
    {
        "name": "obstacle_right_free",
        "obstacle_ahead": True,
        "free_direction": "right",
        "confidence": 0.9,
        "heading_error": -5.0,
        "expected": "FORWARD_RIGHT",
    },
    {
        "name": "obstacle_none",
        "obstacle_ahead": True,
        "free_direction": "none",
        "confidence": 0.9,
        "heading_error": 0.0,
        "expected": "MOVE_BACKWARD",
    },
]


def safety_prompt(case):
    return f"""
You are a rover safety controller.

Choose exactly ONE result from:
SAFE_FORWARD, FORWARD_LEFT, FORWARD_RIGHT, MOVE_BACKWARD

Rules:
- If obstacle_ahead == true and free_direction == left -> FORWARD_LEFT
- If obstacle_ahead == true and free_direction == right -> FORWARD_RIGHT
- If obstacle_ahead == true and free_direction == none -> MOVE_BACKWARD
- Otherwise -> SAFE_FORWARD

Input:
obstacle_ahead={str(case["obstacle_ahead"]).lower()}
free_direction={case["free_direction"]}

Return only the result.
""".strip()


def heading_prompt(case):
    return f"""
You are a rover heading controller.

Choose exactly ONE action from:
MOVE_FORWARD, FORWARD_LEFT, FORWARD_RIGHT

Rules:
- If heading_error_deg > 8 -> FORWARD_RIGHT
- If heading_error_deg < -8 -> FORWARD_LEFT
- Otherwise -> MOVE_FORWARD

Input:
heading_error_deg={case["heading_error"]}

Return only the action.
""".strip()


llm = TacticalLLMDecisionMaker()

try:
    for i, case in enumerate(CASES, 1):
        total_start = time.perf_counter()

        # Safety rule handled deterministically.
        if case["confidence"] <= 0.3:
            safety = "MOVE_BACKWARD"
            action = "MOVE_BACKWARD"
            safety_time = 0.0
            heading_time = 0.0

        else:
            # First Qwen call: local safety / obstacle handling.
            t1 = time.perf_counter()

            safety = llm.decide(
                safety_prompt(case)
            )

            safety_time = time.perf_counter() - t1
            safety = safety.replace("ACTION=", "").strip()

            # Second Qwen call only if the local path is safe.
            if safety == "SAFE_FORWARD":
                t2 = time.perf_counter()

                action = llm.decide(
                    heading_prompt(case)
                )

                heading_time = time.perf_counter() - t2
                action = action.replace("ACTION=", "").strip()

            else:
                action = safety
                heading_time = 0.0

        total_time = time.perf_counter() - total_start

        match = "YES" if action == case["expected"] else "NO"

        print(
            f"{i:02d} "
            f"{case['name']:20s} "
            f"EXPECTED={case['expected']:15s} "
            f"SAFETY={safety:15s} "
            f"ACTION={action:15s} "
            f"MATCH={match:3s} "
            f"S={safety_time:.3f}s "
            f"H={heading_time:.3f}s "
            f"TOTAL={total_time:.3f}s"
        )

finally:
    llm.close()
