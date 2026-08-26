from utils.xlogger import XLogger

from llm.prompt_framework import PromptBuilderBase

class L4MissionPromptBuilder(PromptBuilderBase):
    def build_context(self, rover_state, memory):
        XLogger.log("class L4MissionPromptBuilder", "build_context")
        return (
            f"L4 CONTEXT:\n"
            f"State={rover_state}\n"
            f"Memory={memory}"
        )

    def build_rules(self):
        XLogger.log("class L4MissionPromptBuilder", "build_rules")
        return "Decide the mission-level task."

    def build_output_format(self):
        XLogger.log("class L4MissionPromptBuilder", "build_output_forma")
        return "Output: TASK=<EXPLORE|GOTO|STOP>"
