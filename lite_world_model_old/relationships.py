from dataclasses import dataclass

@dataclass
class SpatialRelationship:
    source_id: str
    relation_type: str
    target_id: str

    confidence: float = 1.0
