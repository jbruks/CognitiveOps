from dataclasses import dataclass

@dataclass
class Region:
    id: str
    terrain_type: str

    roughness: float = 0.0
    slope_deg: float = 0.0
    traversability: float = 1.0

    relative_position: str = "unknown"
    distance_m: float = 0.0

    confidence: float = 1.0
