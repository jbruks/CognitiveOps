from dataclasses import dataclass


@dataclass
class NavigationState:
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
