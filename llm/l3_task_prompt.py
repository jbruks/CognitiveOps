from llm.prompt_framework import PromptBuilderBase

class L3TaskPromptBuilder(PromptBuilderBase):
    def build_context(self, rover_state, perception_state, memory):
        return (
            f"L3 CONTEXT:\n"
            f"State={rover_state}\n"
            f"Perception={perception_state}\n"
            f"Memory={memory}"
        )

    def build_rules(self):
        return "Decide the behavior mode based on context."

    def build_output_format(self):
        return "Output: MODE=<EXPLORE|RECOVER|CAUTIOUS>"
