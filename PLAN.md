# Evidence-Gated Project Execution Plan

## 1. Purpose

This is the operational plan for **Certificate-Gated Dynamic Routing under
Compound Urban Disruptions: A Reproducible Chennai-Oriented Framework**.

The plan separates:

- implementation completion;
- data acquisition completion;
- experimental validation completion; and
- claims that are safe for a paper.

A stage is not marked complete merely because code exists. It must satisfy its
evidence gate.

## 2. Assignment Model

The project is executed autonomously by the coding agent. Tasks are assigned to
one of three agent workstreams:

| Workstream | Assigned responsibility |
|---|---|
| **Data and provenance** | Acquire authentic sources, preserve unchanged inputs, record access time/version/licence/checksum, and reject unverifiable records |
| **Implementation** | Build typed, configurable pipelines without silent constants or hidden fallbacks |
| **Independent verification** | Test schemas, units, determinism, routing correctness, missingness, sensitivity, and claim-to-evidence consistency |

No task is silently delegated to the student. A task requiring unavailable
credentials, restricted data, or manual institutional verification is marked
`BLOCKED` or converted into an explicitly labelled sensitivity experiment.

## 3. Non-Negotiable No-Assumption Protocol

Every numerical value that can affect a result must be classified as exactly
one of:

1. **Observed:** read directly from a versioned source;
2. **Published:** taken from a cited source with matching context and units;
3. **Estimated:** fitted from declared data with a reproducible method;
4. **Scenario parameter:** deliberately varied over a reported range;
5. **Unavailable:** retained as missing and not silently imputed.

Each configurable scientific value must record:

```text
name
value or range
unit
classification = OBSERVED / PUBLISHED / ESTIMATED / SCENARIO / UNAVAILABLE
source reference
spatial and temporal scope
processing method
uncertainty or sensitivity treatment
```

Rules:

- no undocumented speed, capacity, flow, flood-depth, compliance, demand,
  recovery, or emergency-priority value;
- no conversion between vehicles, passenger-car equivalents, and rates without
  explicit units and interval;
- no missing OSM speed/lane value replaced by a universal default in the
  publication pipeline;
- no historical record described as live;
- no simulated outcome described as observed Chennai traffic;
- no rainfall or elevation value treated as proof of street flooding;
- no parameter selected only because it improves the proposed method;
- negative and infeasible results remain in the evidence package.

## 4. Stage Reporting and Critical Self-Review

At the start and end of every stage, the agent updates a status record and
reports:

1. **Inputs:** exact sources, versions, licences, checksums, units, and coverage;
2. **Work completed:** code, data transformations, and generated artifacts;
3. **Verification:** tests, independent comparisons, missingness, and failures;
4. **Assumptions audit:** all non-observed values and why they are allowed;
5. **Claim audit:** what the result supports and does not support;
6. **Decision:** `PASS`, `PASS WITH LIMITATIONS`, `BLOCKED`, or `FAIL`;
7. **Next action:** only work whose prerequisites passed.

If a gate fails, later work may continue only as a clearly labelled synthetic
or engineering experiment; it cannot be presented as Chennai validation.

## 5. Current Evidence Audit

| Stage | Implementation state | Evidence state | Current decision |
|---|---|---|---|
| 1. Controlled flood-to-road proof of concept | Implemented | Previous run recorded; source artifacts are mutable/ignored and constants are demonstration assumptions | **PASS WITH LIMITATIONS** |
| 2. Certificate/controller and prototype CCH | Implemented and tested | Deterministic synthetic evidence committed; no Chennai-scale or traffic claim | **PASS WITH LIMITATIONS** |
| 3. Reproducible Chennai graph | GCC boundary plus dated Geofabrik clip, pyrosm driving graph, and missingness audit implemented | 2022 GCC boundary passed with documented repair; india-260901.osm.pbf clipped and audited on 8 September 2026 | **PASS WITH REPORTED ATTRIBUTE MISSINGNESS** |
| 4. Flood/rainfall road-state evidence | Pinned OpenCity flood KMLs, Open-Meteo ERA5, coarse DEM, drain inventory, distance-sweep mapping, and scenario road-state rules implemented | Historical inventories mapped; rainfall/DEM do not create closures; BLOCKED/SEVERE are SCENARIO overlays | **PASS WITH LIMITATIONS** |
| 5. Chennai traffic and SUMO | GraphML-to-SUMO import, feasibility report, seeded random trips | No public counts/OD; OSM netconvert failed on SUMO 1.18; demand labelled SYNTHETIC | **PASS WITH LIMITATIONS** |
| 6. Chennai CCH integration | Inertial CCH, millisecond metric, finite closure sentinel, OSM-to-CCH maps | 24/24 unpacked costs matched Dijkstra; 20 scenario closures matched; turns not modelled | **PASS WITH LIMITATIONS** |
| 7. Stable projected-load rerouting | Placeholder module | No policy implementation or simulation comparison | **NOT STARTED** |
| 8. Accessibility/population/compliance/criticality | Generic utilities implemented | No Chennai facility/population integration or factor experiment | **PARTIAL** |
| 9. Emergency scenario | Placeholder module | No implemented priority policy or scenario | **NOT STARTED** |
| 10. Full evaluation/publication package | Preliminary method manifest only | Chennai/SUMO experiments and statistical package absent | **NOT STARTED** |

## 6. Stage-by-Stage Tasks and Gates

### Stage 1 — Controlled Historical Flood-to-Road Demonstration

**Objective:** Demonstrate the data-to-road-to-route chain on real Chennai
topology and historical flood evidence.

| Task | Assignment | Required output | State |
|---|---|---|---|
| S1.1 Download OpenCity 2015 hotspot KML and metadata | Data and provenance | Raw KML plus provenance | Implemented |
| S1.2 Download local OSM driving graph and map hotspots in a metric CRS | Implementation | Graph, mapped arcs, distance fields | Implemented |
| S1.3 Apply one controlled closure and compare routes | Implementation | Before/after routes and costs | Implemented |
| S1.4 Test CRS, mapping, capacity/BPR, and closure avoidance | Independent verification | Automated tests | Implemented |
| S1.5 Re-run with pinned inputs and archive checksums/configuration | Data and provenance | Publication manifest | Pending |

**Gate:** The implementation stage is complete. It becomes publication-grade
evidence only when S1.5 passes. The `150 m` mapping distance, `30 km/h` missing
speed, capacity `1200`, flow `600`, and closure are controlled demonstration
parameters—not calibrated Chennai values.

### Stage 2 — Certificate and Prototype Routing-Engine Validation

**Objective:** Validate the certificate controller and prototype CCH adapter on
deterministic fixed-topology workloads.

| Task | Assignment | Required output | State |
|---|---|---|---|
| S2.1 Implement immutable complete metric snapshots and versioning | Implementation | Engine-neutral snapshots | Complete |
| S2.2 Implement exact keyed-edge Dijkstra oracle | Implementation | NetworkX engine | Complete |
| S2.3 Implement finite-integer native CCH adapter | Implementation | RoutingKit engine | Complete |
| S2.4 Implement rational certificate, atomic updates, and mandatory refresh | Implementation | Synchronizer | Complete |
| S2.5 Compare with eager refresh under identical traces | Independent verification | Per-query and summary evidence | Complete |
| S2.6 Test parallel edges, decreases, overflow bounds, path equality, and violations | Independent verification | Automated tests | Complete |

**Gate:** Implementation complete; evidence is preliminary and synthetic. The
certificate principle is established prior art. This stage does not validate
Chennai performance, turn restrictions, city-scale CCH, or traffic benefits.

### Stage 3 — Reproducible Greater Chennai Road Graph

**Objective:** Produce the exact offline-loadable road graph used by all later
stages.

| Task | Assignment | Required output |
|---|---|---|
| S3.1 Fix the study boundary to the union of the OpenCity/GCC **2022 200-ward KML**, resource `e90176d4-319a-45bd-918e-ecce4f048c4d`, whose CKAN record identifies GCC as the organization and the resource source as `chennaicorporation.gov.in` | Data and provenance | Unchanged KML, metadata JSON, checksum, feature-count and geometry report |
| S3.2 Acquire a dated OSM source. Preferred publication source: a date-stamped Geofabrik India PBF with its provider checksum/header timestamp, clipped to S3.1. A cached Overpass extraction may be used for development but does not satisfy the publication gate by itself | Data and provenance | Raw source manifest and Chennai extract |
| S3.3 Build a directed keyed graph while preserving OSM node, way, key, geometry, direction, bridge, tunnel, layer, access, lane, and speed tags | Implementation | Versioned GraphML/Parquet plus data dictionary |
| S3.4 Create deterministic arc identifiers from source identity and direction; prove insertion-order stability and detect collisions | Implementation and verification | Arc-ID module and tests |
| S3.5 Audit coordinates, positive lengths, duplicate/parallel arcs, one-way direction, weak/strong connectivity, components, self-loops, and grade-separation tags | Independent verification | Machine-readable quality report |
| S3.6 Parse only explicit/legally inferred speed information. Report missing/invalid speed and lane coverage without a universal fallback | Implementation | Attribute-coverage report |
| S3.7 Derive free-flow time only where length and defensible speed are available; leave unresolved values missing | Implementation | Unit-checked fields and unresolved-edge list |
| S3.8 Save software versions, commands, configuration, checksums, counts, boundary coverage, and a small QA map | Data and provenance | Stage 3 evidence manifest |

**Completion gate:**

- graph and boundary load without internet;
- every artifact has source URL, retrieval/version date, licence, and SHA-256;
- all retained routable arcs have valid geometry, direction, and positive length;
- deterministic IDs have no collisions;
- missing speed/lane/access/turn information is quantified, not hidden;
- no city-wide free-flow or capacity claim is made for unresolved arcs;
- a second run from the same raw inputs produces matching topology and IDs.

**Critical risk:** An OSM graph alone is not a calibrated traffic network.
Turn restrictions and capacities remain gates for Stages 5–6.

**Current checkpoint:** S3.1–S3.8 passed on 8 September 2026 with reported
attribute missingness. The dated Geofabrik extract
`https://download.geofabrik.de/asia/india-260901.osm.pbf` (Last-Modified
Wed, 02 Sep 2026 05:19:21 GMT; provider MD5
`44ec6a7dff8ff2f3382da80a546b505f`) was clipped to the GCC 2022 union with
osmium `smart` strategy after stripping KML Z=0 coordinates. The clipped
driving graph has 155,345 nodes and 331,545 directed arcs, one weakly and one
strongly connected component, no self-loops, no arc-ID collisions, and no
invalid lengths. Explicit OSM maxspeed is present on 6,092 arcs (about 1.8%);
325,453 arcs have missing maxspeed and therefore no Stage 3 free-flow time.
Lanes are missing on 318,131 arcs. 2,447 nodes lie outside the union because
osmium retains complete ways that cross the boundary. These counts are
topology/attribute facts, not a calibrated traffic network. Turn restrictions
and capacities remain Stages 5–6 gates.

The earlier S3.1 boundary checkpoint remains: 200 uniquely named wards, 9
invalid source geometries repaired, total absolute area change
1.8690520445816219 square metres in EPSG:32644, source SHA-256
`be48ef7eb4320279e790f59da1691ece9efc92b34459ca73c492957943c347e0`.

### Stage 4 — Flood, Rainfall, Freshness, and Road-State Evidence

**Objective:** Create timestamped, explained evidence features and road states
without claiming that indirect evidence is observed street flooding.

| Task | Assignment | Required output |
|---|---|---|
| S4.1 Pin OpenCity historical flood resources and verify geometry/schema/checksums | Data and provenance | Raw historical evidence manifest |
| S4.2 Acquire no-key historical rainfall for the selected event window; add IMERG only when Earthdata access is available and record product/version | Data and provenance | Timestamped rainfall series |
| S4.3 Acquire elevation/hydrology context with product/version/vertical datum documented | Data and provenance | Terrain-context layers |
| S4.4 Align time zones, intervals, CRS, nodata, and spatial support | Implementation | Validated feature table |
| S4.5 Preserve evidence separately as `OBSERVED`, `HISTORICAL_INVENTORY`, `MODELLED`, or `PROXY` | Implementation | Evidence classification |
| S4.6 Map evidence to arcs using source-accuracy-aware matching; where accuracy is unknown, sweep matching distance instead of choosing one value | Implementation and verification | Mapping-sensitivity report |
| S4.7 Produce `UNKNOWN/NORMAL/DEGRADED/SEVERE/BLOCKED` only from declared rules; uncalibrated capacity multipliers remain scenario ranges | Implementation | Explained road-state table |
| S4.8 Inject measured/declared delay, missingness, false-positive, and false-negative scenarios | Independent verification | Freshness/uncertainty evidence |

**Completion gate:** Every state includes source time, retrieval time,
classification, confidence basis, expiry rule, reason, and provenance. There
must be explicit tests for stale/missing/conflicting evidence and recovery.

### Stage 5 — Chennai Traffic Evidence and SUMO Scenario Calibration

**Objective:** Build reproducible traffic scenarios and distinguish observed
inputs from simulated outcomes.

| Task | Assignment | Required output |
|---|---|---|
| S5.1 Inventory available Chennai counts, speeds, travel times, OD evidence, vehicle composition, and incident records with licence and temporal coverage | Data and provenance | Traffic-data feasibility report |
| S5.2 Import the validated Stage 3 graph into SUMO and report conversion losses | Implementation | SUMO network plus loss report |
| S5.3 Build vehicle classes only from sourced composition evidence; unsupported classes remain scenario labels | Implementation | Vehicle-type configuration |
| S5.4 Build OD demand from available evidence. If no observed OD/count data is available, use a labelled synthetic demand family and do not claim calibration | Implementation | OD matrices with provenance class |
| S5.5 Fit or sensitivity-test demand, car-following, lane-changing, PCE, BPR, and capacity values; never select one undocumented default | Implementation and verification | Calibration/sensitivity report |
| S5.6 Script dry, peak, flood, incident, compound, recovery, and evidence-error scenarios with fixed seeds | Implementation | Reproducible scenarios |
| S5.7 Compare simulated counts/speeds/travel times with held-out observations where available | Independent verification | Validation errors and limitations |

**Completion gate:** SUMO runs are deterministic by seed, units are explicit,
queue/spillback outputs are captured, and the paper labels the result
`CALIBRATED`, `PARTIALLY CALIBRATED`, or `SYNTHETIC` from actual validation
evidence.

**Stop condition:** Without independent Chennai traffic observations, this
stage can support scenario analysis but not claims of Chennai traffic
prediction accuracy.

### Stage 6 — Chennai CCH Integration and Differential Validation

**Objective:** Establish whether CCH is correct and worthwhile on the Stage 3
network.

| Task | Assignment | Required output |
|---|---|---|
| S6.1 Create geometry-aware ordering and exact OSM-to-CCH node/arc maps | Implementation | Reproducible CCH topology |
| S6.2 Implement turn-expanded restrictions or explicitly restrict the evaluated topology to the supported turn model | Implementation | Turn-model decision and tests |
| S6.3 Define integer quantization from measured time units and bound its route-cost error | Implementation and verification | Quantization proof/report |
| S6.4 Validate finite closure representation and accumulated-path overflow limits | Independent verification | Adversarial tests |
| S6.5 Compare unpacked CCH paths/costs with Dijkstra on identical metrics, OD pairs, parallel arcs, closures, and recovery | Independent verification | Differential report |
| S6.6 Benchmark preprocessing, ordering, customization, partial update if supported, query, unpacking, and memory | Independent verification | City-scale benchmark |
| S6.7 Compute query/update break-even regions; retain CCH only where evidence supports it | Independent verification | Engine-selection decision |

**Completion gate:** Zero unexplained path/cost mismatches in the declared
model and a measured workload region where CCH is justified. Otherwise,
ALT-guided bidirectional A* becomes the primary candidate and Dijkstra remains
the oracle.

**Current checkpoint:** S6.1–S6.7 passed with limitations on 8 September 2026.
Inertial ordering used OSM `y`/`x` as WGS84 latitude/longitude. OSM-to-CCH
maps for 155,345 nodes and 331,545 arcs are at
`data/processed/cch/stage6_osm_to_cch_maps.json` (SHA-256
`4ac8e689f1ed1f58c7e4ff372d5615357d116f0b204abb02f6c3afc694311d2d`; not
committed). The turn model is **RESTRICTED_TOPOLOGY_NO_TURN_EXPANSION**:
restriction relations are UNAVAILABLE on the Stage 3 graph. Travel times are
integer milliseconds; 6,092 arcs use OBSERVED OSM maxspeed and 325,453 use a
labelled SCENARIO 30 km/h default. Per-arc rounding error is at most 0.5 ms.
Overflow uses a geographic-diameter SCENARIO bound of 137,418,160 ms (bbox
diagonal 47.7 km at 5 km/h with detour factor 4), not the n−1 hop product.
Seed 8597, 24 OD pairs: unpacked CCH costs matched NetworkX Dijkstra on all
24 queries (0 mismatches). Twenty Stage 4 BLOCKED scenario arcs as a finite
sentinel produced 0 oracle mismatches and 0 unpacked paths that used a closed
arc; recovery also matched. Mean query: CCH 0.443 ms (80 queries) versus
NetworkX Dijkstra 160.3 ms (24 queries). Inertial order 2.75 s, CCH construct
1.66 s, full customize 0.313 s, in-place reset 0.175 s. CCH is retained for
repeated queries on this represented metric relative to the NetworkX Dijkstra
oracle. This is not a calibrated traffic result, not a turn-restricted router,
and not a comparison with a tuned C++ Dijkstra.

### Stage 7 — Stable, Projected-Load-Aware Rerouting

**Objective:** Reduce route churn and recommendation-created congestion.

| Task | Assignment | Required output |
|---|---|---|
| S7.1 Implement infeasibility, degradation, minimum-gain, and cooldown rules as configurable policies | Implementation | Policy module and state-machine tests |
| S7.2 Source policy thresholds or evaluate preregistered ranges; do not tune on final outcomes | Data and provenance | Parameter provenance/sweep |
| S7.3 Reserve compliant-vehicle demand in estimated edge-entry time bins with explicit units | Implementation | Reservation ledger |
| S7.4 Recompute post-reservation metrics before applying the certificate | Implementation and verification | Ordering/invariant tests |
| S7.5 Compare route-once, independent rerouting, periodic SUMO rerouting, and projected reservations under identical demand | Independent verification | Paired experiment |
| S7.6 Report churn, reversals, detours, queues, spillback, completion, and negative externality | Independent verification | Stability evidence |

**Completion gate:** Policy invariants pass and benefits persist across declared
threshold/compliance ranges. Do not claim equilibrium or fleet-optimal
assignment.

### Stage 8 — Critical Facilities, Population, Compliance, and Road Criticality

**Objective:** Measure service-access consequences rather than adding arbitrary
population penalties to route cost.

| Task | Assignment | Required output |
|---|---|---|
| S8.1 Acquire and checksum OpenCity/OSM hospital, fire-station, and GCC relief-centre sources | Data and provenance | Facility catalogue manifest |
| S8.2 Validate facility type, coordinates, duplicates, operating-status evidence, and boundary membership; unverifiable entries are flagged/excluded | Independent verification | QA catalogue |
| S8.3 Acquire the matching WorldPop raster/version or an explicitly documented ward-population source | Data and provenance | Population manifest |
| S8.4 Align raster year, CRS, nodata, grid support, and analysis zones; conserve represented population during aggregation | Implementation and verification | Population QA report |
| S8.5 Snap facilities/origins to eligible graph components with reported distances and exclusion reasons | Implementation | Snapped analysis inputs |
| S8.6 Compute nearest-facility disconnection, p50/p90 travel time, and population-weighted access loss | Implementation | Scenario metrics |
| S8.7 Treat service-time thresholds as cited or sensitivity values, not universal facts | Independent verification | Threshold sensitivity |
| S8.8 Run exact seeded compliance cohorts from 0–100%; include multiple seeds unless cohort endpoints are deterministic | Implementation and verification | Compliance curves |
| S8.9 Rank directed keyed arcs by facility-access loss, then group by OSM way ID for physical-road reporting | Implementation | Criticality ranking |

**Completion gate:** Facility and population exclusions are reported; baseline
and disruption use the same population/facility support; uncertainty is
propagated; no criticality claim is based only on one arbitrary threshold.

### Stage 9 — Emergency-Vehicle Scenario

**Objective:** Evaluate a transparent priority policy without pretending to
have live ambulance operations or signal pre-emption.

| Task | Assignment | Required output |
|---|---|---|
| S9.1 Represent ambulance/fire vehicles as declared SUMO scenario classes; tags identify policy treatment, not verified live vehicles | Implementation | Emergency class schema |
| S9.2 Implement safety/feasibility first, then deadline slack/response time, bounded ordinary-user delay, and deterministic tie-breaking | Implementation | Priority policy |
| S9.3 Source deadlines/service targets when available; otherwise evaluate labelled ranges | Data and provenance | Target provenance/sensitivity |
| S9.4 Compare priority on/off with identical incidents, demand, evidence, and seeds | Independent verification | Paired emergency experiment |
| S9.5 Measure arrival, deadline success, severe-edge exposure, reroutes, and ordinary-user external delay | Independent verification | Emergency results |

**Completion gate:** Priority logic is reproducible and reports both emergency
benefit and ordinary-user harm. Manual class tags are acceptable for a
controlled simulation; they are not real-fleet validation.

### Stage 10 — Full Evaluation and Publication Package

**Objective:** Produce auditable evidence whose claims match the implemented
scope.

| Task | Assignment | Required output |
|---|---|---|
| S10.1 Freeze scenarios, hypotheses, metrics, seeds, and exclusions before final comparison | Data and provenance | Experiment specification |
| S10.2 Run route-once Dijkstra, eager Dijkstra, eager CCH, certificate-gated CCH, justified ALT comparator, SUMO periodic routing, and assignment ablations where feasible | Implementation | Baseline matrix |
| S10.3 Run dry/peak/flood/incident/compound/recovery/emergency/compliance/error scenarios with paired seeds | Implementation | Full result set |
| S10.4 Run certificate, engine, stability, reservation, priority, population, and evidence-quality ablations | Independent verification | Ablation matrix |
| S10.5 Report confidence intervals/effect sizes where repeated stochastic simulation exists; never manufacture sample size | Independent verification | Statistical report |
| S10.6 Reproduce from a clean environment and verify every table/figure against machine-readable results | Independent verification | Reproduction log |
| S10.7 Update paper, data statement, limitations, citation search, and claim matrix | Data and provenance | Submission package |

**Completion gate:** All reported values are generated from preserved
artifacts; every claim maps to a result; limitations include data age,
simulation status, OSM/facility completeness, calibration quality, and
algorithmic prior art.

## 7. Execution Order

The strict dependency chain is:

```text
Stage 3 boundary + graph
→ Stage 4 evidence features
→ Stage 5 traffic/SUMO inputs
→ Stage 6 city CCH validation
→ Stage 7 rerouting policy
→ Stage 8 social-impact evaluation
→ Stage 9 emergency scenario
→ Stage 10 full evaluation
```

Parallel work is permitted only when it does not bypass a gate:

- facility and WorldPop acquisition may begin while Stage 4 is developed;
- synthetic unit tests for Stages 6–9 may begin before city data is ready;
- city-level outcome claims wait for Stages 3–9.

## 8. Immediate Execution

The next authorized work is Stage 7:

1. implement infeasibility, degradation, minimum-gain, and cooldown policies;
2. keep thresholds as cited or preregistered ranges, not outcome-tuned values;
3. do not claim Chennai traffic improvement until SUMO comparisons exist.

## 9. Research Integrity Summary

1. Certificate-gated synchronization is not a replacement shortest-path
   algorithm; CCH is the proposed engine and Dijkstra is the oracle.
2. Stages 1 and 2 are implemented, but their current evidence scopes remain
   controlled-demo and preliminary-synthetic respectively.
3. Manual emergency class tags are valid simulation controls, not evidence of
   live ambulance validation.
4. Historical Chennai data can support retrospective evaluation, not a live
   deployment claim.
5. A medium-strength integration/evaluation contribution becomes defensible
   only after the staged evidence gates pass.
