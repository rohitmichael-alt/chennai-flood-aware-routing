# Scripts

Reproducible command-line entry points for the evidence-gated execution stages live here.

Current scripts:

- `run_stage1_poc.py`: downloads the Stage 1 open data sources, maps historical flood hotspots to roads, applies the controlled blocked-edge model assumption, runs before/after Dijkstra routing, and writes CSV/map outputs.
- `run_certified_lazy_experiment.py`: replays one seeded metric-update/query trace through eager and certificate-gated Dijkstra/CCH engines, checks the declared route bound, and writes per-query CSV plus summary JSON evidence.
- `run_stage3_boundary.py`: downloads the pinned OpenCity/GCC 2022 200-ward
  KML, captures provider metadata and SHA-256, explicitly audits/repairs invalid
  source polygons, preserves the exact source, and writes the Stage 3 boundary
  evidence manifest.
- `run_stage3_graph.py`: verifies the dated Geofabrik India PBF, clips it to
  the GCC 2022 union, builds the driving graph without speed imputation, and
  writes the Stage 3 graph audit and QA map.
- `run_stage4_road_state.py`: pins historical flood KMLs, Open-Meteo rainfall,
  and DEM context, maps inventories with a distance sweep, and writes labelled
  scenario road states.
- `run_stage5_sumo.py`: records traffic-data feasibility, imports the Stage 3
  graph into SUMO, and writes seeded synthetic trips. Demand is SYNTHETIC.
- `run_stage6_cch.py`: maps the Stage 3 graph into inertial CCH, quantizes
  travel times to milliseconds, and compares unpacked CCH paths with Dijkstra.
- `check_stage3_reproducibility.py`: rebuilds the graph and compares sorted
  stable node- and arc-ID digests with the committed Stage 3 evidence.
- `run_stage1_publication.py`: regenerates the dated Stage 1 before/after route
  extract, route table, map, and publication evidence from Stage 3/4 artifacts.
- `run_stage7_reservations.py`: evaluates time-binned compliant-only projected
  load reservations on the labelled four-node scenario network.
- `run_stage8_accessibility.py`: streams the city graph into a sparse directed
  projection and evaluates population-weighted facility accessibility and
  dependency exposure.
- `run_stage9_emergency.py`: evaluates the deterministic emergency-priority
  policy and its ordinary-user external-delay cap.
- `run_stage10_evaluation.py`: synthesizes the executed/unexecuted comparison
  matrix, paired-seed intervals, negative results, and final evidence decision.
- `build_research_docx.py` and `build_research_pdf.py`: regenerate the academic
  manuscript artifacts from the evidence-backed Markdown source.

Run the routing experiment after installing `.[test,cch]`:

```bash
python scripts/run_certified_lazy_experiment.py --engine both --mode both
```

The experiment is synthetic. Its timing and synchronization results must not be described as Chennai traffic outcomes.

`run_certified_lazy_sweep.py` regenerates the complete committed main and
epsilon-sensitivity manifest in
`docs/evidence/CERTIFIED_LAZY_SYNC_RESULTS.json`. Per-run CSV/JSON filenames
include a configuration digest, so parameter sweeps do not overwrite one
another.
