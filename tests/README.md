# Tests

Tests should be added with each implementation stage.

Current tests verify:

- project structure;
- Stage 1 CRS, flood-to-road, BPR/capacity, closure, and route change;
- complete versioned metric snapshots;
- monotone certificate pass/fail behavior;
- mandatory refresh after a lower-bound-invalidating decrease;
- closure and reopening;
- keyed parallel-edge path identity;
- native CCH equality with Dijkstra;
- deterministic differential experiments;
- population-weighted accessibility;
- reproducible partial-compliance selection.
- evidence lag and false-positive/false-negative perturbation;
- facility-oriented road-criticality ranking;
- pinned boundary provenance and exact-source archiving;
- explicit invalid-boundary repair auditing;
- deterministic Stage 3 arc identifiers, strict speed parsing, and graph
  missingness reporting.

Latest recorded result: **53 passed**.
