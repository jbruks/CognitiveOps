"""Contract tests for the MF-DoD optional controller adapter (fake hardware)."""
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from mf_dod_mission_runner import run_cycles
from l3_models import NavigationObjective

class Sensor:
    def __init__(self,data): self.data=data
    def read(self): return SimpleNamespace(**self.data)

class Range:
    def __init__(self,valid=True,blocked=False):
        self.valid,self.blocked=valid,blocked
    def read(self): return dict(front_distance_valid=self.valid,front_blocked=self.blocked)

class Vision:
    def __init__(self,choice="MOVE_FORWARD"): self.choice=choice
    def observe(self,state):
        return SimpleNamespace(status="CAMERA_OBSERVED",visual={"confidence":0.8},
                    tactical={"action":self.choice,"reason":"test","source":"fake"})

class Controller:
    def __init__(self):self.commands=[]
    def execute_tactical_action(self,action):self.commands.append(action.name)
    def stop(self):self.commands.append("STOP")

class MotorIntegrationContract(unittest.TestCase):
    def execute(self, vision=None, sonar=None, gps_valid=True):
        gps=Sensor(dict(available=gps_valid,fresh=gps_valid,
              latitude=39.0 if gps_valid else None,
              longitude=-0.6 if gps_valid else None,
              horizontal_accuracy_m=1 if gps_valid else None))
        heading=Sensor(dict(available=True,fresh=True,heading_deg=0))
        motor=Controller()
        output=io.StringIO()
        with patch("mf_dod_mission_runner.time.sleep"):
            run_cycles([NavigationObjective("T1",39.001,-0.6,2,"Inspect")],
                       "example",output,gps,heading,observer=vision,
                       sonar=sonar,motor=motor,max_cycles=1,interval=0)
        return motor.commands,[json.loads(x) for x in output.getvalue().splitlines()]

    def test_allowed_forward_has_stop(self):
        commands,rows=self.execute(Vision(),Range())
        self.assertEqual(commands,["MOVE_FORWARD","STOP"])
        self.assertTrue(any(r["event"]=="INTER_CYCLE_STOP" for r in rows))
    def test_uncertain_range_holds(self):
        commands,_=self.execute(Vision(),Range(valid=False))
        self.assertEqual(commands,["HOLD","STOP"])
    def test_missing_vision_holds(self):
        commands,_=self.execute(None,Range())
        self.assertEqual(commands,["HOLD","STOP"])
    def test_reverse_prohibited(self):
        commands,_=self.execute(Vision("MOVE_BACKWARD"),Range())
        self.assertEqual(commands,["HOLD","STOP"])
    def test_invalid_gps_holds(self):
        commands,_=self.execute(Vision(),Range(),gps_valid=False)
        self.assertEqual(commands,["HOLD","STOP"])

if __name__=="__main__":
    unittest.main()
