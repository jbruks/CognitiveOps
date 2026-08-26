import time

from .world_model import WorldModel
from .navigation_state import NavigationState


class WorldBuilder:
    """
    Initial passive cognitive layer.

    Current responsibilities:
    - receive rover + perception state
    - create lightweight semantic world snapshot
    - remain completely non-invasive
    """

    def __init__(self):
        self.world = WorldModel()

    def update(self, rover_state, perception_state):

        self.world.timestamp = time.time()
        self.world.rover_state = rover_state

        navigation = NavigationState()

        if perception_state.free_direction == "left":
            navigation.best_direction = "left"
            navigation.left_traversability = 0.8

        elif perception_state.free_direction == "right":
            navigation.best_direction = "right"
            navigation.right_traversability = 0.8

        elif perception_state.free_direction == "center":
            navigation.best_direction = "forward"
            navigation.center_traversability = 0.9

        else:
            navigation.best_direction = "unknown"

        navigation.risk_level = (
            1.0 - perception_state.confidence
        )

        self.world.navigation_state = navigation
        self.world.confidence = perception_state.confidence

        return self.world
