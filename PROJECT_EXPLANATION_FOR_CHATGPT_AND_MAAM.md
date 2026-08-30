# Project Explanation for ChatGPT and Ma'am

## Short Project Title

Flood- and Congestion-Aware Dynamic Traffic Routing for Chennai

## One-Line Explanation

This project shows how Chennai road routing can change when real historical flood hotspot data is mapped onto OpenStreetMap roads and used to modify road capacity, travel-time cost, and Dijkstra route selection.

## What This Project Is About

The project is an algorithms and routing project. The main idea is:

```text
road data
-> flood/traffic condition
-> road state
-> effective capacity
-> BPR travel-time cost
-> Dijkstra route
```

Instead of adding a random flood penalty to roads, the project follows a capacity-based model:

```text
flooded or affected road
-> lower effective capacity or blocked road
-> higher BPR travel time or unavailable edge
-> route changes
```

This keeps the routing logic explainable and connected to transport modelling.

## What Has Been Done So Far

Stage 1, the Monday proof of concept, has been completed.

The current implementation demonstrates:

1. A small Chennai road network is downloaded from OpenStreetMap using OSMnx.
2. A real open Chennai flood dataset is downloaded from OpenCity.
3. The flood data is parsed from KML.
4. Historical flood hotspot points are mapped to nearby road segments.
5. At least one real flood-mapped road segment is marked as affected for a controlled demo.
6. That affected road is treated as `BLOCKED` in the proof of concept.
7. Effective capacity becomes zero for the blocked road.
8. BPR travel-time cost becomes unavailable/infinite for that road.
9. Dijkstra is run before and after the disruption.
10. The route changes after the affected road is blocked.
11. A CSV table and route-change map are generated.
12. Tests verify CRS handling, flood-to-road mapping, BPR/capacity behavior, blocked-edge exclusion, and route change.

## What Stage 1 Proves

Stage 1 proves the core project chain:

```text
OpenStreetMap
-> Chennai road graph
-> real historical Chennai flood hotspot data
-> affected road identification
-> road state change
-> capacity change
-> BPR cost change
-> Dijkstra route change
```

This is not yet the full project. It is a working proof that the basic idea is technically possible.

## What Exactly Is In The Repository

Important documents:

- `README.md`: project overview, setup commands, Stage 1 run instructions, outputs, assumptions, and status.
- `CONTEXT.md`: locked project architecture and long-term project scope.
- `PLAN.md`: staged roadmap from Stage 1 to Stage 10.
- `CODEX_SETUP_PROMPT.md`: original repository setup prompt.
- `STAGE1_HANDOFF.md`: detailed handoff for any future AI agent or developer.
- `PROJECT_EXPLANATION_FOR_CHATGPT_AND_MAAM.md`: this explanation document.

Important code:

- `src/chennai_routing/stage1_poc.py`: main Stage 1 orchestration.
- `src/chennai_routing/data/flood.py`: downloads and parses OpenCity flood KML.
- `src/chennai_routing/data/osm.py`: downloads a small OSM driving graph.
- `src/chennai_routing/preprocessing/geospatial.py`: maps flood hotspots to nearest roads.
- `src/chennai_routing/preprocessing/validation.py`: validates CRS and graph basics.
- `src/chennai_routing/models/capacity.py`: applies road-state capacity multipliers.
- `src/chennai_routing/models/bpr.py`: computes BPR travel-time cost.
- `src/chennai_routing/routing/dijkstra.py`: runs shortest-path routing.
- `src/chennai_routing/visualization/maps.py`: creates the before/after route map.
- `scripts/run_stage1_poc.py`: command-line script to reproduce Stage 1.

Tests:

- `tests/test_stage1_poc.py`: focused Stage 1 unit tests.
- `tests/test_project_structure.py`: verifies setup and required docs.

Generated artifacts:

- `outputs/tables/stage1_affected_roads.csv`
- `outputs/tables/stage1_route_summary.csv`
- `outputs/tables/stage1_summary.json`
- `outputs/maps/stage1_before_after_route.png`
- `data/processed/roads/stage1_chennai_osm_graph.graphml`
- `data/raw/flood/chennai_2015_gcc_area_flood_hotspots.kml`

Generated data and outputs are ignored by Git so the repo stays lightweight. They can be recreated with the run command.

## Data Sources Used

Road data:

- Source: OpenStreetMap
- Tool: OSMnx
- Scope: small Chennai bounding box around a real historical flood hotspot

Flood data:

- Source portal: OpenCity
- Dataset: `Chennai Floods 2015 Data`
- Resource: `Chennai 2015 GCC Area Flood Hotspots`
- Format: KML
- License title from CKAN: `Other (Public Domain)`
- Data classification: `HISTORICAL`

Important wording:

The flood data is historical. It should not be described as live flooding or current road closure information.

## Commands To Reproduce

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python scripts\run_stage1_poc.py
.\.venv\Scripts\python -m pytest
```

Last verified test result:

```text
6 passed
```

## How To Explain This To Ma'am

You can say:

> Ma'am, I have completed the first proof-of-concept stage of the Chennai flood-aware routing project. The project uses OpenStreetMap for the road network and a real OpenCity Chennai 2015 historical flood hotspot dataset. I mapped the flood hotspots to nearby road segments, marked one real flood-mapped road as blocked for a controlled demonstration, converted that into effective capacity and BPR travel-time cost, and then reran Dijkstra. The route changed after the affected road was blocked, which proves the basic architecture works.

Then explain the limitation clearly:

> This is not the full final system yet. It is Stage 1 only. The flood data is historical, not live flooding. The blocked-road assumption is used only for a controlled proof of concept. Later stages will make the Chennai road graph more robust and then add flood susceptibility, rainfall, controlled rerouting, simulation, emergency routing, and evaluation.

## What Not To Claim

Do not say:

- We built the full Chennai routing system.
- We have live flood detection.
- We can predict exact flooded roads right now.
- We invented Dijkstra or dynamic routing.
- The historical 2015 flood hotspots mean those roads are flooded today.
- The capacity values are scientifically calibrated.

Correct wording:

- We completed a reproducible Stage 1 proof of concept.
- We used real historical flood hotspot data.
- We demonstrated that flood-mapped road disruption can change Dijkstra routing.
- The current assumptions are model assumptions for the demo.
- The full system will be built in later stages.

## Current Stage Status

```text
Stage 1: DONE
Stage 2: PENDING
Stage 3: PENDING
Stage 4: PENDING
Stage 5: PENDING
Stage 6: PENDING
Stage 7: PENDING
Stage 8: PENDING
Stage 9: PENDING
Stage 10: PENDING
```

## Suggested Next Step

The next development step is Stage 2:

Build a more robust reusable Chennai road graph module with better handling of road classes, missing OSM attributes, edge identifiers, free-flow travel time, and saved processed graph data.

Do not start rainfall, SRTM, SUMO, accidents, emergency routing, or final evaluation until their planned stages.

## Prompt For ChatGPT Website

Paste this into ChatGPT along with this repository or this document:

```text
I am working on a project called Flood- and Congestion-Aware Dynamic Traffic Routing for Chennai. Read this document and explain the project to me in simple terms. Then help me prepare a 3-5 minute explanation for my ma'am. Focus on what Stage 1 achieved, what files are in the repository, what data sources were used, what assumptions were made, what I should not overclaim, and what the next stage should be.
```
