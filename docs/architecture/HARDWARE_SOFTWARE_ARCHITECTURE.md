# CognitiveOps — Hardware and Software Architecture

## Purpose

Physical equipment and software inventory for the PoC handover. This document covers the existing research platform for supervised civilian experiments, not a production or qualified vehicle. It is a preliminary inventory, not an electrical schematic.

## Hardware components

| Component | Role | Identification / status |
| --- | --- | --- |
| RC crawler | Mechanical platform | Axial SCX10 II Deadbolt 4WD RTR, 1:10, supplied reference; confirm actual chassis (older README mentions SCX6 1:6). |
| Brushed DC motor | Propulsion | Exact model to confirm. |
| Electronic speed controller (ESC) | Motor controller | Model to confirm. |
| Steering servo | Steering | Model to confirm. |
| RC transmitter and receiver | Manual operation | Models to confirm. |
| Renesas microcontroller board | Embedded controller | Repository identifies RA4M1; confirm board marking (RA3M1 was also mentioned during handover). |
| Raspberry Pi | Onboard computer | Model, RAM and storage capacity to confirm. |
| USB webcam | Image acquisition | Manufacturer and model to confirm. |
| Ultrasonic sensor | Distance measurement | HC-SR04, front-mounted according to project history; confirm physical installation. |
| Smartphone | GPS/GNSS, compass and available inertial sensors | Apple iPhone running the phyphox app for GPS coordinates and compass heading; exact iPhone model to confirm. |
| Smartphone / network access | Wi-Fi and cellular connectivity | Confirm actual hotspot arrangement and cellular generation. |
| Laptop | Ground station, experiment monitoring and logs | Model and operating system to confirm. |

## Power and supporting equipment

| Item | Verification required |
| --- | --- |
| Rover battery and charger | Chemistry, voltage, capacity, charger model and condition. |
| Raspberry Pi power source | Identify actual supply and rating. |
| BEC / DC-DC converter, if fitted | Identify installed equipment and rating. |
| Switches and physical disconnects | Identify actual isolation provisions. |
| microSD card / storage | Capacity and installed image. |
| USB cables, connectors and wiring | Inventory and condition. |
| USB hub, if fitted | Confirm presence. |
| Mounting brackets, sensor mounts and electronics enclosure | Inspect actual installation. |
| Spare batteries and charging accessories | Confirm availability. |

## Physical overview

The platform comprises the crawler and its existing RC equipment, onboard computing and embedded electronics, camera and distance sensor, smartphone positioning and connectivity, and a laptop used for monitoring. Exact interconnections, power distribution and board revisions must be checked against the actual vehicle during handover.

## Software platform

### iPhone and sensor application

The iPhone runs **phyphox** (Physical Phone Experiments), providing GPS position and compass heading to the research software. The repository includes `sensors/phyphox_discovery.py`, `sensors/phone_position_service.py`, `sensors/phone_attitude_service.py` and `sensors/gps_service.py`. The exact app version and installed experiment configuration must be recorded during handover.

### Python and embedded firmware

| Technology | Purpose / repository reference |
| --- | --- |
| Python 3.11.2 | Version declared in `.python-version`; primary research language. |
| C/C++ (Arduino-style firmware) | Embedded Renesas software in `ra4m1_rover_controller/ra4m1_rover_controller.ino`. |
| Python hardware interface | `l1_rover_controler_ra4m1.py`, `rover_interfaces.py`. |
| Configuration and logging | `config.py`, `utils/xlogger.py`. |
| Existing navigation research | `guidance_demo_*.py`, `l2_tactical_planner.py`, `fallback_guidance.py`, `decision_validator.py`. |
| Cognitive research | `l3_task_planner.py`, `l4_mission_planner.py`, associated model definitions and `mf_dod_*.py` experiments. |
| LLM services and prompt research | `llm/`, `llm_decision.py`, `prompt_builder.py`. |
| Memory and document research | `memory_system.py`, `doctrine_service.py`, `mission_package.py`. |
| Image processing and local perception research | `perception_module.py`, `vision_nn.py`, `vision_nn_worker*.py`. |
| Local model experiments | `ollama_l2_worker.py`, `qwen_l2_realtest.py`, `qwen_l2_split_test.py`. |
| Test software | `tests/`, sensor and hardware test scripts. |

The firmware is an Arduino sketch, so C/C++ is a more accurate description than pure C. The installed board package, toolchain and firmware revision remain to be confirmed.

### AI services and libraries

| Software | Role / status |
| --- | --- |
| OpenAI API (GPT / commonly called ChatGPT API) | Remote model inference; GPT-5.4 is documented in previous research experiments. API access is separate from the ChatGPT application. |
| OpenAI Python SDK 2.29.0 | Declared API client dependency. |
| Ollama / Qwen | Local model experiments; exact model tags and runtime versions to confirm. |
| OpenCV | Image processing; 4.11.0.86 in workstation requirements and 4.12.0.88 in Raspberry Pi requirements. |
| NumPy 1.26.4 | Numerical processing. |
| Pydantic 2.12.5 | Structured data and validation. |
| pySerial 3.5 | Serial communication library. |
| pynmea2 1.19.0 | NMEA parsing. |
| httpx 0.28.1 | HTTP client. |
| tqdm 4.67.3 | Progress reporting. |
| pypdf | Optional PDF research dependency documented in README; not pinned in the two inspected requirements files. |
| PyTorch, Transformers, Pillow | Separate local perception experiments; not part of the inspected baseline requirements. |

The complete pinned baseline dependency lists are [requirements.txt](../../requirements.txt) and [requirements-rpi.txt](../../requirements-rpi.txt). They also include supporting HTTP, typing and validation packages. Do not treat separate experimental environments as baseline dependencies.

### Supporting tools

| Tool | Role / status |
| --- | --- |
| Raspberry Pi OS / Linux | Onboard operating environment; exact installed release to confirm. |
| Git and GitHub | Version control and documentation. |
| QGIS / GeoJSON | Geospatial research and map preparation. |
| Gazebo Sim | Proposed simulation extension; not confirmed as installed or integrated. |

## Handover checklist

- [ ] Record the iPhone model, iOS and phyphox version.
- [ ] Record installed operating systems, Python environments and firmware/toolchain versions.
- [ ] Confirm API access and local model availability without committing credentials.
- [ ] Distinguish baseline dependencies from optional experimental environments.


- [ ] Photograph the complete rover and individual installed components.
- [ ] Record manufacturer, model and revision for each device.
- [ ] Resolve the crawler and microcontroller identification discrepancies.
- [ ] Inventory batteries, chargers, cables, mounts and spare parts.
- [ ] Record the actual power sources and installed interfaces.
- [ ] Confirm manual RC equipment and physical isolation provisions.
- [ ] Update this inventory with verified information.

For observational shadow experiments, keep motor and servo power physically isolated. This inventory does not establish electrical compatibility or safety certification.

## References

- [Crawler reference supplied for handover](https://www.modellbau-berlinski.de/veh_culos-rc-y-accesorios/coches-y-accesorios/offroad-el_ctrico/scx10-ii-deadbolt-4wd-rock-crawler-cepillado-rtr-1_10-tan)
- [Raspberry Pi](https://www.raspberrypi.com/)
- [Renesas](https://www.renesas.com/)
- [phyphox](https://phyphox.org/)
- [OpenAI API](https://platform.openai.com/)
- [Python](https://www.python.org/)
- [Arduino](https://www.arduino.cc/)
- [OpenCV](https://opencv.org/)
- [Ollama](https://ollama.com/)
- [QGIS](https://qgis.org/)
- [Project README](../../README.md)

The inventory is based on project documentation and the handover discussion; no physical inspection or independent verification of the retailer listing has been performed.
