from rover_interfaces import TacticalAction

class FallbackGuidance:
    def decide_action(self, rover_state, perception_state):
        if perception_state.confidence < 0.5:
            return TacticalAction.HOLD

        if perception_state.obstacle_ahead:
            if perception_state.free_direction == "left":
                return TacticalAction.FORWARD_LEFT
            if perception_state.free_direction == "right":
                return TacticalAction.FORWARD_RIGHT
            return TacticalAction.STOP

        if perception_state.corridor_visible and perception_state.free_direction == "center":
            return TacticalAction.MOVE_FORWARD

        return TacticalAction.HOLD
