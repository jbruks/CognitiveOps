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

        #indent = cls.INDENT.get(layer, "")
        #print(f"{indent}[{layer}] {message}")
        
        print(f"[{layer}] {message}")
