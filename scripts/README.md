# Scripts

Place reproducible command-line scripts here as implementation stages begin.

Current scripts:

- `run_stage1_poc.py`: downloads the Stage 1 open data sources, maps historical flood hotspots to roads, applies the controlled blocked-edge model assumption, runs before/after Dijkstra routing, and writes CSV/map outputs.
- `run_certified_lazy_experiment.py`: replays one seeded metric-update/query trace through eager and certificate-gated Dijkstra/CCH engines, checks the declared route bound, and writes per-query CSV plus summary JSON evidence.

Run the routing experiment after installing `.[test,cch]`:

```bash
python scripts/run_certified_lazy_experiment.py --engine both --mode both
```

The experiment is synthetic. Its timing and synchronization results must not be described as Chennai traffic outcomes.
