class MemoryFormatter:

    @staticmethod
    def format_recent_history(memory, n_steps=5):
        history = memory.get_recent_history(n_steps)
        lines = []

        for step in history:
            action = step.get("action")
            perception = step.get("perception", {})
            obstacle = perception.get("obstacle_ahead", "unknown")

            lines.append(f"- {action}, obstacle_ahead={obstacle}")

        return "\n".join(lines)

    @staticmethod
    def format_summary(memory, n_steps=5):
        history = memory.get_recent_history(n_steps)

        if not history:
            return "No recent history."

        actions = [step["action"] for step in history]

        if len(set(actions)) == 1:
            return f"The rover has been repeatedly performing {actions[0]} without variation."

        return "The rover actions show variation."

    @staticmethod
    def build_l3_context(memory, rover_state, perception_state):
        history = MemoryFormatter.format_recent_history(memory)
        summary = MemoryFormatter.format_summary(memory)

        return f"""
Recent history:
{history}

Summary:
{summary}

Current perception:
{perception_state}

Current state:
{rover_state}
""".strip()

    @staticmethod
    def build_l4_context(memory, rover_state):
        history = MemoryFormatter.format_recent_history(memory, n_steps=10)
        summary = MemoryFormatter.format_summary(memory, n_steps=10)

        return f"""
Mission history:
{history}

Summary:
{summary}

Current state:
{rover_state}
""".strip()
