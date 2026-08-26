import time

from rover_interfaces import TacticalAction


class GuidanceNavigator:
    def __init__(self, rover_client, perception_module):
        self.rover_client = rover_client
        self.perception_module = perception_module

    def decide_action(self, rover_state, perception_state):
        if perception_state.confidence < 0.5:
            return TacticalAction.HOLD

        if perception_state.obstacle_ahead:
            if perception_state.free_direction == "left":
                return TacticalAction.TURN_LEFT
            if perception_state.free_direction == "right":
                return TacticalAction.TURN_RIGHT
            return TacticalAction.STOP

        if perception_state.corridor_visible and perception_state.free_direction == "center":
            return TacticalAction.MOVE_FORWARD

        return TacticalAction.HOLD

    def step(self):
        rover_state = self.rover_client.get_state()
        perception_state = self.perception_module.observe()
        action = self.decide_action(rover_state, perception_state)

        print("\n=== Guidance Step ===")
        print(f"Rover state: {rover_state}")
        print(f"Perception: {perception_state}")
        print(f"Chosen action: {action.value}")

        self.rover_client.execute_tactical_action(action)

    def run_loop(self, steps=10, delay_s=1.0):
        for _ in range(steps):
            self.step()
            time.sleep(delay_s)
