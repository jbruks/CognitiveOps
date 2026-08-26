from utils.xlogger import XLogger

def parse_mode(text):
    XLogger.log("l3_task_oparser.py", "parse_mode")
    if "MODE=" in text:
        return text.split("MODE=")[-1].strip().upper()
    return "EXPLORE"


def validate_mode(mode):
    XLogger.log("l3_task_oparser.py", "validate_mode")
    allowed = {"EXPLORE", "RECOVER", "CAUTIOUS"}
    return mode if mode in allowed else "EXPLORE"
