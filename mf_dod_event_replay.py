"""No-actuation replay of recorded L3 navigation results into the L4 mission state machine.

Input is a deliberately minimal JSONL event stream from captured/normalized
navigation logs. NO physical entrypoints, camera, serial or L2 imports.
"""
import argparse
import json
from pathlib import Path

from l3_models import NavigationResult, NavigationStatus
from mf_dod_mission import InspectionObjective, InspectionPlan, MissionOrchestrator
from mf_dod_integrated_agent import load_proposals
from mission_package import MissionPackage

ALLOWED = {"COMPLETED", "BLOCKED", "FAILED"}


def replay(package, proposals, approved_ids, rows):
    approved = package.approve(proposals, approved_ids)
    if not approved:
        raise ValueError("At least one reviewed objective must be approved")
    questions = {p.objective_id: p.question for p in proposals}
    orchestrator = MissionOrchestrator(InspectionPlan(
        package.intent, [InspectionObjective(nav, questions[nav.objective_id])
                         for nav in approved]))
    consumed = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or row.get("event") != "L3_NAVIGATION_FEEDBACK":
            continue
        objective = orchestrator.next_objective()
        if objective is None:
            raise ValueError(f"Unexpected terminal feedback at event {index}")
        if row.get("objective_id") != objective.objective_id:
            raise ValueError(f"Event {index}: unexpected/out-of-order objective_id")
        status = row.get("status")
        if status not in ALLOWED:
            raise ValueError(f"Event {index}: replay accepts terminal feedback only")
        reason = row.get("reason")
        if reason is not None and not isinstance(reason, str):
            raise ValueError(f"Event {index}: invalid reason")
        result = NavigationResult(objective.objective_id,
                                  NavigationStatus(status), reason=reason)
        orchestrator.accept_navigation(result)
        consumed.append({"objective_id": objective.objective_id,
                         "status": status, "reason": reason})
    if not consumed:
        raise ValueError("No L3_NAVIGATION_FEEDBACK events in replay")
    orchestrator.finish_unobserved()
    report = orchestrator.report()
    report.update({"mode": "OFFLINE_EVENT_REPLAY", "physical_actions": 0,
                   "simulation_only": True, "events_consumed": consumed,
                   "missing_feedback": [e.navigation.objective_id
                                        for e in orchestrator.plan.objectives
                                        if e.navigation.objective_id not in
                                        {x["objective_id"] for x in consumed}],
                   "notes": "Replay checks L4 state transitions, not real GPS or motor safety."})
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", required=True)
    p.add_argument("--proposals", required=True)
    p.add_argument("--journal", required=True)
    p.add_argument("--approve", nargs="+", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args(argv)
    package = MissionPackage.load(args.manifest)
    proposals = load_proposals(args.proposals, package)
    path = Path(args.journal)
    if not path.is_file():
        p.error("Event file does not exist")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    output = Path(args.output)
    if output.exists():
        p.error("Refusing to overwrite existing replay report")
    result = replay(package, proposals, args.approve, rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(json.dumps({"mode": result["mode"],
                      "consumed": len(result["events_consumed"]),
                      "missing_feedback": result["missing_feedback"],
                      "report": str(output)}, indent=2))


if __name__ == "__main__":
    main()
