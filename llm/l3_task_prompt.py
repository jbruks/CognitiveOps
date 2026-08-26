from llm.prompt_framework import PromptBuilderBase

class L3TaskPromptBuilder(PromptBuilderBase):
    def build_context(self, rover_state, perception_state, memory):
        history_lines = []

        # ejemplo simple (ajústalo a tu estructura real)
        for step in memory.recent_steps[-5:]:
            action = step.action
            obstacle = step.perception.obstacle_ahead
            history_lines.append(f"- {action}, obstacle_ahead={obstacle}")

        history_text = "\n".join(history_lines) if history_lines else "No recent history."

        # summary simple
        if history_lines:
            last_action = memory.recent_steps[-1].action
            repetitions = sum(1 for s in memory.recent_steps if s.action == last_action)
            summary = f"Repeated {last_action} {repetitions} times"
        else:
            summary = "No recent history."

        return f"""
            Recent history:
            {history_text}

            Summary:
            {summary}

            Current perception:
            {perception_state}

            Current state:
            {rover_state}
            """.strip()

    def build_rules(self):
        return "Decide the behavior mode based on context."

    def build_output_format(self):
        return "Output: MODE=<EXPLORE|RECOVER|CAUTIOUS>"
        
    def decide_task_mode(self, prompt):
        print("[LLM] task mode decision")
        return "MODE=EXPLORE"
        


    def build(self, context):
        return f"""
        You are the task-level planner of an autonomous rover.

        Your job is to analyze recent behavior and decide the current mode.

        {context}

        Instructions:
        - Analyze recent actions and perception
        - Detect patterns (e.g., repetition, lack of progress)
        - Decide if the rover is stuck or progressing

        Definition of stuck:
        The rover is considered STUCK if:
        - It repeats the same action multiple times (>=3)
        - AND there is no change in position or situation
        - AND perception does not improve

        When stuck:
        - You MUST output MODE=RECOVER

        If unsure between EXPLORE and RECOVER:
        - Prefer RECOVER if repetition is observed

        Output:
        MODE=<EXPLORE|RECOVER|CAUTIOUS>
        """.strip()
