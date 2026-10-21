# CognitiveOps Roadmap

## Project direction

CognitiveOps is evolving from an experimental autonomous rover stack toward
a cognitive robotic reconnaissance platform.

The objective is not only to improve autonomous navigation, but to progressively
increase the rover's ability to understand missions, interpret its environment,
make decisions at different cognitive levels, operate over difficult terrain
and interact naturally with a human operator.

Development should remain evidence-driven:

Field testing
→ operational experience
→ identify limitations
→ improve architecture and capabilities
→ field validation


## Current validated baseline

The current experimental platform has demonstrated:

- Physical rover control through L1 and RA4M1.
- Camera-based environmental perception.
- Phone position and attitude integrated into Navigation.
- Deterministic GO_TO_POINT Guidance.
- L2 tactical reasoning using both Guidance and visual perception.
- Autonomous execution of short physical movement primitives.
- Local obstacle avoidance and conservative recovery manoeuvres.
- Automatic mission termination inside the configured arrival radius.
- End-to-end autonomous GO_TO_POINT operation demonstrated in a real
  outdoor field test.

Current cognitive/control architecture:

Mission / L4
↓
Navigation + Guidance / L3
↓
Tactical reasoning / L2
↓
Control / L1
↓
RA4M1
↓
Physical rover

Perception provides environmental information across the cognitive loop.

This baseline should remain reproducible while new capabilities are added.


# Development Roadmap


## 1. Additional field validation

Before significantly changing the current architecture, perform additional
field tests using the validated system.

The objective is not simply to repeat the TOLL experiment, but to expose the
system to different environmental situations.

Candidate tests include:

- Longer GO_TO_POINT missions.
- Open terrain.
- Narrower paths.
- Vegetation.
- Rough terrain.
- Isolated obstacles.
- Multiple successive obstacles.
- Situations requiring temporary deviation from the target direction.
- Recovery after local avoidance.
- Navigation under degraded GPS conditions.

Recorded images should be correlated with selected tactical cycles when
behaviour requires deeper analysis.

The current TOLL experiment becomes the reference baseline against which
future changes can be compared.


## 2. Define real reconnaissance use cases

Move from generic autonomous navigation toward concrete reconnaissance
missions.

The question should change from:

"Can the rover reach a GPS coordinate?"

to:

"What useful reconnaissance task can the rover perform autonomously?"

Candidate use cases include:

- Navigate to a remote area and inspect it.
- Reconnoitre a predefined zone.
- Search for relevant objects or environmental conditions.
- Approach an area, observe it and report findings.
- Follow a sequence of reconnaissance objectives.
- Investigate something detected during a mission.
- Return useful information to the operator.
- React to operator requests while a mission is running.

These use cases should drive the future evolution of the cognitive
architecture.

Navigation should progressively become one capability used by the rover,
rather than the mission itself.


### 2.1 Doctrine Framework

Formalize the cognitive doctrine used by L4, L3 and L2.

The objective is to define a reusable Doctrine Framework rather than
accumulating increasingly complex prompts or procedural rules.

For each cognitive level, define:

- Role.
- Objectives.
- Available context.
- Responsibilities.
- Authority.
- Restrictions.
- Uncertainty handling.
- Delegation rules.
- Escalation rules.
- Expected outputs.

Initial responsibility model:

### L4 — Mission level

Responsible for understanding and managing the overall mission.

Examples:

- Mission objectives.
- Mission progress.
- Mission completion.
- Mission failure.
- Mission priorities.
- High-level replanning.
- Interaction with the operator.

### L3 — Navigation / Guidance level

Responsible for translating mission intent into navigation strategy and
guidance objectives.

Examples:

- Where the rover should progress.
- Navigation strategy.
- Intermediate objectives.
- Recovery from lack of global progress.
- Strategic navigation around environmental constraints.

### L2 — Tactical level

Responsible for selecting the next safe local manoeuvre.

Examples:

- Local obstacle avoidance.
- Traversability reasoning.
- Temporary deviations from Guidance.
- Recovery toward the requested direction.
- Tactical use of perception.

### L1 — Control level

Responsible for deterministic execution of physical commands.

L1 should remain predictable and tightly connected to the physical
capabilities of the rover.

A major Doctrine Framework objective is to clearly define the boundary
between:

local tactical avoidance

and

strategic navigation / replanning.

The framework should allow cognitive capabilities to evolve without turning
the architecture into a large collection of hard-coded behavioural rules.


## 3. QGroundControl integration

Introduce QGroundControl as an operational visualization and supervision
interface.

The objective is to make the autonomous system observable outside terminal
logs.

Potential telemetry includes:

- Rover position.
- Rover heading.
- Mission target.
- Mission status.
- Navigation quality.
- Guidance direction.
- Current tactical action.
- Perception status.
- Cognitive level status.
- System health.

MAVLink should be evaluated as the communication layer between CognitiveOps
and QGroundControl.

Longer term, QGroundControl could provide:

- Mission visualization.
- Waypoint definition.
- Mission monitoring.
- Operator intervention.
- Telemetry recording.
- Field-test analysis.

CognitiveOps should remain responsible for cognitive autonomy; QGroundControl
should primarily provide mission supervision, visualization and interaction.


## 4. Onboard AI and sensor expansion

Reduce dependence on external/cloud computation by progressively moving
perception and cognitive inference onboard the rover.

Evaluate an NVIDIA Jetson-class onboard computer as the main AI computing
platform.

Evaluate local models, including Qwen-family models or other suitable
vision-language and language models, according to:

- Reasoning quality.
- Vision capabilities.
- Latency.
- Memory requirements.
- Power consumption.
- Model size.
- Reliability in offline operation.

The objective is not merely to run an LLM locally, but to enable a rover that
can continue performing cognitive reconnaissance without requiring permanent
Internet connectivity.

In parallel, expand the sensor architecture.

Potential sensors include:

- Improved GNSS.
- RTK GNSS.
- IMU.
- Wheel/vehicle odometry.
- Additional cameras.
- Depth sensing.
- LiDAR or ranging sensors where justified.
- Environmental sensors required by future reconnaissance use cases.

Sensor additions should be driven by demonstrated operational requirements,
not added solely for hardware complexity.

Navigation should progressively evolve toward sensor fusion rather than
depending on a single positioning source.


## 5. Replace RA4M1 with Pixhawk 6

Evaluate migration of the low-level vehicle-control architecture from the
current RA4M1 implementation to a Pixhawk 6-class autopilot.

The objective is to provide a more capable and standardized physical control
layer while preserving the cognitive architecture above it.

Potential benefits include:

- Mature autopilot infrastructure.
- MAVLink integration.
- Improved sensor integration.
- Standardized telemetry.
- Vehicle state estimation.
- More sophisticated control capabilities.
- Better integration with QGroundControl.
- Clearer separation between cognitive autonomy and vehicle control.

The migration should preserve the conceptual hierarchy:

CognitiveOps
→ cognitive decisions
→ navigation / tactical commands
→ vehicle control
→ physical rover

The autopilot should not replace the cognitive architecture. It should become
a stronger execution and vehicle-state platform underneath it.


## 6. Improve capabilities across all cognitive levels

Once real reconnaissance use cases and the Doctrine Framework are established,
progressively increase the capabilities of each cognitive level.

Examples include:

### L4

- Multi-stage missions.
- Mission replanning.
- Mission memory.
- Dynamic objectives.
- Resource and time awareness.
- Operator-requested mission changes.

### L3

- Intermediate navigation objectives.
- Strategic obstacle circumnavigation.
- Progress monitoring.
- Recovery when local avoidance does not restore progress.
- Route reasoning.

### L2

- Better terrain understanding.
- Improved obstacle avoidance.
- Better recovery behaviour.
- Temporal reasoning across successive observations.
- More deliberate use of uncertainty.
- Better balance between mission progress and local safety.

Improvements should preserve clear responsibility boundaries between levels.


## 7. Expand L1 terrain capabilities

Exploit more of the physical capability of the crawler platform.

The current movement primitives intentionally provide a simple and safe
experimental control interface, but they use only a fraction of the rover's
mechanical capabilities.

Future L1 development should investigate control behaviours for:

- Rough terrain.
- Rocks.
- Steeper slopes.
- Ditches and terrain transitions.
- Uneven surfaces.
- Low-speed precision manoeuvring.
- Controlled wheel torque / throttle.
- More precise steering.
- Terrain-dependent speed.
- Difficult obstacle traversal.

Perception and L2 should eventually be able to distinguish between:

"obstacle that must be avoided"

and

"difficult terrain that the crawler is physically capable of traversing."

This distinction is important for an off-road reconnaissance platform.

The objective is not only safer obstacle avoidance, but intelligent use of
the rover's physical mobility.


## 8. Human interaction over radio

Develop a direct communication channel between the human operator and the
cognitive system.

The long-term objective is for the operator to interact with the rover at the
mission and cognitive level rather than only through low-level commands.

Potential interactions include:

- Assign a mission.
- Ask the rover what it is doing.
- Ask what it sees.
- Request inspection of an object or area.
- Change mission priorities.
- Request status.
- Approve or reject significant decisions.
- Abort or redirect a mission.
- Receive reconnaissance findings.

Radio communication should eventually support operation beyond local Wi-Fi
coverage.

The interaction model should preserve the cognitive hierarchy:

Human
↕
L4 Mission cognition
↕
L3 Navigation / Guidance
↕
L2 Tactical cognition
↕
L1 Control

The human operator should normally communicate intent rather than manually
control every movement.


# Engineering improvements to address progressively

The following engineering issues were identified during current development
and field testing. They should be addressed when required by the roadmap
rather than blocking higher-level experimentation unnecessarily.

- Replace the Python fixed execution delay with explicit RA4M1/Pixhawk
  action-completion synchronization.
- Improve navigation accuracy/confidence handling.
- Revisit heading correction behaviour.
- Improve GPS freshness/accuracy policy.
- Evaluate GNSS/RTK and sensor fusion.
- Improve correlation between rich perception output and simplified
  PerceptionState.
- Review MOVE_BACKWARD behaviour using field-test evidence.
- Improve execution and cognitive-cycle telemetry.
- Develop terminal visual approach when GPS precision is insufficient near
  the objective.


# Long-term vision

The target system is not simply an autonomous GPS rover.

The objective is a cognitive reconnaissance robot capable of:

- receiving mission-level intent from a human operator,
- understanding reconnaissance objectives,
- navigating autonomously,
- perceiving and interpreting its environment,
- reasoning at mission, navigation and tactical levels,
- exploiting the physical off-road capabilities of its platform,
- adapting its behaviour when conditions change,
- operating with onboard AI,
- communicating over long-range radio,
- and reporting useful information back to the operator.

The development strategy should remain incremental.

Each major capability should be demonstrated in the field before the next
architectural layer is considered validated.
