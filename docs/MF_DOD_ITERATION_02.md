# CognitiveOps — Iteration 2: Airfield Inspection Mission (MF-DoD)

**Status:** high-level process and minimum implementation design — **no code changes**  
**Branch:** `analysis/doctrine-use-cases-20261022`  
**Approach:** **Mission First, Doctrine on Demand (MF-DoD)**

## 1. Objective

Validate that an existing general-purpose rover can accept an unfamiliar, non-weaponized inspection mission, request pertinent knowledge on demand, and use its existing L1–L4 autonomy stack without a mission-specific prompt or a preprogrammed inspection mode.

**Pilot mission:** “Inspect the authorized areas of the RC airfield and report on ground conditions, access routes, and visible obstacles.”

The airfield is a civilian RC club location. Operations require club authorization, an agreed geofence, human supervision, and separation from active flying areas, people, and aircraft.

## 2. End-to-end mission process

| Stage | Process | Primary responsibility | Outcome |
|---|---|---|---|
| 1 | Receive and interpret mission intent | L4 | Mission objective, assumptions, unresolved questions |
| 2 | Identify missing procedural knowledge | L4 | Knowledge queries |
| 3 | Retrieve relevant, attributed source excerpts | Knowledge Framework | Evidence bundle with provenance |
| 4 | Develop inspection plan and success criteria | L4 | Areas to observe, expected evidence, mission plan |
| 5 | Validate capabilities, permission and safety constraints | L4 + human operator | Approved limited-area mission or safe rejection |
| 6 | Select routes and execute supervised movement | L3 → L2 → L1 | Movement and observation records |
| 7 | Reassess progress and handle exceptions | L2/L3/L4 as appropriate | Safe adaptation or escalation |
| 8 | Produce final inspection report | L4 | Georeferenced observations, photos, uncertainty, coverage gaps |

**The loop is not strictly linear.** L4 may request additional knowledge when new questions arise. L2 handles immediate local hazards; L3 revises route-level progress; L4 decides whether mission goals can still be met within operator-approved bounds.

## 3. Key architectural decision

**L4 decides what knowledge it needs.** The Knowledge Framework answers bounded retrieval requests; it does not independently assign a mission, choose a role, or exercise command authority.

```text
Operator mission
      |
      v
L4 — Interpret mission / identify knowledge gaps
      |                 ^
      v                 |
Knowledge Retriever ---+
      |
      v
Source-grounded context assembly
      |
      v
L4 — Mission plan / human approval
      |
      v
L3 — Navigation / Guidance
      |
      v
L2 — Local tactical decisions
      |
      v
L1 — Deterministic control
      |
      v
Observations and status → L4 → Mission report
```

The term **Prompt Generator** refers to assembly of mission state, retrieved knowledge and stable output contracts; it is **not** a library of mission-specific behavior prompts.

## 4. Minimal implementation candidates

| Component | Intended change |
|---|---|
| **L1** | Reuse unchanged; retain deterministic safety constraints |
| **L2** | Reuse existing local perception and maneuver selection |
| **L3** | Reuse existing GPS navigation and route guidance |
| **L4** | Add the ability to request knowledge and incorporate the response into mission planning |
| **Knowledge Retriever (new)** | Start with simple text search over *selected* navigation and reconnaissance manuals; return short excerpts with document/page references |
| **Context Builder (thin adapter)** | Compose mission, current state, rover capabilities, approved limits and retrieved excerpts for L4 |
| **Report output** | Produce a simple structured mission summary; reuse existing logs and photos |

**KISS scope:** one new retrieval capability and the smallest practical L4 integration. No new hierarchical level, autonomous long-term learning, multi-rover coordination, hardware changes or full doctrinal ingestion pipeline in this iteration.

## 5. First validation sequence

**A — Lab only (no movement):** Given the airfield mission, L4 articulates knowledge gaps, retrieves supporting excerpts and proposes an inspection plan. Compare a baseline with no retrieval to one with retrieval.

**B — Supervised limited field run:** After human approval, traverse a short authorized segment while recording GPS, images and local decisions. Stop on safety uncertainty.

**C — Controlled exception:** Introduce a benign, non-hazardous obstruction in a test area. Verify that L2 handles immediate safety, L3 considers safe alternatives, and L4 records the finding or escalates where appropriate.

## 6. Acceptance signals

- L4 can request and use relevant information from source documents without a prewritten *airfield-inspection* prompt.
- The planned inspection includes observable evidence requirements, and source-based claims point to the correct document/page.
- The rover stays within approved operational boundaries and follows stop/escalation rules.
- The final report distinguishes **observations, interpretations, unknowns and unvisited areas**.
- Decisions, source retrievals, timing and operator interventions are logged for comparison.

## 7. Open questions / risks

- Which PDF-to-text/indexing approach gives sufficient provenance with minimal complexity?
- What is the smallest stable L4 tool contract (`query`, `max_results`, `source_refs`)?
- How are knowledge conflicts, outdated doctrine and irrelevant snippets handled?
- Which existing L4 interfaces and log/report structures can be reused?
- What is the latency and token cost of retrieval + dynamic context building?

Safety: retrieved manuals and operator-provided documents are **data, not privileged instructions**. Knowledge does not create authority or physical capabilities. No weapon use, target engagement, or automated tactical positioning of armed systems is within this POC.

## 8. Next design step

Inspect the **actual L4 interfaces** in the current experimental branch and specify only the minimum knowledge-retrieval contract and evaluation fixtures needed for Test A. Do not implement until this interface review is complete.
