"""Real GPT L3 -> L4 incident replay, with FAKE sensors and NO hardware.

Consumes a previously operator-approved MF-DoD map journal. Injects a
SYNTHETIC persistent tactical blockage while the simulated rover remains
at a fixed location. Calls GPT only when the cognitive hold threshold is
reached. L3 may choose HOLD (there may then be no L4 call), or request
reordering of approved remaining objectives by GPT L4. In neither case
are motor commands available.
"""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from llm.llm_service import LLMService
from mf_dod_cognitive_supervisor import CognitiveSupervisor
from mf_dod_mission_runner import targets_from_journal, run_cycles


class FixedGPS:
    def __init__(self, lat, lon):
        self.position=SimpleNamespace(available=True,fresh=True,latitude=lat,
                                      longitude=lon,horizontal_accuracy_m=1.0,
                                      gps_status="SYNTHETIC")
    def read(self):
        return self.position


class FixedHeading:
    def read(self):
        return SimpleNamespace(available=True,fresh=True,heading_deg=90.0,
                               source="SYNTHETIC")


class SyntheticBlockage:
    def observe(self, navigation):
        return SimpleNamespace(status="SYNTHETIC_BLOCKED",
             visual={"scenario":"PERSISTENT_BLOCKAGE","image_available":False},
             tactical={"action":"HOLD","reason":"SYNTHETIC_OBSTRUCTION",
                       "source":"TEST_INJECTION","executable":False})


def execute(journal, output, model="gpt-5.4", cycles=5, threshold=3,
            backend="openai", intent="Reconnoitre the area"):
    targets=targets_from_journal(journal)
    if len(targets)<2:
        raise ValueError("Need at least two approved targets for an L4 replan")
    # Offset from first objective: this is a test position, not rover telemetry.
    first=targets[0]
    gps=FixedGPS(first.latitude+0.0003,first.longitude)
    service=LLMService(backend=backend,model=model if backend=="openai" else None)
    cognitive=CognitiveSupervisor(service,intent=intent,hold_threshold=threshold,
                                  max_replans=1)
    dest=Path(output)
    if dest.exists():
        raise FileExistsError("Output already exists; select a new JSONL filename")
    with dest.open("x",encoding="utf-8") as stream:
        stream.write(json.dumps({"event":"LAB_SCENARIO",
             "injected":"SYNTHETIC_OBSTRUCTION",
             "real_sensors":False,"physical_actions":0,
             "backend":backend,"model":model if backend=="openai" else "stub",
             "original_journal":str(journal)},ensure_ascii=False)+"\n")
        run_cycles(targets,journal,stream,gps,FixedHeading(),
                   observer=SyntheticBlockage(),sonar=None,
                   max_cycles=cycles,interval=0,approval=lambda _: "",
                   motor=None,cognitive=cognitive)
    rows=[json.loads(x) for x in dest.read_text(encoding="utf-8").splitlines()]
    noteworthy=[x for x in rows if x.get("event") in (
        "L3_REVIEW","L4_REPLAN","COGNITIVE_HOLD","COGNITIVE_SKIP","END")]
    print(json.dumps({"trace":str(dest),
       "l3_reviews":sum(x["event"]=="L3_REVIEW" for x in rows),
       "l4_replans":sum(x["event"]=="L4_REPLAN" for x in rows),
       "events":noteworthy},indent=2,ensure_ascii=False))
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--journal",required=True,help="Approved original L4/L3 map journal")
    p.add_argument("--output",required=True,help="New JSONL output")
    p.add_argument("--model",default="gpt-5.4")
    p.add_argument("--backend",choices=("openai","stub"),default="openai")
    p.add_argument("--cycles",type=int,default=5)
    p.add_argument("--threshold",type=int,default=3)
    p.add_argument("--intent",default="Reconnoitre the area")
    args=p.parse_args()
    if args.cycles<1 or args.threshold<1:
        p.error("cycles and threshold must be >= 1")
    print("LAB ONLY: synthetic blockage, no hardware interfaces, no motors.")
    execute(args.journal,args.output,args.model,args.cycles,args.threshold,
            args.backend,args.intent)


if __name__=="__main__":
    main()
