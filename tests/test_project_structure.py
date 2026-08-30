from pathlib import Path

from chennai_routing.config import ProjectPaths, get_project_paths


def test_project_paths_resolve_to_repository_directories() -> None:
    paths = get_project_paths()

    assert isinstance(paths, ProjectPaths)
    assert paths.root.exists()
    assert paths.raw_data == paths.root / "data" / "raw"
    assert paths.processed_data == paths.root / "data" / "processed"
    assert paths.outputs == paths.root / "outputs"
    assert paths.raw_flood == paths.root / "data" / "raw" / "flood"
    assert paths.processed_roads == paths.root / "data" / "processed" / "roads"
    assert paths.output_maps == paths.root / "outputs" / "maps"


def test_authoritative_documents_exist() -> None:
    root = get_project_paths().root

    assert (root / "CONTEXT.md").is_file()
    assert (root / "PLAN.md").is_file()
    assert (root / "CODEX_SETUP_PROMPT.md").is_file()
