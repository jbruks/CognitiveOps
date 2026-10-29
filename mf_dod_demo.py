"""Executable offline multi-objective MF-DoD demonstration (no rover devices).

Run: python -m mf_dod_demo
All navigation/evidence are explicitly synthetic. No OpenAI or PDF claims.
"""
import json

from doctrine_service import DoctrineService, DoctrinePassage
from l3_models import NavigationObjective, NavigationResult, NavigationStatus
from llm.llm_service import LLMService
from mf_dod_mission import MissionOrchestrator, MissionEvidence


def build_plan():
    # Illustrative test coordinates, not actual approved geographic positions.
    objectives = [
        NavigationObjective("LAB-Z1", 39.0, -0.6, purpose="Inspect surface"),
        NavigationObjective("LAB-Z2", 39.0001, -0.6001, purpose="Inspect access"),
        NavigationObjective("LAB-Z3", 39.0002, -0.6002, purpose="Inspect facilities"),
    ]
    questions = {
        "LAB-Z1": "Are visible surface obstructions present?",
        "LAB-Z2": "Is the access visibly passable?",
        "LAB-Z3": "Are any exterior conditions visible?",
    }
    # Only an illustrative passage, not a verified quotation from a PDF.
    doctrine = DoctrineService([
        DoctrinePassage(
            source="LAB-EXAMPLE: inspection checklist (synthetic)",
            text="Record observations, uncertainty and limitations during inspection.",
            locator=None, verified=False,
        )
    ])
    # Reuse L4's actual preparation function, but with no actuation.
    from l4_mission_planner import L4MissionPlanner
    from l4_models import Mission, MissionTask
    from unittest.mock import patch

    class NoHardware:
        def get_state(self):
            raise RuntimeError("No rover access in offline demo")

    with patch.object(L4MissionPlanner.__init__.__globals__["os"], "makedirs"):
        planner = L4MissionPlanner(
            perception_module=object(),
            l1_rover_controler=NoHardware(),
            task_planner=object(),
            memory_system=object(),
            mission=Mission(MissionTask.GOTO, target_lat=39.0, target_lon=-0.6),
            llm_service=LLMService(backend="stub"),
        )
    return planner.prepare_inspection_plan(
        "Inspect visible surface, facilities and access. Record observations and uncertainty.",
        objectives, questions, doctrine,
    )


def run_demo():
    engine = MissionOrchestrator(build_plan())
    while (objective := engine.next_objective()) is not None:
        if objective.objective_id == "LAB-Z2":
            engine.accept_navigation(NavigationResult(
                objective.objective_id, NavigationStatus.BLOCKED,
                distance_remaining_m=15.0, reason="SYNTHETIC_PERSISTENT_BLOCK"))
        else:
            engine.accept_navigation(NavigationResult(
                objective.objective_id, NavigationStatus.COMPLETED,
                distance_remaining_m=1.0))
            if objective.objective_id == "LAB-Z1":
                engine.record_evidence(MissionEvidence(
                    objective.objective_id,
                    "Synthetic lab observation: no obstruction detected",
                    observed=True, confidence=0.8, image_ref="synthetic://Z1"))
            # LAB-Z3 deliberately has no observations.
    engine.finish_unobserved()
    return engine.report()


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2, ensure_ascii=False))
