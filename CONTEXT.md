# Project Context — Flood- and Congestion-Aware Dynamic Traffic Routing for Chennai

**Status:** LOCKED BASELINE  
**Purpose of this file:** This document is the persistent context for any future AI/Codex/Antigravity agent working on the project. An agent should read this file before modifying, implementing, researching, or proposing changes to the project.

---

## 1. Project Identity

### Working title

**Flood- and Congestion-Aware Dynamic Traffic Routing for Chennai using Time-Dependent Dijkstra with Threshold-Triggered Rerouting and Emergency Vehicle Preemption**

### Core goal — DO NOT CHANGE

Build a dynamic traffic-routing system for Chennai that adapts to:

- traffic congestion,
- accidents/incidents,
- monsoon waterlogging/flooding,

while:

- rerouting normal vehicles only when their current route becomes sufficiently worse,
- giving emergency vehicles a separate priority-routing treatment,
- evaluating the resulting system against a static-Dijkstra baseline.

The project is an **algorithms/routing project**. Data processing is used to generate dynamic road states and edge costs for the routing algorithm.

### Critical scope clarification

The project is **not a pothole-detection project**.

"Water mapping" means identifying/estimating **flooded or flood-prone road segments**, not detecting potholes.

Pothole/road-damage computer vision may be mentioned only as a possible future extension. It is not part of the locked core architecture.

---

# 2. Core Concept

The entire system follows this principle:

**Real-world/open data → road condition → effective road capacity → travel-time cost → routing decision**

The routing algorithm should not receive arbitrary "flood penalties" or unrelated scores. Flooding and accidents primarily affect the **effective capacity/availability of a road**, and the congestion model converts that condition into travel time.

The central chain is:

```text
DATA
  ↓
Road/environment/traffic conditions
  ↓
Road state
  ↓
Effective capacity
  ↓
BPR travel-time model
  ↓
Dynamic edge cost
  ↓
Dijkstra routing
  ↓
Threshold/hysteresis decision
  ↓
Controlled rerouting
```

Emergency vehicles follow a separate routing rule.

---

# 3. Locked System Architecture

## DATA LAYER

### 3.1 OpenStreetMap + OSMnx

**Purpose:** Build the Chennai road topology.

Provides/derives:

- road geometry,
- intersections,
- road segments,
- road class/type,
- length,
- lanes/speed attributes where available.

**Tools:**

- OpenStreetMap
- OSMnx
- GeoPandas
- NetworkX

**Output:** A directed road graph suitable for routing.

Conceptually:

```text
Nodes = intersections/locations
Edges = road segments
```

Each edge should eventually contain attributes such as:

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
effective_capacity
current_flow
road_condition
travel_time
```

Do not assume every OSM edge has every attribute. Missing values must be handled explicitly.

---

### 3.2 SRTM

**Purpose:** Terrain/elevation information.

SRTM is used to obtain elevation for locations/road segments.

**Tools:**

- rasterio
- GeoPandas
- Shapely

**Output example:**

```text
Road A → 14.2 m
Road B → 7.8 m
Road C → 3.9 m
```

Important interpretation:

> Low elevation does NOT mean a road is definitely flooded.

Elevation is a **flood-susceptibility feature**, not direct flood detection.

---

### 3.3 OpenCity Chennai flood datasets

**Purpose:** Historical/observed flood evidence.

Relevant information can include:

- flood hotspots,
- water-stagnation locations,
- crowdsourced flooding reports,
- inundation zones,
- inundation depth,
- flood hazard/return-period information.

These datasets are particularly valuable because they provide Chennai-specific evidence rather than generic global flood information.

Use them to determine whether a road has historical evidence of flooding and to validate the flood model.

**Processing tools:**

- GeoPandas
- Shapely
- KML/GeoJSON/GIS readers

**Important distinction:**

Historical flood data tells us that an area/road **has flooded before**. It does not automatically mean that it is flooded at the current moment.

Therefore:

```text
Historical flood evidence
        ↓
Flood susceptibility
```

not:

```text
Historical flood evidence
        ↓
Definitely flooded now
```

---

### 3.4 OpenCity drainage and water-body layers

**Purpose:** Add hydrological context.

Potential features:

- stormwater drains,
- drainage networks,
- canals,
- lakes/water bodies,
- basin/drainage information.

For each road segment, derive spatial features such as:

```text
distance to nearest drain
distance to nearest water body
```

These features contribute to flood susceptibility.

Do not claim that proximity alone proves flooding.

---

### 3.5 NASA GPM IMERG — PRIMARY RAINFALL SOURCE

**Purpose:** Dynamic rainfall trigger.

NASA GPM IMERG provides precipitation estimates at approximately 30-minute temporal intervals and is suitable for near-real-time and historical precipitation analysis.

This is the **primary rainfall layer** in the locked architecture.

Use rainfall to construct:

- recent 30-minute rainfall,
- rolling 3-hour rainfall,
- rolling 6-hour rainfall.

Conceptually:

```text
IMERG precipitation
       ↓
30-min rainfall
       ↓
rolling accumulation
       ↓
rainfall trigger
```

Rainfall is not itself the flood state.

It acts on the road's underlying susceptibility.

Example:

```text
High susceptibility + heavy rainfall
        ↓
higher current flood severity
```

versus:

```text
Low susceptibility + same rainfall
        ↓
lower current flood severity
```

### Important spatial limitation

IMERG precipitation is relatively coarse spatially compared with individual road segments. Therefore, the implementation should assign/interpolate rainfall from the relevant precipitation grid cell(s) to the road/network area rather than pretending IMERG directly measures rainfall on every individual road.

### OpenWeather

OpenWeather may remain an **optional live-weather extension**.

It is NOT a mandatory dependency for the core reproducible project because historical/API access can depend on subscription/product availability.

---

### 3.6 Sentinel-1 / NASA OPERA DSWx-S1 — OPTIONAL OBSERVED FLOOD CONFIRMATION

**Purpose:** Optional observed surface-water/inundation evidence.

Possible use:

```text
Satellite-derived water extent
        ↓
intersect with road network
        ↓
observed affected roads
```

The core project does **not** require training a new satellite AI model.

Use existing satellite-derived/open products when useful.

This is an enhancement/validation layer, not a dependency for the first implementation.

### Why optional?

Satellite surface-water products have spatial/temporal limitations and are not guaranteed to identify every narrow urban waterlogged road. Therefore they should not be represented as perfect road-level truth.

---

### 3.7 SUMO

**Purpose:** Generate and simulate traffic demand and incident scenarios.

SUMO is an open-source microscopic traffic simulator.

It will be used for:

- synthetic vehicle demand,
- vehicle movement,
- normal vehicles,
- emergency vehicles,
- accident/incident scenarios,
- traffic-flow simulation.

Why simulation?

A reliable public real-time per-road Chennai vehicle-count feed is not assumed to exist for this project. Therefore synthetic demand is explicitly part of the methodology.

Do not pretend simulated traffic is real traffic.

---

# 4. MODEL LAYER

## 4.1 Flood susceptibility

Each road segment receives a susceptibility representation based on static/historical characteristics.

Inputs:

```text
Historical flood evidence
+
Elevation
+
Drainage/water-body proximity
```

Output:

```text
Flood susceptibility
```

The score can be normalized, for example:

```text
0.0 = low susceptibility
1.0 = high susceptibility
```

But the score should be described as a **modelled susceptibility score**, not a statistically calibrated probability unless calibration data actually support that claim.

---

## 4.2 Current flood severity

Current conditions combine:

```text
Flood susceptibility
+
Current/recent rainfall
+
Optional observed flood extent
```

Output:

```text
Current flood severity
```

Use discrete road-condition states:

```text
NORMAL
DEGRADED
SEVERE
BLOCKED
```

The state model is intentionally easier to interpret than pretending to know exact water depth everywhere.

---

## 4.3 Road condition

Example conceptual states:

```text
NORMAL
    ↓
normal operation

DEGRADED
    ↓
reduced effective capacity

SEVERE
    ↓
strongly reduced effective capacity

BLOCKED
    ↓
edge unavailable
```

The exact capacity multipliers must be treated as **simulation/model parameters**, not universal physical truths.

For example, an initial experimental configuration might use:

```text
NORMAL  → 1.0
DEGRADED → 0.7
SEVERE → 0.3
BLOCKED → 0.0
```

These values must later be subjected to sensitivity analysis and should not be claimed as scientifically universal.

---

# 5. Effective Capacity Model

Every road has a baseline capacity:

```text
normal_capacity
```

Road conditions modify it:

```text
effective_capacity
    =
normal_capacity × condition_multiplier
```

Accidents can similarly reduce effective capacity.

For a blocked road:

```text
effective_capacity = 0
```

and the routing system should treat that edge as unavailable/infinite cost rather than trying to use it.

---

# 6. BPR Travel-Time Model

The BPR (Bureau of Public Roads) volume-delay function is used to convert traffic utilization into travel time.

Core form:

```text
t_e(x) = t0 × [1 + α × (x/c)^β]
```

Where:

- `t0` = free-flow travel time,
- `x` = current/projected traffic flow,
- `c` = effective road capacity,
- `α`, `β` = BPR parameters.

Important conceptual chain:

```text
Flood/accident
      ↓
effective capacity decreases
      ↓
x/c increases
      ↓
BPR travel time increases
      ↓
road becomes less attractive
```

Flooding does not need to be inserted as an arbitrary additive time penalty.

This keeps the cost model dimensionally interpretable and consistent with the project's original capacity-based mechanism.

---

# 7. Dynamic Edge Cost

The BPR result becomes the current edge travel-time cost.

Example:

```text
Road 101 → 4.2 min
Road 102 → 8.7 min
Road 103 → BLOCKED
Road 104 → 6.1 min
```

These costs can change as:

- traffic changes,
- rainfall changes,
- flood state changes,
- accidents occur,
- capacity changes.

---

# 8. Routing Layer

## 8.1 Normal vehicles

Normal vehicles use dynamic/time-varying Dijkstra.

The conceptual process:

```text
Origin + destination
        ↓
Current road-state graph
        ↓
Dijkstra
        ↓
Current best route
        ↓
Monitor route cost
        ↓
Has route degraded enough?
     /             \
   NO               YES
   ↓                 ↓
Continue          Reroute
```

---

## 8.2 Time-dependent terminology

The implementation should be precise about the phrase "time-dependent Dijkstra."

A true time-dependent shortest-path implementation has edge travel time that depends on the time at which the vehicle enters the edge.

If the implementation instead simply refreshes edge costs as network conditions change and reruns Dijkstra, it should be described accurately as **dynamic Dijkstra with time-varying edge costs**.

Do not claim a stronger time-dependent formulation unless the implementation actually supports it.

---

# 9. Threshold-Triggered Rerouting

Vehicles are not rerouted continuously.

Example:

```text
Original estimated route time = 20 min
New estimated route time = 25 min
```

Relative increase:

```text
(25 - 20) / 20 = 25%
```

If the initial threshold is 20%:

```text
25% > 20%
→ reroute
```

If:

```text
20 min → 21 min
```

then:

```text
5% increase
→ continue
```

### Important

20% is an **initial experimental parameter**, not a claim that 20% is universally optimal.

Later evaluate multiple thresholds, e.g.:

```text
10%
15%
20%
25%
30%
```

and compare:

- travel time,
- delay,
- reroute count,
- route instability.

---

# 10. Hysteresis / Minimum Improvement

A second protection should prevent route flip-flopping.

Without hysteresis:

```text
Route A slightly better
→ switch to A

A becomes slightly worse
→ switch to B

B becomes slightly worse
→ switch to A
```

The system should require a sufficiently meaningful improvement before switching.

This is intended to reduce unnecessary oscillation.

The exact hysteresis value is another experimental parameter.

---

# 11. Concurrent Rerouting

If multiple vehicles trigger rerouting at the same time:

### Priority order

1. Emergency vehicles
2. Vehicles with greatest route degradation
3. Remaining vehicles

After each vehicle selects a route:

```text
chosen route
     ↓
projected road load updated
     ↓
next vehicle computes route
```

This reduces the chance that many vehicles independently choose the same road because it appeared cheap before their collective effect was accounted for.

This is a sequential approximation; it does NOT guarantee system-wide traffic equilibrium.

---

# 12. Emergency Vehicle Routing

Emergency vehicles use a separate routing rule.

They do NOT simply receive a discount inside the normal congestion-weighted cost function.

Conceptual rule:

```text
Emergency vehicle
       ↓
Exclude BLOCKED roads
       ↓
Avoid SEVERELY degraded roads where possible
       ↓
Choose shortest feasible physical-time route
```

Emergency vehicles are processed before normal reroutes.

This is intended to represent priority/preemptive emergency routing without pretending to model every real-world traffic-signal control mechanism.

---

# 13. Simulation Layer

SUMO provides:

```text
Vehicle demand
     ↓
Traffic flow
     ↓
Incidents/accidents
     ↓
Changing road loads
     ↓
Routing feedback
```

The routing algorithm and simulation should remain conceptually separate:

```text
SUMO
= traffic environment

Routing system
= decision algorithm
```

This separation makes the project easier to test.

---

# 14. Evaluation

## Baseline

Use:

**Static Dijkstra**

Meaning:

```text
Calculate route once
      ↓
Vehicle keeps assigned route
      ↓
No dynamic rerouting
```

Compare it against:

**Our dynamic flood-aware system**

```text
Changing conditions
      ↓
Changing edge costs
      ↓
Controlled rerouting
      ↓
Emergency priority
```

---

## Metrics

### 14.1 Average travel time

Average time taken by vehicles.

Lower is generally better.

### 14.2 Total delay

Extra travel time compared with the chosen free-flow/reference baseline.

Lower is better.

### 14.3 Congestion

Measure utilization/congestion across road segments, such as the `x/c` ratio or a defined congestion threshold.

### 14.4 Rerouting frequency

How frequently vehicles receive new routes.

Too little may indicate slow adaptation.

Too much may indicate instability.

### 14.5 Route instability

Measure repeated switching or route changes.

Useful for evaluating the threshold/hysteresis design.

### 14.6 Blocked-road avoidance

Measure whether normal routing successfully avoids roads that are unavailable.

### 14.7 Emergency response time

Measure time taken by emergency vehicles to reach their destinations.

---

# 15. What Is Actually Novel?

Do NOT claim that the project invented:

- Dijkstra,
- dynamic routing,
- BPR,
- flood-aware routing,
- emergency routing,
- threshold-based rerouting,
- satellite flood mapping.

These are established areas.

The defensible contribution is:

> **A Chennai-specific integration and evaluation framework that combines historical flood susceptibility, terrain/hydrological context, rainfall, optional observed inundation, congestion, and incidents into a common road-capacity model, followed by controlled dynamic rerouting and separate emergency-vehicle priority routing.**

The novelty is therefore in the **specific integration, local application, modelling choices, and experimental evaluation**, not in inventing a new shortest-path algorithm.

---

# 16. Known Limitations

These limitations must remain visible rather than being hidden.

## 16.1 Flood susceptibility is not perfect flood prediction

Elevation + historical flooding + drainage context is an approximation.

## 16.2 Historical flood data is not live flood data

A historical flooded location does not prove it is flooded now.

## 16.3 Satellite products are not perfect road-level detectors

Surface-water products have spatial/temporal limitations.

## 16.4 Rainfall resolution is coarse

IMERG precipitation is much coarser spatially than individual road segments.

## 16.5 Capacity multipliers are modelling assumptions

Unless supported by calibration data, values such as 0.7 or 0.3 should be treated as simulation assumptions.

## 16.6 Synthetic traffic is not real Chennai traffic

SUMO demand is simulated because reliable public per-road vehicle counts are not assumed to be available.

## 16.7 No guaranteed global traffic equilibrium

Sequential per-vehicle rerouting can still produce localized flow oscillation.

## 16.8 No universal optimal rerouting threshold

The 20% threshold is an experimental starting point.

---

# 17. Explicitly Out of Scope

Unless the project is deliberately expanded later, do NOT add these to the core:

- pothole computer-vision detection,
- training a custom satellite flood-detection neural network,
- full hydrodynamic flood simulation,
- city-wide traffic equilibrium optimization,
- reinforcement learning,
- proprietary live traffic dependence,
- proprietary paid weather dependence,
- guaranteed real-time flood detection,
- pretending synthetic traffic is real traffic.

Optional future extensions should not destabilize the core implementation.

---

# 18. Free/Open-Source Technology Principle

The implementation should prioritize:

- OpenStreetMap
- OSMnx
- NetworkX
- GeoPandas
- Shapely
- rasterio
- SRTM
- OpenCity datasets
- NASA GPM IMERG
- Sentinel-1 / NASA OPERA products when useful
- SUMO
- Python

Paid/live APIs may be used only as optional extensions and must not be required for the reproducible core project.

---

# 19. Current Development Status

The road topology is **not yet completed**.

The first practical milestone is therefore not the complete system.

The first milestone is a small end-to-end proof of concept.

---

# 20. Monday Proof-of-Concept — LOCKED

The Monday demonstration should prove the following chain:

```text
OpenStreetMap
      ↓
Chennai road graph
      ↓
Open Chennai flood dataset
      ↓
Flood area/hotspot
      ↓
Identify affected road segments
      ↓
Affected road gets degraded/blocked state
      ↓
Effective capacity changes
      ↓
BPR cost changes
      ↓
Dijkstra route changes
```

### What the demo should show

1. A small/appropriate Chennai road network.
2. One real Chennai flood/inundation dataset.
3. Flood data spatially overlaid with the road network.
4. Identification of affected road segments.
5. At least one affected road being marked as degraded or blocked.
6. A before/after route comparison.
7. The route changes because the affected road becomes more expensive/unavailable.

### What does NOT need to be completed by Monday

- GPM IMERG rainfall integration
- SRTM integration
- drainage layer
- satellite confirmation
- SUMO
- accidents
- emergency vehicles
- threshold/hysteresis
- full evaluation
- live APIs

Those are later stages.

---

# 21. Recommended Implementation Philosophy

Build incrementally.

Do not attempt to build the entire project in one prompt.

Each stage should produce a testable artifact before the next stage begins.

Recommended dependency order:

```text
Road graph
   ↓
Flood overlay
   ↓
Affected-road identification
   ↓
Simple capacity-state model
   ↓
BPR
   ↓
Dijkstra
   ↓
Dynamic updates
   ↓
Threshold/hysteresis
   ↓
Rainfall
   ↓
SRTM/drainage susceptibility
   ↓
SUMO
   ↓
Emergency routing
   ↓
Evaluation
```

Do not replace the architecture simply because another dataset or technique is discovered.

If a new technology is considered, classify it as:

```text
CORE
OPTIONAL ENHANCEMENT
FUTURE EXTENSION
```

before incorporating it.

---

# 22. Context for Future AI/Codex/Antigravity Agents

Any future implementation agent should understand the following:

### The algorithm is the center of the project.

The data pipeline exists to generate meaningful changing edge conditions.

### The flood component is not pothole detection.

Flood/waterlogging is represented through geospatial flood evidence, susceptibility, rainfall, and optional observed inundation.

### Do not fabricate data.

If a real Chennai data source is unavailable, use simulation and explicitly label it as simulated.

### Do not fabricate precision.

If a dataset is coarse, say so.

If a capacity multiplier is an assumption, label it as a model parameter.

If a flood map is historical, label it historical.

### Prefer reproducibility.

A future student/agent should be able to clone/install dependencies, obtain permitted public datasets, run preprocessing, generate the graph, run scenarios, and reproduce the experiment.

### Keep modules separate.

Recommended conceptual modules:

```text
data/
preprocessing/
flood_model/
traffic/
routing/
simulation/
evaluation/
visualization/
```

The exact repository structure can be decided in the later implementation plan, but the separation of concerns should remain.

---

# 23. Final One-Line Mental Model

The whole project can be remembered as:

**ROAD → CONDITIONS → FLOOD/ROAD STATE → CAPACITY → BPR COST → DIJKSTRA → THRESHOLD → REROUTE → EVALUATE**

For emergency vehicles:

**EMERGENCY → PRIORITY RULE → FEASIBLE FASTEST ROUTE**

---

# 24. Final Locked Baseline

The project baseline is:

```text
DATA LAYER
─────────────────────────────────────────

OpenStreetMap + OSMnx
    → road topology + geometry + road class

SRTM
    → elevation

OpenCity Chennai flood datasets
    → historical flood/stagnation/inundation/depth evidence

OpenCity drainage/water-body layers
    → hydrological context

NASA GPM IMERG
    → primary rainfall + 30-min/3h/6h accumulation

Sentinel-1 / NASA OPERA DSWx-S1
    → optional observed flood confirmation

SUMO
    → synthetic traffic + accident scenarios


MODEL LAYER
─────────────────────────────────────────

Historical floods + elevation + drainage/water proximity
                         ↓
                 Flood susceptibility
                         +
                GPM IMERG rainfall
                         +
             Optional observed flooding
                         ↓
                Current flood severity
                         ↓
                 Road condition
          NORMAL / DEGRADED / SEVERE / BLOCKED
                         ↓
                Effective capacity
                         ↓
             Traffic flow + capacity
                         ↓
                       BPR
                         ↓
              Dynamic edge travel time


ROUTING LAYER
─────────────────────────────────────────

Normal vehicle
      ↓
Dynamic/time-varying Dijkstra
      ↓
Threshold + hysteresis
      ↓
Reroute only when sufficiently worse

Emergency vehicle
      ↓
Separate priority rule
      ↓
Exclude blocked/severely degraded roads
      ↓
Shortest feasible physical-time route


EVALUATION
─────────────────────────────────────────

Static Dijkstra
      VS
Dynamic flood-aware system

Average travel time
Total delay
Congestion
Rerouting frequency
Route instability
Blocked-road avoidance
Emergency response time
```

**This architecture is locked. Future planning documents should build on this context rather than redesign it.**
