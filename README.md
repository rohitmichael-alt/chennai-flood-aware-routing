# Flood- and Congestion-Aware Dynamic Traffic Routing for Chennai

## Objective

This repository contains the Stage 1 proof of concept for a Chennai-specific dynamic traffic routing project that will eventually combine flood evidence, congestion, incidents, road capacity, BPR travel-time costs, Dijkstra-based routing, controlled rerouting, and emergency-vehicle priority routing.

Stage 1 implements a small reproducible demonstration only. It does not implement the complete robust Chennai road graph or later-stage dynamic routing system.

## High-Level Architecture

The locked project architecture is:

```text
DATA
-> road/environment/traffic conditions
-> road condition
-> effective capacity
-> BPR travel-time cost
-> dynamic edge cost
-> routing
-> controlled rerouting
-> evaluation
```

Emergency vehicles use a separate priority-routing rule.

## Repository Structure

```text
.
├── CONTEXT.md
├── PLAN.md
├── CODEX_SETUP_PROMPT.md
├── README.md
├── pyproject.toml
├── requirements.txt
├── data/
│   ├── raw/
│   ├── processed/
│   └── README.md
├── src/chennai_routing/
│   ├── config.py
│   ├── data/
│   ├── preprocessing/
│   ├── models/
│   ├── routing/
│   ├── simulation/
│   ├── evaluation/
│   └── visualization/
├── scripts/
├── notebooks/
├── tests/
└── outputs/
    ├── maps/
    ├── figures/
    └── tables/
```

## Technology Overview

Initial core dependencies are intentionally limited to the early-stage geospatial and graph stack:

- OSMnx
- NetworkX
- GeoPandas
- Shapely
- pandas
- NumPy
- Matplotlib
- pytest

Later-stage tools such as SUMO, satellite/raster processing libraries, live API clients, and machine-learning frameworks are not required for Stage 1.

## Environment Setup

Python 3.11 or newer is recommended.

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Activate it on Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

Run tests:

```bash
python -m pytest
```

## Stage 1 Proof of Concept

Run the Stage 1 pipeline:

```powershell
.\.venv\Scripts\python scripts\run_stage1_poc.py
```

The script:

1. Downloads the public-domain OpenCity Chennai 2015 GCC flood hotspot KML.
2. Parses historical flood hotspot points.
3. Downloads a small OpenStreetMap driving graph around a real hotspot using OSMnx.
4. Maps flood hotspot points to nearest road segments after CRS-safe metric projection.
5. Applies a controlled Stage 1 model assumption: one real flood-mapped road edge is treated as `BLOCKED`.
6. Recomputes effective capacity and BPR travel-time cost.
7. Runs Dijkstra before and after the disruption.
8. Writes affected-road, route-summary, graph, provenance, and map outputs.

Generated outputs:

```text
data/raw/flood/chennai_2015_gcc_area_flood_hotspots.kml
data/raw/flood/chennai_2015_gcc_area_flood_hotspots_provenance.json
data/processed/roads/stage1_chennai_osm_graph.graphml
outputs/tables/stage1_affected_roads.csv
outputs/tables/stage1_route_summary.csv
outputs/tables/stage1_summary.json
outputs/maps/stage1_before_after_route.png
```

## Data Sources

- Road network: OpenStreetMap, queried with OSMnx for a small Chennai subarea.
- Flood data: OpenCity, `Chennai Floods 2015 Data`, resource `Chennai 2015 GCC Area Flood Hotspots`, license `Other (Public Domain)`, source listed as `https://www.chennaifloodsdss.in/`.

The flood data is historical. It is not live flooding and must not be interpreted as current road closure evidence.

## Stage 1 Assumptions and Limitations

- Historical flood hotspots are mapped to the nearest road within a documented tolerance.
- The blocked-road state is a controlled proof-of-concept model assumption applied to a real flood-mapped road edge.
- OSM missing speed data uses a visible Stage 1 fallback speed of `30 km/h`.
- Synthetic flow and capacity values are model parameters used only to demonstrate the capacity-to-BPR-to-routing chain.
- The selected origin and destination are the endpoints of the real affected road edge so the route-change demonstration is controlled and reproducible.
- This is dynamic Dijkstra with refreshed edge costs, not a full time-dependent shortest-path formulation.

## Staged Development Workflow

Before implementing any stage, read:

1. `CONTEXT.md`
2. `PLAN.md`
3. `STAGE1_HANDOFF.md` if continuing after Stage 1
4. `PROJECT_EXPLANATION_FOR_CHATGPT_AND_MAAM.md` for a student-facing summary
5. The stage-specific prompt or task description

Follow the status tracker in `PLAN.md`. Do not mark a stage complete until its completion criteria are reproducible and documented.

## Current Status

```text
Stage 1 — Monday Proof of Concept: DONE
Stages 2 onward: PENDING
```

Stage 1 is complete as a Monday proof of concept. Stage 2 remains pending and should turn this prototype into a robust reusable Chennai road-network module.
