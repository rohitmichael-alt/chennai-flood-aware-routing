# Chennai Compound-Disruption Dynamic Routing

Research prototype for flood-, incident-, and congestion-aware routing using:

- OpenStreetMap and Chennai flood evidence;
- effective road capacity and BPR travel-time costs;
- NetworkX Dijkstra and native Customizable Contraction Hierarchies;
- certificate-gated metric synchronization;
- planned stable projected-load rerouting and SUMO evaluation.

## Research Claim

This project does not introduce a new shortest-path algorithm or a new route-certificate theorem. It evaluates a Chennai-oriented integration in which an established lower/upper-bound certificate decides when a stale CCH metric must be refreshed.

See [`docs/PROJECT_RESEARCH_AND_EVIDENCE.md`](docs/PROJECT_RESEARCH_AND_EVIDENCE.md) for the research gap, proof, three-road example, prior art, datasets, preliminary results, and limitations.

## Current Status

| Stage | Status |
|---|---|
| Historical flood-to-road Dijkstra proof of concept | Implemented |
| Certificate-gated synchronization controller | Implemented |
| Exact NetworkX Dijkstra adapter | Implemented |
| Native `routingkit-cch` adapter | Implemented for finite integer experimental metrics |
| Eager baseline and deterministic experiments | Implemented |
| Accessibility and partial-compliance metrics | Implemented |
| Chennai graph/flood/rainfall/SUMO integration | Planned |
| Full publication evaluation | Planned |

Current tests: **28 passing** at the latest recorded verification.

## Install

Python 3.11 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test,cch]"
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test,cch]"
```

## Run Tests

```bash
python -m pytest
```

## Run the Certificate/CCH Experiment

```bash
python scripts/run_certified_lazy_experiment.py \
  --engine both \
  --mode both \
  --seed 8597 \
  --nodes 200 \
  --extra-edges 600 \
  --epochs 100 \
  --updates-per-epoch 5 \
  --queries-per-epoch 50 \
  --epsilon-percent 5
```

The runner compares eager refresh with certificate-gated refresh using identical traces. It writes per-query CSV and summary JSON files under `outputs/tables/`.

Committed evidence from the recorded run is available at [`docs/evidence/CERTIFIED_LAZY_SYNC_RESULTS.json`](docs/evidence/CERTIFIED_LAZY_SYNC_RESULTS.json).

### Preliminary Result

In one seeded 5,000-query CCH workload:

- monotone increases avoided 94 of 100 eager update refreshes;
- mixed increases/decreases avoided 14 of 100;
- no certificate violations or post-refresh exact mismatches were observed.

These are synthetic functional/performance measurements, not Chennai traffic outcomes.

## Run Stage 1

```bash
python scripts/run_stage1_poc.py
```

Stage 1:

1. downloads OpenCity 2015 historical flood hotspots;
2. downloads a small Chennai OSM driving graph;
3. maps historical points to nearby roads;
4. applies a controlled hard closure to one real mapped edge;
5. computes BPR weights;
6. runs Dijkstra before and after closure;
7. writes CSV, JSON, GraphML, and PNG outputs.

Stage 1 proves controlled closure avoidance. It does not prove current flooding, calibrated congestion behaviour, or city-wide performance.

## Routing Components

| File | Responsibility |
|---|---|
| `routing/engine.py` | Engine-neutral snapshots, keyed paths, and protocol |
| `routing/networkx_engine.py` | Exact Dijkstra reference engine |
| `routing/cch_engine.py` | Native experimental CCH adapter |
| `routing/dynamic.py` | Certificate and refresh controller |
| `evaluation/baseline.py` | Eager-refresh oracle |
| `evaluation/experiments.py` | Reproducible synthetic experiment |
| `evaluation/metrics.py` | Population/facility access and compliance utilities |

## Certificate in One Paragraph

If every current represented edge weight is at least its synchronized value, the old exact shortest distance remains a lower bound. The old path evaluated with current weights supplies an upper bound. If:

\[
U\le(1+\epsilon)L,
\]

the path is within \(1+\epsilon\) of the current represented optimum and CCH refresh can be skipped for that query. Any decrease below the synchronized metric invalidates the lower bound and forces refresh.

This principle has close prior art, especially [CPD-Search](https://doi.org/10.24963/ijcai.2019/167), and is not claimed as a new theorem.

## Data and Simulation Rules

- Historical flood data is not live flooding.
- IMERG rainfall is not street flood depth.
- SUMO output is simulated traffic.
- Capacity multipliers and BPR parameters require calibration/sensitivity analysis.
- CCH and Dijkstra must receive identical represented metrics in comparisons.
- CCH speed does not itself improve traffic; route-adoption policy determines network effects.

## Documentation

- [`CONTEXT.md`](CONTEXT.md): authoritative project and claim boundary.
- [`PLAN.md`](PLAN.md): revised stages and completion criteria.
- [`STAGE1_HANDOFF.md`](STAGE1_HANDOFF.md): historical Stage 1 implementation.
- [`docs/PROJECT_RESEARCH_AND_EVIDENCE.md`](docs/PROJECT_RESEARCH_AND_EVIDENCE.md): compact research paper/document.
- `docs/PROJECT_RESEARCH_AND_EVIDENCE.docx`: generated Word version.
