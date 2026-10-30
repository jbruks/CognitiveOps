# Llombai QGIS → MF-DoD mission package

The **visual candidate** overlay is in `qgis_pr/llombai_visual_candidates_review.geojson` (WGS84). It is not a navigation authorization, and is not automatically converted into `kind=authorized`.

The operator's `qgis_pr/llombai_mission.gpkg` is the authoritative **operator-reviewed input**, with layers:
- `authorized_areas`: Polygon, `kind=authorized`
- `excluded_areas`: Polygon, `kind=excluded` (can be empty)
- `inspection_points`: Point, `kind=poi`, unique `poi_id`

These layers can be edited in EPSG:3857. The exporter transforms coordinates to EPSG:4326, verifies polygons and POI containment through `MissionPackage`, and creates `manifest.json`, `site.geojson` and `site_context.txt`. If the authorized layer is empty, the export **fails closed**; do not fabricate a navigation perimeter from the screenshot.

## Run inside the QGIS Python console

After saving changes to the GeoPackage, open QGIS Python console and run this **single line**:

```python
import sys; sys.path.insert(0, '/home/jbru/RoverGit-mf-dod'); from qgis_mission_export import export_mission; export_mission('/home/jbru/RoverGit-mf-dod/qgis_pr/llombai_mission.gpkg', '/home/jbru/RoverGit-mf-dod/mission_packages/llombai')
```

(The command is for the current laptop username/path. Use a different path if needed.)

The output is **simulation only**, regardless of the input geometries. It does not validate route clearance, obstacle margins, terrain, permissions or physical suitability.

## Agent experiment (after exporter passes)

```bash
cd ~/RoverGit-mf-dod
source ~/RoverGit/.venv/bin/activate
python -m mf_dod_integrated_agent mission_packages/llombai/manifest.json --backend openai --allow-api --model gpt-5.4 --save-proposals /tmp/llombai_proposals.json
# Review saved proposals; --approve authorizes ONLY synthetic simulation.
```

Do not commit commercial satellite imagery or large GeoTIFFs to the Git repository without confirming applicable redistribution rights. Existing `main` and physical rover controls remain untouched.
