from dataclasses import dataclass

@dataclass
class ObjectNode:
    id: str
    object_type: str

    relative_position: str = "unknown"
    distance_m: float = 0.0
    bearing_deg: float = 0.0

    size_estimate_m: float = 0.0
    risk_level: float = 0.0

    confidence: float = 1.0
