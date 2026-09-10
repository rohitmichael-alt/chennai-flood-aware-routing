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
- facility-oriented road-criticality ranking.

Latest recorded result: **55 passed** when `routingkit-cch` is installed (4 skip without it).

Pathway tests also cover BPR/capacity validation, Stage 1 graph preservation, identity updates, explained-state snapshots, and the adoption filter.
