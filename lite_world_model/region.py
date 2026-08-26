from dataclasses import dataclass
from typing import Optional


@dataclass
class Region:
    terrain_type: str

    relative_position: Optional[str] = None
    traversability: float = 0.5
