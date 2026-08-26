from dataclasses import dataclass
from typing import List, Optional

from rover_interfaces import PerceptionState


@dataclass
class SimulatedScenario:
    name: str
    obstacle_ahead: bool
    free_direction: str      # "left" | "right" | "center" | "none"
    corridor_visible: bool
    summary: str
    confidence: float = 1.0


class PerceptionModule:
    """
    Scenario-based perception simulator for testing guidance decisions.
    """

    BUILTIN_SCENARIOS = {
        "corridor_forward": SimulatedScenario(
            name="corridor_forward",
            obstacle_ahead=False,
            free_direction="center",
            corridor_visible=True,
            summary="Clear corridor ahead."
        ),
        "obstacle_left_open": SimulatedScenario(
            name="obstacle_left_open",
            obstacle_ahead=True,
            free_direction="left",
            corridor_visible=False,
            summary="Obstacle ahead. Left side looks traversable."
        ),
        "obstacle_right_open": SimulatedScenario(
            name="obstacle_right_open",
            obstacle_ahead=True,
            free_direction="right",
            corridor_visible=False,
            summary="Obstacle ahead. Right side looks traversable."
        ),
        "blocked": SimulatedScenario(
            name="blocked",
            obstacle_ahead=True,
            free_direction="none",
            corridor_visible=False,
            summary="Obstacle ahead and no safe path detected."
        ),
        "uncertain": SimulatedScenario(
            name="uncertain",
            obstacle_ahead=False,
            free_direction="none",
            corridor_visible=False,
            summary="Environment unclear. Reassessment recommended.",
            confidence=0.4
        ),
    }

    def __init__(
        self,
        default_scenario: str = "corridor_forward",
        scenario_sequence: Optional[List[str]] = None,
        loop_sequence: bool = True,
    ):
        if default_scenario not in self.BUILTIN_SCENARIOS:
            raise ValueError(f"Unknown default scenario: {default_scenario}")

        self.default_scenario = default_scenario
        self.scenario_sequence = scenario_sequence or []
        self.loop_sequence = loop_sequence
        self.sequence_index = 0
        self.current_scenario_name = default_scenario

    def set_scenario(self, scenario_name: str) -> None:
        if scenario_name not in self.BUILTIN_SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario_name}")
        self.current_scenario_name = scenario_name

    def _get_next_scenario_name(self) -> str:
        if not self.scenario_sequence:
            return self.current_scenario_name

        if self.sequence_index >= len(self.scenario_sequence):
            if self.loop_sequence:
                self.sequence_index = 0
            else:
                return self.scenario_sequence[-1]

        scenario_name = self.scenario_sequence[self.sequence_index]
        self.sequence_index += 1

        if scenario_name not in self.BUILTIN_SCENARIOS:
            raise ValueError(f"Unknown scenario in sequence: {scenario_name}")

        return scenario_name

    def observe(self) -> PerceptionState:
        scenario_name = self._get_next_scenario_name()
        scenario = self.BUILTIN_SCENARIOS[scenario_name]

        return PerceptionState(
            obstacle_ahead=scenario.obstacle_ahead,
            free_direction=scenario.free_direction,
            corridor_visible=scenario.corridor_visible,
            summary=scenario.summary,
            confidence=scenario.confidence,
        )
