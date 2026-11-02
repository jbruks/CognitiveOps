import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from mf_dod_mission_runner import targets_from_journal,run_cycles

def fixture(path):
    rows=[
      {"stage":"L4_PLAN","output":{"objectives":[
          {"id":"A","feature":"road","goal":"Observe road"},
          {"id":"B","feature":"facility","goal":"Observe facility"}]}},
      {"stage":"OPERATOR_APPROVED_FOR_OFFLINE_ONLY","ids":["A","B"]},
      {"stage":"L3_GEO_PROPOSAL","output":{"objective_id":"A","calculated_gps":{"latitude":39.0,"longitude":-0.6}}},
      {"stage":"L3_GEO_PROPOSAL","output":{"objective_id":"B","calculated_gps":{"latitude":39.0001,"longitude":-0.6}}},
    ]
    path.write_text("\n".join(json.dumps(x) for x in rows)+"\n")

class FakeSensor:
    def __init__(self, values):self.values=values;self.index=0
    def read(self):
        value=self.values[min(self.index,len(self.values)-1)]
        self.index+=1
        return SimpleNamespace(**value)

class MissionRunnerTests(unittest.TestCase):
    def test_targets_from_approved_l3_proposals(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"journal.jsonl";fixture(path)
            result=targets_from_journal(path)
            self.assertEqual([x.objective_id for x in result],["A","B"])
            self.assertEqual(result[1].latitude,39.0001)
    def test_missing_approval_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"journal.jsonl";fixture(path)
            rows=path.read_text().splitlines()
            path.write_text("\n".join(row for row in rows if "OPERATOR_APPROVED" not in row))
            with self.assertRaises(ValueError):targets_from_journal(path)
    def test_unapproved_destination_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"journal.jsonl";fixture(path)
            path.write_text(path.read_text().replace('"objective_id": "B"','"objective_id": "C"'))
            with self.assertRaises(ValueError):targets_from_journal(path)
    def test_two_cycles_same_input_and_no_actuation(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"journal.jsonl";fixture(path)
            targets=targets_from_journal(path)
            gps=FakeSensor([dict(available=True,fresh=True,latitude=39.0,longitude=-0.6,horizontal_accuracy_m=1)])
            attitude=FakeSensor([dict(available=True,fresh=True,heading_deg=90)])
            output=io.StringIO()
            visited=run_cycles(targets,path,output,gps,attitude,max_cycles=2,interval=0,
                               approval=lambda _: "REACHED")
            rows=[json.loads(x) for x in output.getvalue().splitlines()]
            self.assertEqual(visited,1)
            self.assertEqual([r["event"] for r in rows],["START","CYCLE","OPERATOR_REACHED","CYCLE","END"])
            self.assertTrue(all(r["physical_actions"]==0 for r in rows))
            self.assertEqual(rows[3]["objective_id"],"B")
            self.assertFalse(rows[3]["tactical_proposal"]["executable"])
    def test_invalid_sonar_forces_hold(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"journal.jsonl";fixture(path)
            gps=FakeSensor([dict(available=False,fresh=False,latitude=None,longitude=None,horizontal_accuracy_m=None)])
            attitude=FakeSensor([dict(available=False,fresh=False,heading_deg=None)])
            sonar=FakeSensor([dict(front_distance_valid=False,front_blocked=None)])
            output=io.StringIO()
            run_cycles(targets_from_journal(path),path,output,gps,attitude,
                       sonar=sonar,max_cycles=1,interval=0)
            rows=[json.loads(x) for x in output.getvalue().splitlines()]
            self.assertEqual(rows[1]["tactical_proposal"]["action"],"HOLD")

if __name__=="__main__":unittest.main()
