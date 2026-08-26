from utils.xlogger import XLogger

class LLMTraceLogger:

    @staticmethod
    def log_prompt(level, prompt):
        XLogger.log("class LLMTraceLogger:", "log_prompt")
        #print(f"[LLM TRACE][{level}] PROMPT:\n{prompt}\n")

    @staticmethod
    def log_response(level, response):
        XLogger.log("class LLMTraceLogger:", "og_response")
        #print(f"[LLM TRACE][{level}] RESPONSE: {response}")

    @staticmethod
    def log_decision(level, decision):
        XLogger.log("class LLMTraceLogger:", "log_decision")
        #print(f"[LLM TRACE][{level}] DECISION: {decision}")
