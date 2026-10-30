"""Export an operator-reviewed QGIS GeoPackage to CognitiveOps MissionPackage 1.0.

Run inside QGIS Python console editor (PyQGIS required). No layer is changed.
Only polygons explicitly marked kind=authorized count as permission.
"""
import argparse
import json
from pathlib import Path

from qgis.core import (
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsGeometry,
    QgsProject, QgsVectorLayer, QgsWkbTypes,
)


LAYERS = (
    ("authorized_areas", "authorized", QgsWkbTypes.PolygonGeometry),
    ("excluded_areas", "excluded", QgsWkbTypes.PolygonGeometry),
    ("inspection_points", "poi", QgsWkbTypes.PointGeometry),
)


def export_mission(gpkg, output_dir, *, intent=None):
    gpkg = Path(gpkg).expanduser().resolve()
    dest = Path(output_dir).expanduser().resolve()
    if not gpkg.is_file():
        raise FileNotFoundError(gpkg)
    if not dest.exists():
        dest.mkdir(parents=True)
    target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
    features, counts = [], {}
    for layer_name, kind, expected in LAYERS:
        layer = QgsVectorLayer(f"{gpkg}|layername={layer_name}", layer_name, "ogr")
        if not layer.isValid() or layer.geometryType() != expected:
            raise ValueError(f"Missing or invalid GeoPackage layer: {layer_name}")
        transform = QgsCoordinateTransform(layer.crs(), target_crs,
                                           QgsProject.instance().transformContext())
        counts[kind] = 0
        for feature in layer.getFeatures():
            if feature["kind"] != kind:
                raise ValueError(f"{layer_name}: kind must be {kind}")
            geom = QgsGeometry(feature.geometry())
            if geom.isEmpty() or not geom.isGeosValid():
                raise ValueError(f"{layer_name}: invalid geometry")
            geom.transform(transform)
            if geom.isMultipart():
                raise ValueError("Multipart geometry unsupported by MissionPackage 1.0")
            converted = json.loads(geom.asJson())["coordinates"]
            if kind in ("authorized", "excluded"):
                if len(converted) != 1:
                    raise ValueError("Polygon holes unsupported")
                properties = {"kind": kind}
                geometry = {"type": "Polygon", "coordinates": converted}
            else:
                pid = str(feature["poi_id"]).strip()
                if not pid or pid == "NULL":
                    raise ValueError("Missing poi_id")
                properties = {"kind": "poi", "poi_id": pid}
                geometry = {"type": "Point", "coordinates": converted}
            features.append({"type": "Feature", "properties": properties,
                             "geometry": geometry})
            counts[kind] += 1
    if counts["authorized"] == 0:
        raise ValueError("No explicitly authorized areas; refusing to create actionable mission")
    if counts["poi"] == 0:
        raise ValueError("No operator-reviewed POIs")
    from mission_package import MissionPackage
    manifest = {
        "schema_version": "1.0",
        "site_id": "LLOMBAI-AIRFIELD-REVIEW",
        "intent": intent or ("Inspect authorized observation locations and report "
                             "all conditions which cannot be verified."),
        "crs": "EPSG:4326",
        "geojson": "site.geojson",
        "supporting_documents": ["site_context.txt"],
        "data_status": "OPERATOR_REVIEW_REQUIRED_SIMULATION_ONLY",
    }
    collection = {"type": "FeatureCollection", "features": features}
    package = MissionPackage(manifest, collection)
    for pid, coords in package.pois.items():
        if not package.allowed(coords):
            raise ValueError(f"POI {pid} not inside authorized area or inside exclusion")
    (dest / "site.geojson").write_text(json.dumps(collection, indent=2) + "\n",
                                      encoding="utf-8")
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                       encoding="utf-8")
    (dest / "site_context.txt").write_text(
        "Llombai airfield: operator-digitized areas and observation points. "
        "Aerial imagery and candidate geometry are not evidence of passability, "
        "site access rights or up-to-date ground conditions. This package is "
        "for off-line cognitive planning and simulation only. "
        "Do not infer that arriving at a POI verifies the inspection.\n",
        encoding="utf-8")
    print(f"Mission package created at {dest}. Feature counts: {counts}")
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("gpkg")
    parser.add_argument("output_dir")
    args = parser.parse_args()
    export_mission(args.gpkg, args.output_dir)
