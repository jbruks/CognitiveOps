def parse_task(text):
    if "TASK=" in text:
        return text.split("TASK=")[-1].strip().upper()
    return "EXPLORE"


def validate_task(task):
    allowed = {"EXPLORE", "GOTO", "STOP"}
    return task if task in allowed else "EXPLORE"
