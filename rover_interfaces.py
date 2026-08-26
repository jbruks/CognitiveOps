from dataclasses import dataclass
from dataclasses import field
from enum import Enum


class TacticalAction(Enum):
    MOVE_FORWARD = "MOVE_FORWARD"
    FORWARD_LEFT = "FORWARD_LEFT"
    FORWARD_RIGHT = "FORWARD_RIGHT"
    #TURN_LEFT = "FORWARD_LEFT"
    #TURN_RIGHT = "FORWARD_RIGHT"
    MOVE_BACKWARD = "MOVE_BACKWARD" 
    STOP = "STOP"
    HOLD = "HOLD"

@dataclass
class RoverState:
    x: float = 0.0
    y: float = 0.0
    heading_deg: float = 0.0
    speed_m_s: float = 0.0
    armed: bool = False
    mode: str = "UNKNOWN"

@dataclass
class PerceptionState:
    obstacle_ahead: bool
    free_direction: str          # "left" | "right" | "center" | "none"
    corridor_visible: bool
    summary: str = ""
    confidence: float = 1.0
    objects: list = field(default_factory=list)
    regions: list = field(default_factory=list)
