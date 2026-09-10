# Project Context

## Project

**Certificate-Gated Dynamic Routing under Compound Urban Disruptions: A Reproducible Chennai-Oriented Framework**

## Research Goal

Evaluate how Chennai road routes should respond to flood, incident, and congestion changes while controlling:

- route computation and CCH metric-refresh cost;
- bounded represented-cost error;
- unnecessary route switching;
- projected congestion caused by recommendations;
- emergency response and ordinary-user external delay;
- access to critical facilities under partial compliance and uncertain data.

## Claim Boundary

The project does not claim to invent:

- a shortest-path algorithm;
- CCH, Dijkstra, A*, ALT, BPR, SUMO, or rerouting thresholds;
- lower-bound/upper-bound route certificates;
- flood-aware or emergency routing.

The defensible contribution is a Chennai-oriented integration and evaluation framework. The implemented certificate controller applies established bounded-suboptimality reasoning as a CCH metric-refresh gate.

Closest certificate prior art includes [CPD-Search](https://doi.org/10.24963/ijcai.2019/167), truncated incremental search, LazySP, and [CERT-FLOW](https://doi.org/10.31224/7306). Never claim the certificate principle as new.

## Technical Model

```text
road/flood evidence (Stage 1 demo / planned Stage 4)
→ explained road state
→ effective capacity  [implemented]
→ assigned demand / capacity  [Stage 1 uses labelled SCENARIO uniform flow]
→ BPR → integer milliseconds  [implemented glue]
→ certificate refresh gate  [implemented]
→ Dijkstra or prototype CCH  [implemented; city CCH not claimed]
→ adoption-threshold filter  [implemented SCENARIO policy]
→ projected load reservation  [unimplemented]
→ SUMO outcome  [unimplemented]
→ accessibility evaluation utilities  [implemented, no Chennai run]
```

### Path and Control Responsibilities

| Component | Responsibility |
|---|---|
| CCH | Prototype exact engine for finite integer metrics; not a city-scale production claim |
| Dijkstra | Correctness oracle and Stage 1/2 path engine |
| ALT-guided bidirectional A* | Unimplemented backup/comparator |
| Certificate controller | Engine-neutral gate: refresh or keep the synchronized metric |
| Stability policy | SCENARIO threshold/cooldown filter; reservations unimplemented |
| SUMO | Unimplemented on this branch |

## Certificate Assumptions

Let synchronized weights be \(\bar w\), current weights be \(w\), old exact distance be \(L\), and the old path's current cost be \(U\).

If:

\[
w_e\ge\bar w_e\quad\forall e,
\]

then \(L\le d_w(s,t)\le U\). Return the old path when:

\[
U\le(1+\epsilon)L.
\]

Any current weight below its synchronized value invalidates this lower bound and forces refresh unless another valid lower-bound metric is available.

The implemented controller uses complete fixed-topology snapshots and non-negative integer weights. Closures are +inf on Dijkstra and rejected on native CCH. Turn-expanded topology is unimplemented.

## Data Principles

- OSM supplies topology, not guaranteed complete speed/capacity data.
- OpenCity flood records are historical evidence, not current closures.
- IMERG is rainfall forcing, not street flood depth.
- SRTM/NASADEM is susceptibility context, not current flooding.
- SUMO output is simulated, not live Chennai traffic.
- Facility accessibility and population weighting are evaluation outcomes, not arbitrary route penalties.
- Paid/proprietary APIs are optional; the reproducible core remains open.

## Current Implementation

### Implemented

1. Stage 1 OSM/OpenCity flood-to-road closure proof of concept.
2. NetworkX Dijkstra metric engine.
3. Native `routingkit-cch` experimental engine.
4. Certificate-gated synchronizer with atomic versioned updates.
5. Eager-refresh baseline.
6. Deterministic synthetic experiment runner.
7. Population-weighted accessibility, partial-compliance, evidence-robustness, and facility-road-criticality utilities.
8. Differential, certificate, closure/recovery, parallel-edge, and CCH tests.
9. Integer BPR snapshot glue from explained states.
10. SCENARIO route-adoption filter: cooldown does not block degradation or infeasible incumbents.

### Preliminary Evidence

The main synthetic experiment used 200 nodes, 600 extra arcs, 100 update epochs, 5 updates and 50 queries per epoch.

- 55 tests pass with `.[cch]` installed.
- 20,000 main route queries across Dijkstra/CCH and monotone/mixed workloads produced zero certificate violations.
- Monotone CCH workload avoided 94 of 100 eager update refreshes.
- Mixed CCH workload avoided 14 of 100 because decreases invalidated the lower bound.

These results do not establish Chennai traffic outcomes.

### Planned

- stable dated Chennai graph and turn validation;
- flood/rainfall/road-state pipeline;
- Chennai SUMO demand/calibration;
- production CCH ordering and closure representation;
- stability and time-indexed projected reservations;
- facility/population data integration;
- emergency scenario and full ablations.

## Additional Evaluation Factors

Retain:

1. critical-facility accessibility;
2. population-weighted access loss;
3. partial-guidance compliance;
4. uncertainty and data-freshness sensitivity.
5. facility-oriented road criticality.

Do not add unsupported vehicle-specific flood depth or invented physical recovery rates to the core.

## Required Reading

Before changing implementation:

1. `CONTEXT.md`
2. `PLAN.md`
3. `README.md`
4. `docs/PROJECT_RESEARCH_AND_EVIDENCE.md`
5. `STAGE1_HANDOFF.md`

Implementation must distinguish completed evidence from planned work and must report negative results.
