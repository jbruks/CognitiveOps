from dataclasses import dataclass, field
from typing import List


from dataclasses import dataclass, field
from typing import List, Optional

from .navigation_state import NavigationState
from .object_node import ObjectNode
from .region import Region
from utils.xlogger import XLogger


@dataclass
class WorldModel:
    
        
    regions: List = field(default_factory=list)
    objects: List = field(default_factory=list)
    relationships: List = field(default_factory=list)
    affordances: List = field(default_factory=list)

    rover_state = None
    navigation_state = None
    timestamp: float = 0.0
    confidence: float = 1.0
    navigation_state: Optional[NavigationState] = None
    objects: List[ObjectNode] = field(default_factory=list)
    regions: List[Region] = field(default_factory=list)
    relationships: list = field(default_factory=list)
    affordances: list = field(default_factory=list)

    
        
    def semantic_summary(self) -> str:
        XLogger.log("WorldModel", "semantic_summary")
        lines = []

        # =========================
        # Navigation cognition
        # =========================

        nav = self.navigation_state

        if nav:

            lines.append(
                f"Suggested direction: {nav.best_direction}."
            )

            if nav.risk_level < 0.3:
                lines.append(
                    "Terrain risk appears low."
                )

            elif nav.risk_level < 0.7:
                lines.append(
                    "Terrain risk appears moderate."
                )

            else:
                lines.append(
                    "Terrain risk appears high."
                )

        # =========================
        # Objects
        # =========================

        for obj in self.objects:

            desc = f"{obj.object_type}"

            if obj.relative_position:
                desc += (
                    f" at {obj.relative_position}"
                )

            if obj.distance_m is not None:
                desc += (
                    f" ({obj.distance_m:.1f} m)"
                )

            desc += "."

            lines.append(desc)

        # =========================
        # Regions
        # =========================

        for region in self.regions:

            desc = (
                f"{region.terrain_type} region"
            )

            if region.relative_position:
                desc += (
                    f" at {region.relative_position}"
                )

            desc += "."

            lines.append(desc)

        # =========================
        # Empty fallback
        # =========================

        if not lines:
            lines.append(
                "No semantic observations available."
            )

        return "\n".join(lines)
