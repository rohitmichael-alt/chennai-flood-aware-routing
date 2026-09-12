from pathlib import Path

from chennai_routing.config import ProjectPaths, get_project_paths


def test_project_paths_resolve_to_repository_directories() -> None:
    paths = get_project_paths()

    assert isinstance(paths, ProjectPaths)
    assert paths.root.exists()
    assert paths.raw_data == paths.root / "data" / "raw"
    assert paths.processed_data == paths.root / "data" / "processed"
    assert paths.outputs == paths.root / "outputs"
    assert paths.raw_boundary == paths.root / "data" / "raw" / "boundary"
    assert paths.raw_osm == paths.root / "data" / "raw" / "osm"
    assert paths.raw_flood == paths.root / "data" / "raw" / "flood"
    assert paths.raw_rainfall == paths.root / "data" / "raw" / "rainfall"
    assert paths.raw_elevation == paths.root / "data" / "raw" / "elevation"
    assert paths.raw_hydrology == paths.root / "data" / "raw" / "hydrology"
    assert paths.processed_boundary == paths.root / "data" / "processed" / "boundary"
    assert paths.processed_roads == paths.root / "data" / "processed" / "roads"
    assert paths.processed_road_state == paths.root / "data" / "processed" / "road_state"
    assert paths.output_maps == paths.root / "outputs" / "maps"


def test_authoritative_documents_exist() -> None:
    root = get_project_paths().root

    assert (root / "CONTEXT.md").is_file()
    assert (root / "PLAN.md").is_file()
    assert (root / "CODEX_SETUP_PROMPT.md").is_file()
    assert (root / "docs" / "AI_MENTOR_PROTOCOL.md").is_file()
    assert (root / "docs" / "MASTER_PROMPT_FOR_EXECUTOR_AI.md").is_file()
    assert (root / "docs" / "PROJECT_RESEARCH_AND_EVIDENCE.md").is_file()
