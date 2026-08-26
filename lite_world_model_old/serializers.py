import json
from dataclasses import asdict

def world_to_json(world_model):
    return json.dumps(asdict(world_model), indent=2)
