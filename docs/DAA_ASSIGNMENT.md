---
title: "Certificate-Gated Routing"
subtitle: "Design and Analysis of Algorithms — Assignment"
---

**Vellore Institute of Technology (VIT), Chennai**

**Student:** Rohit Michael Raj
**Registration number:** 24BCE5108
**Programme:** B.Tech. Computer Science and Engineering
**Course:** Design and Analysis of Algorithms
**Date:** 8 September 2026

This document is the DAA assignment submission. It is separate from the longer project research-and-evidence file. Experimental tables below use Stage 3–5 artifacts plus the earlier synthetic certificate experiment. They do not claim calibrated Chennai traffic or city-scale CCH timings.

---

# 1. Title

**Certificate-Gated Routing**

Real-world problem: repeated vehicle routing when Chennai road costs change because of flooding, incidents, and congestion.

Proposed approach: keep Customizable Contraction Hierarchies (CCH) as the path engine, and add **Certified Lazy Metric Synchronization (CLMS)** as a query-level gate that refreshes the CCH metric only when a monotone lower/upper-bound certificate cannot guarantee a declared $(1+\varepsilon)$-bound.

CLMS is **not** a replacement for Dijkstra or A\*. Dijkstra remains the correctness oracle. CCH (or Dijkstra) finds the path. CLMS decides whether the engine’s currently synchronized metric is still accurate enough for the query.

---

# 2. Problem Statement

## 2.1 Real-world problem

During monsoon flooding, incidents, and congestion, a Chennai road may remain physically connected while losing speed or capacity. If many vehicles are recomputed independently after every small cost change, two failures appear:

1. **Computational cost.** Exact engines such as Dijkstra re-explore large parts of the graph. CCH can answer queries quickly, but **customizing** CCH to a new complete metric after every update is still expensive when updates are frequent.
2. **Route quality versus staleness.** Using yesterday’s metric for too long can return routes that are much worse than the current optimum.

The computational problem is therefore **snapshot-dynamic shortest paths**: the directed road graph topology is fixed between routing epochs, while non-negative edge weights change from epoch to epoch. This is not time-dependent routing (edge cost as a function of entry time inside one query) unless that model is added later.

## 2.2 Input

- Directed multigraph $G=(V,E)$ with stable arc identities.
- Non-negative integer edge weights $w_e$ (represented travel time, e.g. milliseconds).
- An exact shortest-path engine for a synchronized metric $\bar{w}$ (implemented: NetworkX Dijkstra; prototype: RoutingKit CCH).
- Atomic update batches that replace a subset of weights and produce a new metric version.
- Origin–destination queries $(s,t)$.
- A rational stretch allowance $\varepsilon=p/q$ with integers $p\ge 0$, $q>0$.

## 2.3 Output

For each query:

- status `FOUND` or `UNREACHABLE`;
- a directed keyed path $P$ when found;
- the decision `CURRENT`, `CERTIFIED_STALE`, `REFRESHED`, or an unreachable variant;
- the certificate bounds $L$ and $U$ when a stale path is tested.

## 2.4 Constraints

- Topology does not change inside a CLMS session. Arc insertion/deletion is outside the current algorithm.
- Weights are non-negative. Native CCH currently accepts **finite** integers only; $+\infty$ closures are rejected until a later validation stage.
- The engine query under $\bar{w}$ is exact for that represented metric.
- The current implementation stores complete metric snapshots; it does not maintain a partial CCH overlay update.

## 2.5 Assumptions (declared, not hidden)

| Item | Classification | Statement |
|---|---|---|
| Graph topology | Observed later from OSM | Stage 3 uses a dated extract clipped to the 2022 Greater Chennai Corporation ward union. City-graph timings are not reported in this file. |
| Experimental edge weights | Scenario / synthetic until Stages 4–5 | Later experiments will state whether weights are synthetic or derived from Chennai evidence. |
| $\varepsilon$ | Scenario parameter | A declared rational tolerance; the value used in each later experiment will be reported with that experiment. |
| Dijkstra binary-heap complexity | Published | Standard worst-case bound from algorithm textbooks [1], [2]. |
| CCH query/customization behaviour | Published | Metric-independent contraction, customization, and exact queries as described by Dibbelt et al. [3]. |
| Certificate principle | Published prior art | Lower bound from an old exact distance under nondecreasing weights; upper bound from re-evaluating the old path [4], [5]. |
| Chennai flood/traffic outcomes | Unavailable in this file | Not assumed. Left for Stages 3–5+. |

## 2.6 Example / application scenario

A vehicle must travel from an origin $s$ to a destination $t$ in Chennai while some roads become slower because of congestion or flood-related capacity loss. CCH has already been customized to metric $\bar{w}$. A later metric $w$ increases some road times. CLMS tests whether the old CCH path is still within $(1+\varepsilon)$ of the current optimum. If yes, CCH is **not** customized. If a road recovers and some weight decreases, the stale lower bound is invalid and customization is mandatory.

A three-road numerical illustration is given in Section 6. It uses invented minute values only to show the test $U\le(1+\varepsilon)L$; those minutes are **not** field measurements.

---

# 3. Existing Algorithms — Literature Survey

At least three established algorithms address shortest paths or dynamic routing. Complexities below are the **standard published bounds**, not measurements from this project.

Let $n=|V|$ and $m=|E|$.

## 3.1 Dijkstra’s algorithm

**Working principle.** Maintain a tentative distance $d(v)$ from $s$. Repeatedly extract the unsettled node with smallest $d(v)$ and relax its outgoing arcs. With non-negative weights the first time $t$ is extracted, $d(t)$ is exact [6], [1].

**Time complexity.** With a binary heap the extract-min and decrease-key operations give

$$
T_{\text{Dijkstra}}=O((n+m)\log n).
$$

Each node is extracted once ($O(n\log n)$). Each arc may cause a decrease-key ($O(m\log n)$). With a Fibonacci heap the bound improves to $O(m+n\log n)$ [2]. This report uses the binary-heap bound because that is the usual textbook implementation and matches NetworkX’s heap-based Dijkstra used as the oracle.

**Space complexity.** $O(n+m)$ to store the graph, distance labels, predecessors, and the heap.

**Advantages.** Exact for non-negative weights; simple correctness argument; suitable as an independent oracle.

**Limitations.** Every query after a metric change repeats work close to $O((n+m)\log n)$. On a city graph with many simultaneous queries, this is the computational bottleneck that motivates a customizable index.

**Sources.** Dijkstra (1959) [6]; Cormen et al. [1]; Fredman and Tarjan [2].

## 3.2 A\* search

**Working principle.** Dijkstra’s extract-min uses $d(v)$. A\* uses $f(v)=d(v)+h(v)$, where $h(v)$ estimates remaining cost to $t$. If $h$ is consistent (monotone), A\* is still exact and never expands more nodes than Dijkstra [7]. Landmarks / ALT precompute distances to selected landmarks to obtain $h$ [8].

**Time complexity.** Worst case remains

$$
T_{\mathrm{Astar}}=O((n+m)\log n)
$$

when $h\equiv 0$ (A\* reduces to Dijkstra) or when $h$ is uninformative. With a tight consistent heuristic the **number of expansions** can be much smaller than $n$, but that reduction is instance-dependent and is not a smaller worst-case Big-O.

**Space complexity.** $O(n+m)$ plus any precomputed landmark table. $k$ landmarks typically add $O(kn)$ storage [8].

**Advantages.** Can reduce expansions on goal-directed queries; ALT is a documented backup if CCH is infeasible.

**Limitations.** A weak heuristic gives little gain. Landmark preprocessing is extra work. A\* still does not provide a CCH-style metric-independent index. In this repository, ALT-guided bidirectional A\* is a **planned comparator** and is **not implemented**.

**Sources.** Hart, Nilsson, and Raphael (1968) [7]; Goldberg and Harrelson (2005) [8].

## 3.3 Customizable Contraction Hierarchies (CCH)

**Working principle.** CCH splits routing into three phases [3]:

1. **Metric-independent preprocessing:** contract nodes in a nested-dissection / order-theoretic hierarchy and build an overlay whose structure does not depend on travel times.
2. **Customization:** given a complete metric, compute overlay arc weights (and optional elimination trees) in time linear in the overlay size.
3. **Query:** search only the relevant upward/downward overlay, then unpack the path.

**Time and space complexity.** Dibbelt et al. [3] do not replace Dijkstra’s $O((n+m)\log n)$ with a smaller worst-case combinatorial bound for arbitrary graphs. On **road networks**, after preprocessing:

- customization is linear in the number of overlay arcs;
- queries inspect a small overlay compared with the full graph;
- space is the original graph plus the overlay (empirically near-linear for planar-like road graphs, but overlay size depends on the contraction order).

This assignment therefore states CCH complexity as: **preprocessing once per topology; customization $O(|E_{\text{overlay}}|)$; query much smaller than Dijkstra on road instances, as reported in [3].** No unstated city-scale timing is invented here.

**Advantages.** Exact for the customized metric; many queries can share one customization; weights can change without repeating contraction.

**Limitations.** Customization is still required whenever the metric changes if every query must be exact on the latest metric. Closures, turn restrictions, and integer overflow need extra engineering. The prototype in this repository uses degree ordering and rebuilds a `CCHMetric` on each synchronization; it is not an optimized production CCH.

**Sources.** Dibbelt, Strasser, and Wagner (2016) [3]; Buchhold, Sanders, and Wagner (2019) on CCH with traffic assignment [9].

## 3.4 Related dynamic / certificate methods (survey context)

These are not the three core engines above, but they define the research gap.

| Method | Principle | Limitation relative to this assignment |
|---|---|---|
| Lifelong Planning A\* / D\* Lite [10] | Incremental repair of a search tree | Per-query incremental search, not batched CCH customization |
| Truncated incremental search with bounded suboptimality [5] | Stop repair when a bound holds | Still query-specific incremental search |
| Path planning with CPD heuristics [4] | Old exact distance as lower bound; old path re-evaluated as an upper bound under changing costs | Uses a compressed path database and A\* search, not a CCH refresh gate |
| Chan, Kuncheria, and Macfarlane (2023) [11] | Metropolitan CCH-based dynamic rerouting, customization batching, recheck behaviour, and compliance/penetration | No deterministic per-query monotone stale-metric certificate and no Chennai flood-evidence pipeline |

---

# 4. Research Gap / Motivation

Existing exact engines solve **one** shortest path on **one** metric:

- Dijkstra and A\* repeat almost full work after every metric change.
- CCH moves repeated work into customization, but **eager** CCH still customizes after every update batch if every later query must use the latest weights.

Dynamic search (LPA\*, D\* Lite) repairs a tree for one goal. Bono et al. [4] already use a compressed-path lower/upper-bound idea, but not as a gate on CCH customization.

The limitation this assignment targets is therefore:

> After edge weights have **nondecreased**, many queries could safely reuse a stale CCH (or Dijkstra) metric if a cheap certificate proves the old path is within $(1+\varepsilon)$ of the current optimum. Eager refresh does not test that, so it customizes more often than necessary.

CLMS tries to overcome **unnecessary customization / metric rebuilds**, while still refusing to return a stale path when the bound fails or when any weight has decreased (which invalidates the lower bound).

CLMS does **not** claim to invent Dijkstra, CCH, or the certificate inequality. The algorithmic contribution is the **refresh controller**: when to call `synchronize`, what to do on decreases, and how to compare against an eager baseline under identical traces.

---

# 5. Proposed Novel Algorithm

## 5.1 Name

**Certified Lazy Metric Synchronization (CLMS)**

Paper title form: *Certificate-Gated Dynamic Routing* (CLMS used as a CCH/Dijkstra refresh gate).

## 5.2 Main idea and strategy

Maintain two complete metrics on a **fixed** topology:

- $\bar{w}$: last metric written into the engine (`synchronize`);
- $w$: latest authoritative metric after updates.

On a query $(s,t)$:

1. If any $w_e<\bar{w}_e$, the stale lower bound is invalid. **Refresh** (customize / rebuild) immediately, then query.
2. Else query the engine on $\bar{w}$. Let $P_0$ be the exact path and $L=d_{\bar{w}}(s,t)$.
3. If $w=\bar{w}$, return $P_0$ as `CURRENT`.
4. Else evaluate $U=C_w(P_0)$ by summing **current** weights along the same keyed arcs.
5. If $U\le(1+\varepsilon)L$, return $P_0$ with cost $U$ as `CERTIFIED_STALE` (**no refresh**).
6. Else refresh with $w$, query again, and return the fresh exact path as `REFRESHED`.

The engine (CCH or Dijkstra) still **finds** the path. CLMS only **authorizes reuse** of a stale metric.

## 5.3 Input and output

**Input:** $G$, initial metric, engine, $\varepsilon=p/q$, update batches, queries.
**Output:** per query, a `RouteResult` as in Section 2.3.

The implementation uses exact integer arithmetic for the stretch test:

$$
U\cdot q \le L\cdot(q+p)
\qquad\text{instead of floating }U\le(1+p/q)L.
$$

## 5.4 Pseudocode

```text
algorithm CLMS_Initialize(engine, w0, p, q):
    w_bar ← copy(w0)
    w ← copy(w0)
    engine.synchronize(w_bar)
    pending ← empty
    violating ← empty          // edges with w_e < w_bar_e

algorithm CLMS_ApplyUpdates(batch of replacements):
    apply replacements to w     // version must be contiguous
    pending ← {e in E | w[e] ≠ w_bar[e]}
    violating ← {e in pending | w[e] < w_bar[e]}

algorithm CLMS_Refresh():
    engine.synchronize(w)
    w_bar ← copy(w)
    pending ← empty
    violating ← empty

algorithm CLMS_Route(s, t):
    if violating is not empty:
        CLMS_Refresh()                 // decrease: lower bound invalid
    Q ← engine.query(s, t)             // exact path under w_bar
    if pending is empty:
        return Q                       // CURRENT or post-refresh
    if Q is unreachable:
        return UNREACHABLE as CERTIFIED_UNREACHABLE
    L ← Q.path.cost                    // d_{w_bar}(s,t)
    U ← sum of w[e] over keyed arcs of Q.path
    if U is finite and U * q ≤ L * (q + p):
        return path Q.path with cost U as CERTIFIED_STALE
    CLMS_Refresh()
    return engine.query(s, t)          // REFRESHED
```

Eager baseline used for comparison (not the proposed algorithm):

```text
algorithm Eager_ApplyUpdates(batch):
    apply replacements to w
    engine.synchronize(w)              // always customize / rebuild
```

## 5.5 How CLMS differs from existing algorithms

| Algorithm | What it does | What CLMS does instead |
|---|---|---|
| Dijkstra / A\* | Computes a shortest path on the metric it is given | Still used as engine or oracle; CLMS does not change relaxation |
| Eager CCH | Customizes after every update if the latest metric is required | Customizes only when a decrease occurs or the $(1+\varepsilon)$ test fails |
| LPA\* / D\* Lite | Incrementally repairs a search tree | No search-tree repair; complete snapshot + engine query |
| CPD heuristics [4] | LB/UB certificate inside compressed-path / A\* search | Same inequality class, applied as a **CCH/Dijkstra synchronize gate** with mandatory refresh on decreases |

---

# 6. Algorithm Illustration

The following three parallel roads are a **teaching example**. The numbers in minutes are chosen so that arithmetic is visible. They are not Chennai measurements.

## 6.1 Initial synchronized metric

| Road | $\bar{w}$ (min) |
|---|---:|
| A | 5 |
| B | 6 |
| C | 8 |

Query: origin $s$ to destination $t$ using only one of {A, B, C}.
Engine (CCH or Dijkstra) returns Road A.
$L=5$.
Tolerance $\varepsilon=5\%=5/100$, so the allowed stale cost is

$$
(1+\varepsilon)L = 1.05\times 5 = 5.25.
$$

Integer test with $p=5$, $q=100$: accept stale path iff $U\cdot 100\le L\cdot 105$.

## 6.2 Case I — small increase, certificate passes (no refresh)

Projected load raises only Road A: $w_A=5.2$, $w_B=6$, $w_C=8$.
All weights are $\ge\bar{w}$, so the lower bound remains valid.
Old path A has $U=5.2$.
$5.2\le 5.25$, so CLMS returns A as `CERTIFIED_STALE`. **Customization is skipped.**

| Step | Quantity | Value |
|---|---|---|
| 1 | Query stale engine | Path A, $L=5$ |
| 2 | Evaluate A on $w$ | $U=5.2$ |
| 3 | Test | $5.2\le 5.25$ pass |
| 4 | Refresh? | No |
| 5 | Result | A, cost 5.2 |

## 6.3 Case II — large increase, certificate fails (refresh, same path)

Now $w_A=5.8$.
$U=5.8>5.25$, certificate fails.
CLMS customizes with $(5.8,6,8)$ and queries again.
Fresh optimum is still A at 5.8 (`REFRESHED`).

## 6.4 Case III — increase beyond the next alternative (refresh, new path)

Now $w_A=7.0$.
Stale path A has $U=7.0>5.25$.
After refresh the engine compares 7, 6, 8 and returns B at 6.

## 6.5 Case IV — decrease (mandatory refresh, no certificate)

Road A recovers from 5 to 4.
Then $w_A=4<\bar{w}_A=5$.
The old $L=5$ is **not** a lower bound on the true distance (which is 4).
CLMS refreshes **before** querying. The certificate is not applied.

## 6.6 Decision diagram

```text
updates → compare w and w_bar
              │
              ├── any decrease ──► synchronize engine ──► query ──► REFRESHED
              │
              └── all nondecreasing
                        │
                        ▼
                   query stale engine → path P0, L
                        │
                        ▼
                   U ← cost of P0 under w
                        │
                        ├── U ≤ (1+ε)L ──► return P0 ──► CERTIFIED_STALE
                        │
                        └── else ──► synchronize engine ──► query ──► REFRESHED
```

---

# 7. Correctness / Working Explanation

## 7.1 Theorem (bounded reuse under nondecreasing weights)

**Assumptions.** Fixed topology; complete atomic snapshots; non-negative weights; engine query exact for $\bar{w}$; $w_e\ge\bar{w}_e$ for every arc $e$.

**Claim.** Let $P_0$ be an exact $\bar{w}$-shortest path, $L=d_{\bar{w}}(s,t)$, $U=C_w(P_0)$. If $U\le(1+\varepsilon)L$, then

$$
C_w(P_0)=U\le(1+\varepsilon)\,d_w(s,t).
$$

**Proof.** For every path $P$, $C_{\bar{w}}(P)\le C_w(P)$ because each arc is pointwise at least as costly. Minimizing over $P$ gives $L=d_{\bar{w}}(s,t)\le d_w(s,t)$.
$P_0$ is still feasible, so $d_w(s,t)\le U$.
If $U\le(1+\varepsilon)L$, then $U\le(1+\varepsilon)L\le(1+\varepsilon)d_w(s,t)$.

This is the standard lower/upper-bound certificate used in compressed-path heuristic search [4] and truncated incremental search [5]. It is **applied** here, not claimed as a new theorem.

## 7.2 Why decreases forbid the stale lower bound

If some $w_e<\bar{w}_e$, there may exist a path whose current cost is below $L$. Then $L\not\le d_w(s,t)$, and accepting $U\le(1+\varepsilon)L$ would not imply the $(1+\varepsilon)$ guarantee. CLMS therefore refreshes whenever a violating (decrease) set is nonempty, **before** querying.

## 7.3 Unreachable queries

If the stale engine reports unreachable and weights have only increased, reachability cannot improve, so unreachability remains valid. If a decrease occurred, CLMS has already refreshed, so unreachability is determined on the current metric.

## 7.4 What correctness does **not** cover

- Correctness is with respect to the **represented integer metric**, not with respect to true Chennai travel time, BPR calibration, or SUMO queues.
- Native CCH path equality with Dijkstra is an implementation obligation. The recorded synthetic experiment reported **zero** CCH-versus-Dijkstra oracle mismatches on that workload; that is evidence for those traces, not a proof for all graphs.

---

# 8. Complexity Analysis

Let $n=|V|$, $m=|E|$, $k$ be the number of arcs on the returned path, and $u$ the number of replacements in one update batch.

Let $T_{\text{query}}$ be one exact engine query on the synchronized metric.
Let $T_{\text{sync}}$ be one complete `synchronize` (Dijkstra: rebuild weighted graph; CCH: customization / metric rebuild in the prototype).

## 8.1 Update

The current implementation copies the metric and then **scans all $m$ arcs** to rebuild the pending and violating sets. Replacements are $O(u)$, but the scan dominates:

$$
T_{\text{update}}=O(m).
$$

This is an implementation fact, not an information-theoretic lower bound. A future version could maintain pending sets in $O(u)$ by inspecting only replaced arcs.

## 8.2 Query — CLMS

**Best case (nondecreasing, certificate pass):** one query plus path evaluation

$$
T_{\text{CLMS, best}}=T_{\text{query}}+O(k).
$$

The stretch test is $O(1)$ arithmetic.

**Decrease present:** one mandatory sync, then one query:

$$
T_{\text{CLMS, decrease}}=T_{\text{sync}}+T_{\text{query}}+O(k).
$$

**Certificate fail (nondecreasing):** stale query + $O(k)$ + sync + second query:

$$
T_{\text{CLMS, fail}}=T_{\text{sync}}+2\,T_{\text{query}}+O(k).
$$

**Worst case per query** is therefore

$$
T_{\text{CLMS, worst}}=T_{\text{sync}}+2\,T_{\text{query}}+O(k).
$$

For the **Dijkstra engine**, $T_{\text{query}}=O((n+m)\log n)$ and $T_{\text{sync}}=O(m)$ for a full rebuild, so

$$
T_{\text{CLMS-Dijkstra, worst}}=O((n+m)\log n).
$$

The Big-O matches eager Dijkstra; the improvement is **fewer synchronizations across a workload**, not a better worst-case single query.

For the **CCH engine**, $T_{\text{query}}$ is the CCH query and $T_{\text{sync}}$ is customization. CLMS saves work when many queries take the best-case branch and skip $T_{\text{sync}}$. Mixed decreases force $T_{\text{sync}}$ often; then CLMS cannot be asymptotically cheaper than eager CCH.

## 8.3 Space complexity

CLMS stores two complete weight maps, a pending set, and a violating set:

$$
S_{\text{CLMS}}=O(m)
$$

**in addition to** the engine. Dijkstra engine space is $O(n+m)$. CCH engine space is the overlay of [3], not re-derived here.

Eager refresh stores one weight map plus the engine: also $O(m)$ extra, without a second full copy. CLMS therefore uses **a constant factor more metric storage** (two maps) in exchange for the certificate test.

## 8.4 Workload view (why experiments are needed)

Over $E$ epochs with $Q$ queries each, eager refresh pays about $E\cdot T_{\text{sync}}+EQ\cdot T_{\text{query}}$.
CLMS pays $R\cdot T_{\text{sync}}+EQ\cdot T_{\text{query}}$ plus $O(k)$ path evaluations, where $R\le E$ is the number of refreshes.
If weights mostly increase and $\varepsilon>0$, $R$ can be much smaller than $E$. If decreases are frequent, $R\approx E$ and wall-clock time need not improve. That workload distinction will be measured after Stages 4 and 5.

---

# 9. Implementation

The proposed algorithm is implemented as a refresh controller in front of an exact shortest-path engine. The controller applies atomic metric updates, tests the decrease set, queries the synchronized engine, re-evaluates the returned keyed path on the current metric, and either accepts the stale path or customizes and queries again. Two engines are wired to the same interface: NetworkX Dijkstra as the correctness oracle, and a native RoutingKit CCH prototype for finite integer metrics. An eager baseline synchronizes after every accepted update batch so later comparisons can use identical traces.

Unit tests currently check certificate pass and fail, mandatory refresh after a decrease, keyed parallel-edge identity, CCH equality with Dijkstra on synthetic graphs, rejection of unsafe CCH weights, and exact rational $\varepsilon$. These tests confirm the controller, not Chennai traffic.

Reproduction:

```bash
python scripts/run_stage3_graph.py
python scripts/run_stage4_road_state.py
python scripts/run_stage5_sumo.py
python scripts/run_certified_lazy_experiment.py --engine both --mode both
```

## 9.1 Dated Greater Chennai graph (Stage 3)

Source: Geofabrik `india-260901.osm.pbf`, provider MD5 `44ec6a7dff8ff2f3382da80a546b505f`, clipped to the GCC 2022 ward union. Decision: **PASS WITH REPORTED ATTRIBUTE MISSINGNESS**.

| Quantity | Value | Classification |
|---|---:|---|
| Nodes | 155,345 | OBSERVED |
| Directed arcs | 331,545 | OBSERVED |
| Weak / strong components | 1 / 1 | OBSERVED |
| Explicit OSM maxspeed arcs | 6,092 | OBSERVED |
| Missing maxspeed arcs | 325,453 | UNAVAILABLE |
| Missing lanes | 318,131 | UNAVAILABLE |
| Free-flow time assigned | 6,092 | OBSERVED only where speed exists |
| Arc-ID collisions | 0 | OBSERVED |

This graph is not a calibrated traffic network. Missing speeds were not replaced by a silent city-wide default in Stage 3.

## 9.2 Explained road states (Stage 4)

Historical OpenCity inventories were mapped with a distance sweep. 150 m is a **SCENARIO** reporting distance (same as the Stage 1 demo), not measured KML accuracy. Rainfall and DEM do not create closures. BLOCKED/SEVERE labels are declared scenario rules.

| Matching distance (m) | Hotspot features | Unique matched features | Unmatched | Matched arcs |
|---:|---:|---:|---:|---:|
| 50 | 327 | 318 | 9 | 583 |
| 100 | 327 | 324 | 3 | 594 |
| 150 | 327 | 325 | 2 | 596 |
| 200 | 327 | 326 | 1 | 598 |
| 250 | 327 | 326 | 1 | 598 |

| Assigned scenario state at 150 m | Arc rows | Basis |
|---|---:|---|
| BLOCKED | 596 | Historical hotspot nearest-arc rule (**SCENARIO**) |
| SEVERE | 99,443 | Historical inundation-polygon overlay (**SCENARIO**) |
| Conflicts (hotspot vs inundation) | 269 | Both rules applied; more severe kept |
| UNKNOWN / NORMAL | not tabulated | Default for unmapped arcs |

Open-Meteo ERA5 rainfall for 1 Nov–15 Dec 2015 at (13.0827, 80.2707) totals 731.7 mm over 1,080 hourly rows (**MODELLED** reanalysis, not street flooding). IMERG was **UNAVAILABLE** without Earthdata credentials.

## 9.3 SUMO import (Stage 5)

Demand class: **SYNTHETIC**. Calibration class: **SYNTHETIC**. Vehicle types: **SCENARIO** labels.

| Item | Result |
|---|---|
| Public Chennai counts / OD / speeds | UNAVAILABLE |
| OSM `netconvert` of the GCC extract | FAIL (SUMO 1.18.0 RTree/junction-angle abort) |
| Import used instead | Stage 3 GraphML as SUMO node/edge files |
| SUMO edges / lanes / junctions | 331,545 / 345,252 / 156,607 |
| Observed OSM speeds used | 6,092 |
| SCENARIO default 30 km/h speeds | 325,453 |
| Seeded random trips | 60 trips, seed 8597, 300 s |

SUMO output is simulated traffic. It is not live or counted Chennai traffic. City-scale CCH timings, turns, and closures remain Stage 6.

---

# 10. Comparison with Existing Algorithms

The two implemented baselines compared with Certificate-Gated Routing are:

1. Eager repeated Dijkstra, which rebuilds or re-solves on the latest metric after every update batch.
2. Eager CCH, which customizes after every update batch and then queries.

Certificate-Gated Routing uses the same engine, same graph, same updates, same queries, and the same $\varepsilon=5\%$ as the matching eager method. City-scale comparison on the 331,545-arc Chennai graph is **not** in this table; that is Stage 6. The numbers below are the committed synthetic experiment (`docs/evidence/CERTIFIED_LAZY_SYNC_RESULTS.json`): 200 nodes, 600 extra arcs, 100 epochs, 5 updates and 50 queries per epoch, seed 8597.

| Engine | Update mode | Queries | Eager syncs | CLMS refreshes | Refreshes avoided | Certificate violations | Oracle mismatches |
|---|---|---:|---:|---:|---:|---:|---:|
| Dijkstra | increases only | 5,000 | 101 | 6 | 94 | 0 | 0 |
| Dijkstra | mixed | 5,000 | 101 | 86 | 14 | 0 | 0 |
| CCH | increases only | 5,000 | 101 | 6 | 94 | 0 | 0 |
| CCH | mixed | 5,000 | 101 | 86 | 14 | 0 | 0 |

| Engine | Update mode | Eager total (s) | CLMS total (s) |
|---|---|---:|---:|
| Dijkstra | increases only | 0.705 | 0.587 |
| Dijkstra | mixed | 0.736 | 0.707 |
| CCH | increases only | 0.203 | 0.120 |
| CCH | mixed | 0.202 | 0.209 |

These are single-run synthetic wall-clock values. They are not Chennai traffic outcomes. Mixed workloads include weight decreases, which invalidate the stale lower bound and force refresh; CLMS then does not save customization work. A\* / ALT is not implemented yet and is omitted.

---

# 11. Results and Discussion

On the synthetic monotone-increase workload, Certificate-Gated Routing avoided 94 of 100 post-initial eager refreshes for both Dijkstra and CCH, with zero certificate violations and zero oracle mismatches. On the mixed increase/decrease workload it avoided only 14 of 100, as required by the decrease rule in Section 5. That matches the complexity discussion in Section 8: CLMS helps when weights mostly nondecrease and $\varepsilon>0$, and does not help when recoveries are frequent.

Stages 3–5 now supply a dated Chennai graph, historical flood overlays, and a **SYNTHETIC** SUMO scenario. They do **not** show that CLMS reduces Chennai congestion, emergency response time, or live flood routing. Most OSM arcs still lack explicit maxspeed. Inundation-polygon overlay marks tens of thousands of arcs SEVERE as a scenario, not as observed 2015 closures. City-scale CCH comparison remains Stage 6.

No statement is made that the method is calibrated to Chennai traffic. Stage 5 labels the SUMO run **SYNTHETIC** because no public link counts or OD matrix were obtained.

---

# 12. Conclusion

This assignment studies repeated shortest-path queries when road weights change, with Chennai flood, incident, and congestion routing as the intended real-world setting.

**Proposed algorithm:** Certificate-Gated Routing, implemented as Certified Lazy Metric Synchronization (CLMS). It leaves path-finding to Dijkstra or CCH and refreshes the engine metric only when a decrease invalidates the stale lower bound or when re-evaluating the old path fails $U\le(1+\varepsilon)L$.

**Current status:** The algorithm, proof under stated assumptions, complexity derivation, literature comparison, dated Chennai graph, historical road-state overlays, and a SYNTHETIC SUMO import are complete. City-scale CCH comparison (Stage 6) is not yet run.

**Limitations:** The certificate is established prior art; CLMS is a controller, not a new shortest-path theorem. Prototype CCH is unoptimized. Closures on native CCH and turn-expanded city queries remain unvalidated. Extra space is $O(m)$. Worst-case per-query time remains $\Theta(T_{\text{sync}}+T_{\text{query}})$. Most OSM maxspeed values are missing. SUMO demand is synthetic.

---

# 13. References

IEEE numbered style.

[1] T. H. Cormen, C. E. Leiserson, R. L. Rivest, and C. Stein, *Introduction to Algorithms*, 3rd ed. Cambridge, MA, USA: MIT Press, 2009.

[2] M. L. Fredman and R. E. Tarjan, “Fibonacci heaps and their uses in improved network optimization algorithms,” *J. ACM*, vol. 34, no. 3, pp. 596–615, 1987.

[3] J. Dibbelt, B. Strasser, and D. Wagner, “Customizable contraction hierarchies,” *ACM J. Exp. Algorithmics*, vol. 21, Art. 1.5, 2016. doi: 10.1145/2886843.

[4] M. Bono, A. E. Gerevini, D. D. Harabor, and P. J. Stuckey, “Path planning with CPD heuristics,” in *Proc. 28th Int. Joint Conf. Artif. Intell. (IJCAI)*, 2019, pp. 1199–1205. doi: 10.24963/ijcai.2019/167.

[5] S. Aine and M. Likhachev, “Truncated incremental search,” *Artif. Intell.*, vol. 234, pp. 49–77, 2016. doi: 10.1016/j.artint.2016.01.009.

[6] E. W. Dijkstra, “A note on two problems in connexion with graphs,” *Numer. Math.*, vol. 1, pp. 269–271, 1959.

[7] P. E. Hart, N. J. Nilsson, and B. Raphael, “A formal basis for the heuristic determination of minimum cost paths,” *IEEE Trans. Syst. Sci. Cybern.*, vol. 4, no. 2, pp. 100–107, 1968.

[8] A. V. Goldberg and C. Harrelson, “Computing the shortest path: A\* search meets graph theory,” in *Proc. 16th ACM-SIAM Symp. Discrete Algorithms (SODA)*, 2005, pp. 156–165.

[9] V. Buchhold, P. Sanders, and D. Wagner, “Real-time traffic assignment using engineered customizable contraction hierarchies,” *ACM J. Exp. Algorithmics*, vol. 24, Art. 2.4, 2019. doi: 10.1145/3362693.

[10] S. Koenig, M. Likhachev, and D. Furcy, “Lifelong Planning A\*,” *Artif. Intell.*, vol. 155, no. 1–2, pp. 93–146, 2004.

[11] C. Chan, A. Kuncheria, and J. Macfarlane, “Simulating the impact of dynamic rerouting on metropolitan-scale traffic systems,” *ACM Trans. Model. Comput. Simul.*, vol. 33, no. 1–2, Art. 7, pp. 7:1–7:29, 2023. doi: 10.1145/3579842.

[12] J. Pan, M. A. Khan, I. S. Popa, K. Zeitouni, and C. Borcea, “Proactive vehicle re-routing strategies for congestion avoidance,” in *Proc. 8th IEEE Int. Conf. Distrib. Comput. Sensor Syst. (DCOSS)*, Hangzhou, China, 2012, pp. 265–272. doi: 10.1109/DCOSS.2012.29.

[13] N. Gore, S. Arkatkar, G. Joshi, and C. Antoniou, “Modified Bureau of Public Roads link function,” *Transp. Res. Rec.*, vol. 2677, no. 5, pp. 966–990, 2023. doi: 10.1177/03611981221138511.

[14] Y. Sashank, N. A. Navali, A. Bhanuprakash, B. A. Kumar, and L. Vanajakshi, “Calibration of SUMO for Indian heterogeneous traffic conditions,” in *Recent Advances in Traffic Engineering*, Springer, 2020, ch. 13. doi: 10.1007/978-981-15-3742-4_13.

[15] OpenStreetMap contributors, “OpenStreetMap,” [Online]. Available: https://www.openstreetmap.org/copyright

[16] Geofabrik GmbH, “India OSM extract,” [Online]. Available: https://download.geofabrik.de/asia/india.html

[17] Greater Chennai Corporation / OpenCity, “GCC Ward Information — Chennai GCC Ward Map 2022,” resource ID `e90176d4-319a-45bd-918e-ecce4f048c4d`. [Online]. Available: https://data.opencity.in/dataset/gcc-ward-information

---

# Appendix A — Claim checklist (for the evaluator)

| Required item | Where | Status |
|---|---|---|
| Title with problem + approach | §1 | Complete |
| Input / output / constraints / assumptions | §2 | Complete; assumptions classified |
| Example scenario | §2.6, §6 | Complete; example values labelled invented |
| ≥3 existing algorithms with complexity, pros/cons, citations | §3 | Dijkstra, A\*, CCH |
| Research gap | §4 | Complete |
| Named algorithm + pseudocode + difference | §5 | CLMS |
| Step-by-step illustration | §6 | Complete |
| Correctness | §7 | Proof under stated assumptions |
| Time and space derived, not only Big-O | §8 | Complete |
| Implementation + tests | §9 | Controller described; result tables deferred to Stages 4–5 |
| Compare ≥2 existing methods | §10 | Baselines named; comparison tables deferred to Stages 4–5 |
| Tables; no unsupported improvement claim | §6 illustration; §11 | Experimental tables withheld until Stages 4–5 |
| Conclusion + limitations | §12 | Complete |
| ≥10 references, ≥5 papers, IEEE | §13 | 17 entries; papers [2]–[14] |

**Intentionally blank until Stages 3–5:** Chennai graph timings, flood-state accuracy, SUMO travel time, memory profiling, A\* implementation numbers. Those will be added only from generated artifacts.
