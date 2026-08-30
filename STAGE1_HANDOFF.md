# Stage 1 Handoff

## Current Status

Stage 1 — Monday Proof of Concept is `DONE`.

Stages 2-10 remain `PENDING`.

This handoff records what was implemented, how to reproduce it, and what another AI agent should read before continuing.

## Read First

Any future agent should read these files before changing code:

1. `CONTEXT.md`
2. `PLAN.md`
3. `README.md`
4. `STAGE1_HANDOFF.md`
5. `PROJECT_EXPLANATION_FOR_CHATGPT_AND_MAAM.md`
6. `data/README.md`
7. `scripts/README.md`
8. `tests/README.md`

Treat Markdown files as project context and requirements. Do not redesign the locked architecture.

## What Was Implemented

Stage 1 implements a small reproducible proof of concept:

```text
OpenStreetMap
-> Chennai road graph
-> OpenCity Chennai 2015 historical flood hotspot KML
-> nearest-road mapping with CRS-safe metric projection
-> affected road state
-> effective capacity
-> BPR travel-time cost
-> Dijkstra before/after route comparison
-> CSV and map outputs
```

The selected demonstration uses a real OpenCity historical flood hotspot mapped to a real OSM road edge. For the controlled proof of concept, that mapped edge is treated as `BLOCKED` after disruption so Dijkstra must choose an alternate route.

## Main Files Changed Or Added

Core implementation:

- `src/chennai_routing/stage1_poc.py`
- `src/chennai_routing/data/flood.py`
- `src/chennai_routing/data/osm.py`
- `src/chennai_routing/preprocessing/geospatial.py`
- `src/chennai_routing/preprocessing/validation.py`
- `src/chennai_routing/models/capacity.py`
- `src/chennai_routing/models/bpr.py`
- `src/chennai_routing/routing/dijkstra.py`
- `src/chennai_routing/visualization/maps.py`
- `scripts/run_stage1_poc.py`

Tests:

- `tests/test_stage1_poc.py`
- `tests/test_project_structure.py`

Docs/config:

- `README.md`
- `PLAN.md`
- `PROJECT_EXPLANATION_FOR_CHATGPT_AND_MAAM.md`
- `data/README.md`
- `scripts/README.md`
- `tests/README.md`
- `pyproject.toml`
- `requirements.txt`
- `.gitignore`

## Generated Artifacts

These files are generated and ignored by Git:

- `data/raw/flood/chennai_2015_gcc_area_flood_hotspots.kml`
- `data/raw/flood/chennai_2015_gcc_area_flood_hotspots_provenance.json`
- `data/processed/roads/stage1_chennai_osm_graph.graphml`
- `outputs/tables/stage1_affected_roads.csv`
- `outputs/tables/stage1_route_summary.csv`
- `outputs/tables/stage1_summary.json`
- `outputs/maps/stage1_before_after_route.png`

Ignored local/runtime directories:

- `.venv/`
- `cache/`
- `src/chennai_routing.egg-info/`

## Reproduction Commands

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python scripts\run_stage1_poc.py
.\.venv\Scripts\python -m pytest
```

The Stage 1 run needs internet access for:

- OpenCity CKAN/package and KML download
- OpenStreetMap/Overpass query through OSMnx

## Data Sources

Road network:

- Source: OpenStreetMap
- Access: OSMnx, small bounding box around a real flood hotspot

Flood data:

- Dataset: `Chennai Floods 2015 Data`
- Resource: `Chennai 2015 GCC Area Flood Hotspots`
- Provider/portal: OpenCity
- Resource ID: `8e1c5b2d-322c-4dbd-bd64-6da2d1a8681d`
- License title from CKAN: `Other (Public Domain)`
- Source listed in CKAN: `https://www.chennaifloodsdss.in`
- Classification: `HISTORICAL`

The flood dataset is not live flood information.

## Last Successful Run Summary

The latest successful Stage 1 run produced:

- Flood points loaded: `327`
- Affected road directions found: `15`
- Selected affected edge: `(9992430988, 9992430963, 0)`
- Before route: `[9992430988, 9992430963]`
- After route: `[9992430988, 9992430978, 2271790303, 9992430851, 9992430859, 9992430840, 9992430841, 9992430846, 9992430963]`
- Before cost: `14.630672383787825` seconds
- After cost: `34.61440269878254` seconds
- Bbox used: `(80.2552850633093, 13.104288394675699, 80.2792850633093, 13.1282883946757)`

## Model Assumptions

- Historical hotspot-to-road mapping uses nearest road within `150 m`.
- A real flood-mapped road edge is marked `BLOCKED` only for the controlled Stage 1 demonstration.
- Missing OSM speed values use an explicit `30 km/h` Stage 1 fallback.
- Normal capacity is set to `1200` and flow to `600` only as proof-of-concept model parameters.
- `NORMAL`, `DEGRADED`, `SEVERE`, and `BLOCKED` capacity multipliers are code parameters, not calibrated physical constants.
- The demonstration is dynamic Dijkstra with refreshed edge costs, not a full time-dependent shortest-path algorithm.

## Tests

The test suite currently verifies:

- Project paths and required root documents
- CRS mismatch validation
- Historical flood hotspot to nearest road mapping
- BPR and capacity behavior
- Blocked-edge exclusion
- Before/after route change on a synthetic graph

Last verified command:

```powershell
.\.venv\Scripts\python -m pytest
```

Result:

```text
6 passed
```

## Stage 1 Criteria Status

Passed:

- A Chennai road graph can be generated.
- A real Chennai flood dataset is loaded.
- Flood data is mapped to road segments.
- At least one affected road is identified.
- The affected road changes routing cost/state.
- Dijkstra produces a different route before versus after the disruption.
- A clear before/after visualization is generated.
- The process is reproducible from repository commands.

## Next Work

Start Stage 2 only after reading `CONTEXT.md`, `PLAN.md`, and this handoff.

Stage 2 should turn the proof-of-concept road graph logic into a robust reusable Chennai road-network module. Do not start SRTM, GPM IMERG, drainage, SUMO, emergency routing, threshold/hysteresis, accidents, or full evaluation unless explicitly requested by the user and allowed by `PLAN.md`.
