from dataclasses import dataclass, field
from typing import List

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
    



    def semantic_summary(self) -> str:

        lines = []

    # Navigation interpretation
        if self.navigation_state:

            nav = self.navigation_state

            if nav.best_direction:
                lines.append(
                    f"Suggested direction is {nav.best_direction}."
                )

            if nav.traversable:
                lines.append(
                    "Terrain ahead appears traversable."
                )
            else:
                lines.append(
                "Terrain ahead may be hazardous."
                )

        # Semantic objects
        for obj in self.objects:

            desc = f"{obj.object_type}"

            if obj.relative_position:
                desc += f" detected {obj.relative_position}"

            if obj.distance_m is not None:
                desc += f" at {obj.distance_m:.1f} meters"

            desc += "."

            lines.append(desc)

        # Regions
        for region in self.regions:

            region_desc = f"Region detected: {region.name}"

            if region.traversability:
                region_desc += (
                    f" ({region.traversability})"
                )

            region_desc += "."

            lines.append(region_desc)

        return "\n".join(lines)        
