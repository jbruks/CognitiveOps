def parse_mode(text):
    if "MODE=" in text:
        return text.split("MODE=")[-1].strip().upper()
    return "EXPLORE"


def validate_mode(mode):
    allowed = {"EXPLORE", "RECOVER", "CAUTIOUS"}
    return mode if mode in allowed else "EXPLORE"
