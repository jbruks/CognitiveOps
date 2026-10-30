"""Build a SIMULATION-ONLY mission package from reviewed visual candidates.

This never writes authorized_areas/inspection_points in the operator GeoPackage.
The synthetic geofence is a computational envelope, NOT access authorization.
"""
import argparse
import json
from pathlib import Path

from mission_package import MissionPackage


def build(candidate_path, destination):
    candidate_path = Path(candidate_path)
    destination = Path(destination)
    source = json.loads(candidate_path.read_text(encoding="utf-8"))
    if source.get("type") != "FeatureCollection":
        raise ValueError("Expected candidate FeatureCollection")
    points = []
    polygons = []
    for item in source.get("features", []):
        geometry = item.get("geometry", {})
        props = item.get("properties", {})
        if props.get("not_authorized") is not True:
            raise ValueError("Candidate source must explicitly be non-authorizing")
        if geometry.get("type") == "Point":
            coordinates = geometry.get("coordinates")
            if not isinstance(coordinates, list) or len(coordinates) != 2:
                raise ValueError("Malformed candidate point")
            points.append((props["name"], coordinates))
        elif geometry.get("type") == "Polygon":
            polygons.append((props["name"], geometry))
        else:
            raise ValueError("Unsupported candidate geometry")
    if not points:
        raise ValueError("No candidate observation points")
    if len(set(name for name, _ in points)) != len(points):
        raise ValueError("Duplicate candidate names")
    # Broad simulation-only rectangle around the candidate POIs, never
    # interpreted as an operational polygon or physical clearance.
    xs = [xy[0] for _, xy in points]
    ys = [xy[1] for _, xy in points]
    margin = 0.0002
    minx, maxx = min(xs) - margin, max(xs) + margin
    miny, maxy = min(ys) - margin, max(ys) + margin
    outer = [[minx, miny], [maxx, miny], [maxx, maxy],
             [minx, maxy], [minx, miny]]
    features = [
        {"type": "Feature",
         "properties": {"kind": "authorized", "scope": "SIMULATION_ONLY_NOT_REAL_PERMISSION"},
         "geometry": {"type": "Polygon", "coordinates": [outer]}}
    ]
    for name, xy in points:
        features.append({"type": "Feature",
                         "properties": {"kind": "poi", "poi_id": name},
                         "geometry": {"type": "Point", "coordinates": xy}})
    # Do not auto-convert visually inferred pond/buildings into hard exclusions.
    manifest = {"schema_version": "1.0", "site_id": "LLOMBAI-VISUAL-SIM-ONLY",
                "crs": "EPSG:4326", "geojson": "site.geojson",
                "intent": "Propose non-actuating visual inspection of candidate "
                          "observation points around Llombai airfield. "
                          "Report all unverified conditions.",
                "supporting_documents": ["site_context.txt"],
                "data_status": "VISUAL_CANDIDATES_SIMULATION_ONLY_NO_REAL_ACCESS_PERMISSION"}
    collection = {"type": "FeatureCollection", "features": features}
    package = MissionPackage(manifest, collection)
    for name in package.pois:
        if not package.allowed(package.pois[name]):
            raise ValueError("Simulation candidate outside simulation envelope")
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "site.geojson").write_text(
        json.dumps(collection, indent=2) + "\n", encoding="utf-8")
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (destination / "site_context.txt").write_text(
        "Operator accepted approximate visual feature placements for an offline "
        "cognitive experiment. All locations and the generated computational "
        "envelope are SIMULATION ONLY; neither proves operator access rights, "
        "safe terrain, a traversable path nor actual visibility. Candidate "
        "visual surfaces: " + ", ".join(name for name, _ in polygons) +
        ". Real inspection evidence has not been collected.\n", encoding="utf-8")
    return {"site_id": package.site_id, "poi_ids": sorted(package.pois),
            "simulation_only": True, "physical_permission": False,
            "candidate_polygon_count": len(polygons)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates")
    parser.add_argument("output")
    args = parser.parse_args()
    print(json.dumps(build(args.candidates, args.output), indent=2))


if __name__ == "__main__":
    main()
