"""Operator-supplied mission data, not doctrine or motor authority.

GeoJSON coordinates are WGS84 [longitude, latitude]. Boundary points are
rejected conservatively. Candidate goals must coincide with an operator POI.
"""
from dataclasses import dataclass
from pathlib import Path
import json
import math

from l3_models import NavigationObjective


def _point(p):
    if (not isinstance(p, (list, tuple)) or len(p) != 2
            or any(isinstance(v, bool) or not isinstance(v, (int, float))
                   or not math.isfinite(v) for v in p)
            or not -180 <= p[0] <= 180 or not -90 <= p[1] <= 90):
        raise ValueError("Invalid WGS84 lon/lat")
    return (float(p[0]), float(p[1]))


def _ring(raw):
    if not isinstance(raw, list) or len(raw) < 4:
        raise ValueError("Polygon requires closed ring")
    pts = [_point(p) for p in raw]
    if pts[0] != pts[-1] or len(set(pts[:-1])) < 3:
        raise ValueError("Invalid polygon ring")
    return tuple(pts)


def _on_boundary(point, ring):
    x, y = point
    for (ax, ay), (bx, by) in zip(ring, ring[1:]):
        cross = (x-ax)*(by-ay)-(y-ay)*(bx-ax)
        if abs(cross) < 1e-11 and min(ax,bx) <= x <= max(ax,bx) and min(ay,by) <= y <= max(ay,by):
            return True
    return False


def _inside(point, ring):
    """Strict interior; boundary excluded, including segment endpoints."""
    x, y = point
    inside = False
    for (ax, ay), (bx, by) in zip(ring, ring[1:]):
        cross = (x-ax)*(by-ay) - (y-ay)*(bx-ax)
        if abs(cross) < 1e-11 and min(ax,bx) <= x <= max(ax,bx) and min(ay,by) <= y <= max(ay,by):
            return False
        if (ay > y) != (by > y):
            at_x = ax + (bx-ax)*(y-ay)/(by-ay)
            if x < at_x:
                inside = not inside
    return inside


@dataclass(frozen=True)
class ProposedGoal:
    objective_id: str
    poi_id: str
    purpose: str
    question: str
    source_ids: tuple[str, ...]
    approved: bool = False


class MissionPackage:
    def __init__(self, manifest, feature_collection):
        if manifest.get("schema_version") != "1.0":
            raise ValueError("Unsupported mission package version")
        self.intent = manifest.get("intent", "")
        if not isinstance(self.intent, str) or not self.intent.strip():
            raise ValueError("Mission order required")
        if manifest.get("crs") != "EPSG:4326":
            raise ValueError("Explicit EPSG:4326 CRS required")
        self.site_id = manifest.get("site_id")
        if not isinstance(self.site_id, str) or not self.site_id:
            raise ValueError("site_id required")
        if feature_collection.get("type") != "FeatureCollection":
            raise ValueError("GeoJSON FeatureCollection required")
        self.authorized = []
        self.exclusions = []
        self.pois = {}
        for feature in feature_collection.get("features", []):
            geom = feature["geometry"]
            kind = feature.get("properties", {}).get("kind")
            if geom["type"] == "Polygon" and kind in ("authorized", "excluded"):
                coords = geom["coordinates"]
                if len(coords) != 1:
                    raise ValueError("Polygon holes unsupported; provide separate exclusion polygons")
                ring = _ring(coords[0])
                (self.authorized if kind == "authorized" else self.exclusions).append(ring)
            elif geom["type"] == "Point" and kind == "poi":
                poi_id = feature.get("properties", {}).get("poi_id")
                if not isinstance(poi_id, str) or not poi_id or poi_id in self.pois:
                    raise ValueError("Unique poi_id required")
                self.pois[poi_id] = _point(geom["coordinates"])
            else:
                raise ValueError("Unsupported feature or missing kind")
        if not self.authorized:
            raise ValueError("Authorized polygon required")
        self.document_sources = manifest.get("supporting_documents", [])
        if not isinstance(self.document_sources, list):
            raise ValueError("supporting_documents must be a list")
        self.manifest = manifest

    @classmethod
    def load(cls, manifest_path):
        path = Path(manifest_path)
        manifest = json.loads(path.read_text(encoding="utf-8"))
        geo = manifest.get("geojson")
        if not isinstance(geo, str) or Path(geo).is_absolute() or ".." in Path(geo).parts:
            raise ValueError("GeoJSON must be a relative local path")
        geo_path = path.parent / geo
        return cls(manifest, json.loads(geo_path.read_text(encoding="utf-8")))

    def allowed(self, point):
        p = _point(point)
        return any(_inside(p, ring) for ring in self.authorized) and not any(
            _inside(p, ring) or _on_boundary(p, ring) for ring in self.exclusions)

    def candidate(self, objective_id, poi_id, purpose, question):
        if poi_id not in self.pois:
            raise ValueError("Invented POI")
        if not self.allowed(self.pois[poi_id]):
            raise ValueError("POI outside authorized zone or in exclusion")
        if not all(isinstance(x, str) and x for x in (objective_id, purpose, question)):
            raise ValueError("Malformed proposal")
        return ProposedGoal(objective_id, poi_id, purpose, question,
                            (f"map:poi:{poi_id}",))

    def approve(self, proposals, approved_ids):
        """Explicit operator gate. No caller may infer approval from GPT text."""
        ids = list(approved_ids)
        chosen = set(ids)
        if not chosen or len(chosen) != len(ids):
            raise ValueError("Explicit unique approval IDs required")
        if len({p.objective_id for p in proposals}) != len(proposals):
            raise ValueError("Duplicate proposals")
        if not chosen.issubset({p.objective_id for p in proposals}):
            raise ValueError("Approval refers to unknown proposal")
        out = []
        for p in proposals:
            if p.objective_id in chosen:
                if p.poi_id not in self.pois or not self.allowed(self.pois[p.poi_id]):
                    raise ValueError("Unsafe proposal")
                lon, lat = self.pois[p.poi_id]
                out.append(NavigationObjective(p.objective_id, lat, lon, purpose=p.purpose))
        return out
