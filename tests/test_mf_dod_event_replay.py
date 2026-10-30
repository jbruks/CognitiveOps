"""Offline contract replay tests. No motor, camera or hardware imports."""
import unittest
from llm.llm_service import LLMService
from mission_package import MissionPackage
from mf_dod_integrated_agent import prepare_proposals
from mf_dod_event_replay import replay


class EventReplayTests(unittest.TestCase):
    def setUp(self):
        self.package = MissionPackage(
            {"schema_version": "1.0", "site_id": "LAB-REPLAY",
             "intent": "Inspect reference points", "crs": "EPSG:4326",
             "supporting_documents": []},
            {"type": "FeatureCollection", "features": [
                {"type": "Feature", "properties": {"kind": "authorized"},
                 "geometry": {"type": "Polygon", "coordinates":
                              [[[0, 0], [5, 0], [5, 5], [0, 5], [0, 0]]]}},
                *[{"type": "Feature", "properties": {"kind": "poi", "poi_id": pid},
                   "geometry": {"type": "Point", "coordinates": xy}}
                  for pid, xy in (("A", [1, 1]), ("B", [2, 2]))]]})
        self.proposals, _, _ = prepare_proposals(self.package, LLMService())
        self.ids = [p.objective_id for p in self.proposals]

    def test_replays_blocked_and_arrived_without_observation(self):
        report = replay(self.package, self.proposals, self.ids, [
            {"event": "L3_NAVIGATION_FEEDBACK", "objective_id": self.ids[0],
             "status": "BLOCKED", "reason": "REPLAYED_BLOCK"},
            {"event": "L3_NAVIGATION_FEEDBACK", "objective_id": self.ids[1],
             "status": "COMPLETED"}])
        self.assertEqual([x["status"] for x in report["objectives"]],
                         ["INACCESSIBLE", "UNVERIFIED"])
        self.assertEqual(report["physical_actions"], 0)
        self.assertEqual(report["missing_feedback"], [])

    def test_rejects_unexpected_feedback(self):
        with self.assertRaises(ValueError):
            replay(self.package, self.proposals, self.ids, [
                {"event": "L3_NAVIGATION_FEEDBACK", "objective_id": self.ids[1],
                 "status": "COMPLETED"}])
        with self.assertRaises(ValueError):
            replay(self.package, self.proposals, self.ids, [
                {"event": "L3_NAVIGATION_FEEDBACK", "objective_id": self.ids[0],
                 "status": "IN_PROGRESS"}])


if __name__ == "__main__":
    unittest.main()
