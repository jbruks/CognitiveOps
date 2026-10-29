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

## Cognitive live-GPT and local-document extension (pending workstation verification)

The implementation also includes `mf_dod_cognitive_demo.py`, with **no hardware imports or calls**.

```bash
cd ~/RoverGit-mf-dod
source ~/RoverGit/.venv/bin/activate
git pull --ff-only

# All offline tests, without an OpenAI request:
python -m unittest -v tests/test_shared_inference_service.py tests/test_mf_dod_skeleton.py tests/test_mf_dod_mission.py tests/test_mf_dod_memory_reasoning.py tests/test_mf_dod_cognitive_demo.py

# Offline cognitive integration with deterministic simulated L4/L3 advice:
python -m mf_dod_cognitive_demo

# Optional local PDFs (requires "pip install pypdf" in the virtualenv):
python -m mf_dod_cognitive_demo --pdf "/absolute/path/manual.pdf"

# Only after verifying credentials and accepting billable API requests:
# export OPENAI_API_KEY=...  # NEVER commit credentials or post the key
python -m mf_dod_cognitive_demo --backend openai --allow-api --model gpt-5.4 --pdf "/absolute/path/manual.pdf"
```

The OpenAI demo makes **two requests**: one L4 ordering of approved goals and one L3 evaluation of a **synthetic** blockage. No motor commands are possible via this module. The demo does not drive or connect to the physical rover; L3's actual `step()` and L4's physical `step()` remain distinct. The L3 request can only return `HOLD` or `REQUEST_L4_REPLAN`, and even a replan request is only logged.

PDF ingestion uses `pypdf` and labels extracted fragments `PDF page N` (1-based physical page order). This is **not a verified printed page citation** and is not OCR. Non-extractable scans and missing PDFs are not silently replaced with made-up citations. Operator must provide the actual PDF file paths; the documented two manuals have not yet been validated as local sources.

For this specific demo, the L4 output is a validated order of previously approved objectives, **not arbitrary geographic mission planning**, and the navigation/observations are still synthetic. Do not take `completed: true` as full verified inspection: inaccessible and unverified zones remain in the output.

## Experiments A/B: contextual planning and closed-loop simulated replanning

File: `mf_dod_experiments_ab.py`. All geographic targets are synthetic LAB coordinates. It **never invokes motor control**.

**Experiment A** asks L4 to order the same approved objectives under two different constraints: ordinary conditions, and eastward glare plus a temporary access limitation. We record order, reason and supplied constraints. A change in order is *not* required to pass tests; the experiment assesses context sensitivity of actual GPT advice, not guaranteed novelty.

**Experiment B** asks L4 to plan, simulates a blockage at the first selected goal, asks L3 to recommend either `HOLD` or `REQUEST_L4_REPLAN`, then calls L4 again only on the latter. The replan may permute only remaining previously approved objectives. The blocked objective remains `INACCESSIBLE`, and pending items remain `UNVERIFIED`, because the experiment deliberately performs no additional navigation. It records `physical_actions: 0`.

```bash
cd ~/RoverGit-mf-dod
git pull --ff-only
python -m unittest -v tests/test_mf_dod_experiments_ab.py
python -m mf_dod_experiments_ab
# Requires existing OPENAI_API_KEY; may incur API charges.
python -m mf_dod_experiments_ab --backend openai --allow-api --model gpt-5.4
```

Live mode makes two scenario calls, one initial plan call, one L3 review call and (only if requested) one L4 replan call: **four or five model requests total**. It does not invoke the real rover stack, does not validate actual navigation alternatives, and does not attach PDF doctrine. Tests use a mocked API client and require no network.

## Doctrine on Demand controlled A/B — added, awaiting PDF sources and tests

Entrypoint: `mf_dod_doctrine_experiment.py`. Same mission, restrictions and approved objectives in both arms. The only varied input is retrieved doctrine text (plus a mode marker indicating its presence). The model may change the order and reasoning, but it must not add or omit destinations.

```bash
cd ~/RoverGit-mf-dod
source ~/RoverGit/.venv/bin/activate
git pull --ff-only
python -m unittest -v tests/test_mf_dod_doctrine_experiment.py

# Empty-source baseline: intentionally reports NO_MATCHES_OR_SOURCES
python -m mf_dod_doctrine_experiment

# With one or more actual local PDF paths, requires pypdf
python -m pip install pypdf
python -m mf_dod_doctrine_experiment --pdf "/absolute/path/to/manual.pdf"

# After verifying PDF extraction, optional billable GPT comparison
python -m mf_dod_doctrine_experiment --backend openai --allow-api \
  --model gpt-5.4 --pdf "/absolute/path/to/manual.pdf"
```

**Source inventory caveat:** GitHub code search on the default branch did not surface the referenced manuals; it does not conclusively inventory binary assets in the feature branch. No original PDF file has been downloaded, extracted or verified here. Operator must supply actual PDF paths before claiming Doctrine on Demand with genuine sources. Citation `PDF page N` refers to physical PDF page index, not printed manual pagination. Retrieval is basic lexical overlap; relevance and whether the doctrinal input *improves* planning require manual examination, not merely a changed objective order.

The experiment reports `with_doctrine: null` if no relevant passages are found. It does not connect to hardware or execute navigation. Live use incurs one API call without matches or two with matches.


### Reference PDF discovery

The Doctrine A/B experiment now discovers all `*.pdf` files in `docs/references/` by default. Explicit `--pdf` arguments override auto-discovery. Four manuals were confirmed on the operator's machine: `MCTP 3-01A (SECURED).pdf`, `MCRP 3-34.3 (W CH 1) (SECURED).pdf`, `ATP 3-20.98 Reconnaissance Platoon 2013.pdf`, and `fm_3-25.26_map_reading_and_land_navigation.pdf`. The secured files may require decryption or raise extraction errors; their content has not yet been inspected. To limit cost and avoid protected files, pass `--pdf docs/references/fm_3-25.26_map_reading_and_land_navigation.pdf` explicitly. The generated PDF page labels are indices, not verified printed references.
