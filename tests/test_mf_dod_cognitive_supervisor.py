import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from l3_models import NavigationObjective
from mf_dod_cognitive_supervisor import CognitiveSupervisor
from mf_dod_mission_runner import run_cycles

def goal(name,lat=39.001):
    return NavigationObjective(name,lat,-0.6,2,"Observe "+name)

class FakeService:
    def __init__(self,l3="REQUEST_L4_REPLAN",order=None):
        self.l3=l3
        self.order=order
        self.requests=[]
    def infer(self,level,instructions,context,allowed_decisions):
        self.requests.append(("L3",context))
        return SimpleNamespace(output={"decision":self.l3,"reason":"Persistent blockage"},
                               request_id="req-L3",model="fake",provider="fake")
    def plan_objectives(self,intent,approved_objectives,context):
        self.requests.append(("L4",context))
        ids=[x["objective_id"] for x in approved_objectives]
        return SimpleNamespace(output={"objective_ids":self.order or list(reversed(ids)),
                                       "reason":"Avoid blocked destination"},
                               request_id="req-L4",model="fake",provider="fake")

class Sensor:
    def __init__(self,data):self.data=data
    def read(self):return SimpleNamespace(**self.data)

class CognitiveMissionTests(unittest.TestCase):
    def test_success_has_no_gpt_calls(self):
        service=FakeService()
        c=CognitiveSupervisor(service,"Reconnoitre",hold_threshold=1)
        status,rem,events=c.review(goal("A"),[goal("B")],
             {"status":"OBSERVING_MANUAL_MOTION"},{"action":"MOVE_FORWARD"})
        self.assertEqual(status,"CONTINUE")
        self.assertEqual(events,[])
        self.assertEqual(service.requests,[])
    def test_block_triggers_l3_l4_replan_with_approved_only(self):
        service=FakeService()
        c=CognitiveSupervisor(service,"Reconnoitre",hold_threshold=2)
        current,remaining=goal("A"),[goal("B"),goal("C")]
        nav={"status":"GPS_UNAVAILABLE"}
        tactical={"action":"HOLD"}
        self.assertEqual(c.review(current,remaining,nav,tactical)[0],"CONTINUE")
        decision,ordered,events=c.review(current,remaining,nav,tactical)
        self.assertEqual(decision,"REPLAN")
        self.assertEqual([x.objective_id for x in ordered],["C","B"])
        self.assertEqual([e["event"] for e in events],["L3_REVIEW","L4_REPLAN"])
        self.assertEqual(events[1]["request_id"],"req-L4")
    def test_l3_hold_stops_without_l4(self):
        service=FakeService(l3="HOLD")
        c=CognitiveSupervisor(service,"Reconnoitre",hold_threshold=1)
        decision,_,_=c.review(goal("A"),[goal("B")],
                           {"status":"GPS_UNAVAILABLE"},{"action":"HOLD"})
        self.assertEqual(decision,"HOLD")
        self.assertEqual(len(service.requests),1)
    def test_l4_cannot_invent_or_omit_targets(self):
        service=FakeService(order=["X"])
        c=CognitiveSupervisor(service,"Reconnoitre",hold_threshold=1)
        with self.assertRaises(ValueError):
            c.review(goal("A"),[goal("B")],
                     {"status":"GPS_UNAVAILABLE"},{"action":"HOLD"})
    def test_bounded_replans_hold_on_second_failure(self):
        service=FakeService()
        c=CognitiveSupervisor(service,"Reconnoitre",hold_threshold=1,max_replans=1)
        self.assertEqual(c.review(goal("A"),[goal("B"),goal("C")],
                         {"status":"GPS_UNAVAILABLE"},{"action":"HOLD"})[0],"REPLAN")
        self.assertEqual(c.review(goal("B"),[goal("C")],
                         {"status":"GPS_UNAVAILABLE"},{"action":"HOLD"})[0],"HOLD")
    def test_integration_replans_in_shadow_without_motor_calls(self):
        service=FakeService()
        c=CognitiveSupervisor(service,"Reconnoitre",hold_threshold=1)
        gps=Sensor({"available":False,"fresh":False,"latitude":None,
                    "longitude":None,"horizontal_accuracy_m":None})
        heading=Sensor({"available":False,"fresh":False,"heading_deg":None})
        output=io.StringIO()
        with patch("mf_dod_mission_runner.time.sleep"):
            run_cycles([goal("A"),goal("B"),goal("C")],"example",output,gps,heading,
                       max_cycles=2,interval=0,cognitive=c)
        rows=[json.loads(x) for x in output.getvalue().splitlines()]
        self.assertTrue(any(x["event"]=="L4_REPLAN" for x in rows))
        cycles=[x["objective_id"] for x in rows if x["event"]=="CYCLE"]
        self.assertEqual(cycles,["A","C"])
        self.assertTrue(all(x["physical_actions"]==0 for x in rows))

if __name__=="__main__":unittest.main()
