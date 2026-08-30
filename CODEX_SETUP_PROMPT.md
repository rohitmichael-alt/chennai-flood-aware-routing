# CODEX_SETUP_PROMPT.md

## Purpose

This prompt is for the **initial repository/setup stage only** of the Chennai flood- and congestion-aware dynamic traffic routing project.

Before doing anything, read:

1. `CONTEXT.md`
2. `PLAN.md`
3. This file: `CODEX_SETUP_PROMPT.md`

`CONTEXT.md` is the authoritative description of the project's architecture, scope, terminology, data sources, assumptions, limitations, and locked baseline.

`PLAN.md` is the authoritative staged implementation roadmap.

Do not redesign or replace either document.

---

# Your Role

You are the **initial project architect/setup agent**.

Your job is to create a clean repository/workspace that can later be opened in Cursor for staged implementation.

This is a **repository setup task only**.

Use high reasoning before making changes.

Inspect the current workspace first.

If an existing repository or useful files are present, do not blindly delete or overwrite them.

---

# Current Project Status

The project is currently:

```text
Stage 1 — Monday Proof of Concept: IN PROGRESS
Stages 2 onward: PENDING
```

The Chennai road topology is **not yet complete**.

Do not imply that Stage 1 has already been implemented.

---

# What You MUST Do

Create a clean, professional Python repository suitable for long-term development of the project.

The repository should separate these responsibilities:

```text
DATA
PREPROCESSING
MODELS
ROUTING
SIMULATION
EVALUATION
VISUALIZATION
```

Use a structure approximately like:

```text
project-root/
│
├── README.md
├── CONTEXT.md
├── PLAN.md
├── CODEX_SETUP_PROMPT.md
├── pyproject.toml
├── requirements.txt
├── .gitignore
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── README.md
│
├── src/
│   └── chennai_routing/
│       ├── __init__.py
│       ├── config.py
│       │
│       ├── data/
│       │   ├── __init__.py
│       │   ├── osm.py
│       │   ├── flood.py
│       │   ├── rainfall.py
│       │   ├── elevation.py
│       │   └── hydrology.py
│       │
│       ├── preprocessing/
│       │   ├── __init__.py
│       │   ├── roads.py
│       │   ├── geospatial.py
│       │   └── validation.py
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   ├── flood_susceptibility.py
│       │   ├── road_condition.py
│       │   ├── capacity.py
│       │   └── bpr.py
│       │
│       ├── routing/
│       │   ├── __init__.py
│       │   ├── dijkstra.py
│       │   ├── dynamic.py
│       │   ├── rerouting.py
│       │   └── emergency.py
│       │
│       ├── simulation/
│       │   ├── __init__.py
│       │   └── sumo.py
│       │
│       ├── evaluation/
│       │   ├── __init__.py
│       │   ├── baseline.py
│       │   ├── metrics.py
│       │   └── experiments.py
│       │
│       └── visualization/
│           ├── __init__.py
│           ├── maps.py
│           └── plots.py
│
├── scripts/
│   └── README.md
│
├── notebooks/
│   └── README.md
│
├── tests/
│   ├── __init__.py
│   └── README.md
│
└── outputs/
    ├── maps/
    ├── figures/
    └── tables/
```

You may make small engineering adjustments if necessary, but preserve the separation of responsibilities.

Do not over-engineer the repository.

---

# Authoritative Documents

Place these at the repository root:

```text
CONTEXT.md
PLAN.md
CODEX_SETUP_PROMPT.md
```

Preserve the contents of the supplied `CONTEXT.md` and `PLAN.md`.

Do not rewrite their architecture.

---

# Python Project Setup

Create a modern Python project configuration.

Use:

```text
pyproject.toml
requirements.txt
```

Prefer Python 3.11+ unless the environment already has a deliberate project version that should be preserved.

Provide a normal virtual-environment workflow.

Do not require Docker.

Do not require paid software/services.

---

# Initial Dependencies

Configure only reasonable core dependencies for the early project.

Expected candidates:

```text
osmnx
networkx
geopandas
shapely
pandas
numpy
matplotlib
```

Do not install or make mandatory the later-stage tools unless genuinely required for repository setup.

Do not add heavy machine-learning frameworks.

Do not add SUMO tooling yet.

Do not add satellite-processing dependencies yet.

Do not add live API clients yet.

Those belong to later stages.

---

# Configuration

Create a simple configuration mechanism without hardcoded machine-specific paths.

The project should be able to resolve directories such as:

```text
project root
data/raw
data/processed
outputs
```

Do not put any:

```text
API keys
passwords
tokens
personal absolute paths
```

into tracked files.

Use environment variables only when justified.

---

# README.md

Create a professional README containing:

1. Project title
2. Project objective
3. High-level architecture
4. Repository structure
5. Technology overview
6. Environment setup
7. Virtual-environment commands
8. Dependency installation
9. Test command
10. Staged-development workflow
11. Current status

The README must explicitly state:

```text
Stage 1 has NOT yet been implemented.
```

Do not claim that the Chennai road graph, flood mapping, BPR, Dijkstra, or routing system already works.

---

# Data Directory

Create:

```text
data/raw/
data/processed/
```

Create `data/README.md` explaining:

- raw external data belongs in `data/raw`,
- processed/generated data belongs in `data/processed`,
- large datasets should generally not be committed to Git,
- provenance should be recorded once a dataset is introduced.

Do not download datasets during this task.

---

# Git Setup

Initialize Git if necessary.

Create a suitable `.gitignore` covering at least:

- Python caches
- virtual environments
- pytest cache
- Jupyter checkpoints
- IDE/editor settings
- `.env`
- large downloaded datasets
- generated outputs where appropriate

Do not commit secrets.

Do not commit virtual environments.

Do not commit large external datasets.

---

# Testing Setup

Prepare a minimal testing infrastructure.

`pytest` may be used.

Create the test directory and enough configuration/documentation that a future stage can add tests cleanly.

Do not implement substantive project tests now.

---

# Cursor Compatibility

The resulting repository should be easy to open in Cursor.

When the root folder is opened, the following should be immediately visible:

```text
CONTEXT.md
PLAN.md
CODEX_SETUP_PROMPT.md
README.md
src/
data/
tests/
outputs/
```

Avoid unnecessary IDE-specific configuration.

---

# AI-Agent Friendliness

This project will be developed incrementally using AI coding agents.

Therefore:

- keep modules logically separated,
- use descriptive filenames,
- avoid giant files,
- centralize configuration,
- document assumptions,
- keep paths reproducible,
- use TODOs only when they correspond to future PLAN.md stages,
- make responsibilities of modules obvious.

Future agents should be able to see clearly where to implement:

```text
road data
flood data
rainfall
elevation
hydrology
capacity
BPR
Dijkstra
dynamic routing
rerouting
emergency routing
SUMO
evaluation
visualization
```

---

# STRICTLY DO NOT IMPLEMENT

This is critical.

Do NOT:

- download Chennai road data,
- build the Chennai road graph,
- download flood data,
- spatially intersect flood data with roads,
- implement flood susceptibility,
- implement rainfall integration,
- implement SRTM processing,
- implement drainage/water-body analysis,
- implement satellite flood detection,
- implement capacity calculations,
- implement BPR,
- implement Dijkstra,
- implement threshold rerouting,
- implement hysteresis,
- implement SUMO,
- implement accident scenarios,
- implement emergency routing,
- implement evaluation experiments.

This task ends after repository setup.

---

# Architecture Integrity Rules

The locked project architecture must remain:

```text
DATA
→ road/environment/traffic conditions
→ road condition
→ effective capacity
→ BPR travel-time cost
→ dynamic edge cost
→ routing
→ controlled rerouting
→ evaluation
```

Emergency vehicles use a separate priority-routing rule.

Do not replace the capacity-based flood/incident mechanism with arbitrary additive penalty scores.

Do not turn the project into a pothole-detection project.

Do not add a custom AI/ML model simply because it is possible.

---

# Verification Before Finishing

Before stopping, verify all of the following:

1. `CONTEXT.md` exists.
2. `PLAN.md` exists.
3. `CODEX_SETUP_PROMPT.md` exists.
4. `PLAN.md` still says Stage 1 is `IN PROGRESS`.
5. Later stages remain `PENDING`.
6. No Stage 1 implementation was performed.
7. No datasets were downloaded.
8. The Python project configuration is valid.
9. Core dependencies are specified.
10. The test setup can be discovered.
11. Git is initialized if appropriate.
12. No secrets are present.
13. The project opens cleanly as a normal folder/repository.

---

# Final Report

When finished, report:

### Repository
- exact repository path
- Git status

### Structure
- important directories and files created

### Environment
- detected Python version
- virtual-environment creation command
- activation command for Windows
- activation command for Linux/macOS
- dependency installation command
- test command

### Verification
- configuration check
- dependency/setup check
- test discovery result

### Status

Explicitly state:

```text
Repository setup is complete.
Stage 1 implementation has NOT been started.
```

Do not mark Stage 1 as DONE.

Do not modify the status of future stages.

STOP after setup.
