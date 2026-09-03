from dataclasses import dataclass
from enum import Enum


class TaskMode(Enum):
    EXPLORE = "EXPLORE"
    RECOVER = "RECOVER"
    CAUTIOUS = "CAUTIOUS"


class GuidanceTaskType(Enum):
    FOLLOW_BEARING = "FOLLOW_BEARING"
    HOLD = "HOLD"


@dataclass
class GuidanceTask:
    task_type: GuidanceTaskType
    desired_heading_deg: float | None = None
    distance_remaining_m: float | None = None
    heading_error_deg: float | None = None
