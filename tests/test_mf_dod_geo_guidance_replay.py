import json
import tempfile
import unittest
from pathlib import Path
from mf_dod_geo_guidance_replay import guidance,replay

class GuidanceReplayTests(unittest.TestCase):
    def test_north(self):
        g=guidance(39,-0.6,39.001,-0.6,0)
        self.assertAlmostEqual(g["bearing_deg"],0,places=2)
        self.assertEqual(g["heading_error_deg"],0)
        self.assertGreater(g["distance_m"],100)
    def test_heading_error(self):
        g=guidance(39,-0.6,39.001,-0.6,90)
        self.assertEqual(g["heading_error_deg"],-90)
    def test_invalid(self):
        with self.assertRaises(ValueError):
            guidance(100,0,39,0)
    def test_approval_required(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"x.jsonl"
            path.write_text(json.dumps({"stage":"L3_GEO_PROPOSAL","output":{"objective_id":"A","calculated_gps":{"latitude":39,"longitude":-0.6}}})+"\n")
            with self.assertRaises(ValueError):
                replay(path,39,-0.6)
    def test_replay(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"x.jsonl"
            path.write_text("\n".join(map(json.dumps,[
                {"stage":"OPERATOR_APPROVED_FOR_OFFLINE_ONLY","ids":["A"]},
                {"stage":"L3_GEO_PROPOSAL","request_id":"req1","output":{"objective_id":"A","calculated_gps":{"latitude":39.001,"longitude":-0.6}}}
            ]))+"\n")
            result=replay(path,39,-0.6)
            self.assertEqual(result[0]["llm_request_id"],"req1")
            self.assertEqual(result[0]["physical_actions"],0)
            self.assertEqual(result[0]["status"],"SIMULATED_GUIDANCE_ONLY")

if __name__=="__main__":
    unittest.main()
