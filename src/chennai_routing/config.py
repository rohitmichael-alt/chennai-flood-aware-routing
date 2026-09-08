"""Central project path configuration."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    """Repository directories used by the project."""

    root: Path
    raw_data: Path
    processed_data: Path
    outputs: Path
    raw_boundary: Path
    raw_osm: Path
    raw_flood: Path
    raw_rainfall: Path
    raw_elevation: Path
    raw_hydrology: Path
    processed_boundary: Path
    processed_roads: Path
    processed_flood: Path
    processed_rainfall: Path
    processed_elevation: Path
    processed_hydrology: Path
    processed_road_state: Path
    output_maps: Path
    output_tables: Path


def get_project_paths() -> ProjectPaths:
    """Resolve project directories without machine-specific absolute paths."""

    root = Path(__file__).resolve().parents[2]
    return ProjectPaths(
        root=root,
        raw_data=root / "data" / "raw",
        processed_data=root / "data" / "processed",
        outputs=root / "outputs",
        raw_boundary=root / "data" / "raw" / "boundary",
        raw_osm=root / "data" / "raw" / "osm",
        raw_flood=root / "data" / "raw" / "flood",
        raw_rainfall=root / "data" / "raw" / "rainfall",
        raw_elevation=root / "data" / "raw" / "elevation",
        raw_hydrology=root / "data" / "raw" / "hydrology",
        processed_boundary=root / "data" / "processed" / "boundary",
        processed_roads=root / "data" / "processed" / "roads",
        processed_flood=root / "data" / "processed" / "flood",
        processed_rainfall=root / "data" / "processed" / "rainfall",
        processed_elevation=root / "data" / "processed" / "elevation",
        processed_hydrology=root / "data" / "processed" / "hydrology",
        processed_road_state=root / "data" / "processed" / "road_state",
        output_maps=root / "outputs" / "maps",
        output_tables=root / "outputs" / "tables",
    )
