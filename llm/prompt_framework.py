from utils.xlogger import XLogger

class PromptBuilderBase:
    def build_context(self, *args, **kwargs):
        XLogger.log("class PromptBuilderBase:", "build_context")
        return ""

    def build_rules(self):
        XLogger.log("class PromptBuilderBase:", "build_rules")
        return ""

    def build_output_format(self):
        XLogger.log("class PromptBuilderBase:", "build_output_format")
        return ""

    def build(self, *args, **kwargs):
        XLogger.log("class PromptBuilderBase:", "build")
        context = self.build_context(*args, **kwargs)
        rules = self.build_rules()
        output = self.build_output_format()

        return f"{context}\n\n{rules}\n\n{output}".strip()

    @staticmethod
    def compose_cognitive_context(level, intent, objective, constraints,
                                  memory_events=(), doctrine_hits=()):
        """Build bounded level context without site-specific prompt templates."""
        import json
        if level not in ("L3", "L4"):
            raise ValueError("Only L3/L4 cognitive contexts are supported")
        return {
            "level": level,
            "intent": intent,
            "objective": objective,
            "constraints": constraints,
            "recent_events": list(memory_events)[-10:],
            "doctrine": list(doctrine_hits)[:5] if level == "L4" else [],
        }
