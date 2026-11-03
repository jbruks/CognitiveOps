# Rural Crossroads Lab — second cognitive scenario

**Status:** synthetic offline L4/L3 generalization test, not a field operating site.

This package intentionally differs from Llombai: farm-like yard/buildings,
a gravel-road junction, woodland patches, orchard rows and an excavated pond.
No predefined POIs are sent to GPT. L4 must identify visible objectives and
L3 must choose observation pixels.

The georeferencing is deliberately invented, with a synthetic CRS origin.
**Never feed targets from this package to powered `mf_dod_mission_runner`.**

## Build independent georeferenced raster

```bash
python -m experiments.build_rural_crossroads_lab \
  --output mission_packages/rural_crossroads_lab/rural_crossroads.tif
```

## Run the same L4 → L3 image cognitive test

```bash
python -m mf_dod_map_recon_poc \
  --map mission_packages/rural_crossroads_lab/rural_crossroads.tif \
  --context mission_packages/rural_crossroads_lab/site_context.txt \
  --mission "Reconnoitre the rural area" \
  --journal /tmp/cognitiveops_rural_recon_01.jsonl
```

Type uppercase `YES` to authorize OFFLINE pixel and coordinate proposals.

Review L4 feature choices and L3 pixels on the synthetic image; compare with
Llombai's four types of objective. Keep all outputs offline. For a real second
field site, supply its *own* checked GeoTIFF/context, access permissions and
validated operating boundary. This synthetic file is not that map.
