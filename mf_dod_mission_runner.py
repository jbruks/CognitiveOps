"""MF-DoD sequential mission runner. Non-actuating PoC integration.

Consumes approved L4/L3 map-recon journal; retains target order; performs
one observable discrete GPS/heading/tactical advisory cycle per iteration.
No legacy L1/L2.step imports, no ARM, STOP or motor commands. A future
powered adapter requires separate field-safety verification.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from l3_models import NavigationObjective
from mf_dod_live_shadow import evaluate_position
from mf_dod_geo_guidance_replay import replay


def targets_from_journal(path):
    """Only accept targets tied to one explicit offline approval."""
    records=[json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    approvals=[r for r in records if r.get("stage")=="OPERATOR_APPROVED_FOR_OFFLINE_ONLY"]
    if len(approvals)!=1 or not isinstance(approvals[0].get("ids"),list):
        raise ValueError("Exactly one offline approval event required")
    approved=approvals[0]["ids"]
    if len(set(approved))!=len(approved) or not approved:
        raise ValueError("Invalid approved IDs")
    plans=[r for r in records if r.get("stage")=="L4_PLAN"]
    if len(plans)!=1 or not isinstance(plans[0].get("output",{}).get("objectives"),list):
        raise ValueError("Exactly one L4 plan required")
    plan=plans[0]["output"]["objectives"]
    by_id={p["id"]:p for p in plan}
    if len(by_id)!=len(plan) or set(approved)!=set(by_id):
        raise ValueError("Approval and L4 plan do not match")
    proposals=[r for r in records if r.get("stage")=="L3_GEO_PROPOSAL"]
    if len(proposals)!=len(approved):
        raise ValueError("Exactly one L3 proposal required per approved objective")
    targets=[]
    seen=set()
    for row in proposals:
        out=row["output"]
        oid=out["objective_id"]
        if oid in seen or oid not in by_id:
            raise ValueError("Duplicate or unapproved L3 target")
        seen.add(oid)
        gps=out.get("calculated_gps")
        if not gps:
            raise ValueError("Unresolved L3 destination: "+oid)
        # Geodesic routine verifies finite and bounded numeric coordinates.
        from mf_dod_geo_guidance_replay import guidance
        guidance(gps["latitude"],gps["longitude"],gps["latitude"],gps["longitude"])
        targets.append(NavigationObjective(oid,gps["latitude"],gps["longitude"],
                  radius_m=5.0,purpose=by_id[oid]["goal"]))
    if seen!=set(approved):
        raise ValueError("Approved targets missing")
    return targets


def record(stream,kind,cycle,**payload):
    row={"utc":datetime.now(timezone.utc).isoformat(),
         "event":kind,"cycle":cycle,"physical_actions":0,**payload}
    stream.write(json.dumps(row,ensure_ascii=False,default=str)+"\n")
    stream.flush()
    return row


def run_cycles(targets, source_journal, stream, gps, attitude,
               observer=None, sonar=None, max_cycles=0, interval=3,
               approval=input):
    """Sequential, non-actuating mission; dependencies injectable for tests."""
    record(stream,"START",0,source_journal=str(source_journal),
           approved_objectives=[t.objective_id for t in targets],
           physical_mode="SHADOW_ONLY")
    idx=0
    cycle=0
    try:
        while idx<len(targets) and (max_cycles==0 or cycle<max_cycles):
            cycle+=1
            target=targets[idx]
            pos=gps.read()
            heading=attitude.read()
            nav=evaluate_position(pos,heading,target)
            row={"objective_id":target.objective_id,
                 "target":{"latitude":target.latitude,"longitude":target.longitude,
                           "radius_m":target.radius_m},
                 "gps":vars(pos),"attitude":vars(heading),"navigation":nav}
            proposed={"action":"HOLD","executable":False,"reason":"NO_VALID_TACTICAL_OBSERVATION"}
            if observer is not None:
                obs=observer.observe(nav)
                row["perception"]={"status":obs.status,"visual":obs.visual}
                proposed=obs.tactical
            if sonar is not None:
                sample=sonar.read()
                row["ultrasonic"]=sample
                if sample.get("front_distance_valid") is not True or sample.get("front_blocked") is not False:
                    proposed={"action":"HOLD","executable":False,"reason":"SONAR_BLOCKED_OR_INVALID"}
            row["tactical_proposal"]={**proposed,"executable":False}
            record(stream,"CYCLE",cycle,**row)
            print(f"[{cycle}] {target.objective_id} {nav['status']} distance={nav['distance_m']} bearing={nav['bearing_deg']} tactical={proposed['action']} (NOT EXECUTED)")
            if (nav["status"]=="OBSERVING_MANUAL_MOTION" and nav["distance_m"] is not None
                    and nav["distance_m"]<=target.radius_m):
                if approval("Candidate arrival only. Mark REACHED to advance (or Enter): ").strip()=="REACHED":
                    record(stream,"OPERATOR_REACHED",cycle,objective_id=target.objective_id,
                           inspection="UNVERIFIED")
                    idx+=1
            if idx<len(targets) and interval:
                time.sleep(interval)
    except KeyboardInterrupt:
        record(stream,"INTERRUPTED",cycle)
    finally:
        record(stream,"END",cycle,visited=idx,total=len(targets),
               inspections="UNVERIFIED",physical_actions=0)
    return idx


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--l3-journal",required=True,
                   help="Previously generated and offline-approved L4/L3 map journal")
    p.add_argument("--output",required=True,help="New append-only mission JSONL")
    p.add_argument("--mode",choices=("shadow",),default="shadow",
                   help="This iteration deliberately has no powered mode")
    p.add_argument("--camera",action="store_true")
    p.add_argument("--ultrasonic",action="store_true",
                   help="Only GET_DISTANCE; requires motors/servos electrically isolated")
    p.add_argument("--cycles",type=int,default=0)
    p.add_argument("--interval",type=float,default=3)
    args=p.parse_args(argv)
    if args.cycles<0 or args.interval<0:
        p.error("Invalid cycles/interval")
    targets=targets_from_journal(args.l3_journal)
    print("MISSION SHADOW: zero physical actions; candidate geometry is NOT operating permission")
    for target in targets:
        print(target.objective_id,target.latitude,target.longitude,target.purpose)
    if input("Confirm reviewed destinations for MANUAL SHADOW ONLY (type YES): ").strip()!="YES":
        print("Aborted before opening sensors");return
    if args.ultrasonic and input("Motor AND servo power disconnected? Type DISCONNECTED: ").strip()!="DISCONNECTED":
        print("Aborted before opening serial");return
    from sensors.phone_position_service import PhonePositionService
    from sensors.phone_attitude_service import PhoneAttitudeService
    observer=sonar=None
    with Path(args.output).open("x",encoding="utf-8") as stream:
        try:
            if args.camera:
                from mf_dod_shadow_perception import ShadowCameraObserver
                observer=ShadowCameraObserver()
            if args.ultrasonic:
                from mf_dod_shadow_sonar import ReadOnlySonar
                sonar=ReadOnlySonar().open()
            run_cycles(targets,args.l3_journal,stream,
                       PhonePositionService(),PhoneAttitudeService(),
                       observer=observer,sonar=sonar,
                       max_cycles=args.cycles,interval=args.interval)
        finally:
            if sonar is not None: sonar.close()
            if observer is not None: observer.close()

if __name__=="__main__":
    main()
