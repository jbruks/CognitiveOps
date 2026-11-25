# CognitiveOps — Hardware Architecture

## Purpose

Physical equipment inventory for the PoC handover. This document covers the existing research platform for supervised civilian experiments, not a production or qualified vehicle. It is a preliminary inventory, not an electrical schematic.

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
| Smartphone | GPS/GNSS, compass and available inertial sensors | Model and sensor availability to confirm; Phyphox used in project. |
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

## Handover checklist

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
- [Phyphox](https://phyphox.org/)
- [Project README](../../README.md)

The inventory is based on project documentation and the handover discussion; no physical inspection or independent verification of the retailer listing has been performed.
