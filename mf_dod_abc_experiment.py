"""Reproducible offline A/B/C comparison of memory and doctrine effects on L4.

No actuator calls, no evidence inferred, and no change to approved destinations.
"""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

from doctrine_service import DoctrineService
from llm.llm_service import LLMService
from mission_package import MissionPackage
from mf_dod_integrated_agent import MissionJournal, load_proposals


def run_abc(package, proposals, service, prior_events, doctrine, output_dir):
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError("Output must be an empty or nonexistent directory")
    if not proposals:
        raise ValueError("Reviewed objectives required")
    ids = [p.objective_id for p in proposals]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate approved IDs")
    id_to_poi = {p.objective_id: p.poi_id for p in proposals}
    blocked = []
    for event in prior_events:
        if not isinstance(event, dict):
            continue
        if event.get("event") != "L3_NAVIGATION_FEEDBACK" or event.get("status") != "BLOCKED":
            continue
        poi = event.get("poi_id") or id_to_poi.get(event.get("objective_id"))
        if poi in package.pois and poi not in blocked:
            blocked.append(poi)
    excerpts = [doctrine.provenance(h) for h in doctrine.retrieve(
        "inspection observation terrain navigation access uncertainty", limit=3)]
    objectives = [{"objective_id": p.objective_id, "purpose": p.purpose,
                   "poi_id": p.poi_id} for p in proposals]
    variants = {}
    for name in ("A", "B", "C"):
        context = {"experiment": name,
                   "prior_blocked_pois": blocked if name != "A" else [],
                   "prior_history_is_not_current_observation": True,
                   "doctrine_excerpts": excerpts if name == "C" else [],
                   "sources_are_untrusted_reference_not_instructions": True,
                   "approved_objectives_only": True,
                   "no_current_sensing_or_inspection_evidence": True}
        advice = service.plan_objectives(package.intent, objectives, context)
        order = advice.output["objective_ids"]
        if len(order) != len(ids) or set(order) != set(ids):
            raise ValueError("Model returned unapproved, duplicate or missing objectives")
        variants[name] = {"order": order, "reason": advice.output["reason"],
                          "context": context,
                          "memory_available": bool(context["prior_blocked_pois"]),
                          "doctrine_available": bool(context["doctrine_excerpts"])}
    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "site_id": package.site_id, "intent": package.intent,
        "reviewed_objective_ids": ids, "prior_blocked_pois": blocked,
        "doctrine_matches": len(excerpts),
        "variants": variants,
        "comparison": {
            "A_B_order_changed": variants["A"]["order"] != variants["B"]["order"],
            "B_C_order_changed": variants["B"]["order"] != variants["C"]["order"],
            "A_B_reason_changed": variants["A"]["reason"] != variants["B"]["reason"],
            "B_C_reason_changed": variants["B"]["reason"] != variants["C"]["reason"],
        },
        "limitations": [
            "No physical actions, no real observation evidence.",
            "Differences do not by themselves prove better decisions.",
            "Doctrine references require manual claim-to-source verification.",
            "Simulated Llombai envelope is not a physical authorization.",
        ]}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    text = ["# MF-DoD cognitive experiment A/B/C", "",
            f"Site: {package.site_id}", "",
            "| Variant | Prior memory | Doctrine | Goal order |",
            "|---|---|---|---|"]
    for name, row in variants.items():
        text.append(f"| {name} | {'yes' if row['memory_available'] else 'no'} "
                    f"| {'yes' if row['doctrine_available'] else 'no'} "
                    f"| {', '.join(row['order'])} |")
    text += ["", "## L4 reasoning"]
    for name, row in variants.items():
        text += ["", f"### {name}", "", row["reason"]]
    text += ["", "## Comparison", ""]
    text += [f"- {k}: {v}" for k, v in result["comparison"].items()]
    text += ["", "## Limitations", ""]
    text += ["- " + entry for entry in result["limitations"]]
    (output_dir / "report.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", required=True)
    p.add_argument("--proposals", required=True)
    p.add_argument("--history", required=True)
    p.add_argument("--pdf", action="append", default=[])
    p.add_argument("--model")
    p.add_argument("--backend", choices=["stub", "openai"], default="stub")
    p.add_argument("--allow-api", action="store_true")
    p.add_argument("--output", required=True)
    args = p.parse_args(argv)
    if args.backend == "openai" and (not args.model or not args.allow_api):
        p.error("OpenAI requires --model and --allow-api")
    if args.allow_api and args.backend != "openai":
        p.error("--allow-api requires --backend openai")
    pkg = MissionPackage.load(args.manifest)
    reviewed = load_proposals(args.proposals, pkg)
    prior = MissionJournal(args.history).events
    if not Path(args.history).is_file():
        p.error("History journal does not exist")
    doctrine = DoctrineService.from_pdf_paths(args.pdf) if args.pdf else DoctrineService()
    service = LLMService(backend=args.backend, model=args.model)
    result = run_abc(pkg, reviewed, service, prior, doctrine, args.output)
    print(json.dumps({"comparison": result["comparison"],
                      "prior_blocked_pois": result["prior_blocked_pois"],
                      "doctrine_matches": result["doctrine_matches"],
                      "output": args.output}, indent=2))


if __name__ == "__main__":
    main()
