# PLAN.md — Chennai Flood- and Congestion-Aware Dynamic Traffic Routing

**Status:** LOCKED EXECUTION PLAN  
**Companion context:** `Chennai_Flood_Aware_Routing_Project_Context.md`

> This is the execution roadmap. The architecture in the Context file is locked.  
> Do not redesign the project because a new dataset, API, or technique is discovered.  
> Any proposed addition must first be classified as **Core**, **Optional Enhancement**, or **Future Extension**.

---

# 0. How to use this plan

This file is intended to be read by every AI/Codex/Antigravity agent before implementation.

Every stage has:

- **Status**
- **Objective**
- **Inputs**
- **Tasks**
- **Expected outputs**
- **Completion criteria**
- **Do not move forward until...**

Use these statuses:

```text
PENDING
IN PROGRESS
BLOCKED
DONE
```

Only mark a stage `DONE` when its completion criteria have been met and its output is reproducible.

### Current status

```text
Stage 1 — Monday Proof of Concept: DONE
Stages 2–10: PENDING
```

The user has **not completed the Chennai road topology yet**.

---

# 1. Overall roadmap

```text
STAGE 1
Monday proof of concept
OSM → road graph → flood overlay → affected roads
→ capacity state → BPR → Dijkstra route change
        ↓
STAGE 2
Complete robust Chennai road graph
        ↓
STAGE 3
Historical flood + hydrology + elevation susceptibility
        ↓
STAGE 4
Rainfall integration using NASA GPM IMERG
        ↓
STAGE 5
Dynamic flood/road-condition model
        ↓
STAGE 6
BPR + dynamic/time-varying Dijkstra
        ↓
STAGE 7
Threshold + hysteresis + controlled concurrent rerouting
        ↓
STAGE 8
SUMO traffic + accident scenarios
        ↓
STAGE 9
Emergency-vehicle priority routing
        ↓
STAGE 10
Evaluation, experiments, robustness, documentation
        ↓
FINAL SYSTEM
```

Optional satellite/observed-flood confirmation can be inserted after Stage 3 or Stage 4 without becoming a core dependency.

---

# 2. STAGE 1 — MONDAY PROOF OF CONCEPT

**Status: DONE**

## Objective

Create the smallest end-to-end demonstration proving that:

> Flood information can be mapped onto the Chennai road graph, can change a road's condition/cost, and can cause Dijkstra to choose a different route.

## Scope

Only build:

```text
OpenStreetMap
 ↓
Chennai road graph
 ↓
Open Chennai flood dataset
 ↓
Flood area/hotspot → affected road segments
 ↓
Affected road → degraded/blocked state
 ↓
Effective capacity changes
 ↓
BPR cost changes
 ↓
Dijkstra route changes
```

## Data

Primary:

- OpenStreetMap road network
- One real, openly available Chennai flood dataset

Do not require:

- GPM IMERG
- SRTM
- drainage
- satellite processing
- SUMO
- accidents
- emergency routing
- live APIs

## Tasks

### 1.1 Set up project environment

Install only necessary packages.

Expected core packages:

```text
osmnx
networkx
geopandas
shapely
pandas
matplotlib
```

Add raster/satellite packages only when their stage arrives.

### 1.2 Obtain a manageable Chennai road area

Do NOT immediately download all of Chennai if it makes debugging difficult.

Use a reproducible city/subarea selection.

The chosen area must contain enough road alternatives for a route-change demonstration.

### 1.3 Download/build the OSM road graph

Use OSMnx.

Verify:

- graph exists,
- nodes exist,
- edges exist,
- geometry exists,
- lengths are present,
- graph is routable.

### 1.4 Obtain one Chennai flood dataset

Prefer an open flood/inundation/stagnation/hotspot dataset with geographic coordinates or polygons.

Do not manually invent flood locations.

### 1.5 Normalize coordinate reference systems

Ensure:

```text
flood data CRS
=
road data CRS
```

before spatial operations.

### 1.6 Spatially map flood information to roads

For polygons:

```text
Flood polygon
      ↓
intersect / spatial join
      ↓
affected road segments
```

For point/hotspot data:

```text
Flood point
      ↓
nearest road / buffer
      ↓
affected road segment
```

Use a clearly documented spatial tolerance.

### 1.7 Mark road state

For the demo only:

```text
NORMAL
BLOCKED
```

or:

```text
NORMAL
DEGRADED
```

depending on what the dataset supports.

Do not pretend the dataset gives exact physical road capacity.

### 1.8 Demonstrate route change

Create a controlled origin/destination pair where:

```text
Route A = normal shortest route

Flood affects Route A
       ↓
Route A becomes expensive/unavailable

Dijkstra
       ↓
Route B selected
```

### 1.9 Produce a visual

At minimum show:

- road network,
- flood area/hotspot,
- affected roads,
- origin,
- destination,
- before route,
- after route.

## Expected outputs

```text
data/
  roads/
  flood/

notebooks/ or scripts/

output/
  road_graph.png
  flood_overlay.png
  before_after_route.png
  affected_roads.csv
```

Exact folder structure may be refined during implementation, but outputs must remain identifiable.

## Monday presentation

Explain:

> "We have started building the Chennai road graph and are connecting real Chennai flood information to road segments. The prototype demonstrates that when a road is affected, its routing cost/state changes and Dijkstra can select an alternative path."

## Completion criteria

Stage 1 is DONE when:

- a reproducible Chennai road graph can be generated,
- one real Chennai flood dataset is loaded,
- flood information is spatially associated with road segments,
- at least one road is marked affected,
- route computation works,
- before/after route differs under a controlled scenario,
- a clear visual is available.

---

# 3. STAGE 2 — ROBUST CHENNAI ROAD GRAPH

**Status: PENDING**

## Objective

Turn the Monday prototype into a clean reusable road-network module.

## Tasks

- Define geographic study area.
- Download appropriate OSM driving network.
- Clean graph.
- Ensure directed edges.
- Preserve road geometry.
- Extract road class.
- Extract lanes where available.
- Extract speed where available.
- Calculate road length.
- Calculate free-flow travel time.
- Establish baseline capacity assumptions.
- Assign stable edge identifiers.
- Save processed graph.

## Important data issue

OSM attributes can be missing.

Do not silently assume:

```text
lanes = 2
speed = 50 km/h
```

for every road.

Any fallback assumption must be explicit and documented.

## Output

A reusable graph object/data file containing, where available:

```text
edge_id
from_node
to_node
geometry
length
road_class
lanes
speed
free_flow_time
capacity
```

## Completion criteria

A clean road graph can be loaded without re-downloading OSM data and is suitable for routing and spatial joins.

---

# 4. STAGE 3 — FLOOD SUSCEPTIBILITY MODEL

**Status: PENDING**

## Objective

Move from "this road was flooded in one dataset" to a more general **flood susceptibility** representation.

## Inputs

### Historical flood evidence

OpenCity Chennai:

- flood hotspots,
- water-stagnation locations,
- inundation zones,
- inundation depth,
- historical flood information.

### Elevation

SRTM.

### Hydrology

OpenCity drainage/water-body layers where useful.

## Tasks

### 4.1 Historical flood feature

For each road, derive a historical evidence feature.

Examples:

```text
number of historical flood observations nearby
```

or:

```text
whether road intersects historical inundation zone
```

Do not automatically interpret historical presence as current flooding.

### 4.2 Elevation feature

Sample SRTM elevation onto roads.

Possible derived feature:

```text
mean elevation
minimum elevation
```

Use the simplest defensible feature first.

### 4.3 Hydrological proximity

Calculate:

```text
distance to nearest drain
distance to nearest water body
```

Only include a feature if the dataset quality is adequate.

### 4.4 Normalize features

Convert features to comparable scales.

### 4.5 Compute susceptibility

Build a transparent score from:

```text
historical flood evidence
+
elevation
+
hydrological context
```

Do not label it as a calibrated probability unless calibration data support that claim.

## Output

```text
road_id
flood_susceptibility
historical_flood_feature
elevation
drain_distance
waterbody_distance
```

## Completion criteria

Every usable road segment has a documented susceptibility value and the contribution of each input is traceable.

---

# 5. STAGE 4 — RAINFALL INTEGRATION

**Status: PENDING**

## Objective

Add the dynamic rainfall trigger.

## Primary source

**NASA GPM IMERG**

Use it as the core rainfall source.

## Derived rainfall features

Use:

```text
30-minute rainfall
3-hour rolling accumulation
6-hour rolling accumulation
```

The exact rolling windows are part of the locked design.

## Tasks

1. Obtain appropriate IMERG precipitation data.
2. Extract the Chennai spatial extent.
3. Convert to a usable geospatial/time-series representation.
4. Associate precipitation values with the study area/road network.
5. Build rolling rainfall accumulations.
6. Store timestamped rainfall states.
7. Handle missing data explicitly.

## Important limitation

IMERG's spatial resolution is coarser than individual roads.

Therefore:

> rainfall is a spatial forcing applied to road areas/grid cells, not a direct measurement at every road.

Do not claim road-level measurement precision that the source does not provide.

## Optional

OpenWeather may be used later for a live-weather demonstration, but it must not be required for reproducibility.

CHIRPS may be used for historical rainfall validation if needed, but it is not required in the core.

## Completion criteria

Given a timestamp/scenario, the system can return rainfall and accumulated rainfall for the study area and feed it into the flood model.

---

# 6. STAGE 5 — DYNAMIC FLOOD / ROAD-CONDITION MODEL

**Status: PENDING**

## Objective

Convert susceptibility + rainfall + optional observed flood evidence into an interpretable road state.

## Inputs

```text
Flood susceptibility
+
30-min rainfall
+
3h rainfall
+
6h rainfall
+
optional observed flood extent
```

## Output states

```text
NORMAL
DEGRADED
SEVERE
BLOCKED
```

## Tasks

1. Define transparent state-transition rules.
2. Define initial rainfall thresholds/parameters.
3. Incorporate susceptibility.
4. Allow observed flooding to override/escalate state where appropriate.
5. Separate soft degradation from hard closure.
6. Record why each road received its state.

## Example conceptual model

```text
low susceptibility + low rainfall
→ NORMAL

high susceptibility + moderate rainfall
→ DEGRaded

high susceptibility + heavy accumulated rainfall
→ SEVERE

observed/known closure
→ BLOCKED
```

The exact thresholds must be documented as experimental assumptions.

## Completion criteria

For any road and time/scenario, the system can explain:

```text
road state
why it got that state
effective capacity multiplier
```

---

# 7. STAGE 6 — CAPACITY + BPR + DYNAMIC DIJKSTRA

**Status: PENDING**

## Objective

Connect road conditions to the actual shortest-path algorithm.

## 6.1 Effective capacity

Use:

```text
effective_capacity
=
normal_capacity × condition_multiplier
```

Initial conceptual states:

```text
NORMAL   → 1.0
DEGRADED → 0.7
SEVERE   → 0.3
BLOCKED  → 0.0
```

These are model parameters and must be tested, not presented as universal physical constants.

## 6.2 Traffic flow

For early tests, use controlled/synthetic flow.

Later, SUMO provides simulated flow.

## 6.3 BPR

Use:

```text
t_e(x) = t0 × [1 + α × (x/c)^β]
```

where:

```text
t0 = free-flow time
x  = current/projected flow
c  = effective capacity
```

## 6.4 Dynamic edge cost

Update edge travel time whenever relevant road state or traffic state changes.

## 6.5 Dijkstra

Run shortest path using current edge costs.

## Terminology requirement

If edge costs change between routing events, describe the system accurately.

If the implementation truly models:

```text
w_e(t)
```

as a function of entry/departure time, it can be described as time-dependent Dijkstra.

Otherwise use:

> dynamic Dijkstra with time-varying edge costs.

Do not overclaim.

## Completion criteria

The system can:

```text
change road capacity
→ recompute BPR travel time
→ update edge costs
→ run Dijkstra
→ produce a different route
```

---

# 8. STAGE 7 — THRESHOLD + HYSTERESIS REROUTING

**Status: PENDING**

## Objective

Prevent unnecessary continuous rerouting.

## Threshold

Initial experimental threshold:

```text
20%
```

For a route:

```text
old_cost = T_old
new_cost = T_new

degradation =
(T_new - T_old) / T_old
```

Reroute if degradation exceeds the configured threshold.

## Hysteresis

Require a sufficiently meaningful improvement before switching to another route.

This reduces route flip-flopping.

## Sensitivity experiment

Test:

```text
10%
15%
20%
25%
30%
```

Measure:

- average travel time,
- delay,
- rerouting count,
- route instability.

## Completion criteria

The system demonstrates that:

- small changes do not trigger unnecessary reroutes,
- significant degradation does,
- hysteresis reduces repeated switching,
- threshold choice can be evaluated experimentally.

---

# 9. STAGE 8 — SUMO TRAFFIC + ACCIDENT SCENARIOS

**Status: PENDING**

## Objective

Replace simple synthetic flow assumptions with reproducible traffic simulation.

## SUMO responsibilities

- vehicle demand,
- vehicle movement,
- traffic flow,
- normal vehicles,
- emergency vehicles,
- accident/incident scenarios.

## Tasks

1. Import/construct compatible road network.
2. Generate traffic demand.
3. Generate origins/destinations.
4. Add vehicle types.
5. Add emergency vehicles.
6. Inject accident events.
7. Extract vehicle/edge flow.
8. Feed projected/current flow into routing model.
9. Update road capacity for incidents.

## Accident model

An accident is represented as a capacity/availability disruption.

Example:

```text
accident
 ↓
lane/road capacity reduction
 ↓
BPR cost increase
```

or, if severe:

```text
road blocked
 ↓
edge unavailable
```

Do not invent real accident events and label them as real Chennai events.

## Completion criteria

A repeatable SUMO scenario produces traffic flow and incidents that can affect routing costs.

---

# 10. STAGE 9 — EMERGENCY VEHICLE PRIORITY

**Status: PENDING**

## Objective

Implement the separate emergency-routing rule.

## Normal vehicles

Use:

```text
dynamic cost
→ Dijkstra
→ threshold/hysteresis
```

## Emergency vehicles

Use:

```text
Emergency
 ↓
exclude BLOCKED
 ↓
avoid SEVERE where feasible
 ↓
shortest feasible physical-time route
```

Do not simply multiply normal congestion cost by a discount factor.

## Concurrent rerouting

Process:

```text
1. emergency vehicles
2. most degraded normal vehicles
3. remaining vehicles
```

After each selected route:

```text
update projected edge loads
 ↓
calculate next route
```

## Completion criteria

Emergency vehicles consistently receive priority under scenarios where competing routes exist, while blocked roads remain excluded.

---

# 11. STAGE 10 — FULL EVALUATION

**Status: PENDING**

## Objective

Determine whether the dynamic system actually improves routing outcomes compared with static Dijkstra.

## Baseline

```text
Static Dijkstra
→ route assigned once
→ no rerouting
```

## System under test

```text
Dynamic road conditions
→ dynamic edge costs
→ controlled rerouting
→ emergency priority
```

## Scenarios

At minimum test:

### Scenario A — Normal congestion

No flooding, no accident.

### Scenario B — Flood disruption

One or more susceptible roads become degraded/blocked.

### Scenario C — Flood + congestion

Flood disruption occurs while traffic is high.

### Scenario D — Accident

Capacity reduction/closure without flooding.

### Scenario E — Flood + accident + congestion

Combined disruption.

### Scenario F — Emergency vehicle

Emergency vehicle competes with normal traffic under disruption.

### Scenario G — Threshold sensitivity

Compare multiple rerouting thresholds.

### Scenario H — Hysteresis sensitivity

Compare route instability with/without hysteresis.

## Metrics

### Average travel time

### Total delay

### Congestion

For example, track road utilization and the proportion of roads exceeding selected congestion thresholds.

### Rerouting frequency

### Route instability

Track repeated route changes and back-and-forth switching.

### Blocked-road avoidance

Check whether routes use unavailable roads.

### Emergency response time

Measure emergency travel time from origin to destination.

## Completion criteria

Produce tables/plots comparing baseline and dynamic routing across controlled scenarios.

---

# 12. OPTIONAL SATELLITE/OBSERVED-FLOOD ENHANCEMENT

**Status: OPTIONAL — NOT REQUIRED FOR CORE**

Do not allow this feature to block the main project.

Possible sources:

- Sentinel-1 derived products
- NASA OPERA DSWx-S1
- existing Chennai satellite-derived flood maps

Possible pipeline:

```text
Observed surface-water extent
        ↓
Spatial overlay with roads
        ↓
Observed affected roads
        ↓
Confirm/escalate road state
```

Use this as:

- validation,
- observed-event confirmation,
- future enhancement.

Do not claim perfect road-level flood detection.

---

# 13. Data Quality Rules

Every AI/agent working on the project must follow these rules.

## Rule 1 — Never fabricate data

No invented flood locations, traffic counts, accidents, rainfall values, or road capacities.

## Rule 2 — Label simulated data

SUMO traffic and scripted accidents are:

```text
SIMULATED
```

## Rule 3 — Label historical data

Historical flood datasets are:

```text
HISTORICAL
```

not live conditions.

## Rule 4 — Label model assumptions

Capacity multipliers and thresholds are:

```text
MODEL PARAMETERS
```

unless empirically calibrated.

## Rule 5 — Preserve CRS

Every geospatial operation must verify coordinate reference systems.

## Rule 6 — Preserve provenance

Record:

```text
source
download date
dataset/product version when available
processing steps
```

## Rule 7 — Prefer reproducibility

Core experiments must work without paid APIs.

---

# 14. Novelty / Research Claim

The project must NOT claim:

> "We invented dynamic routing."

It must NOT claim novelty for:

- Dijkstra,
- BPR,
- dynamic routing,
- flood-aware routing,
- emergency routing,
- threshold rerouting,
- satellite flood mapping.

The defensible contribution is:

> **A Chennai-specific integration and evaluation framework that combines historical flood susceptibility, terrain/hydrological context, rainfall, optional observed inundation, congestion, and incidents into a common road-capacity model, followed by controlled dynamic rerouting and separate emergency-vehicle priority routing.**

The report should emphasize:

1. Chennai-specific application.
2. Unified capacity-based disruption model.
3. Historical + dynamic flood information.
4. Controlled rerouting rather than continuous route switching.
5. Separate emergency routing.
6. Experimental evaluation against static Dijkstra.

---

# 15. Explicit Non-Goals

Do not expand the core project into:

- pothole detection,
- dashcam computer vision,
- custom satellite deep-learning training,
- hydrodynamic flood simulation,
- reinforcement learning,
- full traffic equilibrium,
- proprietary API dependency,
- guaranteed live flood detection.

If these are discussed, classify them as future work.

---

# 16. Repository/Implementation Discipline

The final implementation should conceptually separate:

```text
data/
    road/
    flood/
    rainfall/
    elevation/
    hydrology/

preprocessing/
    road_processing
    flood_mapping
    rainfall_processing
    elevation_mapping

models/
    flood_susceptibility
    road_condition
    capacity
    bpr

routing/
    dijkstra
    dynamic_routing
    rerouting
    emergency

simulation/
    sumo
    scenarios

evaluation/
    baseline
    metrics
    experiments

visualization/
    maps
    routes
    plots
```

Exact filenames may change, but responsibilities should remain separated.

---

# 17. AI/Codex/Antigravity Execution Rules

When asking an AI coding agent to implement a stage:

1. Read `CONTEXT.md`.
2. Read this `PLAN.md`.
3. Identify the current stage.
4. Do not implement future stages unless explicitly requested.
5. Do not change locked architecture.
6. Use open/free sources first.
7. Verify dataset formats and licensing before depending on them.
8. Build small, testable functions.
9. Create a reproducible example/test.
10. Explain assumptions.
11. Report blockers rather than silently substituting fabricated data.
12. Update the stage status only after completion criteria are met.

---

# 18. Stage Status Tracker

| Stage | Description | Status |
|---|---|---|
| 1 | Monday proof of concept | **DONE** |
| 2 | Robust Chennai road graph | PENDING |
| 3 | Flood susceptibility | PENDING |
| 4 | GPM IMERG rainfall | PENDING |
| 5 | Dynamic flood/road state | PENDING |
| 6 | Capacity + BPR + Dijkstra | PENDING |
| 7 | Threshold + hysteresis | PENDING |
| 8 | SUMO + accidents | PENDING |
| 9 | Emergency routing | PENDING |
| 10 | Evaluation | PENDING |
| Optional | Satellite/observed flood confirmation | OPTIONAL |

---

# 19. Monday Agent Prompt

Use this as the first implementation prompt **after giving the agent `CONTEXT.md` and this `PLAN.md`**:

```text
You are implementing STAGE 1 — MONDAY PROOF OF CONCEPT of the Chennai Flood- and Congestion-Aware Dynamic Traffic Routing project.

READ THESE FIRST:
1. Chennai_Flood_Aware_Routing_Project_Context.md
2. PLAN.md

IMPORTANT:
- The architecture is LOCKED.
- Do not redesign the project.
- Do not add pothole detection.
- Do not add AI/computer vision unless explicitly required.
- Do not implement later stages.
- The goal is a small, reproducible proof of concept.

CURRENT PROJECT STATUS:
The Chennai road topology is NOT yet complete.

STAGE 1 GOAL:
Demonstrate this exact chain:

OpenStreetMap
→ Chennai road graph
→ one real open Chennai flood dataset
→ spatially map flood area/hotspot to affected road segments
→ mark affected road(s) as degraded or blocked
→ update effective capacity/state
→ update BPR travel-time cost
→ run Dijkstra
→ show that the selected route changes.

TASKS:

1. Inspect the current repository/workspace before creating files.
2. Set up only the dependencies required for Stage 1.
3. Download or obtain a manageable Chennai driving road network using OSMnx.
4. Validate that the graph is routable and contains geometry/length.
5. Obtain one real, openly available Chennai flood dataset.
6. Inspect its CRS, geometry type, attributes, and geographic coverage.
7. Convert the road graph into a GeoDataFrame if required.
8. Normalize CRS between the flood data and roads.
9. Perform a spatial intersection/nearest-road mapping between the flood data and road segments.
10. Produce a table identifying affected road IDs.
11. Mark affected roads as BLOCKED or DEGRADED based only on what the dataset supports. Do not invent physical measurements.
12. For the proof of concept, use a transparent simple capacity/state assumption.
13. Implement the BPR cost calculation for the road edges.
14. Select a controlled origin and destination with at least two plausible routes.
15. Compute the shortest route before the flood disruption.
16. Apply the flood disruption.
17. Recompute edge costs.
18. Compute the shortest route after the disruption.
19. Verify that the selected route changes. If the real flood data does not naturally produce a route change, create a clearly labelled controlled demonstration scenario by selecting/marking one affected edge from the real flood-mapped set. Do not fabricate a flood location.
20. Generate a clear visualization showing:
    - road network,
    - flood area/hotspot,
    - affected road,
    - origin,
    - destination,
    - before route,
    - after route.
21. Save a small CSV/table of affected road segments.
22. Add basic tests for:
    - CRS compatibility,
    - flood-to-road mapping,
    - blocked-edge exclusion,
    - route before/after.
23. Write a short README section explaining exactly what has been completed and what remains for Stage 2.

DO NOT IMPLEMENT:
- SRTM
- GPM IMERG
- drainage/water-body susceptibility
- satellite processing
- SUMO
- accidents
- emergency routing
- threshold/hysteresis
- full evaluation

Those belong to later stages.

DATA RULES:
- Use free/open data.
- Do not require paid APIs.
- Do not fabricate data.
- Clearly label historical flood data as historical.
- Clearly label any simulation/controlled scenario as simulated.
- Preserve dataset provenance and source information.
- Do not claim that historical flood data represents current flooding.

SUCCESS CRITERIA:
Stage 1 is complete only if:
1. A Chennai road graph can be generated.
2. A real Chennai flood dataset is loaded.
3. Flood data is mapped to road segments.
4. At least one affected road is identified.
5. The affected road changes the routing cost/state.
6. Dijkstra produces a different route before vs after the disruption.
7. A clear before/after visualization is generated.
8. The process can be reproduced from the repository.

At the end:
- summarize files created,
- summarize commands/run steps,
- list data sources,
- state assumptions,
- state known limitations,
- state exactly which Stage 1 success criteria passed,
- do NOT mark later stages as complete.
```

---

# 20. Definition of "Done"

The project is not "done" because a map looks good.

A stage is done when:

```text
Implementation
    +
Data provenance
    +
Test
    +
Reproducible output
    +
Clear explanation
```

all exist.

The final project is successful if the dynamic system demonstrates measurable improvement or useful trade-offs against static Dijkstra under controlled Chennai flood/congestion/incident scenarios, while honestly documenting its assumptions and limitations.
