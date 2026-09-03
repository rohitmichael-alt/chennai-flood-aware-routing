# Algorithm Research, Novelty Audit, and Routing Engine Decision

**Project:** Flood- and Congestion-Aware Dynamic Traffic Routing for Chennai  
**Research cutoff:** 3 September 2026  
**Scope of this document:** Research and recommendation only. No routing implementation has been replaced.

## 1. Executive Summary

Stage 1 is a valid, reproducible proof of concept, but it is much smaller than the proposed final system. It downloads a small Chennai OpenStreetMap (OSM) graph, maps historical 2015 flood hotspots to nearby roads, assigns one mapped edge a controlled `BLOCKED` state, converts that state to zero effective capacity and infinite BPR travel time, and reruns NetworkX Dijkstra. It does **not** yet ingest rainfall, model current flooding, simulate traffic, process incidents, implement emergency priority, or control rerouting.

The current implementation is **snapshot dynamic shortest-path routing with refreshed edge weights**, not a formal time-dependent shortest-path algorithm. The edge cost used during a query is a scalar. It does not depend on the time at which a vehicle enters that edge.

### Decision

**Primary recommendation: Customizable Contraction Hierarchies (CCH).**

CCH separates:

1. expensive, weight-independent preprocessing of the road topology;
2. comparatively fast customization when BPR/flood/incident weights change; and
3. fast hierarchical route queries.

That workflow matches this project better than repeatedly searching the full Chennai graph after every update. CCH was specifically designed for road networks with changing metrics ([Dibbelt, Strasser, and Wagner, 2016](https://doi.org/10.1145/2886843)). It is exact for the customized non-negative scalar metric. It is not a new algorithm and is not, by itself, the project's novelty.

**Backup recommendation: D* Lite.**

D* Lite incrementally repairs a previous route after local edge-cost changes and is easier to implement in pure Python ([Koenig and Likhachev, 2002](https://cdn.aaai.org/AAAI/2002/AAAI02-072.pdf)). It is a reasonable fallback for a corridor, one vehicle/OD pair, and sparse closures. It is less suitable than CCH when BPR updates change many edges or many unrelated origin-destination queries must be answered.

### Defensible novelty

The broad ideas are already established: flood-aware routing, congestion-aware routing, BPR, dynamic replanning, D* Lite, CCH, emergency routing, rerouting thresholds, and hysteresis. A 2017 paper also already studied post-disaster vehicle routing for the Chennai floods ([Ganguly and Roy, 2017](https://doi.org/10.1109/ICT-DM.2017.8275694)).

The strongest defensible contribution is therefore:

> A reproducible Chennai-specific framework that translates heterogeneous flood, incident, and congestion evidence into a common effective-capacity/BPR metric, batch-customizes a modern road-network routing index, and evaluates event-triggered, stability-aware, priority-sensitive rerouting while accounting for the extra load created by rerouted vehicles.

The **combination appears underexplored** in the reviewed literature. That is not proof that nobody has done it. The paper must not claim “first” without a formal systematic review, expert review, and an updated search immediately before submission.

### Data correction

OpenWeather is **not completely paid**. Its official pricing pages list a permanent free plan for current weather and a 5-day/3-hour forecast. The separate One Call 4.0 product includes 1,000 calls/day at no charge within a pay-as-you-call subscription, with charges above that allowance ([official pricing](https://openweathermap.org/full-price), [One Call FAQ](https://openweathermap.org/faq)). An account/API key is required, and historical/bulk capabilities vary by product. NASA GPM IMERG should remain the primary rainfall source because it is open, reproducible, 30-minute, globally gridded precipitation data; OpenWeather is only an optional live-weather convenience layer.

## 2. Current Stage 1 Assessment

### 2.1 What is implemented

The active pipeline is in [`src/chennai_routing/stage1_poc.py`](../src/chennai_routing/stage1_poc.py):

1. Fetch OpenCity CKAN metadata and the Chennai 2015 GCC flood-hotspot KML.
2. Parse 327 historical point locations into EPSG:4326.
3. Center a small OSM driving-network query on the first usable point.
4. Add OSM speed and free-flow travel-time attributes.
5. Project flood points and roads to a local metric CRS.
6. Map historical points to nearest roads within 150 m.
7. Assign every road the same demonstration flow (`600`) and normal capacity (`1200`).
8. Mark one real flood-mapped edge `BLOCKED` in a controlled scenario.
9. Convert `BLOCKED` to zero capacity, hence infinite BPR travel time.
10. Run Dijkstra before and after the blockage.
11. Save GraphML, CSV, JSON, and a route-change map.

The selected origin and destination are the endpoints of the affected edge. This deliberately forces a small before/after demonstration; it is not a representative Chennai trip experiment.

### 2.2 Where Dijkstra is used

[`src/chennai_routing/routing/dijkstra.py`](../src/chennai_routing/routing/dijkstra.py) calls:

```python
nx.shortest_path(graph, origin, destination, weight=weight, method="dijkstra")
```

[`src/chennai_routing/stage1_poc.py`](../src/chennai_routing/stage1_poc.py) imports this helper and queries the unblocked and blocked copies of the graph. [`tests/test_stage1_poc.py`](../tests/test_stage1_poc.py) imports the same helper for a four-node route-change test.

### 2.3 Current edge weights

For edge \(e\):

\[
t_e=t^0_e\left[1+\alpha\left(\frac{x_e}{c^{eff}_e}\right)^\beta\right]
\]

where:

- \(t^0_e\) is OSMnx travel time, or length divided by a 30 km/h fallback;
- \(x_e=600\) for every edge in Stage 1;
- \(c_e=1200\) for every edge in Stage 1;
- \(c^{eff}_e=c_e m(s_e)\);
- \(m(\text{NORMAL})=1\), \(m(\text{DEGRADED})=0.7\), \(m(\text{SEVERE})=0.3\), and \(m(\text{BLOCKED})=0\);
- \(\alpha=0.15\), \(\beta=4\).

These values are demonstration parameters, not Chennai-calibrated measurements. BPR is implemented in [`src/chennai_routing/models/bpr.py`](../src/chennai_routing/models/bpr.py), and capacity multipliers are in [`src/chennai_routing/models/capacity.py`](../src/chennai_routing/models/capacity.py).

### 2.4 Representation status

| Component | Current representation | Status |
|---|---|---|
| Flood | Historical point mapped to nearest road; chosen edge forced `BLOCKED` | Implemented controlled demo |
| Congestion | One fixed flow and capacity for all edges, then BPR | Demonstration only |
| Accident/incident | Planned capacity reduction or closure | Not implemented |
| Rainfall | Planned IMERG 30-minute/3-hour/6-hour features | Stub only |
| Susceptibility | Planned history + elevation + hydrology score | Stub only |
| Dynamic road state | Planned `NORMAL/DEGRADED/SEVERE/BLOCKED` rules | Stub only |
| SUMO | Planned edge flows and scripted incidents | Stub only |
| Threshold/hysteresis | Planned controlled rerouting | Stub only |
| Emergency priority | Planned separate feasible-fastest routing | Stub only |
| Evaluation | Planned baseline/scenario metrics | Stub only |

### 2.5 What can be preserved

Preserve:

- OSM/OSMnx graph acquisition and GraphML persistence;
- flood KML acquisition, parsing, and provenance;
- CRS validation and nearest-road mapping;
- road-condition vocabulary;
- effective-capacity interface;
- BPR function and tests, while recalibrating parameters later;
- output tables/maps and the controlled affected-edge scenario;
- separation among data, models, routing, simulation, evaluation, and visualization.

Change later:

- replace the routing helper behind a stable router interface;
- add stable integer arc IDs and graph-to-CCH arrays;
- distinguish topology preprocessing, metric customization, and route query;
- provide changed-edge batches after road-state/BPR updates;
- implement real per-edge or simulated flow instead of constants;
- implement route-allocation, threshold, hysteresis, and emergency policies outside the shortest-path engine;
- record engine/customization/query timings.

Nothing in the GIS or flood-preprocessing pipeline needs to be destroyed.

## 3. Is the Current Method Actually Time-Dependent?

### 3.1 Formal distinction

A static shortest-path query has one scalar cost \(w_e\) per edge.

A **dynamic graph** changes scalar edge weights between queries:

\[
G_0=(V,E,w^0),\quad G_1=(V,E,w^1),\ldots
\]

A formal **time-dependent shortest-path** problem uses an edge travel-time function:

\[
w_e(\tau)
\]

where \(\tau\) is the time the vehicle enters edge \(e\). If a path reaches an edge at 08:35 rather than 08:10, the traversal cost can differ within the same query. Most exact time-dependent road algorithms assume FIFO: entering an edge later cannot produce an earlier exit solely by waiting on that edge. See the time-dependent routing overview and CATCHUp formulation in [Strasser, Zeitz, and Wagner (2020)](https://doi.org/10.4230/LIPIcs.ESA.2020.81).

### 3.2 Classification of Stage 1

Stage 1:

- writes one scalar `stage1_weight` to every edge;
- runs a shortest-path query;
- changes one edge to infinite cost;
- runs another independent shortest-path query.

It is therefore **dynamic shortest path with snapshot/time-varying edge weights**, not formal time-dependent routing. “Time-dependent Dijkstra” should not be used for the current implementation.

## 4. Dijkstra Assessment

### 4.1 Why it should not be the final engine

Dijkstra is correct and not “bad because it is old.” The problem is fit:

- each update causes a fresh search with no reuse of topology preprocessing or prior search state;
- a city-scale graph plus many vehicles/scenarios creates many repeated searches;
- it does not itself coordinate vehicles or prevent herding;
- it has no native anytime behavior;
- it does not turn snapshot costs into formal time-dependent routing;
- changing the cost model requires no special support, but also receives no acceleration.

The important criticism is repeated-computation cost and missing system policy, not age.

### 4.2 Why it should remain a baseline

Dijkstra is:

- exact for non-negative scalar edge weights;
- simple to verify;
- already implemented;
- useful as a correctness oracle on small graphs;
- the cleanest way to measure whether a modern index actually improves update/query runtime.

Use two baseline modes:

1. **static Dijkstra:** route once and never update;
2. **repeated snapshot Dijkstra:** rerun after each accepted edge-weight batch.

The proposed system should use neither mode as its production engine.

## 5. Literature Review

### 5.1 Foundational route search and replanning

- **Dijkstra (1959):** E. W. Dijkstra, “A Note on Two Problems in Connexion with Graphs,” *Numerische Mathematik*. [DOI](https://doi.org/10.1007/BF01386390).
- **A\* (1968):** Peter Hart, Nils Nilsson, and Bertram Raphael, “A Formal Basis for the Heuristic Determination of Minimum Cost Paths,” *IEEE Transactions on Systems Science and Cybernetics*. [DOI](https://doi.org/10.1109/TSSC.1968.300136).
- **ALT (2005):** Andrew Goldberg and Chris Harrelson, “Computing the Shortest Path: A\* Search Meets Graph Theory,” *SODA*. [Microsoft Research page](https://www.microsoft.com/en-us/research/publication/computing-the-shortest-path-a-search-meets-graph-theory/).
- **LPA\* (2004):** Sven Koenig, Maxim Likhachev, and David Furcy, “Lifelong Planning A\*,” *Artificial Intelligence*. [DOI](https://doi.org/10.1016/j.artint.2003.12.001).
- **D* Lite (2002):** Sven Koenig and Maxim Likhachev, “D* Lite,” *AAAI*. [AAAI PDF](https://cdn.aaai.org/AAAI/2002/AAAI02-072.pdf).
- **AD\* (2005):** Maxim Likhachev et al., “Anytime Dynamic A*: An Anytime, Replanning Algorithm,” *ICAPS*. [AAAI page](https://aaai.org/papers/icaps-05-027-anytime-dynamic-a-an-anytime-replanning-algorithm/).

A*, ALT, LPA*, D* Lite, and AD* are established algorithms. Their use cannot be claimed as novelty.

### 5.2 Road-network hierarchy methods

- Robert Geisberger et al., “Contraction Hierarchies: Faster and Simpler Hierarchical Routing in Road Networks,” *WEA 2008*. [DOI](https://doi.org/10.1007/978-3-540-68552-4_24).
- Julian Dibbelt, Ben Strasser, and Dorothea Wagner, “Customizable Contraction Hierarchies,” *ACM Journal of Experimental Algorithmics*, 2016. [DOI](https://doi.org/10.1145/2886843).
- Moritz Baum et al., “UnLimited TRAnsfers for Multi-Modal Route Planning,” *ESA 2019* (relevant to multimodal hierarchy design, not this road-only core). [DOI](https://doi.org/10.4230/LIPIcs.ESA.2019.14).
- Ben Strasser, Dorothea Wagner, and Tim Zeitz, “Space-Efficient, Fast and Exact Routing in Time-Dependent Road Networks” (CATCHUp), *ESA 2020*. [DOI](https://doi.org/10.4230/LIPIcs.ESA.2020.81); [reproducibility repository](https://github.com/kit-algo/catchup).
- Thomas Werner and Tim Zeitz, “Combining Predicted and Live Traffic with Time-Dependent A* Potentials,” *ESA 2022*. [DOI](https://doi.org/10.4230/LIPIcs.ESA.2022.89).

CCH is the practical fit for repeatedly changing scalar metrics. CATCHUp is attractive only after the project implements genuine \(w_e(\tau)\) functions. Its research implementation is Rust-oriented and more difficult to integrate into this Python repository.

### 5.3 Dynamic distance labels, 2021–2026

- Mengxuan Zhang et al., “Dynamic Hub Labeling for Road Networks,” *IEEE ICDE 2021*. [DOI](https://doi.org/10.1109/ICDE51399.2021.00036).
- Muhammad Farhan, Henning Koehler, and Qing Wang, “BatchHL: Answering Distance Queries on Batch-Dynamic Networks at Scale,” *ACM SIGMOD 2022*. [DOI](https://doi.org/10.1145/3514221.3517883).
- Muhammad Farhan, Henning Koehler, and Qing Wang, “BatchHL+: Batch Dynamic Labelling for Distance Queries on Large-Scale Networks,” *VLDB Journal*, published 2023/volume 2024. [DOI](https://doi.org/10.1007/s00778-023-00799-9); [C++ code](https://github.com/mufarhan/BatchHL-Plus).
- Mengxuan Zhang et al., “Partitioned Dynamic Hub Labeling for Large Road Networks,” *IEEE TKDE*, 2025. [DOI](https://doi.org/10.1109/TKDE.2025.3538694).
- “Stable Tree Labelling for Accelerating Distance Queries on Dynamic Road Networks,” *EDBT 2025*. [paper](https://www.openproceedings.org/2025/conf/edbt/paper-127.pdf).
- “Dual-Hierarchy Labelling: Scaling Up Distance Queries on Dynamic Road Networks,” 2025 preprint. [arXiv](https://arxiv.org/abs/2506.18013).

These are modern dynamic-graph results, but they optimize distance-query index maintenance. They are not turnkey vehicle routers: path unpacking, directed multigraph conversion, turn restrictions, floating travel-time weights, time dependence, and Python integration still need engineering. BatchHL+'s public implementation is a small C++ research repository, not a maintained Python package. Selecting it only because it was published recently would increase delivery risk without creating application novelty.

### 5.4 Flood and disruption routing

Representative literature shows that the broad domain is occupied:

- Elizabeth Pregnolato et al., “The Impact of Flooding on Road Transport: A Depth-Disruption Function,” *Transportation Research Part D*, 2017. [DOI](https://doi.org/10.1016/j.trd.2017.06.020).
- “Efficient Dynamic Route Optimization for Urban Flooding Evacuation Based on Cellular Automata,” *Computers, Environment and Urban Systems*, 2021. [DOI](https://doi.org/10.1016/j.compenvurbsys.2021.101622).
- “Dynamic Network Flow Optimization for Real-Time Evacuation Reroute Planning under Multiple Road Disruptions,” *Reliability Engineering & System Safety*, 2021. [DOI](https://doi.org/10.1016/j.ress.2021.107644).
- “Quantitative Flood Risk Evaluation to Improve Drivers' Route Choice,” *Reliability Engineering & System Safety*, 2022. [DOI](https://doi.org/10.1016/j.ress.2021.108202).
- “High-Resolution Flood Numerical Model and Dijkstra Algorithm Based Risk Avoidance Routes Planning,” *Water Resources Management*, 2023. [DOI](https://doi.org/10.1007/s11269-023-03500-5).
- “Vehicle Route Planning for Relief Item Distribution under Flood Uncertainty,” *Applied Sciences*, 2024. [DOI](https://doi.org/10.3390/app14114482).
- “Probabilistic Functionality Assessment of Road Networks for Medical Emergency Vehicles during Flooding,” *Natural Hazards*, 2026. [DOI](https://doi.org/10.1007/s11069-026-08005-z).
- “Analyzing Emergency Service Performance under Compound Pluvial Flooding and Traffic Congestion,” *Water*, 2026. [DOI](https://doi.org/10.3390/w18060736).

Therefore, “flood-aware routing,” “flood plus congestion,” “uncertain flood routing,” and “emergency routing during floods” are not defensible novelty claims by themselves.

### 5.5 Traffic assignment, stability, and herding

An individually shortest route is not necessarily a good network allocation. If every vehicle reacts to the same new weights, a low-cost detour can become overloaded.

- Wardrop's user-equilibrium principles are foundational: John Wardrop, 1952, *Proceedings of the Institution of Civil Engineers*. [DOI](https://doi.org/10.1680/ipeds.1952.11259).
- Jahn et al. studied system-optimal routing with user constraints in *Operations Research* (2005). [DOI](https://doi.org/10.1287/opre.1040.0197).
- Angelelli et al. studied system-optimal traffic flow with user constraints in *EJOR* (2021 issue). [DOI](https://doi.org/10.1016/j.ejor.2020.12.043).
- Bianchin and Pasqualetti showed that real-time routing apps can produce oscillatory congestion and that regulating reaction rates can stabilize the system. [arXiv](https://arxiv.org/abs/2003.10018).
- A 2026 *Nature Cities* field study rerouted fewer than 2% of trips, bounded detours near the fastest viable path, and observed modest network benefits rather than redirecting all users at once. [DOI](https://doi.org/10.1038/s44284-026-00443-x).

Thresholds, hysteresis, minimum hold times, bounded route regret, limited participation, and sequential projected-load updates are established stabilization ideas. Their specific use with Chennai flood-induced capacity batches can be evaluated, but the ideas themselves are not novel.

### 5.6 Emergency and multimodal priority

Emergency priority, transit signal priority, and joint routing/signal control are established fields. Examples include:

- Zhaowei Su et al., “EMVLight: A Decentralized Reinforcement Learning Framework for Efficient Passage of Emergency Vehicles,” *Transportation Research Part C*, 2022. [DOI](https://doi.org/10.1016/j.trc.2022.103955).
- Multi-modal emergency/transit/freight priority research in *Transportation Research Record* (2023). [DOI](https://doi.org/10.1177/03611981221134627).

This project has no public Chennai signal-phase/telemetry feed and should not claim signal preemption. A feasible individual project can prioritize **route computation/order and projected capacity reservation**, then evaluate response time in SUMO.

### 5.7 Learning-assisted and reinforcement-learning routing

Learning can predict edge travel times or choose actions, but it does not remove the need for a safe route solver.

- A 2024 ACM study combined spatio-temporal graph convolutional congestion prediction with A*. [DOI](https://doi.org/10.1145/3657640).
- Flood-risk route choice has also been combined with reinforcement learning; see the 2022 *Reliability Engineering & System Safety* study above.
- EMVLight uses multi-agent reinforcement learning for emergency routing/signal control.

For this project, end-to-end RL is not recommended: Chennai training/validation data are insufficient, safety and distribution-shift behavior are hard to defend, and simulation-only gains would weaken the real-data claim. A later predictor may estimate edge flow/travel time while CCH remains the deterministic routing engine.

## 6. Chennai-Specific Literature Review

### 6.1 Directly relevant routing work

**S. Ganguly and S. Roy, “A Network Based Approach for Post-Disaster Relief by Vehicle Route Planning — Case Study of Chennai Floods,” 2017 International Conference on Information and Communication Technologies for Disaster Management.** [DOI](https://doi.org/10.1109/ICT-DM.2017.8275694).

The paper uses a Chennai/OSM post-disaster network, broken links, branch-and-bound vehicle routing, demand priorities, and service-time/queue considerations for relief distribution. It establishes that Chennai flood vehicle-route planning is not new. It does not provide the proposed near-real-time capacity/BPR customization, evolving rainfall/flood states, route hysteresis, broad congestion simulation, or CCH comparison.

### 6.2 Chennai flood mapping and transport exposure

- “Flood Vulnerability Assessment of Urban Road Network: A Case Study of Chennai,” 2018. [DOI](https://doi.org/10.17485/ijst/2018/v11i6/110831). This concerns network vulnerability/exposure, not the proposed dynamic routing engine.
- “Change Detection Based Flood Mapping of 2015 Flood Event of Chennai City Using Sentinel-1 SAR Images,” *IGARSS 2019*. [DOI](https://doi.org/10.1109/IGARSS.2019.8899282). Dense urban SAR limitations are relevant.
- “Near Real Time Flood Inundation Mapping Using Social Media Data: A Case Study of Chennai Floods,” 2021. [DOI](https://doi.org/10.1186/s40677-021-00195-x). Crowdsourced observations can improve event validation but have spatial and participation bias.
- “Flooded Streets—A Crowdsourced Sensing System for Disaster Response: A Case Study of Chennai Floods,” *IEEE Systems Conference*, 2016. [DOI](https://doi.org/10.1109/SYSENG.2016.7753186).

### 6.3 Chennai traffic simulation evidence

“Calibration of SUMO for Indian Heterogeneous Traffic Conditions” used a Chennai road segment and supports local calibration rather than default homogeneous-lane assumptions. [Springer chapter DOI](https://doi.org/10.1007/978-981-15-3742-4_13).

### 6.4 Feature audit of the closest Chennai work

| Feature | Ganguly & Roy 2017 | Chennai flood-mapping studies | Current project opportunity |
|---|---|---|---|
| Chennai road network | Yes | Exposure/intersection in some studies | Preserve OSM topology |
| Dynamic rainfall | No | Sometimes event rainfall context | IMERG/IMD feature stream |
| Historical flood evidence | 2015 disruption context | Yes | OpenCity susceptibility/validation |
| Congestion/BPR | No evidence of the proposed chain | No | Capacity-consistent BPR scenarios |
| Incidents plus flood | No | No | Compound capacity updates |
| Modern dynamic road index | No | No | CCH customization study |
| Event-trigger/hysteresis | No | No | Stability evaluation |
| Emergency/public-service priority | Relief-demand priority | Not routing | Route-query and load-reservation policy |
| Concurrent rerouting/herding | No | No | Sequential/batched allocation experiment |
| Live operational validation | No | No | At most non-interventional shadow mode |

### 6.5 Answer to “has the same Chennai system already been published?”

No reviewed source reproduces the entire proposed pipeline. However, there is substantial partial overlap:

- Chennai flood relief routing exists.
- Chennai flood mapping and road vulnerability exist.
- Flood plus congestion routing exists outside Chennai.
- emergency routing under flooding exists outside Chennai;
- capacity disruption, BPR, dynamic replanning, CCH, and route-stability controls all exist separately.

The safe statement is:

> Searches completed through 3 September 2026 found no indexed work that evaluates the exact combination of Chennai-specific flood/rainfall evidence, unified effective-capacity/BPR updates, CCH metric customization, event-triggered stable rerouting, emergency-first route allocation, and feedback-aware projected loads.

This is a **potential integration/evaluation gap**, not proof of universal absence.

## 7. Data Source Audit

### 7.1 Core and optional source matrix

| Source | Contents and resolution | Time/update status | Chennai/access/licence | Decision |
|---|---|---|---|---|
| [OpenStreetMap](https://www.openstreetmap.org/copyright) / [OSMnx](https://github.com/gboeing/osmnx) | Community road topology, geometry, classes, some lanes/speeds/signals; completeness varies | OSM continuously edited; downloaded snapshot must be dated | Chennai covered; no key for normal OSMnx/Overpass use; OSM data are ODbL and OSMnx software is MIT | **Primary** road graph |
| [NASA SRTM](https://www.earthdata.nasa.gov/data/catalog/lpcloud-srtmgl1-003) | Near-global elevation; SRTMGL1 is 1 arc-second, about 30 m | Static mission acquired February 2000 | Chennai covered; free Earthdata account for common downloads; NASA Earthdata terms | **Primary susceptibility feature**, never current flooding |
| [OpenCity Chennai Flooding Data](https://data.opencity.in/dataset/chennai-flooding-data) | KML inundation points/depth, 2015 points, hazard/return-period layers | Historical/static; portal metadata updated 2025 | Chennai; direct downloads; verify each resource's licence/provenance before redistribution | **Primary historical evidence/validation** |
| [OpenCity storm-water drains](https://data.opencity.in/dataset/chennai-stormwater-drain-swd-maps), [basin drainage](https://data.opencity.in/dataset/chennai-basin-drainage-maps), and [water-body census](https://data.opencity.in/dataset/tamil-nadu-water-bodies-census-data) | KML storm-water drains for 114 wards, macro/micro drains, rivers/canals, and census water-body points | Historical/static; source vintages differ; portal metadata updated 2025 | Chennai/basin; direct KML downloads; SWD resource says public domain, while water-body metadata shows non-commercial wording and an inconsistent licence ID—verify each resource | **Conditional** susceptibility feature; exclude weak or incompatible layers |
| [NASA GPM IMERG](https://gpm.nasa.gov/data/imerg) V07 | 0.1° precipitation, 30-minute estimates | Early about 4 h; Late about 14 h; Final about 3.5 months | Chennai covered; free; Earthdata registration normally required; NASA data generally open with citation | **Primary rainfall**: Early for delayed accumulation, Final for calibration |
| [Sentinel-1](https://sentiwiki.copernicus.eu/web/s1-mission) | C-band SAR; IW high-resolution GRD is about 20×22 m effective resolution on 10×10 m pixel spacing | Acquisition-dependent, not continuous; C/D constellation nominal revisit is 6 days from mid-2026, but local acquisition availability must be checked | Chennai covered when acquired; Copernicus Data Space account; Sentinel data are free, full, and open with source credit | **Optional event confirmation**, not narrow-road truth |
| [NASA OPERA DSWx-S1](https://doi.org/10.5067/OPDSWS1-L3V1) | Analysis-ready water/confidence GeoTIFFs at 30 m; designed for open water bodies larger than about 3 ha and 200 m width | Forward production since September 2024; 6–12 day revisit, not routing-time continuity | Near-global including Chennai when source acquisitions exist; free Earthdata/PO.DAAC access | **Optional regional validation only**; unsuitable for most street waterlogging |
| [Eclipse SUMO](https://eclipse.dev/sumo/) | Microscopic multimodal traffic simulation, OSM import, incidents, TraCI | Synthetic scenario time steps | Any Chennai network; open source EPL-2.0/GPL-2.0 | **Primary simulation**, explicitly not observed traffic |
| [India Flood Inventory / IFI-Impacts](https://doi.org/10.5281/zenodo.16994648) | Multi-source event/impact inventory, 1967–2023; district flooded area and severity products | Historical; v4 published 2025 | Includes Chennai/Tamil Nadu events at coarse administrative/event scale; open Zenodo dataset; cite [Natural Hazards paper](https://doi.org/10.1007/s11069-021-04698-6) | **Optional event selection/context**, not road state |
| [Sen1Floods11](https://openaccess.thecvf.com/content_CVPRW_2020/html/w11/Bonafilia_Sen1Floods11_A_Georeferenced_Dataset_to_Train_and_Test_Deep_Learning_CVPRW_2020_paper.html) | 4,831 georeferenced 512×512 chips at 10 m across 11 events; 446 hand-labelled chips plus automatically derived labels | Static 2020 ML benchmark | Six continents, but not a Chennai live feed; distributed as CC BY 4.0 by current dataset mirrors; verify downloaded package notice | **Remove from core**; optional only if training/benchmarking a flood mapper |
| [STURM-Flood](https://doi.org/10.5281/zenodo.12748983) | 21,602 Sentinel-1 and 2,675 Sentinel-2 tiles, 128×128 at 10 m, 60 events; about 4 GB | Static ML dataset | Global; Chennai event inclusion is not assured; open dataset/code, cite [2025 data paper](https://doi.org/10.1080/20964471.2025.2458714) | **Remove from core**; custom flood DL is outside scope |

### 7.2 OpenWeather correction

Verified against official OpenWeather pages on 3 September 2026:

| Product | Official status | Appropriate project role |
|---|---|---|
| Permanent Free plan | Current Weather API and 3-hourly 5-day forecast are listed; API key/account required | Optional demo/context |
| One Call API 4.0 | Pay-as-you-call subscription with 1,000 calls/day included free; overage charged; current, short forecasts, alerts, and long timeline products vary by endpoint | Optional extension only; enforce a daily cap |
| Bulk/history | Product/plan dependent; substantial archives and bulk features are not simply part of every free endpoint | Do not make reproducibility depend on it |

Sources: [API overview](https://openweathermap.org/api), [official pricing](https://openweathermap.org/full-price), [official FAQ](https://openweathermap.org/faq), and [One Call 4.0 documentation](https://openweathermap.org/api/one-call-4).

Conclusion: “OpenWeather is paid” is inaccurate. “Some useful OpenWeather capabilities are free, while One Call and history/bulk have product-specific subscription/overage conditions” is accurate. IMERG remains the better scientific core because its product definition, archive, and 30-minute grid are reproducible.

### 7.3 Satellite suitability

Sentinel-1 and OPERA add value only as **event-level observed-water evidence**:

- SAR can observe through cloud and at night.
- Dense urban double bounce, layover, radar shadow, vegetation, and permanent-water confusion limit classification.
- Sentinel-1's 10 m pixel spacing is finer than its roughly 20×22 m IW-GRD effective resolution, and a 30 m DSWx posting does not guarantee detection of a narrow flooded carriageway.
- Acquisition/revisit is not synchronized with a routing event.
- Satellite water extent can arrive too late for immediate rerouting.
- OPERA DSWx-S1 targets open inland water bodies larger than about 3 ha and 200 m width, which directly excludes most street-scale waterlogging.

Use satellite products to validate or escalate states on sufficiently large/intersecting areas. Do not infer exact road water depth or passability from a single pixel. A custom Sentinel flood neural network is not justified for this project; Sen1Floods11 and STURM-Flood should therefore remain outside the core.

### 7.4 Data semantics that must remain separate

| Evidence | What it can support | What it cannot prove |
|---|---|---|
| Low SRTM elevation | Static susceptibility | A road is flooded now |
| Historical OpenCity point | Prior flood evidence | Current closure |
| Drain/water-body distance | Hydrological context | Direction or depth of flooding |
| IMERG rain | Area rainfall forcing/accumulation | Road-level water depth |
| Sentinel/DSWx water | Observed surface-water evidence at acquisition scale | Continuous current passability |
| SUMO flow | Controlled traffic experiment | Actual Chennai traffic |
| Scripted incident | Robustness scenario | Historical real incident |

## 8. Routing Algorithm Comparison

Ratings are relative to this project, not universal rankings.

| Algorithm | Dynamic Updates | Replanning Efficiency | Road Network Suitability | Flood Suitability | Traffic Suitability | Implementation Difficulty | Research Value | Novelty Value | Recommendation |
|---|---|---|---|---|---|---|---|---|---|
| Dijkstra | Fresh query | Low at scale | Correct baseline | Handles changed weights only | Handles scalar BPR weights | Low | Essential baseline | None | Baseline only |
| A* | Fresh query; heuristic reusable | Better than Dijkstra with strong admissible heuristic | Good | Handles changed weights | Good for snapshots | Low–medium | Useful baseline | None | Comparator |
| Bidirectional A* | Fresh query from both ends | Often faster; stopping rules are subtle | Good | Same as A* | Good for snapshots | Medium | Useful comparator | None | Comparator |
| ALT | Landmark preprocessing; changed weights may weaken/invalidate bounds | Fast static queries | Strong | Closures manageable only with valid lower bounds | Broad changes complicate landmarks | Medium | Good benchmark | None | Comparator |
| CH | Weight-dependent hierarchy | Very fast queries; expensive rebuild after changes | Excellent static roads | Poor for frequent closures unless updated | Poorer for changing metrics | High | Established | None | Not primary |
| **CCH** | Fast metric customization after topology preprocessing | Strong for update batches plus many queries | **Excellent** | Local or batch capacity changes fit customization | **Strong for refreshed BPR metric** | High but bounded | **High** | Engine itself none | **Primary** |
| CATCHUp / TD-CCH | Time-dependent profiles; live updates remain complex | Fast exact TD queries after indexing | Excellent | Useful if hazard/traffic is forecast by entry time | Strong for predicted profiles | Very high; Rust research stack | High future value | None | Future upgrade, not current |
| LPA* | Incrementally repairs changed vertices | Strong for repeated same OD and sparse changes | Good | Good for localized flood/incident changes | Weakens under network-wide flow refresh | Medium | Good ablation | None | Candidate, not primary |
| D* Lite | LPA*-derived repair; moving start | Strong for one moving agent and sparse changes | Good on directed graphs with care | Good local closure repair | Poorer for many OD/global BPR changes | Medium | Strong backup | None | **Backup** |
| AD* / Anytime Dynamic A* | Incremental plus bounded-suboptimal anytime refinement | Useful under strict compute deadlines | Possible, mostly robotics evidence | Handles local updates | Limited road-network evidence | High | Interesting emergency ablation | None | Not primary |
| Dynamic hub labeling | Maintains query labels | Excellent distance queries after complex updates | Strong research fit | Can reflect edge changes | Path recovery/turns/weights add work | Very high | High algorithm-study value | Existing | Not student core |
| BatchHL+ | Batch insert/delete label maintenance | Excellent reported update/query scale | Generic large networks | Batch disruption concept fits | Floating weighted road integration uncertain | Very high; C++ research code | High comparator concept | Existing | Do not select |
| Stable Tree Labelling | 2025 stable hierarchy and dynamic labels | Strong reported balance | Designed for dynamic roads | Relevant | Relevant | Very high; no mature Python engine | Current research | Existing | Literature only |
| Partitioned Dynamic Hub Labeling | Incremental/partitioned index maintenance | Strong reported scale | Designed for large roads | Relevant | Relevant | Very high | Current research | Existing | Literature only |
| Learning-assisted A*/GNN | Predictor changes costs/heuristic | Depends on model and safe fallback | Potentially good | Needs labeled hazard data | Strong prediction potential | High data burden | Optional future | Established combination | Predictor only |
| End-to-end RL routing | Learns actions under simulation | Fast inference, expensive/fragile training | Possible | Distribution shift/safety risk | Can model interaction | Very high | Risky | Established | Not recommended |

## 9. Novelty Matrix

| Feature/combination | Existing work? | Evidence | Degree of overlap | Potential gap |
|---|---|---|---|---|
| Chennai flood routing | Yes | [Ganguly & Roy 2017](https://doi.org/10.1109/ICT-DM.2017.8275694) | Direct city/topic overlap | Dynamic capacity, congestion, modern index, stability |
| Flood + congestion | Yes | [CEUS 2021](https://doi.org/10.1016/j.compenvurbsys.2021.101622); [Water 2026](https://doi.org/10.3390/w18060736) | Strong concept overlap | Chennai reproducibility and update-policy evaluation |
| Flood + emergency routing | Yes | [Natural Hazards 2026](https://doi.org/10.1007/s11069-026-08005-z) | Strong | Multi-class routing with load feedback in Chennai |
| BPR + flood | Partial | Flood disruption functions and BPR traffic are established separately | Medium | Unified, calibrated capacity chain under Chennai events |
| Capacity degradation | Yes | Standard disruption modelling | Strong | Evidence-backed Chennai calibration/sensitivity |
| Event-triggered rerouting | Yes | Dynamic routing/control literature | Strong | Trigger interaction with flood batches and CCH customization |
| Hysteresis/route stability | Yes | Routing oscillation and bounded-rationality literature | Strong | Empirical compound-disruption stability study |
| Incremental shortest paths | Yes | LPA*, D* Lite, dynamic labels | Complete algorithm overlap | Application/evaluation only |
| Anytime routing | Yes | AD* | Complete algorithm overlap | Emergency compute-budget ablation only |
| Emergency priority | Yes | EMVLight and multi-modal priority literature | Strong | Route-only priority without unavailable signal control |
| Unified effective capacity for flood + incidents + congestion | Partial | Capacity reduction and BPR are common; exact integration varies | Medium | Transparent, traceable multi-hazard update mechanism |
| CCH + Chennai flood-capacity batches | No exact match found | Searches through cutoff | Partial via CCH traffic customization and Chennai flood routing separately | **Underexplored implementation/evaluation combination** |
| CCH + threshold/hysteresis + sequential projected loads | No exact match found | Searches through cutoff | Components individually established | **Potential systems contribution** |
| Entire combination A from prompt | No exact match found | Broad multi-database search | Many components separately occupied | **Potential integration/evaluation gap** |
| Combinations B–D | Partial | Incremental/dynamic flood routing exists; exact BPR/stability coupling not located | Medium–high | Comparative experimental gap, not new base algorithm |
| Combination E | Partial | Physical capacity/disruption models exist | Medium | Traceable common-capacity implementation and sensitivity |

### 9.1 Novelty classification

- **Already established:** all named path algorithms, BPR, flood routing, congestion routing, emergency routing, threshold rerouting, hysteresis, system-optimal routing.
- **Application-level:** Chennai implementation with current open datasets.
- **Modelling contribution:** one auditable effective-capacity chain for flood and incident disruption, with sensitivity/calibration rather than arbitrary penalties.
- **System-integration contribution:** batching road-state changes into CCH customization, stable rerouting, and projected-load-aware vehicle ordering.
- **Evaluation contribution:** controlled comparison across compound Chennai scenarios, update locality, many-vehicle load feedback, stability, emergency response, and runtime.
- **Potential algorithmic contribution only:** a new partial-customization trigger or bounded route-allocation method, if formally specified and shown to differ from prior methods. This has not yet been established.

## 10. Candidate Algorithms

### 10.1 Customizable Contraction Hierarchies

**Fit:** Best match for a mostly fixed Chennai topology and frequently refreshed scalar costs. It can reuse topology preprocessing across normal, emergency, and scenario-specific metrics.

**Does not solve:** flood inference, BPR calibration, time dependence, threshold logic, or multi-vehicle equilibrium.

**Complexity:** Native-library adapter, node/arc indexing, path unpacking, turn/parallel-edge handling, and persisted preprocessing. Use [RoutingKit](https://github.com/RoutingKit/RoutingKit) as the reference implementation. Python integration must be proved on the target machines before making it mandatory.

**Expected performance:** much faster queries than full-graph Dijkstra after customization; actual customization latency must be measured on the Chennai graph and update batches.

**Literature status:** mature and established. No novelty from merely using CCH.

### 10.2 D* Lite

**Fit:** Good when a vehicle is already moving and only a few nearby roads change. Reuses `g`/`rhs` state and repairs inconsistent vertices.

**Does not fit:** many unrelated OD pairs and global BPR refreshes. Each vehicle/query may need separate state, increasing memory and complexity.

**Complexity:** feasible pure Python implementation with a priority queue and admissible geodesic heuristic; directed multigraph and changed-edge tests are essential.

**Expected performance:** potentially strong for sparse updates; can be slower than fresh search when much of the graph changes.

**Literature status:** foundational, not new.

### 10.3 LPA*

**Fit:** Repeated same-source/same-goal queries with localized changes.

**Limit:** A moving vehicle makes D* Lite's formulation more convenient. Like D* Lite, broad traffic changes reduce reuse.

**Complexity:** moderate and explainable in a viva.

**Literature status:** established.

### 10.4 AD*

**Fit:** Can quickly return a bounded-suboptimal route and improve it while reusing work; attractive when emergency computation has a hard deadline.

**Limit:** evidence and implementations are concentrated in robotics, and approximate route quality complicates fair traffic comparisons. It does not address herding.

**Complexity:** high for a correct student implementation.

**Literature status:** established since 2005.

### 10.5 CATCHUp / time-dependent A* potentials

**Fit:** Best conceptual candidate if the final model predicts a FIFO travel-time function for every edge and departure time.

**Limit:** the project currently has snapshot costs, not such functions. Research code is substantially harder to integrate and customize for sudden incidents.

**Complexity:** very high; Rust/C++-oriented reproducibility.

**Literature status:** modern exact time-dependent routing, but not application novelty.

## 11. Recommended Final Algorithm

### 11.1 Exact name

**Customizable Contraction Hierarchies (CCH), using metric customization after accepted road-cost update batches.**

### 11.2 Why it is appropriate

The Chennai road topology changes slowly. Flood severity, incidents, and traffic cause edge **weights** or availability to change much more often. CCH was designed for this separation.

### 11.3 Why it is technically better than repeated Dijkstra here

- topology ordering/preprocessing is reused;
- all changed BPR weights can be customized as a batch;
- many normal/emergency queries share the same customized index;
- separate metrics can represent normal and emergency feasibility without rebuilding topology;
- query and update costs can be measured separately;
- it scales more plausibly from the tiny Stage 1 bbox to a Chennai subnetwork.

CCH still uses hierarchical shortest-path ideas and bidirectional searches internally. The honest claim is not “unrelated to Dijkstra”; it is “a preprocessed, customizable hierarchical road-network engine rather than repeated full-graph Dijkstra.”

### 11.4 Proposed interaction with the model

```text
OSM topology
  -> stable node/arc IDs
  -> one-time CCH ordering and topology preprocessing

rain/flood/incident/SUMO update
  -> road state
  -> effective capacity
  -> BPR edge weight
  -> changed-edge batch
  -> thresholded CCH metric customization

vehicle request
  -> class-specific feasibility/metric
  -> CCH query
  -> route-stability acceptance check
  -> projected load reservation
  -> next vehicle query
```

### 11.5 Emergency interaction

Do not apply an arbitrary “emergency discount.” Build a separate metric:

- blocked roads remain unavailable;
- severely degraded roads are excluded or constrained unless no feasible route exists;
- feasible physical travel time is minimized;
- emergency requests are queried/reserved before normal reroutes.

The engine can share topology preprocessing while customizing/querying different class-specific weights.

### 11.6 Route stability

CCH returns the current best route; the policy decides whether to adopt it:

1. calculate the current route's cost under the new metric;
2. trigger a query only when degradation or a hard safety event warrants it;
3. accept a new route only when improvement exceeds hysteresis;
4. enforce a minimum hold interval except for closures/safety;
5. limit each rerouting batch;
6. reserve projected flow after every accepted route.

Threshold and hysteresis are controls around CCH, not modifications to the CCH algorithm.

### 11.7 Expected computational benefit

Expect faster route queries and better amortization across many vehicles. Do not promise a speedup before benchmarking:

- topology preprocessing time;
- full and partial customization time;
- query latency;
- memory;
- changed-edge batch size;
- number of OD queries per update;
- break-even point versus repeated Dijkstra and D* Lite.

## 12. Backup Algorithm

**D* Lite** is the backup.

Use it if:

- native CCH build/bindings are unreliable on the student's machines;
- the final study is one corridor rather than city scale;
- updates are sparse and localized;
- each vehicle maintains a route while its start moves.

Implement D* Lite from the original pseudocode with a tested priority queue and admissible geographic lower bound. Do not use an unverified tutorial implementation. It remains an established algorithm, so novelty must still come from modelling and evaluation.

## 13. Proposed Research Contribution

### 13.1 Algorithmic contribution

**Current strength: weak/potential.** CCH and the surrounding controls are established. A stronger algorithmic claim would require a formally specified and evaluated update scheduler, partial-customization rule, or bounded load-allocation mechanism. Until then, call this an algorithm **application and comparative evaluation**, not a new shortest-path algorithm.

### 13.2 Modelling contribution

**Defensible:**

- flood and incidents act through availability/effective capacity;
- BPR translates flow/capacity into travel time;
- every state records provenance and reason;
- arbitrary unitless hazard penalties are avoided;
- parameter sensitivity exposes uncertainty.

This is an integration of established models, not a new physical law.

### 13.3 System-integration contribution

**Most promising:**

- Chennai geospatial evidence and rainfall;
- capacity-consistent compound disruptions;
- CCH update batching;
- stable event-triggered rerouting;
- emergency-first and degradation-aware ordering;
- projected-load updates to reduce herd behavior.

### 13.4 Chennai-specific contribution

**Defensible as an empirical contribution:** a reproducible Chennai network/event benchmark and an honest audit of public-data limitations. Locality alone is insufficient; the value comes from reproducibility, calibrated assumptions, and comprehensive evaluation.

### 13.5 Evaluation contribution

**Strong if executed well:** compare algorithms under update locality, disruption severity, demand, vehicle priority, stale/missing data, and rerouting compliance. Report confidence intervals and negative results.

### 13.6 Suggested faculty statement

> We are not claiming to invent CCH, BPR, or flood-aware routing. Our contribution is a reproducible Chennai-specific compound-disruption framework that converts flood and incident evidence into a common capacity-based travel-time model, applies modern CCH metric customization for repeated routing, and evaluates stability-aware, priority-sensitive rerouting with feedback from projected route loads against static and repeated Dijkstra.

## 14. What Is NOT Novel

Do not claim novelty for:

- Dijkstra, A*, ALT, LPA*, D* Lite, AD*, CH, CCH, CATCHUp, hub labeling, or BatchHL+;
- dynamic or time-dependent routing generally;
- BPR;
- reducing capacity after flood or incident disruption;
- flood-aware, congestion-aware, risk-aware, or emergency routing generally;
- Chennai flood vehicle routing generally;
- historical-flood susceptibility mapping;
- IMERG or Sentinel flood inputs;
- threshold-triggered rerouting;
- hysteresis, hold-down timers, or bounded rationality;
- processing emergency requests first;
- SUMO simulation;
- sequential load updates as a general idea;
- using real maps with simulated traffic.

## 15. Recommended Stage 1 Refactor

This section is a design only. No refactor is performed in this research phase.

### 15.1 Preserve the public contract

Keep:

- `apply_stage1_costs(graph, blocked_edges, ...)`;
- route inputs `graph`, `origin`, `destination`, and `weight`;
- route output as node/arc sequence plus cost;
- affected-edge selection;
- current CSV/JSON/map outputs;
- legacy Dijkstra test as baseline evidence.

### 15.2 Proposed module structure

```text
src/chennai_routing/routing/
  base.py                 # Router protocol and RouteResult
  dijkstra_baseline.py    # existing behavior, evaluation only
  cch_adapter.py          # MultiDiGraph <-> stable integer arcs
  cch_router.py           # preprocess/customize/query/unpack
  update_batch.py         # changed-edge batches and triggers
  allocation.py           # emergency order and projected loads
  stability.py            # threshold, hysteresis, hold time
```

### 15.3 Files likely changed later

- `src/chennai_routing/routing/dijkstra.py`: retain or rename as explicit baseline.
- `src/chennai_routing/stage1_poc.py`: inject a router; do not mix CCH internals into GIS code.
- `src/chennai_routing/routing/dynamic.py`: customization orchestration.
- `src/chennai_routing/routing/rerouting.py`: trigger and acceptance policy.
- `src/chennai_routing/routing/emergency.py`: class-specific feasibility/metric.
- `src/chennai_routing/preprocessing/roads.py`: stable node/arc indexing.
- `src/chennai_routing/evaluation/baseline.py`: static/repeated Dijkstra.
- tests and documentation.

### 15.4 Data structures

Persist:

- `node_id -> contiguous_index`;
- `arc_id -> (u, v, key)`;
- CCH order/topology;
- current weight vector;
- changed arc indices;
- edge state/provenance;
- route arc sequence, not only node sequence;
- customization/query version and timestamps.

Parallel OSM edges must not be silently collapsed unless the retained arc and its attributes are explicitly recorded.

### 15.5 Migration strategy

1. Freeze the current Stage 1 outputs as legacy evidence.
2. Add a router protocol without changing behavior.
3. Add CCH graph conversion and round-trip tests.
4. Compare CCH paths/costs to Dijkstra on small fixtures.
5. Add full/partial customization tests for increase, decrease, and blocked edges.
6. Switch Stage 1's proposed-engine run only after exactness tests pass.
7. Keep Dijkstra executable only through baseline/evaluation configuration.
8. Add load allocation and stability controls after the core engine is correct.

### 15.6 Test strategy

- CCH equals Dijkstra cost on random small non-negative directed graphs.
- edge increase/decrease and infinity update produce the expected route.
- parallel edges and one-way roads are preserved.
- blocked roads are never returned.
- customization version matches the queried weight version.
- route unpacking maps back to valid OSM arcs.
- emergency and normal metrics remain separate.
- thresholds suppress minor route changes.
- hard closure bypasses hysteresis.
- sequential reservations alter later vehicle choices.
- deterministic seed and fixture tests work offline.

## 16. Experimental Plan

### 16.1 Algorithms

Required:

- static Dijkstra;
- repeated snapshot Dijkstra;
- CCH with full customization;
- CCH with partial/incremental customization if supported reliably;
- D* Lite backup/ablation for localized updates.

Optional:

- A*/ALT snapshot comparator;
- CATCHUp only after true time-dependent profiles exist.

### 16.2 Scenarios

1. normal demand;
2. peak congestion;
3. localized flood closure;
4. widespread flood degradation;
5. incident only;
6. flood + incident + congestion;
7. emergency vehicle under each disruption;
8. many vehicles rerouted simultaneously;
9. stale/missing rainfall or flood evidence;
10. update batches of increasing size and spatial dispersion;
11. threshold/hysteresis sensitivity;
12. different capacity/BPR parameter sets.

### 16.3 Metrics

| Category | Metrics |
|---|---|
| Mobility | average travel time, total delay, throughput, stops |
| Congestion | edge \(x/c\), overloaded-edge count/duration, queue spillback in SUMO |
| Stability | reroute count, route churn, back-and-forth switches, hold-time violations |
| Safety | blocked-road use, severe-edge exposure, disconnected requests |
| Priority | emergency response time, deadline success, delay imposed on normal users |
| System effect | total person/vehicle delay, maximum individual detour, load concentration |
| Algorithm | preprocessing, customization, query and end-to-end latency; memory; expanded vertices where available |
| Updates | changed edges processed, batch size, update locality, updates/second |
| Robustness | missing-data performance, sensitivity intervals, failure/fallback rate |

### 16.4 Statistical reporting

- repeat stochastic SUMO scenarios across seeds;
- predefine primary outcomes;
- report medians/means as appropriate, dispersion, and confidence intervals;
- use paired comparisons on the same demand/event seeds;
- report effect sizes, not only p-values;
- do not select only favorable peak periods;
- distinguish algorithm runtime improvement from travel-time improvement.

### 16.5 Baseline fairness

All algorithms must receive:

- the same graph snapshot;
- the same edge weights and update batches;
- the same OD requests;
- equivalent blocked-edge semantics;
- measured preprocessing/customization costs;
- the same route-acceptance policy when comparing engines.

Otherwise the study would compare policies rather than algorithms.

## 17. Risks and Limitations

1. **CCH integration risk:** reference implementations are native C++/Rust, not a simple NetworkX replacement.
2. **No guaranteed Python package stability:** validate build, path unpacking, licences, and platform support before committing.
3. **CCH is not novelty:** publication needs the modelling/evaluation contribution.
4. **Snapshot limitation:** CCH over refreshed weights is not formal time-dependent routing.
5. **Global BPR changes:** frequent full-network changes can make customization expensive.
6. **Traffic-data gap:** public road-level Chennai counts/speeds are limited; SUMO is simulation.
7. **Flood-ground-truth gap:** historical points and coarse rainfall cannot prove current road passability.
8. **Satellite limitations:** spatial/revisit/urban errors prevent road-level certainty.
9. **Capacity calibration:** current multipliers, capacities, and BPR parameters are assumptions.
10. **No signal preemption evidence:** route priority must not be presented as traffic-signal control.
11. **Herding:** sequential reservations are an approximation, not dynamic user equilibrium.
12. **Compliance:** suggested routes may not be followed.
13. **Emergency ethics:** unsafe recommendations must fail closed and remain simulation/shadow decisions.
14. **Study-area validity:** a small corridor cannot support city-wide claims.
15. **Novelty search limit:** inaccessible papers, patents, theses, and later publications may overlap.

## 18. Final Recommendation

### Explicit answers

1. **What is wrong with Dijkstra as the final algorithm?**  
   It recomputes from scratch, does not exploit fixed road topology or prior updates, and scales poorly for many Chennai queries. Its age is not the technical problem.

2. **Strongest practical replacement?**  
   Customizable Contraction Hierarchies with batched metric customization.

3. **Why technically better?**  
   It reuses topology preprocessing, customizes changing BPR/flood/incident weights, and answers many exact route queries quickly.

4. **Is CCH itself novel?**  
   No. It is established 2016 work building on CH.

5. **What is defensible novelty?**  
   The Chennai-specific, unified effective-capacity/BPR disruption model combined with CCH update batches, stability-aware priority routing, projected-load feedback, and comprehensive compound-event evaluation.

6. **Has essentially the same Chennai flood-routing system been published?**  
   Chennai flood relief routing has been published, but the exact proposed integrated system was not located. The overlap is substantial enough that no “first Chennai flood router” claim is valid.

7. **What appears underexplored?**  
   CCH customization under flood/incident capacity batches, coupled with rerouting stability and feedback-aware multi-vehicle priority allocation on reproducible Chennai events.

8. **Can it be implemented reliably in Python?**  
   The orchestration can be Python, but the practical CCH core should use a verified native implementation such as RoutingKit through a small adapter. Pure-Python CCH is not recommended. D* Lite is the reliable pure-Python backup.

9. **How much of Stage 1 changes?**  
   The GIS/data/flood/capacity/BPR/visualization pipeline can remain. Routing calls, graph indexing, tests, timing/provenance, and documentation change. This is a focused routing-layer migration, not a rewrite.

10. **What should faculty be told?**  
    The project does not claim a new base shortest-path algorithm. It contributes and evaluates a transparent Chennai-specific compound-disruption routing framework using a modern customizable road-network engine, stable rerouting, emergency-aware allocation, and honest public-data/simulation boundaries.

### Decision gate before implementation

Do not replace Stage 1 yet. First obtain approval for:

- CCH as primary and D* Lite as backup;
- snapshot dynamic routing for the first final-system version;
- Dijkstra retained only as baseline/correctness oracle;
- integration/evaluation novelty rather than a false new-algorithm claim;
- a bounded Chennai study area and explicit simulation limitations.

## Search Method and Coverage Note

The review used combinations of the prompt's Chennai queries plus searches for flood routing, BPR/capacity disruption, dynamic shortest paths, CCH/CATCHUp, LPA*/D* Lite/AD*, dynamic hub labeling, BatchHL+, route stability, emergency priority, dynamic traffic assignment, and learning-assisted routing. Sources were sought through publisher/DOI pages and material discoverable in Google Scholar-style indexes, IEEE, ACM, Springer, ScienceDirect/Elsevier, AAAI, TR venues, Crossref/OpenAlex/Semantic Scholar-style metadata, arXiv, official repositories, NASA, Copernicus, Eclipse, OpenStreetMap, OpenCity, and Zenodo.

Representative exact searches included:

```text
"Chennai" flood routing
"Chennai" flood evacuation routing
"Chennai" congestion flood emergency routing
"Chennai" BPR capacity flood routing
"Chennai" rainfall road capacity
"Customizable Contraction Hierarchies" dynamic traffic
"CATCHUp" time-dependent routing live traffic
"D* Lite" flood evacuation routing
"Anytime Dynamic A*" road routing
"BatchHL+" dynamic shortest path
"dynamic hub labeling" road networks
flood routing BPR capacity degradation incident hysteresis
routing apps oscillation herding bounded regret
```

The cutoff is 3 September 2026. A final paper should repeat the searches, add backward/forward citation chasing, record inclusion/exclusion decisions, and have a supervisor review the novelty statement.
