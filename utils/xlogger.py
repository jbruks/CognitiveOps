from datetime import datetime


class XLogger:

    ENABLED = True

    INDENT = {
        "L4": "",
        "L3": "  ",
        "L2": "    ",
        "L1": "      ",
    }

    @classmethod
    def log(cls, layer: str, message: str):

        if not cls.ENABLED:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # indent = cls.INDENT.get(layer, "")
        # print(f"{timestamp} {indent}[{layer}] {message}")

        print(f"[{timestamp}] [{layer}] {message}")
