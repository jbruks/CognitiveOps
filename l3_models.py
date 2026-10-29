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


class NavigationStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class NavigationObjective:
    """L4 request; constraints remain independently enforced."""
    objective_id: str
    latitude: float
    longitude: float
    radius_m: float = 5.0
    purpose: str = ""


@dataclass(frozen=True)
class NavigationResult:
    """L3 observation; no unverified physical-action acknowledgements."""
    objective_id: str
    status: NavigationStatus
    distance_remaining_m: float | None = None
    reason: str | None = None
