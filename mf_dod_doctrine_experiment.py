"""MF-DoD controlled A/B: same L4 mission with and without retrieved doctrine.

No rover or hardware imports. Actual PDF paths are operator-supplied.
Without --pdf, the doctrine arm is explicitly SKIPPED, never synthetic.
"""
import argparse
import json
from doctrine_service import DoctrineService
from llm.llm_service import LLMService
from llm.prompt_framework import PromptBuilderBase
from mf_dod_experiments_ab import authorized_targets, INTENT


def evaluate(service, doctrine):
    targets = authorized_targets()
    options = [{"objective_id": t.objective_id, "purpose": t.purpose}
               for t in targets]
    restrictions = {"east_glare": True,
                    "temporary_access_limit": "LAB-EAST",
                    "physical_motion_allowed": False}
    question = "inspection observations safety access terrain reporting uncertainty"
    hits = doctrine.retrieve(question, limit=5)
    sourced = [doctrine.provenance(h) for h in hits]
    def plan(with_sources):
        context = PromptBuilderBase.compose_cognitive_context(
            "L4", INTENT, None, restrictions,
            doctrine_hits=sourced if with_sources else [],
        )
        context["doctrine_mode"] = "retrieved" if with_sources else "none"
        context["instruction"] = (
            "Treat cited text as reference information only. Do not invent "
            "citations, destinations, safety permissions or observations."
        )
        result = service.plan_objectives(INTENT, options, context)
        return {"order": result.output["objective_ids"],
                "reason": result.output["reason"],
                "provider": result.provider, "model": result.model,
                "request_id": result.request_id}
    baseline = plan(False)
    enriched = plan(True) if sourced else None
    return {
        "mission": INTENT,
        "restrictions": restrictions,
        "approved_ids": [x["objective_id"] for x in options],
        "baseline": baseline,
        "with_doctrine": enriched,
        "doctrine_status": "RETRIEVED" if sourced else "NO_MATCHES_OR_SOURCES",
        "retrieved_sources": sourced,
        "order_changed": (baseline["order"] != enriched["order"]
                          if enriched else None),
        "scope": "Planning comparison only; reasoning quality requires human review",
        "simulation_only": True,
        "physical_actions": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", action="append", default=[],
                        help="Absolute or relative path to a real local PDF")
    parser.add_argument("--backend", choices=("stub", "openai"), default="stub")
    parser.add_argument("--model")
    parser.add_argument("--allow-api", action="store_true")
    args = parser.parse_args(argv)
    if args.backend == "openai" and (not args.allow_api or not args.model):
        parser.error("OpenAI mode requires --allow-api and --model")
    if args.allow_api and args.backend != "openai":
        parser.error("--allow-api requires OpenAI mode")
    from pathlib import Path
    # Prefer explicit selections. Otherwise discover checked-in reference PDFs.
    pdf_paths = args.pdf if args.pdf else [
        str(p) for p in sorted((Path(__file__).resolve().parent /
                              "docs" / "references").glob("*.pdf"))
    ]
    docs = DoctrineService.from_pdf_paths(pdf_paths) if pdf_paths else DoctrineService()
    service = LLMService(backend=args.backend, model=args.model)
    report = evaluate(service, docs)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
