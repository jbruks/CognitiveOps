from rover_interfaces import TacticalAction

class DecisionValidationError(Exception):
    pass

def parse_llm_response(response_text: str) -> TacticalAction:
    if not response_text:
        raise DecisionValidationError("Empty LLM response")

    cleaned = response_text.strip()

    if cleaned.startswith("ACTION="):
        cleaned = cleaned.split("=", 1)[1].strip()

    cleaned = cleaned.upper()

    try:
        return TacticalAction[cleaned]
    except KeyError as exc:
        raise DecisionValidationError(
            f"Unsupported action from LLM: {cleaned}"
        ) from exc

def validate_action(action: TacticalAction, rover_state, perception_state) -> TacticalAction:
    if rover_state.mode not in ("GUIDED", "UNKNOWN"):
        if action in (
            TacticalAction.MOVE_FORWARD,
            TacticalAction.FORWARD_LEFT,
            TacticalAction.FORWARD_RIGHT,
        ):
            raise DecisionValidationError(
                f"Unsafe action {action.value}: rover mode is {rover_state.mode}"
            )

    if not rover_state.armed and action in (
        TacticalAction.MOVE_FORWARD,
        TacticalAction.FORWARD_LEFT,
        TacticalAction.FORWARD_RIGHT,
    ):
        raise DecisionValidationError(
            f"Unsafe action {action.value}: rover is not armed"
        )

    if perception_state.confidence < 0.3 and action == TacticalAction.MOVE_FORWARD:
        raise DecisionValidationError(
            "Unsafe action MOVE_FORWARD: perception confidence too low"
        )

    return action
