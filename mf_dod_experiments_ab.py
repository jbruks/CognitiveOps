"""MF-DoD experiments A/B: context-adaptive plans and closed-loop lab replanning.

All observations and navigation results are synthetic. No rover imports or
physical commands. GPT can only permute already-approved remaining objectives.
"""
import argparse
import json

from l3_models import NavigationObjective, NavigationResult, NavigationStatus
from llm.llm_service import LLMService
from mf_dod_mission import InspectionObjective, InspectionPlan, MissionOrchestrator


INTENT = "Inspect approved areas and report any areas that cannot be verified."


def authorized_targets():
    return [
        NavigationObjective("LAB-RUNWAY", 39.0, -0.6, purpose="Inspect runway"),
        NavigationObjective("LAB-EAST", 39.0001, -0.6001, purpose="Inspect eastern access"),
        NavigationObjective("LAB-FACILITIES", 39.0002, -0.6002,
                            purpose="Inspect exterior facilities"),
        NavigationObjective("LAB-WEST", 39.0003, -0.6003, purpose="Inspect western access"),
    ]


def _options(targets):
    return [{"objective_id": x.objective_id, "purpose": x.purpose} for x in targets]


def scenario_plan(service, scenario, restrictions):
    """Compare context-sensitive decisions without assuming GPT must reorder."""
    targets = authorized_targets()
    advice = service.plan_objectives(
        INTENT, _options(targets),
        {"scenario": scenario, "restrictions": restrictions,
         "authority": "Order only the supplied approved objectives; "
                      "constraints are advisory, not new movement permissions."},
    )
    return {"scenario": scenario, "restrictions": restrictions,
            "order": advice.output["objective_ids"],
            "reason": advice.output["reason"], "provider": advice.provider,
            "model": advice.model}


def compare_scenarios(service):
    return [
        scenario_plan(service, "normal",
                      {"east_glare": False, "temporary_access_limit": None}),
        scenario_plan(service, "restricted",
                      {"east_glare": True, "temporary_access_limit": "LAB-EAST",
                       "note": "Delay eastern observations if useful; do not "
                               "claim the access is safe or open."}),
    ]


def run_replanning(service):
    """L4 plan -> simulated blockage -> L3 advice -> L4 reorders remaining only."""
    targets = authorized_targets()
    initial = service.plan_objectives(
        INTENT, _options(targets), {"scenario": "blocked route exercise"})
    by_id = {t.objective_id: t for t in targets}
    plan = InspectionPlan(
        INTENT,
        [InspectionObjective(by_id[oid], "Record visible limitations")
         for oid in initial.output["objective_ids"]],
        decisions=[{"event": "PLAN_CREATED", "order": initial.output["objective_ids"],
                    "provider": initial.provider, "reason": initial.output["reason"]}],
    )
    engine = MissionOrchestrator(plan)
    goal = engine.next_objective()
    # Synthetic obstruction on the first approved goal, whichever GPT chooses.
    blocked_id = goal.objective_id
    engine.accept_navigation(NavigationResult(
        blocked_id, NavigationStatus.BLOCKED, 9.0, "SYNTHETIC_BLOCKAGE"))
    review = service.infer(
        "L3",
        "Rover is stopped at a simulated obstruction. Respond HOLD or "
        "REQUEST_L4_REPLAN only; do not propose motion commands.",
        {"blocked_objective_id": blocked_id,
         "operator_authorized_to_move": False,
         "reason": "SYNTHETIC_BLOCKAGE"},
        ("HOLD", "REQUEST_L4_REPLAN"),
    )
    decision = review.output["decision"]
    plan.decisions.append({
        "event": "L3_REVIEW", "decision": decision,
        "reason": review.output["reason"], "provider": review.provider,
        "action_executed": False,
    })
    if decision == "REQUEST_L4_REPLAN":
        remaining = [o for o in plan.objectives if o.status.value == "PENDING"]
        if remaining:
            advice = service.plan_objectives(
                INTENT, _options([o.navigation for o in remaining]),
                {"event": "PERSISTENT_BLOCK", "blocked_id": blocked_id,
                 "prior_decisions": list(plan.decisions),
                 "instruction": "Reorder only remaining approved objectives; "
                                "blocked objectives cannot be retried."},
            )
            by_remaining = {o.navigation.objective_id: o for o in remaining}
            reordered = [by_remaining[oid] for oid in advice.output["objective_ids"]]
            # Safety: preserve terminal records and avoid duplicate objectives.
            terminal = [o for o in plan.objectives if o.status.value != "PENDING"]
            plan.objectives = terminal + reordered
            plan.decisions.append({
                "event": "L4_REPLAN", "order": advice.output["objective_ids"],
                "reason": advice.output["reason"], "provider": advice.provider,
                "excluded_blocked_id": blocked_id, "action_executed": False,
            })
    else:
        plan.decisions.append({
            "event": "L4_REPLAN_SKIPPED", "reason": "L3 requested HOLD",
            "action_executed": False,
        })
    # No further navigation occurs without approval; remaining areas unverified.
    engine.finish_unobserved()
    report = engine.report()
    report["blocked_id"] = blocked_id
    report["simulation_only"] = True
    report["physical_actions"] = 0
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("stub", "openai"), default="stub")
    parser.add_argument("--model")
    parser.add_argument("--allow-api", action="store_true")
    args = parser.parse_args(argv)
    if args.backend == "openai" and (not args.allow_api or not args.model):
        parser.error("OpenAI requires --allow-api and --model")
    if args.allow_api and args.backend != "openai":
        parser.error("--allow-api requires --backend openai")
    service = LLMService(backend=args.backend, model=args.model)
    print(json.dumps({"comparison": compare_scenarios(service),
                      "replanning": run_replanning(service)},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
