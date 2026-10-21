import time
from types import SimpleNamespace

from llm_decision import TacticalLLMDecisionMaker
#from prompt_builder import build_tactical_prompt
from prompt_builder import build_tactical_prompt_qwen



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


rover_state = SimpleNamespace(
    mode="AUTONOMOUS",
    armed=True,
    speed_m_s=0.0,
    x=0.0,
    y=0.0,
)

gps_state = {
    "gps_fix_ok": True,
    "movement_state": "UNKNOWN",
    "confidence": "HIGH",
}

llm = TacticalLLMDecisionMaker()

for i, case in enumerate(CASES, 1):
    perception_state = SimpleNamespace(
        obstacle_ahead=case["obstacle_ahead"],
        free_direction=case["free_direction"],
        corridor_visible=True,
        confidence=case["confidence"],
        summary=f"Suggested direction: {case['free_direction']}.",
        regions=[],
        objects=[],
    )

    l3_task = {
        "task_type": "FOLLOW_BEARING",
        "desired_direction": "UNKNOWN",
        "desired_heading_deg": "UNKNOWN",
        "heading_error_deg": case["heading_error"],
        "distance_remaining_m": 60.0,
        "task_text": "Follow bearing toward target",
        "priority": "SAFETY_FIRST",
    }

    prompt = build_tactical_prompt_qwen(
        rover_state,
        perception_state,
        l3_task,
        gps_state,
    )

    start = time.perf_counter()
    result = llm.decide(prompt)
    elapsed = time.perf_counter() - start

    action = result.replace("ACTION=", "").strip()
    match = "YES" if action == case["expected"] else "NO"

    print(
        f"{i:02d} "
        f"{case['name']:20s} "
        f"EXPECTED={case['expected']:15s} "
        f"QWEN={action:15s} "
        f"MATCH={match:3s} "
        f"TIME={elapsed:.3f}s"
    )

llm.close()
