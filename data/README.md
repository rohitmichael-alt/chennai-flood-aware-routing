# Data Directory

Use this directory for project data once a stage introduces a dataset.

- `data/raw/` stores unchanged external source data.
- `data/processed/` stores cleaned, normalized, or generated data derived from raw inputs.
- Large datasets should generally not be committed to Git.
- Record provenance when a dataset is introduced, including source, download date, license or access terms, dataset version when available, and processing steps.

Stage 1 downloads the OpenCity Chennai 2015 GCC Area Flood Hotspots KML into `data/raw/flood/` and records provenance beside it.

Stage 1 also writes the OSM-derived graph to `data/processed/roads/`. These are generated artifacts and are ignored by Git.

Stage 3 downloads the pinned OpenCity/GCC 2022 ward KML and provider metadata
to `data/raw/boundary/`, then writes validated ward and union GeoJSON files to
`data/processed/boundary/`. These working copies are ignored. The exact source
is preserved in `docs/evidence/sources/gcc_wards_2022.kml.gz`, and the checksum,
licence, source geometry repairs, and audit are committed in
`docs/evidence/STAGE3_BOUNDARY_RESULTS.json`.
