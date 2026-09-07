"""Authentic Greater Chennai Corporation study-boundary acquisition."""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import requests
from shapely.validation import explain_validity

GCC_WARD_PACKAGE_ID = "gcc-ward-information"
GCC_WARD_PACKAGE_API = (
    "https://data.opencity.in/api/3/action/package_show?id=gcc-ward-information"
)
GCC_2022_WARD_RESOURCE_ID = "e90176d4-319a-45bd-918e-ecce4f048c4d"
EXPECTED_GCC_WARD_COUNT = 200
USER_AGENT = "chennai-routing-research/0.1 (reproducible academic data acquisition)"


@dataclass(frozen=True)
class BoundaryProvenance:
    """Provider metadata and local integrity information for a boundary file."""

    dataset_id: str
    dataset_title: str
    provider_organization: str
    package_api_url: str
    package_metadata_modified: str
    resource_id: str
    resource_name: str
    resource_url: str
    resource_format: str
    resource_last_modified: str
    resource_source: str
    resource_license: str
    retrieved_at_utc: str
    content_sha256: str
    content_bytes: int


@dataclass(frozen=True)
class BoundaryRepairRecord:
    """One deterministic validity repair applied to a provider geometry."""

    feature_index: str
    feature_name: str
    source_geometry_type: str
    source_validity_error: str
    repaired_geometry_type: str
    source_area_square_metres: float
    repaired_area_square_metres: float
    absolute_area_change_square_metres: float


@dataclass(frozen=True)
class BoundaryAudit:
    """Geometry checks that define the Stage 3 study boundary."""

    feature_count: int
    expected_feature_count: int
    crs: str
    empty_geometry_count: int
    source_invalid_geometry_count: int
    repaired_geometry_count: int
    post_repair_invalid_geometry_count: int
    non_polygon_geometry_count: int
    duplicate_name_count: int | None
    area_measurement_crs: str
    total_absolute_repair_area_change_square_metres: float
    maximum_absolute_repair_area_change_square_metres: float
    repair_records: tuple[BoundaryRepairRecord, ...]
    union_geometry_type: str
    union_is_valid: bool
    bounds_wgs84: tuple[float, float, float, float]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_json(
    session: requests.Session,
    url: str,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    response = session.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("success") is not True or not isinstance(payload.get("result"), dict):
        raise ValueError("OpenCity CKAN package response is not a successful dataset record.")
    return payload


def _select_2022_resource(package_payload: dict[str, Any]) -> dict[str, Any]:
    resources = package_payload["result"].get("resources")
    if not isinstance(resources, list):
        raise ValueError("OpenCity CKAN package record has no resource list.")
    matches = [
        item
        for item in resources
        if isinstance(item, dict) and item.get("id") == GCC_2022_WARD_RESOURCE_ID
    ]
    if len(matches) != 1:
        raise ValueError(
            "Expected exactly one GCC 2022 ward resource with ID "
            f"{GCC_2022_WARD_RESOURCE_ID}; found {len(matches)}."
        )
    resource = matches[0]
    if str(resource.get("format", "")).upper() != "KML":
        raise ValueError("The pinned GCC 2022 ward resource is not declared as KML.")
    if resource.get("state") != "active":
        raise ValueError("The pinned GCC 2022 ward resource is not active.")
    return resource


def download_gcc_2022_wards(
    output_directory: Path,
    *,
    session: requests.Session | None = None,
    timeout_seconds: float = 60.0,
    retrieved_at_utc: str | None = None,
) -> tuple[Path, Path, BoundaryProvenance]:
    """Download the pinned OpenCity/GCC 2022 ward KML and record provenance."""

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive.")
    output_directory.mkdir(parents=True, exist_ok=True)
    client = session or requests.Session()
    package_payload = _get_json(client, GCC_WARD_PACKAGE_API, timeout_seconds=timeout_seconds)
    package = package_payload["result"]
    resource = _select_2022_resource(package_payload)
    resource_url = str(resource.get("url", ""))
    if not resource_url.startswith("https://"):
        raise ValueError("The pinned GCC 2022 ward resource must use HTTPS.")

    response = client.get(
        resource_url,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    content = response.content
    if not content:
        raise ValueError("Downloaded GCC 2022 ward KML is empty.")

    organization = package.get("organization")
    provider = organization.get("title", "") if isinstance(organization, dict) else ""
    provenance = BoundaryProvenance(
        dataset_id=str(package.get("name", "")),
        dataset_title=str(package.get("title", "")),
        provider_organization=str(provider),
        package_api_url=GCC_WARD_PACKAGE_API,
        package_metadata_modified=str(package.get("metadata_modified", "")),
        resource_id=GCC_2022_WARD_RESOURCE_ID,
        resource_name=str(resource.get("name", "")),
        resource_url=resource_url,
        resource_format=str(resource.get("format", "")),
        resource_last_modified=str(resource.get("last_modified", "")),
        resource_source=str(resource.get("source", "")),
        resource_license=str(resource.get("license_id", "")),
        retrieved_at_utc=retrieved_at_utc or _utc_now(),
        content_sha256=hashlib.sha256(content).hexdigest(),
        content_bytes=len(content),
    )

    kml_path = output_directory / "gcc_wards_2022.kml"
    metadata_path = output_directory / "gcc_wards_2022_provenance.json"
    kml_path.write_bytes(content)
    metadata_path.write_text(
        json.dumps(
            {
                "provenance": asdict(provenance),
                "provider_package_record": package_payload,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return kml_path, metadata_path, provenance


def load_and_audit_gcc_2022_wards(
    kml_path: Path,
    *,
    expected_feature_count: int = EXPECTED_GCC_WARD_COUNT,
    repair_invalid: bool = False,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, BoundaryAudit]:
    """Load ward polygons, enforce source checks, and return their union."""

    if expected_feature_count <= 0:
        raise ValueError("expected_feature_count must be positive.")
    wards = gpd.read_file(kml_path)
    if wards.crs is None:
        raise ValueError("GCC ward KML has no CRS.")
    wards = wards.to_crs("EPSG:4326")

    empty_count = int(wards.geometry.is_empty.sum() + wards.geometry.isna().sum())
    if len(wards) != expected_feature_count:
        raise ValueError(
            f"Expected {expected_feature_count} GCC ward features; found {len(wards)}."
        )
    if empty_count:
        raise ValueError(f"GCC ward KML contains {empty_count} empty geometries.")

    name_column = next(
        (column for column in ("Name", "name", "WARD_NO", "ward_no") if column in wards),
        None,
    )
    source_invalid_mask = ~wards.geometry.is_valid
    source_invalid_count = int(source_invalid_mask.sum())
    if source_invalid_count and not repair_invalid:
        raise ValueError(
            f"GCC ward KML contains {source_invalid_count} invalid geometries."
        )

    area_crs = wards.estimate_utm_crs()
    if area_crs is None:
        raise ValueError("Could not determine a projected CRS for boundary repair audit.")
    source_projected = wards.to_crs(area_crs)
    source_areas = source_projected.geometry.area
    validity_errors = {
        index: explain_validity(geometry)
        for index, geometry in wards.loc[source_invalid_mask].geometry.items()
    }
    source_geometry_types = {
        index: geometry.geom_type
        for index, geometry in wards.loc[source_invalid_mask].geometry.items()
    }

    if source_invalid_count:
        wards = wards.copy()
        wards.loc[source_invalid_mask, "geometry"] = (
            wards.loc[source_invalid_mask].geometry.make_valid()
        )

    post_repair_invalid_count = int((~wards.geometry.is_valid).sum())
    non_polygon_count = int(
        (~wards.geometry.geom_type.isin(["Polygon", "MultiPolygon"])).sum()
    )
    if post_repair_invalid_count:
        raise ValueError(
            "Deterministic make_valid repair left "
            f"{post_repair_invalid_count} invalid geometries."
        )
    if non_polygon_count:
        raise ValueError(
            "Boundary processing produced "
            f"{non_polygon_count} non-polygon geometries."
        )

    repaired_projected = wards.to_crs(area_crs)
    repaired_areas = repaired_projected.geometry.area
    repair_records = tuple(
        BoundaryRepairRecord(
            feature_index=str(index),
            feature_name=(
                str(wards.at[index, name_column]).strip() if name_column else ""
            ),
            source_geometry_type=source_geometry_types[index],
            source_validity_error=validity_errors[index],
            repaired_geometry_type=wards.at[index, "geometry"].geom_type,
            source_area_square_metres=float(source_areas.at[index]),
            repaired_area_square_metres=float(repaired_areas.at[index]),
            absolute_area_change_square_metres=float(
                abs(repaired_areas.at[index] - source_areas.at[index])
            ),
        )
        for index in wards.index[source_invalid_mask]
    )
    duplicate_name_count = (
        int(wards[name_column].astype(str).str.strip().duplicated().sum())
        if name_column
        else None
    )
    union_geometry = wards.geometry.union_all()
    union = gpd.GeoDataFrame(
        {"boundary_source": [GCC_2022_WARD_RESOURCE_ID]},
        geometry=[union_geometry],
        crs=wards.crs,
    )
    bounds = tuple(float(value) for value in union.total_bounds)
    audit = BoundaryAudit(
        feature_count=len(wards),
        expected_feature_count=expected_feature_count,
        crs=str(wards.crs),
        empty_geometry_count=empty_count,
        source_invalid_geometry_count=source_invalid_count,
        repaired_geometry_count=len(repair_records),
        post_repair_invalid_geometry_count=post_repair_invalid_count,
        non_polygon_geometry_count=non_polygon_count,
        duplicate_name_count=duplicate_name_count,
        area_measurement_crs=str(area_crs),
        total_absolute_repair_area_change_square_metres=sum(
            record.absolute_area_change_square_metres for record in repair_records
        ),
        maximum_absolute_repair_area_change_square_metres=max(
            (
                record.absolute_area_change_square_metres
                for record in repair_records
            ),
            default=0.0,
        ),
        repair_records=repair_records,
        union_geometry_type=union_geometry.geom_type,
        union_is_valid=bool(union_geometry.is_valid),
        bounds_wgs84=(bounds[0], bounds[1], bounds[2], bounds[3]),
    )
    if not audit.union_is_valid:
        raise ValueError("Union of GCC ward polygons is invalid.")
    return wards, union, audit


def write_boundary_evidence(
    *,
    wards: gpd.GeoDataFrame,
    union: gpd.GeoDataFrame,
    audit: BoundaryAudit,
    provenance: BoundaryProvenance,
    processed_directory: Path,
    evidence_path: Path,
    raw_kml_path: Path,
    archived_kml_path: Path | None = None,
    artifact_root: Path | None = None,
) -> tuple[Path, Path, Path]:
    """Write processed geometry, a compact manifest, and deterministic source archive."""

    processed_directory.mkdir(parents=True, exist_ok=True)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    wards_path = processed_directory / "gcc_wards_2022.geojson"
    union_path = processed_directory / "gcc_boundary_2022.geojson"
    wards.to_file(wards_path, driver="GeoJSON")
    union.to_file(union_path, driver="GeoJSON")

    if archived_kml_path is None:
        archived_kml_path = evidence_path.parent / "sources" / "gcc_wards_2022.kml.gz"
    archived_kml_path.parent.mkdir(parents=True, exist_ok=True)
    with (
        raw_kml_path.open("rb") as source,
        archived_kml_path.open("wb") as destination,
        gzip.GzipFile(
            filename="gcc_wards_2022.kml",
            mode="wb",
            fileobj=destination,
            mtime=0,
        ) as compressed,
    ):
        while chunk := source.read(1024 * 1024):
            compressed.write(chunk)

    def manifest_path(path: Path) -> str:
        if artifact_root is None:
            return str(path)
        return str(path.resolve().relative_to(artifact_root.resolve()))

    evidence_path.write_text(
        json.dumps(
            {
                "stage": 3,
                "component": "study_boundary",
                "decision": (
                    "PASS WITH DOCUMENTED SOURCE GEOMETRY REPAIR"
                    if audit.repaired_geometry_count
                    else "PASS"
                ),
                "provenance": asdict(provenance),
                "audit": asdict(audit),
                "artifacts": {
                    "archived_source": manifest_path(archived_kml_path),
                    "processed_wards": manifest_path(wards_path),
                    "processed_union": manifest_path(union_path),
                },
                "claim_limit": (
                    "This validates the 2022 GCC study boundary only; it does not "
                    "complete the dated OSM road-graph stage."
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return wards_path, union_path, archived_kml_path
