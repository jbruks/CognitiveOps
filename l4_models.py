from dataclasses import dataclass
from enum import Enum


class MissionTask(Enum):
    EXPLORE = "EXPLORE"
    GOTO = "GOTO"
    STOP = "STOP"


class MissionStatus(Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


@dataclass
class Mission:
    task: MissionTask

    target_lat: float | None = None
    target_lon: float | None = None

    arrival_radius_m: float = 2.0

    status: MissionStatus = MissionStatus.PENDING
