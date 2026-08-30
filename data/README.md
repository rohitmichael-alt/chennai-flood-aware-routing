# Data Directory

Use this directory for project data once a stage introduces a dataset.

- `data/raw/` stores unchanged external source data.
- `data/processed/` stores cleaned, normalized, or generated data derived from raw inputs.
- Large datasets should generally not be committed to Git.
- Record provenance when a dataset is introduced, including source, download date, license or access terms, dataset version when available, and processing steps.

Stage 1 downloads the OpenCity Chennai 2015 GCC Area Flood Hotspots KML into `data/raw/flood/` and records provenance beside it.

Stage 1 also writes the OSM-derived graph to `data/processed/roads/`. These are generated artifacts and are ignored by Git.
