

from .world_model import WorldModel
from .navigation_state import NavigationState
from .object_node import ObjectNode
from .region import Region


class WorldBuilder:

    def __init__(self):
        self.world = WorldModel()

    def update(
        self,
        rover_state,
        perception_state,
    ):

        # =========================
        # Reset frame-local state
        # =========================

        self.world.objects = []
        self.world.regions = []
        self.world.relationships = []
        self.world.affordances = []

        # =========================
        # Navigation cognition
        # =========================

        navigation = NavigationState(
            best_direction=getattr(
                perception_state,
                "free_direction",
                "forward",
            ),

            risk_level=getattr(
                perception_state,
                "risk_level",
                0.5,
            ),

            left_traversability=getattr(
                perception_state,
                "left_score",
                0.5,
            ),

            center_traversability=getattr(
                perception_state,
                "center_score",
                0.5,
            ),

            right_traversability=getattr(
                perception_state,
                "right_score",
                0.5,
            ),
        )

        self.world.navigation_state = navigation

        # =========================
        # Minimal object population
        # =========================

        if getattr(
            perception_state,
            "obstacle_detected",
            False,
        ):

            obstacle = ObjectNode(
                id="obstacle_1",

                object_type="obstacle",

                relative_position="front",

                distance_m=1.5,

                risk_level=navigation.risk_level,

                confidence=getattr(
                    perception_state,
                    "confidence",
                    0.8,
                ),
            )

            self.world.objects.append(
                obstacle
            )

        # =========================
        # Minimal region population
        # =========================

        region = Region(
            terrain_type="terrain",

            relative_position="ahead",

            traversability=(
                navigation.center_traversability
            ),
        )

        self.world.regions.append(region)

        return self.world
