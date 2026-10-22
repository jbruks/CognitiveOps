# Doctrine analysis — source catalogue

**Branch:** `analysis/doctrine-use-cases-20261022`  
**Status:** literature collection / analysis only — no rover implementation.

## Purpose

Study public doctrine as source material for *non-weaponized* rover requirements: logistics transport, environmental reconnaissance, observation, route assessment, safe arrival and parking. Separate source documents from validated use cases and from robot-level responsibilities. A manual is not automatically executable software.

## Verified references to acquire

| Domain | Reference | Official source | Status |
|---|---|---|---|
| Logistics | FM 4-0, *Sustainment Operations* (Aug 2024) | https://rdl.train.army.mil/catalog-ws/view/100.ATSC/0D7107B6-A6B7-445A-B598-253BB85CC28A-1308676390333/fm4_0.pdf | Source URL verified; PDF not yet copied |
| Logistics | MCTP 3-40F, *Distribution and Transportation Operations* | https://www.marines.mil/News/Publications/MCPEL/Electronic-Library-Display/Article/899565/mctp-3-40f/ | Official publication page verified; PDF not yet copied |
| Logistics | MCTP 3-40B, *Tactical Logistics* (2025) | https://www.marines.mil/News/Publications/MCPEL/Electronic-Library-Display/Article/899787/mctp-3-40b/ | Official publication page verified; PDF not yet copied |
| Deployment logistics | ATP 3-35, *Army Deployment and Redeployment* | https://cascom.army.mil/asrp/doctrine-pubs.html | Official index reference; access and edition to check |
| Reconnaissance | MCTP 3-01A, *Scouting and Patrolling* | Existing copy in `docs/references/` | Existing baseline |
| Reconnaissance | ATP 3-20.98, *Scout Platoon* | Existing copy in `docs/references/` | Existing baseline |
| Navigation | FM 3-25.26, *Map Reading and Land Navigation* | Existing copy in `docs/references/` | Existing baseline |
| Specialized observation | TC 3-22.10, *Sniper* | Official publicly accessible edition/link to verify | Bibliographic lead only; limit analysis to non-weaponized observation |
| Mobile air-defense organization | MCRP 3-20F, *Ground-Based Air Defense* (approved 2025) | https://www.marines.mil/News/Messages/Messages-Display/Article/4392026/q4fy25-and-q1fy26-approved-doctrine-and-training-publications/ | Approval notice verified; full publicly available PDF not verified |
| Air-defense historical reference | FM 3-01.44, *Short-Range Air Defense Operations* | Edition and official full-text URL to verify | Bibliographic lead only |

## Analysis boundaries

- Permitted research focus: mission decomposition, route planning, cargo handling, observation/reporting, autonomy limits, human supervision, safe mobility, platform readiness.
- Excluded from robot behaviors: weapon operation, target selection or engagement, sniper firing procedures, tactical siting/optimization of armed air-defense assets.
- Do not presume that a bibliographic reference is an acquired, reviewed, or executable document.
- No L1/L2/L3/L4 implementation changes are authorized in this branch.

## Planned artifacts

1. Use-case catalogue (logistics / reconnaissance / safe platform deployment).
2. Requirements traceability: publication → use case → cognitive responsibility → capability.
3. Gap analysis against existing L1–L4 architecture.
4. Validation scenarios, safety gates and open questions.

## Integration

The analysis branch was created from `main`. Changes can be proposed later using a pull request against `main`; do not merge automatically.
