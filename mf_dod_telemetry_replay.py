"""Read-only parser for historical CognitiveOps text telemetry.

Normalizes each [L4] step into a diagnostic cycle. No actuator/serial imports.
A physical log's geographic origin is never assumed to match a MissionPackage.
"""
import argparse
import json
import re
from pathlib import Path

STAMP = re.compile(r"^\[(\d{4}-\d\d-\d\d [^\]]+)\] ")
POSITION = re.compile(r"Phone position: lat=(\S+) lon=(\S+) accuracy=(\S+?)m? status=(\S+) fresh=(\S+) available=(\S+)")
ATTITUDE = re.compile(r"Phone attitude: heading=(\S+) fresh=(\S+) available=(\S+)")
GUIDANCE = re.compile(r"Guidance: (HOLD|FOLLOW_BEARING) bearing=(\S+) distance=(\S+) heading_error=(\S+)")
ACTION = re.compile(r"Executing tactical action via RA4M1: (\S+)")
US = re.compile(r"Distance=([-\d.]+) cm \| Blocked=(\w+) \| Valid=(\w+)")
DONE = re.compile(r"GO_TO_POINT completed: distance=([-\d.]+) m")


def number(value):
    if value is None or value in ("None", "Nonem", "nan"):
        return None
    try:
        return float(value.removesuffix("m"))
    except (ValueError, TypeError):
        return None


def bool_value(value):
    return {"True": True, "False": False}.get(value)


def normalize_log(raw):
    cycles, current = [], None
    outside = {"start_events": [], "unattributed": []}
    for lineno, original in enumerate(raw.splitlines(), 1):
        line = STAMP.sub("", original).strip()
        if line == "[L4] step":
            current = {"cycle": len(cycles) + 1,
                       "source_line": lineno,
                       "position": None, "attitude": None, "guidance": None,
                       "actions": [], "ultrasonic": [], "events": [],
                       "completed_distance_m": None}
            cycles.append(current)
            continue
        if current is None:
            if any(term in line for term in ("Controller ping", "Rover armed", "mission started")):
                outside["start_events"].append({"line": lineno, "text": line})
            continue
        if (m := POSITION.search(line)):
            lat, lon, accuracy, status, fresh, available = m.groups()
            current["position"] = {"latitude": number(lat),
                                   "longitude": number(lon),
                                   "accuracy_m": number(accuracy),
                                   "status": status,
                                   "fresh": bool_value(fresh),
                                   "available": bool_value(available)}
        elif (m := ATTITUDE.search(line)):
            heading, fresh, available = m.groups()
            current["attitude"] = {"heading_deg": number(heading),
                                   "fresh": bool_value(fresh),
                                   "available": bool_value(available)}
        elif (m := GUIDANCE.search(line)):
            kind, bearing, distance, error = m.groups()
            current["guidance"] = {"kind": kind, "bearing_deg": number(bearing),
                                   "distance_m": number(distance),
                                   "heading_error_deg": number(error)}
        elif (m := ACTION.search(line)):
            # Inter-cycle STOP is distinct from an autonomous tactical STOP.
            current["actions"].append({"action": m.group(1), "line": lineno,
                                       "intercycle": bool(current.get("_intercycle"))})
            current["_intercycle"] = False
        elif "Inter-cycle STOP" in line:
            current["_intercycle"] = True
        elif (m := US.search(line)):
            dist, blocked, valid = m.groups()
            current["ultrasonic"].append({
                "distance_cm": number(dist) if valid == "True" else None,
                "blocked": bool_value(blocked),
                "valid": bool_value(valid), "line": lineno})
        elif (m := DONE.search(line)):
            current["completed_distance_m"] = float(m.group(1))
            current["events"].append({"type": "SOFTWARE_REPORTED_ARRIVAL", "line": lineno})
        elif "No valid GPS position" in line:
            current["events"].append({"type": "GPS_UNAVAILABLE", "line": lineno})
        elif "[RECOVERY]" in line:
            current["events"].append({"type": "RECOVERY_NOTICE", "line": lineno,
                                      "text": line})
        elif "Guidance HOLD" in line:
            current["events"].append({"type": "GUIDANCE_HOLD", "line": lineno})
    for cycle in cycles:
        cycle.pop("_intercycle", None)
        p = cycle["position"]
        cycle["gps_usable"] = bool(p and p["fresh"] is True
                                   and p["available"] is True
                                   and p["latitude"] is not None
                                   and p["longitude"] is not None)
    return {"format": "COGNITIVEOPS_TEXT_CYCLES_V1",
            "source_type": "HISTORICAL_PHYSICAL_RUNTIME_LOG",
            "objective_attribution": "UNKNOWN_NOT_MATCHED_TO_MISSION_PACKAGE",
            "cycles": cycles, **outside}


def summary(parsed):
    cycles = parsed["cycles"]
    return {"cycles": len(cycles),
            "valid_position_cycles": sum(bool(c["gps_usable"]) for c in cycles),
            "guidance_hold_cycles": sum(c["guidance"] is not None and
                                        c["guidance"]["kind"] == "HOLD"
                                        for c in cycles),
            "reported_arrivals": sum(c["completed_distance_m"] is not None
                                     for c in cycles),
            "recovery_notices": sum(e["type"] == "RECOVERY_NOTICE"
                                    for c in cycles for e in c["events"]),
            "invalid_ultrasonic_samples": sum(s["valid"] is False for c in cycles
                                               for s in c["ultrasonic"]),
            "notes": ["GPS availability alone does not establish accuracy or safety",
                      "STOP during an inter-cycle interval is not a blockage",
                      "Software-reported arrival is not independently verified",
                      "No automatic match to Llombai POIs or simulation geofence"]}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("log")
    p.add_argument("--output", required=True)
    args = p.parse_args(argv)
    path = Path(args.log)
    if not path.is_file():
        p.error("Input log not found")
    dest = Path(args.output)
    if dest.exists():
        p.error("Refusing to overwrite report")
    parsed = normalize_log(path.read_text(encoding="utf-8", errors="replace"))
    parsed["source_file"] = path.name
    parsed["summary"] = summary(parsed)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(parsed, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(json.dumps({"source": path.name, **parsed["summary"],
                      "output": str(dest)}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
