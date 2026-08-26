from dataclasses import dataclass

@dataclass
class Affordance:
    action_type: str

    traversability: float = 0.0
    safe_speed_m_s: float = 0.0

    relative_direction: str = "forward"

    confidence: float = 1.0
