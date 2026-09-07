"""Stage 3 orchestration for the reproducible Greater Chennai graph."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from chennai_routing.config import get_project_paths
from chennai_routing.data.boundary import (
    BoundaryAudit,
    BoundaryProvenance,
    download_gcc_2022_wards,
    load_and_audit_gcc_2022_wards,
    write_boundary_evidence,
)


@dataclass(frozen=True)
class Stage3BoundaryResult:
    """Paths and checks for the completed Stage 3 boundary substage."""

    raw_kml_path: str
    raw_metadata_path: str
    processed_wards_path: str
    processed_union_path: str
    archived_source_path: str
    evidence_path: str
    provenance: dict[str, object]
    audit: dict[str, object]
    decision: str
    next_gate: str


def _repository_relative(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def run_stage3_boundary() -> Stage3BoundaryResult:
    """Acquire, validate, and preserve the exact Stage 3 study boundary."""

    paths = get_project_paths()
    kml_path, metadata_path, provenance = download_gcc_2022_wards(paths.raw_boundary)
    wards, union, audit = load_and_audit_gcc_2022_wards(
        kml_path,
        repair_invalid=True,
    )
    evidence_path = paths.root / "docs" / "evidence" / "STAGE3_BOUNDARY_RESULTS.json"
    archived_path = (
        paths.root / "docs" / "evidence" / "sources" / "gcc_wards_2022.kml.gz"
    )
    wards_path, union_path, archived_path = write_boundary_evidence(
        wards=wards,
        union=union,
        audit=audit,
        provenance=provenance,
        processed_directory=paths.processed_boundary,
        evidence_path=evidence_path,
        raw_kml_path=kml_path,
        archived_kml_path=archived_path,
        artifact_root=paths.root,
    )
    return Stage3BoundaryResult(
        raw_kml_path=_repository_relative(kml_path, paths.root),
        raw_metadata_path=_repository_relative(metadata_path, paths.root),
        processed_wards_path=_repository_relative(wards_path, paths.root),
        processed_union_path=_repository_relative(union_path, paths.root),
        archived_source_path=_repository_relative(archived_path, paths.root),
        evidence_path=_repository_relative(evidence_path, paths.root),
        provenance=asdict(provenance),
        audit=asdict(audit),
        decision=(
            "PASS WITH DOCUMENTED SOURCE GEOMETRY REPAIR"
            if audit.repaired_geometry_count
            else "PASS"
        ),
        next_gate=(
            "Acquire a dated OSM source, normalize the full road graph, and pass "
            "the Stage 3 topology and missingness audit."
        ),
    )


__all__ = [
    "BoundaryAudit",
    "BoundaryProvenance",
    "Stage3BoundaryResult",
    "run_stage3_boundary",
]
