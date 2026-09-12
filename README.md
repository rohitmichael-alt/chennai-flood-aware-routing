# Chennai Compound-Disruption Dynamic Routing

Research prototype for flood-conditioned and congestion-aware routing using:

- OpenStreetMap and Chennai flood evidence;
- effective road capacity and BPR travel-time costs;
- NetworkX Dijkstra and native Customizable Contraction Hierarchies;
- certificate-gated metric synchronization;
- time-binned projected-load reservations and a reproducible SUMO network import.

## Research Claim

This project does not introduce a new shortest-path algorithm or a new route-certificate theorem. It evaluates a Chennai-oriented integration in which an established lower/upper-bound certificate decides when a stale CCH metric must be refreshed.

See [`docs/PROJECT_RESEARCH_AND_EVIDENCE.md`](docs/PROJECT_RESEARCH_AND_EVIDENCE.md) for the research gap, proof, three-road example, prior art, datasets, preliminary results, and limitations.

Any later AI executor must use the copy-paste brief in [`docs/MASTER_PROMPT_FOR_EXECUTOR_AI.md`](docs/MASTER_PROMPT_FOR_EXECUTOR_AI.md).

## Current Status

| Stage | Status |
|---|---|
| Historical flood-to-road Dijkstra proof of concept | Dated Stage 3 extract; **PASS WITH LIMITATIONS** |
| Certificate-gated synchronization controller | Implemented |
| Exact NetworkX Dijkstra adapter | Implemented |
| Native `routingkit-cch` adapter | City graph validated against Dijkstra; 0/24 cost mismatches |
| Eager baseline and deterministic experiments | Implemented |
| Accessibility, compliance, and road criticality | Chennai graph/WorldPop/catalogues run; **PASS WITH LIMITATIONS** |
| Integer BPR snapshot pathway glue | Implemented |
| SCENARIO route-adoption/reservation policy | Implemented; matched SUMO periodic comparator unexecuted |
| Chennai graph/flood/rainfall/SUMO integration | Graph/state/network import complete; traffic outcomes synthetic/unexecuted |
| Full publication evaluation | **PARTIAL**; explicit comparator and ablation gaps in Stage 10 evidence |

Current tests: run `python -m pytest`; optional Stage 8 requires `.[stage8]`.

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

Regenerate the committed full main/sensitivity manifest:

```bash
python scripts/run_certified_lazy_sweep.py
```

Committed evidence from the recorded run is available at [`docs/evidence/CERTIFIED_LAZY_SYNC_RESULTS.json`](docs/evidence/CERTIFIED_LAZY_SYNC_RESULTS.json).

### Preliminary Result

In one seeded 5,000-query CCH workload:

- monotone increases avoided 94 of 100 eager update refreshes;
- mixed increases/decreases avoided 14 of 100;
- no certificate violations or post-refresh exact mismatches were observed.

These are synthetic functional/performance measurements, not Chennai traffic outcomes.

## Run the dated Stage 1 publication demonstration

```bash
python scripts/run_stage1_publication.py
```

Stage 1:

1. loads the pinned Stage 3 Chennai graph and Stage 4 historical-evidence state table;
2. selects an affected directed arc with a finite alternative;
3. preserves the route union as a documented GraphML extract;
4. applies a controlled hard closure to one real mapped edge;
5. computes BPR weights;
6. runs Dijkstra before and after closure;
7. writes CSV, JSON, GraphML, and PNG outputs.

Stage 1 demonstrates controlled scenario closure avoidance. It does not prove current flooding, calibrated congestion behaviour, or city-wide traffic outcomes.

## Run the full evidence pipeline

Use the Stage 3-10 scripts in numeric order. Machine-readable committed outputs are under `docs/evidence/`; `STAGE10_EVALUATION_RESULTS.json` is the authoritative executed/unexecuted matrix.

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
| `evaluation/robustness.py` | Evidence-lag and classification-error experiments |

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
- [`docs/SENIOR_RESEARCH_REVIEW.md`](docs/SENIOR_RESEARCH_REVIEW.md): literature-grounded project-to-paper cross-analysis, novelty pivots, rejection risks, and venue guidance.
- `docs/PROJECT_RESEARCH_AND_EVIDENCE.docx`: generated Word version.
