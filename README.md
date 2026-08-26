

# CognitiveOps

CognitiveOps is an experimental cognitive autonomy stack for a physical
ground rover. The project explores how hierarchical cognition,
transversal perception, memory, world representation, mission intent,
and physical control can be combined in a real robotic system.

The current platform uses:

-   **Raspberry Pi** for high-level perception, cognition, planning, and
    autonomy
-   **Renesas RA4M1** microcontroller for low-level real-time rover
    control
-   **Axial SCX6 1/6** crawler platform
-   **Camera-based perception**
-   **GPS positioning**
-   **OpenCV**
-   **Multimodal LLM reasoning**

The project evolved from simulation and PIX6-based experiments into a
physical RA4M1-controlled rover.

------------------------------------------------------------------------

## Architecture

CognitiveOps is organized around two complementary structures:

1.  A **vertical L1--L4 cognitive/control hierarchy**
2.  A **transversal perception system** that provides environmental
    context across the hierarchy

Perception is **not a fifth level**. It is a shared subsystem that
observes the physical world and makes structured context available to
the cognitive and control layers.

``` text
                         COGNITIVE / CONTROL HIERARCHY

        ┌──────────────────────────────────────────────────┐
        │                  L4 — MISSION                    │
        │          Mission goals / GPS targets             │
        └──────────────────────┬───────────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────────┐
        │                    L3 — TASK                     │
        │       Task modes / cognitive reasoning          │
        └──────────────────────┬───────────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────────┐
        │                  L2 — TACTICAL                   │
        │    Multimodal reasoning / action selection      │
        └──────────────────────┬───────────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────────┐
        │                   L1 — CONTROL                   │
        │       Rover state / physical action execution   │
        └──────────────────────┬───────────────────────────┘
                               │
                               ▼
                            RA4M1
                               │
                               ▼
                        PHYSICAL ROVER


   ┌────────────────────── PERCEPTION ──────────────────────┐
   │                                                       │
   │  Camera ─┐                                            │
   │          ├──► Perception Module ───► PerceptionResult │
   │  GPS ────┘                            │               │
   │                                      ├─ perception_state
   │                                      ├─ image_bytes   │
   │                                      ├─ world_model   │
   │                                      └─ gps_state     │
   │                                                       │
   │     ═══════ TRANSVERSAL CONTEXT ═══════► L4          │
   │     ═══════ TRANSVERSAL CONTEXT ═══════► L3          │
   │     ═══════ TRANSVERSAL CONTEXT ═══════► L2          │
   │     ═══════ TRANSVERSAL CONTEXT ═══════► L1          │
   │                                                       │
   └───────────────────────────────────────────────────────┘
```

Conceptually, the system combines:

``` text
Vertical hierarchy              Transversal systems

L4  Mission cognition  ◄──────  Perception
 ↓                              Lite World Model
L3  Task cognition     ◄──────  Memory
 ↓                              GPS / sensors
L2  Tactical cognition ◄──────  Logging / traces
 ↓
L1  Physical control   ◄──────  Rover state / sensing
 ↓
RA4M1
```

------------------------------------------------------------------------

## Perception

Perception is transversal to the L1--L4 hierarchy.

The system evolved from predefined simulated scenarios to real
camera-based and multimodal perception. The perception subsystem can
combine:

-   Camera capture
-   OpenCV image processing
-   Multimodal LLM vision
-   Structured perception state
-   GPS state
-   Lite World Model construction

A perception cycle can produce a shared result containing:

``` text
PerceptionResult
│
├── perception_state
├── image_bytes
├── world_model
└── gps_state
```

Typical structured perception information includes:

``` text
obstacle_ahead
free_direction
corridor_visible
summary
confidence
```

The camera image can also be supplied directly to multimodal reasoning
rather than relying only on a reduced symbolic description.

------------------------------------------------------------------------

## L4 --- Mission Cognition

L4 is the highest planning layer currently implemented.

Its role is to represent mission-level intent and pass that intent down
the hierarchy. The architecture supports structured missions such as
GPS-directed objectives.

Example:

``` python
{
    "mission_type": "GO_TO_GPS",
    "target_position": {
        "lat": 39.470000,
        "lon": -0.500000
    },
    "mission_text": "Reach target GPS position."
}
```

The mission context flows from L4 toward L3, where it can influence
task-level reasoning.

``` text
Mission
   ↓
L4 Mission Planner
   ↓
L3 Task Planner
   ↓
L2 Tactical Planner
   ↓
L1 Rover Controller
```

------------------------------------------------------------------------

## L3 --- Task Cognition

L3 operates above individual movement decisions.

Its role is to reason about the rover's current behavioral mode using
information such as:

-   Mission context
-   Current perception
-   Recent behavior
-   Memory
-   Repeated actions
-   Progress or lack of progress
-   Recovery conditions

Modes explored during development include:

``` text
EXPLORE
RECOVER
CAUTIOUS
```

One objective of this layer is to detect behavior patterns that cannot
be recognized from a single tactical decision. For example, repeated
actions without meaningful progress can indicate that the rover is stuck
and should enter a recovery-oriented mode.

------------------------------------------------------------------------

## L2 --- Tactical Cognition

L2 is responsible for tactical action selection.

It can reason over both structured perception and the current camera
image. Inputs can include:

-   Rover state
-   Camera image
-   Perception summary
-   World context
-   Mission/task context
-   Allowed actions
-   Safety constraints

Typical tactical actions include:

``` text
MOVE_FORWARD
MOVE_BACKWARD
FORWARD_LEFT
FORWARD_RIGHT
HOLD
STOP
```

LLM output is parsed and validated before execution. Fallback guidance
is available when an LLM decision cannot be safely accepted.

------------------------------------------------------------------------

## L1 --- Physical Control

L1 provides the interface between the cognitive stack and the physical
rover.

It is responsible for rover state and execution of tactical actions
through the RA4M1 controller.

The Raspberry Pi performs high-level processing, while the RA4M1 handles
the real-time low-level control required by the crawler hardware.

``` text
Raspberry Pi
     │
     │ serial communication
     ▼
   RA4M1
     │
     ├── steering servo
     └── drive control
             │
             ▼
       Axial SCX6 1/6
```

This separation keeps high-level cognitive processing independent from
real-time actuator control.

------------------------------------------------------------------------

## RA4M1 Firmware

The low-level controller firmware is stored under:

``` text
ra4m1_rover_controller/
└── ra4m1_rover_controller.ino
```

The firmware is maintained and programmed using the appropriate RA4M1
development tooling rather than as part of the Python runtime.

The `.ino` source is an essential part of the rover system even though
most of CognitiveOps is implemented in Python.

------------------------------------------------------------------------

## GPS

GPS is implemented as an independent sensor service.

The GPS layer is intentionally separated from mission logic: it reports
physical state rather than deciding where the rover should travel.

The GPS subsystem can provide information such as:

-   Latitude and longitude
-   Altitude
-   Fix quality
-   Satellite count
-   HDOP
-   Estimated speed
-   Estimated heading
-   Recent movement
-   Position confidence

GPS state is incorporated into the shared perception context, allowing
higher cognitive layers to reason about spatial mission objectives
without coupling the GPS sensor itself to mission decisions.

The repository also includes a dedicated GPS test utility.

``` text
sensors/
├── gps_service.py
└── test_gps_service.py
```

------------------------------------------------------------------------

## Lite World Model

CognitiveOps contains a lightweight structured representation of the
perceived environment:

``` text
lite_world_model/
```

Its components represent concepts such as:

-   Objects
-   Regions
-   Spatial relationships
-   Navigation state
-   Affordances
-   Environmental observations

The objective is to give the cognitive hierarchy a compact
representation of the environment beyond the immediate camera frame,
without requiring a heavyweight mapping system.

------------------------------------------------------------------------

## Memory

The architecture includes a memory system for retaining recent rover
behavior and cognitive context.

Memory can support reasoning about:

-   Recent actions
-   Repeated behavior
-   Perception history
-   Lack of progress
-   Recovery situations
-   Task context
-   Mission context

This gives higher cognitive layers temporal context instead of forcing
every decision to be purely reactive.

------------------------------------------------------------------------

## Multimodal Reasoning

CognitiveOps progressively evolved from symbolic simulated perception to
real multimodal reasoning.

A tactical decision can combine:

``` text
Camera image
     +
Structured perception
     +
Rover state
     +
World model
     +
Memory / context
     +
Mission intent
     ↓
Cognitive decision
```

This makes it possible to use visual information directly while
retaining explicit structured state for validation, memory, planning,
and debugging.

------------------------------------------------------------------------

## Decision Validation and Fallback

LLM responses are not sent directly to the actuators.

The stack includes:

-   Response parsing
-   Allowed-action validation
-   Rover-state validation
-   Perception-aware checks
-   Fallback guidance
-   Diagnostic logging

The objective is to keep probabilistic cognitive reasoning separated
from deterministic execution constraints.

------------------------------------------------------------------------

## Logging and Experimental Traces

Logging was progressively extended across the cognitive stack.

Instrumentation covers areas including:

-   Perception
-   LLM interactions
-   Prompt generation
-   Decision parsing
-   Validation
-   L2 tactical reasoning
-   L3 task reasoning
-   L4 mission reasoning
-   Memory
-   World-model construction

Runtime camera frames and experimental traces can also be generated
during rover operation.

Generated images and runtime logs are intentionally excluded from source
control where appropriate.

------------------------------------------------------------------------

## Hardware Platform

``` text
                         Raspberry Pi
                              │
             ┌────────────────┼────────────────┐
             │                │                │
          Camera             GPS        CognitiveOps
                                              │
                                              │ Serial
                                              ▼
                                            RA4M1
                                              │
                                     ┌────────┴────────┐
                                     │                 │
                                Steering            Drive
                                     │                 │
                                     └────────┬────────┘
                                              ▼
                                       Axial SCX6 1/6
```

------------------------------------------------------------------------

## Repository Structure

The main components of the current architecture are:

``` text
CognitiveOps/
│
├── l1_rover_controler_ra4m1.py
├── l2_tactical_planner.py
├── l3_task_planner.py
├── l4_mission_planner.py
│
├── perception_module.py
├── memory_system.py
├── prompt_builder.py
├── decision_validator.py
├── fallback_guidance.py
├── rover_interfaces.py
│
├── lite_world_model/
│   ├── world_model.py
│   ├── world_builder.py
│   ├── navigation_state.py
│   ├── object_node.py
│   ├── region.py
│   ├── relationships.py
│   └── ...
│
├── llm/
│   ├── llm_service.py
│   ├── l3_task_prompt.py
│   ├── l3_task_parser.py
│   ├── l4_mission_prompt.py
│   ├── l4_mission_parser.py
│   ├── llm_trace.py
│   ├── memory_formatter.py
│   └── ...
│
├── sensors/
│   ├── gps_service.py
│   └── test_gps_service.py
│
├── ra4m1_rover_controller/
│   └── ra4m1_rover_controller.ino
│
├── utils/
│   └── xlogger.py
│
├── guidance_demo_ra4m1_i5.py
└── guidance_demo_ra4m1_i50.py
```

------------------------------------------------------------------------

## Physical Test Launchers

Two launcher variants are intentionally preserved for physical testing:

``` text
guidance_demo_ra4m1_i5.py
guidance_demo_ra4m1_i50.py
```

They execute the autonomy loop for different numbers of iterations:

-   **`i5`** --- short 5-step test
-   **`i50`** --- longer 50-step test

The short test is useful for controlled validation of changes on the
physical rover before running longer autonomous sequences.

------------------------------------------------------------------------

## Development Evolution

CognitiveOps was built incrementally through a sequence of experimental
Lunar Rover revisions.

  -----------------------------------------------------------------------
  Revision                            Milestone
  ----------------------------------- -----------------------------------
  LR014                               Real camera perception using OpenCV

  LR015                               Multimodal image + LLM tactical
                                      reasoning

  LR016                               Reverse driving capability

  LR017                               Autonomous execution and
                                      decision-loop diagnostics

  LR018                               Hierarchical L3/L4 planning and
                                      cognitive memory

  LR019                               Formalized L3/L4 models, parsers
                                      and LLM tracing

  LR020                               L3 LLM-based task planning and
                                      recovery modes

  LR021                               Per-run image capture and execution
                                      traces

  LR027                               Layered L1/L2 architecture and Lite
                                      World Model

  LR030                               Architecture consolidation and
                                      legacy cleanup

  LR033                               Simplified cognitive planning and
                                      refined world-model integration

  LR037                               Comprehensive logging across the
                                      cognitive stack

  LR042                               Shared cognitive/perception context
                                      across planning levels

  LR044                               GPS state integrated into the
                                      cognitive perception pipeline

  LR045                               L3/L4 mission handoff with GPS
                                      target context

  LR046                               Final development state;
                                      code-equivalent to LR045
  -----------------------------------------------------------------------

Earlier development also included simulation and PIX6-based stages
before migration to the physical RA4M1 rover platform.

------------------------------------------------------------------------

## Current Development State

The latest development directory is:

``` text
LR046
```

LR046 is code-equivalent to LR045 for the files tracked by Git.
Therefore the repository's final code commit is LR045 while representing
the final LR046 source state.

Final tracked implementation milestone:

``` text
RA1M4 LR045: fix L3/L4 mission handoff with GPS target context
```

------------------------------------------------------------------------

## Experimental Status and Safety

CognitiveOps is an experimental robotics and autonomous-systems research
project.

The system controls physical hardware and combines deterministic control
software with probabilistic perception and LLM-based reasoning. LLM
output must not be treated as intrinsically safe actuator control.

Physical tests should be performed in a controlled environment with
appropriate supervision and a reliable way to stop the rover
immediately.

------------------------------------------------------------------------

## Project Goal

The objective of CognitiveOps is broader than autonomous driving.

The project investigates how a physical robotic system can combine:

``` text
Perception
     +
World Representation
     +
Memory
     +
Hierarchical Cognition
     +
Mission Intent
     +
Physical Action
```

into a coherent autonomous architecture.

The rover is the physical experimental platform used to develop and test
that architecture.
