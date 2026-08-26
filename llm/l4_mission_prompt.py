from llm.prompt_framework import PromptBuilderBase

class L4MissionPromptBuilder(PromptBuilderBase):
    def build_context(self, rover_state, memory):
        return (
            f"L4 CONTEXT:\n"
            f"State={rover_state}\n"
            f"Memory={memory}"
        )

    def build_rules(self):
        return "Decide the mission-level task."

    def build_output_format(self):
        return "Output: TASK=<EXPLORE|GOTO|STOP>"
