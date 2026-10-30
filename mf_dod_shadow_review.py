"""Conservative offline shadow review of normalized physical rover logs.

Diagnostic only: no LLM, actuator, serial, GPS objectives or geofence decisions.
"""
import argparse
import json
from pathlib import Path


def analyze(data, *, max_gps_accuracy_m=10.0, recovery_window=10):
    if data.get("format") != "COGNITIVEOPS_TEXT_CYCLES_V1":
        raise ValueError("Unsupported telemetry format")
    cycles = data.get("cycles")
    if not isinstance(cycles, list):
        raise ValueError("Missing cycles")
    findings = []
    recent_recovery = []
    for cycle in cycles:
        number = cycle["cycle"]
        pos = cycle.get("position")
        if not cycle.get("gps_usable"):
            findings.append({"cycle": number, "level": "HOLD_RECOMMENDED",
                             "reason": "GPS_UNAVAILABLE"})
        elif pos and (pos.get("accuracy_m") is None or
                      pos["accuracy_m"] > max_gps_accuracy_m):
            findings.append({"cycle": number, "level": "REVIEW",
                             "reason": "GPS_ACCURACY_UNCERTAIN",
                             "accuracy_m": pos.get("accuracy_m")})
        for sample in cycle.get("ultrasonic", []):
            if sample.get("valid") is False:
                findings.append({"cycle": number, "level": "REVIEW",
                                 "reason": "ULTRASONIC_INVALID"})
        recovered = any(e.get("type") == "RECOVERY_NOTICE"
                        for e in cycle.get("events", []))
        if recovered:
            recent_recovery.append(number)
            recent_recovery = [x for x in recent_recovery
                               if number - x < recovery_window]
            findings.append({"cycle": number, "level": "REVIEW",
                             "reason": "RECOVERY_ATTEMPT_RECORDED"})
            if len(recent_recovery) >= 3:
                findings.append({"cycle": number, "level": "ESCALATE_TO_OPERATOR",
                                 "reason": "REPEATED_RECOVERY_NOTICES"})
                recent_recovery = []
    counts = {}
    for f in findings:
        counts[f["reason"]] = counts.get(f["reason"], 0) + 1
    return {"mode": "OFFLINE_SHADOW_DIAGNOSTIC",
            "source_file": data.get("source_file"),
            "cycles": len(cycles),
            "findings": findings, "counts": counts,
            "physical_actions": 0, "model_calls": 0,
            "limitations": [
                "Findings are diagnostics, not reconstructed L3 decisions.",
                "Recorded ultrasonic validity and GPS accuracy are incomplete safety evidence.",
                "Repeated recovery notices are not proof of repeated physical reverse motion.",
                "No timestamp-based latency or progress analysis; cycle indices only.",
                "No mission/POI association and no physical navigation authorization."]}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("normalized_json")
    p.add_argument("--output", required=True)
    args = p.parse_args(argv)
    source = Path(args.normalized_json)
    output = Path(args.output)
    if output.exists():
        p.error("Refusing to overwrite output")
    result = analyze(json.loads(source.read_text(encoding="utf-8")))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(json.dumps({k: result[k] for k in
                      ("mode", "source_file", "cycles", "counts",
                       "physical_actions", "model_calls")},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
