"""MF-DoD sequential mission runner. non-actuating shadow and explicitly gated motor mode.

Consumes approved L4/L3 map-recon journal; retains target order; performs
one observable discrete GPS/heading/tactical advisory cycle per iteration.
Motor mode reuses L1 with one-time enablement, bounded actions and STOP.
It never calls L2.step() or its automatic reverse recovery.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from l3_models import NavigationObjective
from mf_dod_live_shadow import evaluate_position


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
               approval=input, motor=None, action_seconds=1.0,
               cognitive=None):
    """Sequential mission with injectable motor, no per-maneuver approvals."""
    record(stream,"START",0,source_journal=str(source_journal),
           approved_objectives=[t.objective_id for t in targets],
           physical_mode="MOTOR" if motor else "SHADOW_ONLY")
    idx=0
    cycle=0
    stop_reason=None
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
            selected="HOLD"
            if motor is not None:
                safe_range=(row.get("ultrasonic",{}).get("front_distance_valid") is True
                            and row["ultrasonic"].get("front_blocked") is False)
                safe_camera=(row.get("perception",{}).get("status")=="CAMERA_OBSERVED")
                if nav["status"]=="OBSERVING_MANUAL_MOTION" and safe_range and safe_camera:
                    if proposed.get("action") in ("MOVE_FORWARD","FORWARD_LEFT","FORWARD_RIGHT"):
                        if nav["distance_m"]>target.radius_m:
                            selected=proposed["action"]
                row["motor_decision"]={"action":selected}
            record(stream,"CYCLE",cycle,**row)
            if motor is not None:
                from rover_interfaces import TacticalAction
                try:
                    if selected!="HOLD":
                        record(stream,"MOTOR_COMMAND",cycle,objective_id=target.objective_id,
                               action=selected,physical_actions=1)
                        motor.execute_tactical_action(TacticalAction[selected])
                        time.sleep(action_seconds)
                    else:
                        motor.execute_tactical_action(TacticalAction.HOLD)
                finally:
                    motor.stop()
                    record(stream,"INTER_CYCLE_STOP",cycle,objective_id=target.objective_id,
                           physical_actions=1)
            print(f"[{cycle}] {target.objective_id} {nav['status']} distance={nav['distance_m']} bearing={nav['bearing_deg']} tactical={proposed['action']} (motor={selected if motor else 'OFF'})")
            if (nav["status"]=="OBSERVING_MANUAL_MOTION" and nav["distance_m"] is not None
                    and nav["distance_m"]<=target.radius_m):
                if approval("Candidate arrival only. Mark REACHED to advance (or Enter): ").strip()=="REACHED":
                    record(stream,"OPERATOR_REACHED",cycle,objective_id=target.objective_id,
                           inspection="UNVERIFIED")
                    idx+=1
                    if cognitive is not None:
                        cognitive.reset()
            # Cognitive mission review occurs AFTER each physical cycle's STOP.
            # No changes to the pre-existing L1/L2 motion command path.
            if cognitive is not None and idx<len(targets) and target.objective_id==targets[idx].objective_id:
                decision, remaining, events=cognitive.review(
                    target,targets[idx+1:],nav,proposed)
                for event in events:
                    kind=event.pop("event")
                    record(stream,kind,cycle,**event)
                if decision=="HOLD":
                    stop_reason="L3_HOLD"
                    record(stream,"COGNITIVE_HOLD",cycle,objective_id=target.objective_id)
                    break
                if decision=="REPLAN":
                    record(stream,"COGNITIVE_SKIP",cycle,objective_id=target.objective_id,
                           inspection="UNVERIFIED_BLOCKED")
                    targets=targets[:idx]+remaining
            if idx<len(targets) and interval:
                time.sleep(interval)
    except KeyboardInterrupt:
        record(stream,"INTERRUPTED",cycle)
    finally:
        record(stream,"END",cycle,visited=idx,total=len(targets),
               inspections="UNVERIFIED",stop_reason=stop_reason,physical_actions=0)
    return idx


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--l3-journal",required=True,
                   help="Previously generated and offline-approved L4/L3 map journal")
    p.add_argument("--output",required=True,help="New append-only mission JSONL")
    p.add_argument("--mode",choices=("shadow","motor"),default="shadow")
    p.add_argument("--motor-enable",action="store_true")
    p.add_argument("--serial",default="/dev/serial/by-id/usb-Arduino_UNO_WiFi_R4_CMSIS-DAP_3CDC7544B664-if01")
    p.add_argument("--action-seconds",type=float,default=1.0)
    p.add_argument("--allow-api",action="store_true",help="Enable live GPT L3/L4 event reviews")
    p.add_argument("--model",default="gpt-5.4")
    p.add_argument("--mission-intent",default="Reconnoitre the area")
    p.add_argument("--hold-threshold",type=int,default=3)
    p.add_argument("--max-replans",type=int,default=1)
    p.add_argument("--camera",action="store_true")
    p.add_argument("--ultrasonic",action="store_true",
                   help="Only GET_DISTANCE; requires motors/servos electrically isolated")
    p.add_argument("--cycles",type=int,default=0)
    p.add_argument("--interval",type=float,default=3)
    args=p.parse_args(argv)
    if (args.cycles<0 or args.interval<0 or not 0<args.action_seconds<=3
            or args.hold_threshold<1 or args.max_replans<0):
        p.error("Invalid cycles/interval")
    targets=targets_from_journal(args.l3_journal)
    print("MF-DOD MODE:",args.mode,"; map targets do not imply access permission")
    if args.mode=="motor" and not (args.motor_enable and args.camera and args.ultrasonic):
        p.error("motor mode requires --motor-enable --camera --ultrasonic")
    for target in targets:
        print(target.objective_id,target.latitude,target.longitude,target.purpose)
    if input("Confirm destinations and mode (type YES): ").strip()!="YES":
        print("Aborted before opening sensors");return
    if args.mode=="shadow" and args.ultrasonic and input("Motor AND servo power disconnected? Type DISCONNECTED: ").strip()!="DISCONNECTED":
        print("Aborted before opening serial");return
    from sensors.phone_position_service import PhonePositionService
    from sensors.phone_attitude_service import PhoneAttitudeService
    if args.mode=="motor" and input("Confirm controlled site and cutoff; type ENABLE MOTORS: ").strip()!="ENABLE MOTORS":
        print("Not enabled");return
    cognitive=None
    if args.allow_api:
        from llm.llm_service import LLMService
        from mf_dod_cognitive_supervisor import CognitiveSupervisor
        cognitive=CognitiveSupervisor(LLMService(backend="openai",model=args.model),
                     intent=args.mission_intent,hold_threshold=args.hold_threshold,
                     max_replans=args.max_replans)
    observer=sonar=motor=None
    with Path(args.output).open("x",encoding="utf-8") as stream:
        try:
            if args.camera:
                from mf_dod_shadow_perception import ShadowCameraObserver
                observer=ShadowCameraObserver()
            if args.mode=="motor":
                from l1_rover_controler_ra4m1 import L1RoverControler
                motor=L1RoverControler(args.serial)
                motor.connect_and_prepare()
                class MotorSonar:
                    def read(self): return motor.get_front_sensor_state()
                sonar=MotorSonar()
            elif args.ultrasonic:
                from mf_dod_shadow_sonar import ReadOnlySonar
                sonar=ReadOnlySonar().open()
            run_cycles(targets,args.l3_journal,stream,
                       PhonePositionService(),PhoneAttitudeService(),
                       observer=observer,sonar=sonar,
                       max_cycles=args.cycles,interval=args.interval,
                       motor=motor,action_seconds=args.action_seconds,
                       cognitive=cognitive)
        finally:
            if motor is not None:
                try: motor.stop()
                finally: motor.disarm()
            elif sonar is not None: sonar.close()
            if observer is not None: observer.close()

if __name__=="__main__":
    main()
