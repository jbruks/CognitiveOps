from dataclasses import dataclass
from enum import Enum

class TacticalAction(Enum):
    MOVE_FORWARD = "MOVE_FORWARD"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    #TURN_LEFT = "FORWARD_LEFT"
    #TURN_RIGHT = "FORWARD_RIGHT"
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
