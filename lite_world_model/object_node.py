from dataclasses import dataclass
from typing import Optional


@dataclass
class ObjectNode:
    id: str
    object_type: str

    relative_position: Optional[str] = None
    distance_m: Optional[float] = None

    confidence: float = 1.0
    risk_level: float = 0.0
