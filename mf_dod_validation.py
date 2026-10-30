"""Offline cognitive validation: reuse mission memory, doctrine and operator evidence.

Reads reviewed proposals; never actuates or infers visual evidence from arrival.
"""
import argparse
import json
from pathlib import Path

from doctrine_service import DoctrineService
from llm.llm_service import LLMService
from l3_models import NavigationResult, NavigationStatus
from mission_package import MissionPackage
from mf_dod_mission import (InspectionPlan, InspectionObjective, MissionOrchestrator,
                            MissionEvidence)
from mf_dod_integrated_agent import MissionJournal, load_proposals


def validate(package, proposals, service, approved_ids, prior_events=(),
             evidence=None, doctrine=None, blocked_poi=None, journal=None):
    evidence = {} if evidence is None else evidence
    doctrine = doctrine or DoctrineService()
    journal = journal or MissionJournal()
    approved = package.approve(proposals, approved_ids)
    if not isinstance(evidence, dict) or not set(evidence).issubset(
            {o.objective_id for o in approved}):
        raise ValueError("Evidence must target approved objectives only")
    for value in evidence.values():
        if (not isinstance(value, dict)
                or set(value) != {"description", "observed", "source_ref"}
                or not isinstance(value["description"], str)
                or not value["description"].strip()
                or type(value["observed"]) is not bool
                or not isinstance(value["source_ref"], str)
                or not value["source_ref"].strip()):
            raise ValueError("Operator evidence requires description, observed and source_ref")
    blocked_history = [
        row["poi_id"] for row in prior_events
        if isinstance(row, dict)
        and row.get("event") == "L3_NAVIGATION_FEEDBACK"
        and row.get("status") == "BLOCKED"
        and row.get("poi_id") in package.pois
    ][-10:]
    hits = doctrine.retrieve(
        "inspection observation terrain navigation access uncertainty", limit=3)
    citations = [doctrine.provenance(h) for h in hits]
    ids = [o.objective_id for o in approved]
    reason = "No previous blocked POI; retained approved order"
    if blocked_history and len(approved) > 1:
        advice = service.plan_objectives(
            package.intent,
            [{"objective_id": o.objective_id,
              "purpose": o.purpose,
              "poi_id": next(p.poi_id for p in proposals
                             if p.objective_id == o.objective_id)}
             for o in approved],
            {"prior_blocked_pois": blocked_history,
             "history_is_not_current_observation": True,
             "doctrine_excerpts": citations,
             "reorder_approved_objectives_only": True})
        ids = advice.output["objective_ids"]
        reason = advice.output["reason"]
    journal.record("L4_CONTEXT_REVIEW", prior_blocked_pois=blocked_history,
                   order=ids, reason=reason,
                   doctrine_sources=[{"source": c["source"], "locator": c["locator"]}
                                    for c in citations])
    by_id = {o.objective_id: o for o in approved}
    questions = {p.objective_id: p.question for p in proposals}
    plan = InspectionPlan(
        package.intent,
        [InspectionObjective(by_id[i], questions[i]) for i in ids],
        doctrine=citations)
    orchestrator = MissionOrchestrator(plan)
    while (objective := orchestrator.next_objective()) is not None:
        poi_id = next(p.poi_id for p in proposals
                      if p.objective_id == objective.objective_id)
        is_blocked = blocked_poi == poi_id
        result = NavigationResult(
            objective.objective_id,
            NavigationStatus.BLOCKED if is_blocked else NavigationStatus.COMPLETED,
            10.0 if is_blocked else 1.0,
            "SYNTHETIC_OBSTRUCTION" if is_blocked else None)
        orchestrator.accept_navigation(result)
        journal.record("L3_NAVIGATION_FEEDBACK", objective_id=objective.objective_id,
                       poi_id=poi_id, status=result.status.value, reason=result.reason)
        if result.status == NavigationStatus.COMPLETED and objective.objective_id in evidence:
            item = evidence[objective.objective_id]
            orchestrator.record_evidence(
                MissionEvidence(objective.objective_id, item["description"],
                                item["observed"],
                                limitation=None if item["observed"]
                                else "OPERATOR_COULD_NOT_VERIFY"))
            journal.record("OPERATOR_EVIDENCE", objective_id=objective.objective_id,
                           source_ref=item["source_ref"], observed=item["observed"],
                           description=item["description"])
    orchestrator.finish_unobserved()
    report = orchestrator.report()
    report.update({"simulation_only": True, "physical_actions": 0,
                   "execution_order": ids, "prior_blocked_pois": blocked_history,
                   "events": journal.events, "doctrine_context": citations,
                   "attribution_status": "SOURCE_LOCATORS_ONLY_NOT_CLAIM_VERIFIED"})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--load-proposals", required=True)
    parser.add_argument("--approve", nargs="+", required=True)
    parser.add_argument("--prior-journal")
    parser.add_argument("--journal")
    parser.add_argument("--evidence", help="Operator-authored JSON mapping objective IDs to evidence")
    parser.add_argument("--block-poi", help="POI to block in simulated navigation")
    parser.add_argument("--pdf", action="append", default=[])
    parser.add_argument("--backend", choices=["stub", "openai"], default="stub")
    parser.add_argument("--model")
    parser.add_argument("--allow-api", action="store_true")
    args = parser.parse_args(argv)
    if args.backend == "openai" and (not args.allow_api or not args.model):
        parser.error("OpenAI requires --allow-api --model")
    if args.allow_api and args.backend != "openai":
        parser.error("--allow-api requires --backend openai")
    if args.prior_journal and args.journal and Path(args.prior_journal).resolve() == Path(args.journal).resolve():
        parser.error("Prior and current journals must differ")
    package = MissionPackage.load(args.manifest)
    proposals = load_proposals(args.load_proposals, package)
    prior = MissionJournal(args.prior_journal).events if args.prior_journal else []
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8")) if args.evidence else {}
    doctrine = DoctrineService.from_pdf_paths(args.pdf) if args.pdf else DoctrineService()
    service = LLMService(backend=args.backend, model=args.model)
    result = validate(package, proposals, service, args.approve, prior, evidence,
                      doctrine, args.block_poi, MissionJournal(args.journal))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
