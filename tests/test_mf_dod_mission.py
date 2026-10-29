"""Offline MF-DoD mission, doctrine provenance and evidence tests."""
import unittest

# Importing the existing skeleton test installs the same safe perception
# import boundary needed by l4_mission_planner.
from tests import test_mf_dod_skeleton  # noqa: F401

from doctrine_service import DoctrineService, DoctrinePassage
from l3_models import NavigationObjective, NavigationResult, NavigationStatus
from mf_dod_mission import (
    InspectionObjective, InspectionPlan, InspectionStatus,
    MissionOrchestrator, MissionEvidence,
)
from mf_dod_demo import run_demo


class DoctrineAndMissionTest(unittest.TestCase):
    def test_doctrine_returns_attributed_passages_only(self):
        svc = DoctrineService([
            DoctrinePassage("handbook", "Document observations and uncertainty",
                            locator="p.12", verified=True),
            DoctrinePassage("other", "Drive quickly toward coordinates"),
        ])
        hits = svc.retrieve("How to document observations and uncertainty?")
        self.assertEqual(len(hits), 1)
        provenance = svc.provenance(hits[0])
        self.assertEqual(provenance["source"], "handbook")
        self.assertEqual(provenance["locator"], "p.12")
        self.assertTrue(provenance["locator_verified"])

    def test_navigation_arrival_is_not_evidence(self):
        goal = NavigationObjective("X", 39.0, -0.6)
        plan = InspectionPlan("Inspect", [InspectionObjective(goal, "What is visible?")])
        mission = MissionOrchestrator(plan)
        self.assertEqual(mission.next_objective(), goal)
        mission.accept_navigation(NavigationResult("X", NavigationStatus.COMPLETED, 1.0))
        self.assertEqual(plan.objectives[0].status, InspectionStatus.AWAITING_EVIDENCE)
        self.assertFalse(mission.report()["completed"])
        mission.record_evidence(MissionEvidence("X", "Synthetic photo", observed=True))
        self.assertEqual(plan.objectives[0].status, InspectionStatus.OBSERVED)
        self.assertTrue(mission.report()["completed"])

    def test_block_does_not_fabricate_observation(self):
        goal = NavigationObjective("X", 39.0, -0.6)
        mission = MissionOrchestrator(InspectionPlan("Inspect", [
            InspectionObjective(goal, "What is visible?")]))
        mission.next_objective()
        mission.accept_navigation(NavigationResult("X", NavigationStatus.BLOCKED,
                                                   16.0, "OBSTACLE"))
        report = mission.report()
        self.assertEqual(report["objectives"][0]["status"], "INACCESSIBLE")
        self.assertEqual(report["objectives"][0]["evidence"], [])
        with self.assertRaises(ValueError):
            mission.record_evidence(MissionEvidence("X", "Not observed", False))

    def test_end_to_end_offline_plan_navigation_and_report(self):
        report = run_demo()
        self.assertEqual([x["status"] for x in report["objectives"]],
                         ["OBSERVED", "INACCESSIBLE", "UNVERIFIED"])
        self.assertTrue(report["completed"])
        self.assertEqual(len(report["decision_log"]), 4)
        self.assertEqual(len(report["doctrine_sources"]), 1)
        self.assertFalse(report["doctrine_sources"][0]["locator_verified"])
        self.assertEqual(report["objectives"][1]["evidence"], [])


if __name__ == "__main__":
    unittest.main()
