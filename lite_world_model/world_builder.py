

from .world_model import WorldModel
from .navigation_state import NavigationState
from .object_node import ObjectNode
from .region import Region
from utils.xlogger import XLogger



class WorldBuilder:

    def __init__(self):
        XLogger.log("WorldBuilder", "__init__")
        self.world = WorldModel()

    def update(
        self,
        rover_state,
        perception_state,
    ):
        XLogger.log("class WorldBuilder:", "Update")
        # =========================
        # Reset frame-local state
        # =========================
        self.world.objects = []
        self.world.regions = []
        self.world.relationships = []
        self.world.affordances = []
        self.world.confidence = getattr(
            perception_state,
            "confidence",
            0.0,
        )
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
        for i, obj in enumerate(perception_state.objects):
            position = obj.get("position", {})

            obstacle = ObjectNode(
                id=f"obstacle_{i + 1}",
                object_type=obj.get("type", "obstacle"),
                relative_position=position.get("region", "unknown"),
                distance_m=obj.get("distance_m"),
                risk_level=navigation.risk_level,
                confidence=getattr(
                    perception_state,
                    "confidence",
                    0.8,
                ),

            )

            self.world.objects.append(obstacle)
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
        self.world.semantic_summary()
        XLogger.log("class WorldBuilder:", "End update: "+f"objects={len(perception_state.objects)} " + f"regions={len(perception_state.regions)}")

        return self.world
