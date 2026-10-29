"""Offline MF-DoD mission lifecycle, separate from physical actuation.

Uses approved navigation targets only. The adapter to L3 can be a fake for a
lab demonstration; physical authorization and geographic validation are out of
scope. Evidence never becomes 'observed' without explicit observation input.
"""
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone

from l3_models import NavigationObjective, NavigationResult, NavigationStatus


class InspectionStatus(str, Enum):
    PENDING = "PENDING"
    NAVIGATING = "NAVIGATING"
    AWAITING_EVIDENCE = "AWAITING_EVIDENCE"
    OBSERVED = "OBSERVED"
    PARTIAL = "PARTIAL"
    UNVERIFIED = "UNVERIFIED"
    INACCESSIBLE = "INACCESSIBLE"


@dataclass(frozen=True)
class MissionEvidence:
    objective_id: str
    description: str
    observed: bool
    confidence: float | None = None
    image_ref: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    limitation: str | None = None

    def __post_init__(self):
        if not self.objective_id or not self.description:
            raise ValueError("Evidence needs an objective and description")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be 0..1")


@dataclass
class InspectionObjective:
    navigation: NavigationObjective
    question: str
    status: InspectionStatus = InspectionStatus.PENDING
    evidence: list[MissionEvidence] = field(default_factory=list)
    issue: str | None = None


@dataclass
class InspectionPlan:
    intent: str
    objectives: list[InspectionObjective]
    doctrine: list[dict] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.intent.strip() or not self.objectives:
            raise ValueError("Mission must have intent and objectives")
        ids = [o.navigation.objective_id for o in self.objectives]
        if len(ids) != len(set(ids)):
            raise ValueError("Navigation objective IDs must be unique")


class MissionOrchestrator:
    """L4-only mission state machine; never sends a motor command."""

    def __init__(self, plan: InspectionPlan):
        self.plan = plan
        self.active_id = None

    def next_objective(self):
        if self.active_id is not None:
            return next(o.navigation for o in self.plan.objectives
                        if o.navigation.objective_id == self.active_id)
        for entry in self.plan.objectives:
            if entry.status == InspectionStatus.PENDING:
                entry.status = InspectionStatus.NAVIGATING
                self.active_id = entry.navigation.objective_id
                return entry.navigation
        return None

    def accept_navigation(self, result: NavigationResult):
        if result.objective_id != self.active_id:
            raise ValueError("Unexpected navigation objective result")
        entry = next(o for o in self.plan.objectives
                     if o.navigation.objective_id == self.active_id)
        if result.status == NavigationStatus.COMPLETED:
            entry.status = InspectionStatus.AWAITING_EVIDENCE
            self.active_id = None
        elif result.status in (NavigationStatus.BLOCKED, NavigationStatus.FAILED):
            entry.status = InspectionStatus.INACCESSIBLE
            entry.issue = result.reason or result.status.value
            self.active_id = None
        self.plan.decisions.append({
            "objective_id": result.objective_id, "status": result.status.value,
            "reason": result.reason, "distance_m": result.distance_remaining_m,
        })

    def record_evidence(self, evidence: MissionEvidence):
        entry = next((o for o in self.plan.objectives
                      if o.navigation.objective_id == evidence.objective_id), None)
        if entry is None:
            raise ValueError("Unknown objective")
        if entry.status not in (InspectionStatus.AWAITING_EVIDENCE,
                                InspectionStatus.PARTIAL):
            raise ValueError("Cannot attribute evidence before navigation arrival")
        entry.evidence.append(evidence)
        entry.status = (InspectionStatus.OBSERVED if evidence.observed
                        else InspectionStatus.PARTIAL)

    def finish_unobserved(self):
        if self.active_id is not None:
            raise ValueError("Navigation still active")
        for entry in self.plan.objectives:
            if entry.status in (InspectionStatus.PENDING,
                                InspectionStatus.AWAITING_EVIDENCE):
                entry.status = InspectionStatus.UNVERIFIED

    def report(self):
        return {
            "intent": self.plan.intent,
            "completed": all(o.status not in (
                InspectionStatus.PENDING, InspectionStatus.NAVIGATING,
                InspectionStatus.AWAITING_EVIDENCE) for o in self.plan.objectives),
            "objectives": [
                {"id": o.navigation.objective_id, "question": o.question,
                 "status": o.status.value, "issue": o.issue,
                 "evidence": [vars(e).copy() for e in o.evidence]}
                for o in self.plan.objectives
            ],
            "doctrine_sources": list(self.plan.doctrine),
            "decision_log": list(self.plan.decisions),
        }
