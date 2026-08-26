class PromptBuilderBase:
    def build_context(self, *args, **kwargs):
        return ""

    def build_rules(self):
        return ""

    def build_output_format(self):
        return ""

    def build(self, *args, **kwargs):
        context = self.build_context(*args, **kwargs)
        rules = self.build_rules()
        output = self.build_output_format()

        return f"{context}\n\n{rules}\n\n{output}".strip()
