"""MF-DoD live MANUAL SHADOW — first safe integration stage.

Reads the existing phone GPS/heading services; no L1, L2, camera, serial,
servo, or actuator imports. Operators move the rover by hand. The Llombai
simulation package is accepted for observational comparison ONLY, never
as a physical operating authorization. GPT decisions are advisory.
"""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time

from l3_models import NavigationObjective
from llm.llm_service import LLMService
from mf_dod_integrated_agent import prepare_proposals, site_documents
from mission_package import MissionPackage
from sensors.phone_attitude_service import PhoneAttitudeService
from sensors.phone_position_service import PhonePositionService


class ActuationForbidden(RuntimeError):
    pass


class NoActuation:
    """Intentional hard stop for integrations attempting to use this as L1."""
    def __getattr__(self, name):
        raise ActuationForbidden("No L1 method permitted in MANUAL_SHADOW: " + name)


def distance_m(lat1, lon1, lat2, lon2):
    a1, a2 = math.radians(lat1), math.radians(lat2)
    da, dl = a2-a1, math.radians(lon2-lon1)
    h = math.sin(da/2)**2 + math.cos(a1)*math.cos(a2)*math.sin(dl/2)**2
    return 6371000 * 2 * math.atan2(math.sqrt(h), math.sqrt(max(0, 1-h)))


def bearing_deg(lat1, lon1, lat2, lon2):
    a1, a2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2-lon1)
    y = math.sin(dl)*math.cos(a2)
    x = math.cos(a1)*math.sin(a2)-math.sin(a1)*math.cos(a2)*math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def evaluate_position(position, attitude, target, max_accuracy_m=10.0):
    """Pure diagnostics, never a physical arrival confirmation."""
    if (not position.available or not position.fresh
            or position.latitude is None or position.longitude is None):
        return {"status": "GPS_UNAVAILABLE", "distance_m": None,
                "bearing_deg": None, "heading_error_deg": None}
    accuracy = position.horizontal_accuracy_m
    if (accuracy is None or not math.isfinite(accuracy)
            or accuracy < 0 or accuracy > max_accuracy_m):
        return {"status": "GPS_ACCURACY_UNCERTAIN", "distance_m": None,
                "bearing_deg": None, "heading_error_deg": None}
    if not all(math.isfinite(v) for v in (position.latitude, position.longitude)):
        return {"status": "GPS_INVALID", "distance_m": None,
                "bearing_deg": None, "heading_error_deg": None}
    dist = distance_m(position.latitude, position.longitude,
                      target.latitude, target.longitude)
    bearing = bearing_deg(position.latitude, position.longitude,
                          target.latitude, target.longitude)
    if not attitude.available or not attitude.fresh or attitude.heading_deg is None:
        return {"status": "HEADING_UNAVAILABLE", "distance_m": dist,
                "bearing_deg": bearing, "heading_error_deg": None}
    delta = (bearing - attitude.heading_deg + 180) % 360 - 180
    return {"status": "OBSERVING_MANUAL_MOTION", "distance_m": dist,
            "bearing_deg": bearing, "heading_error_deg": delta}


def log_event(path, event, **fields):
    row = {"timestamp": datetime.now(timezone.utc).isoformat(),
           "mode": "MANUAL_SHADOW", "event": event,
           "physical_actions": 0, **fields}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mission", required=True, help="Manifest JSON or package directory")
    p.add_argument("--manual", action="store_true", required=True)
    p.add_argument("--camera", action="store_true", help="Opt-in live camera/VisionNN and non-actuating L2 advice")
    p.add_argument("--ultrasonic", action="store_true", help="Opt-in RA4M1 GET_DISTANCE diagnostic only; requires motor/servo power disconnected")
    p.add_argument("--model", default="gpt-5.4", help="GPT model when --allow-api is set")
    p.add_argument("--allow-api", action="store_true", help="Explicitly enable GPT L4/L3 calls")
    p.add_argument("--cycles", type=int, default=0, help="0 means until Ctrl+C")
    p.add_argument("--interval", type=float, default=3.0)
    p.add_argument("--output", default=None)
    args = p.parse_args(argv)
    if args.cycles < 0 or args.interval < 0.1:
        p.error("Invalid cycle limit or interval")
    source = Path(args.mission)
    manifest = source / "manifest.json" if source.is_dir() else source
    pkg = MissionPackage.load(manifest)
    # Explicitly no serial controller construction or imports.
    output = (Path(args.output) if args.output else
              Path("shadow_logs") / ("manual_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".jsonl"))
    if output.exists():
        p.error("Refusing to overwrite shadow log")
    output.parent.mkdir(parents=True, exist_ok=True)
    service = LLMService(backend="openai" if args.allow_api else "stub",
                         model=args.model if args.allow_api else None)
    print("MANUAL_SHADOW / NO L1 ARM or actuator commands; sonar optional GET_DISTANCE only")
    print("IMPORTANT: Physically isolate motor and servo power before moving manually.")
    print("Mission candidate geometry is simulation-only; this is not movement authorization.")
    goals, _, rationale = prepare_proposals(pkg, service,
                                            site_documents(manifest, pkg),
                                            doctrine=None)
    for g in goals:
        print(f"  {g.objective_id}: {g.poi_id} — {g.purpose}")
    if not goals:
        p.error("No goals proposed")
    choice = input("Approve listed goal IDs for OBSERVATION ONLY (comma separated; Enter aborts): ").strip()
    ids = [x.strip() for x in choice.split(",") if x.strip()]
    objectives = pkg.approve(goals, ids) if ids else []
    if not objectives or len(objectives) != len(ids):
        print("No observation approved; exiting")
        return
    by_id = {x.objective_id: x for x in objectives}
    advice = service.plan_objectives(pkg.intent, [
        {"objective_id": x.objective_id, "purpose": x.purpose}
        for x in objectives], context={"mode": "MANUAL_SHADOW",
                                        "simulation_only_geometry": True})
    order = advice.output["objective_ids"]
    print("L4 proposed observational order:", " -> ".join(order))
    if input("Confirm OBSERVATIONAL order (type YES): ").strip() != "YES":
        print("Not confirmed; exiting")
        return
    log_event(output, "START", site_id=pkg.site_id, order=order,
              planning_reason=rationale, api_enabled=args.allow_api,
              model=args.model if args.allow_api else "stub",
              no_actuator_interface=True)
    phone_gps, phone_heading = PhonePositionService(), PhoneAttitudeService()
    camera = None
    if args.camera:
        from mf_dod_shadow_perception import ShadowCameraObserver
        camera = ShadowCameraObserver()
    sonar = None
    current = 0
    try:
        if args.ultrasonic:
            if input("Motor AND servo power physically disconnected? Type DISCONNECTED: ").strip() != "DISCONNECTED":
                print("Ultrasonic port NOT opened; stopping")
                return
            from mf_dod_shadow_sonar import ReadOnlySonar
            sonar = ReadOnlySonar().open()
        step = 0
        while not args.cycles or step < args.cycles:
            step += 1
            pos, heading = phone_gps.read(), phone_heading.read()
            target = by_id[order[current]]
            state = evaluate_position(pos, heading, target)
            row = {"cycle": step, "objective_id": target.objective_id,
                   "position": vars(pos), "heading": vars(heading),
                   "navigation": state, "movement_source": "HUMAN_OPERATOR"}
            print(f"[{step}] {target.objective_id}: {state['status']} "
                  f"distance={state['distance_m']} heading_error={state['heading_error_deg']}")
            if camera is not None:
                observation = camera.observe(state)
                row["perception"] = observation.visual
                row["perception_status"] = observation.status
                row["tactical_proposal"] = observation.tactical
                print("[CAMERA]", observation.status, "proposed:", observation.tactical["action"], "(NOT EXECUTED)")
            if sonar is not None:
                sample = sonar.read()
                row["ultrasonic"] = sample
                # Invalid/no-echo is UNKNOWN, never interpreted as a clear corridor.
                if (sample["front_distance_valid"] is not True
                        or sample["front_blocked"] is not False):
                    row["tactical_proposal"] = {
                        "action": "HOLD", "reason": "SONAR_UNCERTAIN_OR_BLOCKED",
                        "source": "SHADOW_GUARD", "executable": False}
                    print("[SONAR] UNKNOWN/BLOCKED -> HOLD advisory")
                else:
                    print("[SONAR]", sample["front_distance_cm"], "cm; diagnostic only")
            log_event(output, "OBSERVATION", **row)
            # Arrival is not certified: an operator must explicitly mark a goal
            # reached before the next goal can be observed.
            if (state["status"] == "OBSERVING_MANUAL_MOTION"
                    and state["distance_m"] <= target.radius_m):
                print("Candidate arrival only; manual evidence confirmation required.")
                if input("Mark navigation reached by operator? (type REACHED): ").strip() == "REACHED":
                    log_event(output, "OPERATOR_NAVIGATION_REACHED",
                              objective_id=target.objective_id,
                              distance_m=state["distance_m"],
                              inspection_status="UNVERIFIED")
                    current += 1
                    if current >= len(order):
                        print("All approved observational goals visited; inspections UNVERIFIED")
                        break
            # Optional event-triggered L3 advice, not an automatic action.
            if state["status"] != "OBSERVING_MANUAL_MOTION":
                try:
                    review = service.infer(
                        "L3", "Manual walking observation only. Decide HOLD or REQUEST_OPERATOR_REVIEW. "
                              "Do not propose motor instructions or assert arrival.",
                        {"objective_id": target.objective_id, "navigation": state},
                        ("HOLD", "REQUEST_OPERATOR_REVIEW"))
                    log_event(output, "L3_ADVICE", objective_id=target.objective_id,
                              decision=review.output["decision"],
                              reason=review.output["reason"])
                except Exception as exc:
                    log_event(output, "L3_ERROR_HOLD", error=str(exc))
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped by operator (no actuator commands).")
        log_event(output, "INTERRUPTED")
    finally:
        if sonar is not None:
            sonar.close()
        if camera is not None:
            camera.close()
        log_event(output, "END", inspection_status="UNVERIFIED")
        print("Shadow log:", output)


if __name__ == "__main__":
    main()
