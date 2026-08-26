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
