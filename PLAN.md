# Project Execution Plan

**Authoritative research direction:** certificate-gated CCH routing under compound Chennai flood, incident, and traffic disruption.

## Status Summary

| Stage | Description | Status |
|---|---|---|
| 1 | Historical flood-to-road closure proof of concept | **DONE** |
| 2 | Certificate controller and routing-engine experiment | **DONE — preliminary synthetic evidence** |
| 3 | Reproducible Chennai graph | PENDING |
| 4 | Flood/rainfall road-state pipeline | PENDING |
| 5 | Chennai traffic and SUMO calibration | PENDING |
| 6 | Production Chennai CCH integration | PENDING |
| 7 | Stable projected-load rerouting | PENDING |
| 8 | Facility/population/compliance/criticality evaluation | PARTIAL — generic methods implemented |
| 9 | Emergency scenario | PENDING |
| 10 | Full experiments and publication package | PENDING |

## Stage 1 — Historical Flood Closure Proof of Concept

**Objective:** Demonstrate the data-to-road-to-route chain.  
**Inputs:** OSM road graph and OpenCity 2015 historical flood hotspots.  
**Method:** CRS-safe nearest-road mapping, controlled hard closure, effective capacity, BPR, two Dijkstra snapshots.  
**Evidence:** CSV/JSON/GraphML/PNG outputs and Stage 1 tests.  
**Status:** **DONE.**

**Claim limit:** It demonstrates closure avoidance, not calibrated congestion-sensitive routing or current flooding.

## Stage 2 — Certificate and Routing-Engine Validation

**Objective:** Validate bounded stale-metric routing and native CCH integration before city-scale work.  
**Implemented:**

- fixed-topology complete metric snapshots;
- exact keyed-edge NetworkX Dijkstra engine;
- native `routingkit-cch` finite-integer adapter;
- exact rational \(\epsilon\) certificate;
- atomic monotone/mixed weight updates;
- mandatory refresh when the stale lower bound is invalid;
- eager-refresh baseline;
- deterministic experiment traces and machine-readable results;
- 45 tests.

**Status:** **DONE as preliminary synthetic evidence.**

**Claim limit:** The certificate principle has close prior art. Results do not establish Chennai traffic outcomes, city-scale speed, turn handling, or closure-sentinel correctness.

## Stage 3 — Reproducible Chennai Graph

**Objective:** Build the exact graph used by the paper.

Tasks:

1. choose and justify study boundary;
2. obtain a dated OSM snapshot;
3. preserve stable keyed arcs and geometries;
4. validate direction, one-way rules, parallel arcs, grade separation, and connectivity;
5. document missing speed/lane handling;
6. derive free-flow times and baseline capacity assumptions;
7. save source date, checksum, software versions, and data dictionary.

Completion requires a graph that loads without a live OSM query and passes structural tests.

## Stage 4 — Flood and Road-State Evidence

**Objective:** Produce explained, timestamped road states.

**Current status:** Generic lag/false-positive/false-negative perturbation and
summary methods are implemented; Chennai evidence ingestion is pending.

Inputs:

- OpenCity historical flood/hazard evidence;
- SRTM/NASADEM;
- drains/water bodies when quality permits;
- IMERG 30-minute and rolling accumulation;
- optional verified closure/area-water evidence.

Output:

```text
edge_id
state = NORMAL / DEGRADED / SEVERE / BLOCKED
capacity_multiplier
source_time
confidence
expiry
reason
```

Completion requires historical replay, missing/stale-data tests, and no claim that rainfall or elevation alone proves road flooding.

## Stage 5 — Chennai Traffic and SUMO Calibration

**Objective:** Generate reproducible dynamic traffic and incidents.

Tasks:

1. import the Stage 3 graph into SUMO;
2. define heterogeneous Chennai vehicle classes;
3. construct documented OD demand;
4. calibrate/sensitivity-test behaviour against available Chennai studies;
5. convert assigned entering demand to compatible PCE/time units;
6. script normal, flood, incident, peak, and compound scenarios;
7. separate BPR estimated route cost from SUMO realized travel time.

Completion requires repeatable scenarios, seeds, queue/spillback outputs, and explicit simulation labels.

## Stage 6 — Production Chennai CCH Integration

**Objective:** Validate CCH on the real study graph.

Tasks:

- geometry-aware inertial/nested-dissection ordering;
- OSM-to-CCH node/arc mapping;
- turn-expanded or explicitly limited turn model;
- finite closure sentinel and overflow proof;
- integer quantization-error analysis;
- path-unpacking equality against Dijkstra;
- full and partial customization benchmark;
- query-to-update break-even analysis.

CCH remains interchangeable: if feasibility fails, use ALT-guided bidirectional A* and retain Dijkstra as oracle.

## Stage 7 — Stable Projected-Load Rerouting

**Objective:** Prevent route churn and self-created congestion.

Tasks:

1. implement degradation and minimum-gain triggers;
2. implement cooldown and infeasibility override;
3. place projected demand in estimated edge-entry time bins;
4. reserve load only for compliant vehicles;
5. apply the certificate after post-reservation metric updates;
6. compare greedy reservations with independent shortest paths and SUMO periodic rerouting.

Do not claim equilibrium or optimal fleet assignment.

## Stage 8 — Accessibility, Population, Compliance, and Road Criticality

**Objective:** Measure public-service impact.

Inputs:

- verified hospital/health-centre, fire-station, and relief-centre locations;
- WorldPop or validated ward population;
- scenario travel-time matrices.

Metrics:

- connected/disconnected population;
- p50/p90 nearest-facility travel time;
- population-weighted access loss;
- origins over 15/30-minute declared thresholds;
- exact seeded cohorts at 0%, 25%, 50%, 75%, and 100% compliance;
- directed arcs ranked by newly disconnected population and added facility travel time, then grouped by OSM way ID for physical-road reporting.

**Current status:** Generic metrics, deterministic compliance selection, evidence perturbation, and facility-road-criticality ranking are implemented; Chennai data integration is pending.

## Stage 9 — Emergency Scenario

**Objective:** Evaluate priority without unsupported signal control.

Policy:

1. safety/feasibility;
2. deadline slack and response time;
3. bounded ordinary-user external delay;
4. stable tie-breaking.

Measure emergency arrival, deadline success, severe-edge exposure, and normal-user harm. Do not claim traffic-signal preemption or live ambulance data.

## Stage 10 — Full Evaluation and Publication Package

### Baselines

- route-once Dijkstra;
- eager repeated Dijkstra;
- eager CCH;
- certificate-gated CCH;
- ALT-guided bidirectional A*;
- SUMO periodic routing;
- independent and projected-load-aware assignment.

### Required Scenarios

- dry/off-peak;
- dry/peak;
- flood only;
- incident only;
- flood + incident + peak demand;
- false-positive/delayed evidence;
- recovery/decrease;
- emergency request;
- compliance sensitivity.

### Required Ablations

- certificate on/off;
- CCH versus Dijkstra with identical policy;
- stability on/off;
- projected reservations on/off;
- emergency priority on/off;
- population weighting on/off.

### Required Reporting

- paired seeds and confidence intervals;
- preprocessing/customization/query/unpack/epoch timing;
- travel time, delay, queues, spillback, and completion;
- route churn and reversals;
- certificate hit/violation rate;
- facility access and population-weighted loss;
- source provenance and limitations;
- negative results.

Completion requires a clean-environment reproduction and a paper whose claims match generated evidence.

## Current Reproduction

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test,cch]"
python -m pytest
python scripts/run_certified_lazy_experiment.py --engine both --mode both
```

## Research Integrity Rules

1. Never call the certificate principle new.
2. Never call simulation live traffic.
3. Never call historical flood data current.
4. Never claim city-scale outcomes from synthetic graphs.
5. Never compare CCH and Dijkstra network outcomes under different policies.
6. Preserve full update, query, and path identity.
7. Report assumptions and negative results.
