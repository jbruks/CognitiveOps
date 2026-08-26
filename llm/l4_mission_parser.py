from utils.xlogger import XLogger

def parse_task(text):
    XLogger.log("l4_mission_parser.py", "parse_task")
    if "TASK=" in text:
        return text.split("TASK=")[-1].strip().upper()
    return "EXPLORE"


def validate_task(task):
    XLogger.log("l4_mission_parser.py", "validate_task")
    allowed = {"EXPLORE", "GOTO", "STOP"}
    return task if task in allowed else "EXPLORE"
