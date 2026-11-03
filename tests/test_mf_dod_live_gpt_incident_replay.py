import json
import tempfile
import unittest
from pathlib import Path
from experiments.mf_dod_live_gpt_incident_replay import execute

class LiveGPTIncidentReplayTests(unittest.TestCase):
    def test_stub_replay_no_hardware_and_no_motor(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            journal=folder/"input.jsonl"
            rows=[
              {"stage":"L4_PLAN","output":{"objectives":[
                {"id":"A","feature":"track","goal":"Observe track"},
                {"id":"B","feature":"structure","goal":"Observe structure"}]}},
              {"stage":"OPERATOR_APPROVED_FOR_OFFLINE_ONLY","ids":["A","B"]},
              {"stage":"L3_GEO_PROPOSAL","output":{"objective_id":"A","calculated_gps":{"latitude":39.0,"longitude":-0.6}}},
              {"stage":"L3_GEO_PROPOSAL","output":{"objective_id":"B","calculated_gps":{"latitude":39.001,"longitude":-0.6}}}
            ]
            journal.write_text("\n".join(json.dumps(x) for x in rows)+"\n")
            result=execute(journal,folder/"out.jsonl",backend="stub",threshold=2,cycles=3)
            self.assertEqual(result[0]["event"],"LAB_SCENARIO")
            self.assertTrue(any(x["event"]=="L3_REVIEW" for x in result))
            self.assertFalse(any(x["event"]=="MOTOR_COMMAND" for x in result))
            self.assertTrue(all(x["physical_actions"]==0 for x in result))
            self.assertEqual(result[0]["real_sensors"],False)
    def test_missing_input_approval(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"bad.jsonl"
            path.write_text("{}\n")
            with self.assertRaises(ValueError):
                execute(path,Path(d)/"out.jsonl",backend="stub")

if __name__=="__main__":
    unittest.main()
