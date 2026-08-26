from dataclasses import dataclass

@dataclass
class NavigationState:
    best_direction: str = "unknown"

    left_traversability: float = 0.0
    center_traversability: float = 0.0
    right_traversability: float = 0.0

    risk_level: float = 0.0

    recommended_speed_m_s: float = 0.0
