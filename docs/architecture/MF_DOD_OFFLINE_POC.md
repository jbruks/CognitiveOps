# MF-DoD — Offline Cognitive POC (implementation checkpoint)

**Branch:** `feature/mf-dod-cognitive-architecture`  
**Starting checkpoint:** `2e72fb1` (9 prior tests passed on user laptop).  
**Hardware boundary:** no L1, L2, VisionNN or RA4M1 changes in this block.

## What the offline demonstration actually does

- Reuses the existing L4 planner to prepare a multi-objective inspection plan from operator-supplied approved `NavigationObjective` records.
- Gives L4 an ordered list of objectives from the shared LLM service. Stub mode preserves input order; optional OpenAI mode can propose a different order but responses are validated as an exact permutation of approved IDs.
- Includes a minimal `DoctrineService` that searches *already-extracted passages* and returns source, locator, verification flag and excerpt. **It has not parsed the repository PDFs or verified their page references.**
- Uses `MissionOrchestrator` to track navigation results, evidence and status. Arrival does not count as inspection evidence; blockage becomes inaccessible, and no evidence is fabricated.
- Adds mission/navigation event recording to the existing `MemorySystem` and bounded context composition to the existing prompt framework.
- Provides an explicit non-actuating L3 strategic review through the shared inference interface.
- Runs an illustrative three-objective offline inspection in `mf_dod_demo.py`, with synthetic navigation and evidence. One area is observed, one inaccessible, one unverified.

## Run on the laptop

```bash
cd ~/RoverGit-mf-dod
source ~/RoverGit/.venv/bin/activate
git pull --ff-only
python -m unittest -v tests/test_shared_inference_service.py tests/test_mf_dod_skeleton.py tests/test_mf_dod_mission.py tests/test_mf_dod_memory_reasoning.py
python -m mf_dod_demo
```

Expect **17 tests** (previous nine + four doctrine/mission + three memory + one full-plan validation), subject to workstation verification. `mf_dod_demo` outputs a JSON report and **does not** touch the rover.

## Deliberately incomplete

1. Document extraction and verified page-level citation from actual doctrine PDFs.
2. Interpreting arbitrary maps into *approved* navigation goals. The model cannot invent geographic permissions.
3. Real L4 scheduling on the physical `step()` loop. Current inspection mission lifecycle is an explicit offline orchestrator, while legacy GO_TO_POINT behavior remains unchanged.
4. Real image/geolocation evidence capture and review. Demo evidence is synthetic and labeled as such.
5. Validated navigation detours. L3 can request review but never autonomously chooses an unverified waypoint.
6. Real GPT model performance, latency, API error budget, invocation policies and complete fault handling.
7. End-to-end physical validation; L2 retains an automatic reverse recovery after three block cycles, which must be separately safety-reviewed before field testing.

The offline POC is a **system-integration demonstration, not a claim of autonomous site-inspection capability**. Test results must be obtained from the user's worktree before marking any related issue complete.
