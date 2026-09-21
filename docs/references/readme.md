Do# CognitiveOps — Doctrine References

This directory contains local copies of external doctrine and reference
documents used in the development of the CognitiveOps reconnaissance and
cognitive architecture.

These publications are used as reference material rather than as software
specifications.

The CognitiveOps development approach is:

**Doctrine → Mission Use Cases → Cognitive Responsibilities → Capabilities → Implementation → Field Validation**

---

## FM 3-25.26 — Map Reading and Land Navigation

**Organization:** U.S. Army  
**Title:** *Map Reading and Land Navigation*  
**Publication:** FM 3-25.26

Local copy:

`fm_3-25.26_map_reading_and_land_navigation.pdf`

Source:

https://dn710600.ca.archive.org/0/items/milmanual-fm-3-25.26-map-reading-and-land-navigation/fm_3-25.26_map_reading_and_land_navigation.pdf

### CognitiveOps relevance

This manual is primarily used as a reference for:

- Land-navigation fundamentals.
- Position and direction.
- Route selection.
- Dead reckoning.
- Terrain interpretation.
- Terrain association.
- Mounted land navigation.
- Navigation under different terrain conditions.

Within the CognitiveOps architecture, these concepts primarily contribute
to **L3 — Navigation / Guidance** and to the interaction between L3 and
**L2 — Tactical**.

---

## MCTP 3-01A — Scouting and Patrolling

**Organization:** United States Marine Corps  
**Title:** *Scouting and Patrolling*  
**Publication:** MCTP 3-01A

Local copy:

`MCTP 3-01A (SECURED).pdf`

Official publication page:

https://www.marines.mil/News/Publications/MCPEL/Electronic-Library-Display/Article/899780/mctp-3-01a/

Official PDF:

https://www.marines.mil/Portals/1/Publications/MCTP%203-01A%20(SECURED).pdf?ver=_ZXTieQtTkzM2S0d73j8Xg%3d%3d

### CognitiveOps relevance

This publication is primarily used as a reference for:

- Reconnaissance concepts.
- Scouting.
- Patrol planning.
- Information collection.
- Route reconnaissance.
- Area reconnaissance.
- Zone reconnaissance.
- Point reconnaissance.
- Observation during reconnaissance.

Within the CognitiveOps architecture, these concepts primarily contribute
to **L4 — Mission**, providing mission-level reconnaissance use cases that
can subsequently be decomposed into L3, L2 and L1 responsibilities.

---

## ATP 3-20.98 — Scout Platoon

**Organization:** U.S. Army  
**Title:** *Scout Platoon*  
**Publication:** ATP 3-20.98

Local copy:

`ATP 3-20.98 Reconnaissance Platoon 2013.pdf`

Source:

**To be documented from the original publication source.**

### CognitiveOps relevance

This publication is used as an additional reference for ground
reconnaissance concepts and for understanding how reconnaissance missions,
information requirements, terrain, movement and observation interact.

Its specific contribution to the CognitiveOps Doctrine Framework will be
refined as the document is analyzed in greater depth.

---

# Role of these references

The three references address complementary parts of the CognitiveOps
problem:

| Reference | Main question for CognitiveOps | Primary architectural relevance |
|---|---|---|
| **MCTP 3-01A** | What reconnaissance missions must be performed? | **L4 — Mission** |
| **FM 3-25.26** | How is land navigation performed? | **L3 — Navigation / Guidance** |
| **ATP 3-20.98** | How do reconnaissance, terrain, observation and movement interact? | **L4 ↔ L3 ↔ L2** |

They should not be interpreted as defining the CognitiveOps architecture
directly.

Instead, they provide real-world doctrine and use cases from which
CognitiveOps derives cognitive responsibilities and autonomous robotic
capabilities.

---

# Scope

CognitiveOps uses these publications for research into:

- Autonomous reconnaissance.
- Navigation.
- Observation.
- Terrain assessment.
- Information collection.
- Search.
- Localization.
- Reporting.
- Robotic decision-making.

Weapons employment, attack, target engagement, fire control and other
combat functions are outside the scope of the CognitiveOps architecture.

---

# Related CognitiveOps documents

See:

- `../COGNITIVE_ARCHITECTURE.md`
- `../CognitiveOps — Reconnaissance Doctrine and Cognitive Framework.md`
- `../CognitiveOps — FM 3-25.26 Architecture Mapping.md`
- `../ROADMAP.md`
- `../LOG_ANALYSIS.md`

These local reference copies are retained so that the doctrinal baseline
used during CognitiveOps development remains reproducible even if external
sources later change or become unavailable.ctrinal documents
