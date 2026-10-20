class VisionNN:
    """
    Placeholder for the local neural-network vision path.

    The implementation will be added incrementally. For now this class
    only provides the integration shell and always declines the frame so
    PerceptionModule continues through the existing GPT vision path.
    """

    def analyze(self, frame):
        return {
            "accepted": False,
            "source": "vision_nn_stub",
        }
