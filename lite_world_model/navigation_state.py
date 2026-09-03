from dataclasses import dataclass


@dataclass
class NavigationState:
    # Global navigation
    latitude: float | None = None
    longitude: float | None = None
    heading_deg: float | None = None
    speed_m_s: float = 0.0

    position_valid: bool = False
    heading_valid: bool = False

    # Local navigation / traversability
    best_direction: str = "forward"
    risk_level: float = 0.5
    left_traversability: float = 0.5
    center_traversability: float = 0.5
    right_traversability: float = 0.5

    @property
    def max_traversability(self):
        return max(
            self.left_traversability,
            self.center_traversability,
            self.right_traversability,
        )
