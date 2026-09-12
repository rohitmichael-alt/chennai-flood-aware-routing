"""OpenCity storm-water drain inventory for Stage 4 hydrology context.

Drain maps do not prove capacity, maintenance, or current flooding.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import requests

from chennai_routing.data.flood import parse_kml_features

USER_AGENT = "chennai-routing-research/0.1 (reproducible academic data acquisition)"
SWD_PACKAGE_API = (
    "https://data.opencity.in/api/3/action/package_show?id=chennai-stormwater-drain-swd-maps"
)
SWD_2023_RESOURCE_ID = "107ac467-2381-4718-9632-645560bc8360"


@dataclass(frozen=True)
class HydrologyProvenance:
    """Provenance for the 2023 GCC storm-water drain KML."""

    package_api: str
    resource_id: str
    resource_name: str
    source_url: str
    license_title: str | None
    retrieved_at_utc: str
    content_sha256: str
    content_bytes: int
    feature_count: int
    evidence_class: str
    claim_limit: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def download_swd_2023_kml(
    output_directory: Path,
    *,
    session: requests.Session | None = None,
    retrieved_at_utc: str | None = None,
    timeout_seconds: float = 60.0,
) -> tuple[Path, HydrologyProvenance, gpd.GeoDataFrame]:
    """Download the pinned 2023 SWD KML without treating it as flood depth."""

    from hashlib import sha256

    output_directory.mkdir(parents=True, exist_ok=True)
    client = session or requests.Session()
    package_response = client.get(
        SWD_PACKAGE_API,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout_seconds,
    )
    package_response.raise_for_status()
    package = package_response.json()["result"]
    resource = next(
        (item for item in package.get("resources", []) if item.get("id") == SWD_2023_RESOURCE_ID),
        None,
    )
    if resource is None:
        raise ValueError(f"OpenCity SWD resource not found: {SWD_2023_RESOURCE_ID}")
    download_url = resource["url"]
    content_response = client.get(
        download_url,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout_seconds,
    )
    content_response.raise_for_status()
    content = content_response.content
    kml_path = output_directory / "chennai_swd_map_2023.kml"
    kml_path.write_bytes(content)
    features = parse_kml_features(
        kml_path,
        source="OpenCity Chennai Stormwater Drain Map 2023",
        evidence_class="HISTORICAL_INVENTORY",
        id_prefix="opencity_swd_2023",
    )
    provenance = HydrologyProvenance(
        package_api=SWD_PACKAGE_API,
        resource_id=SWD_2023_RESOURCE_ID,
        resource_name=resource.get("name", ""),
        source_url=download_url,
        license_title=package.get("license_title"),
        retrieved_at_utc=retrieved_at_utc or _utc_now(),
        content_sha256=sha256(content).hexdigest(),
        content_bytes=len(content),
        feature_count=len(features),
        evidence_class="HISTORICAL_INVENTORY",
        claim_limit=(
            "The 2023 SWD map is an inventory of mapped drains. It does not prove "
            "conveyance capacity, maintenance state, or street flooding."
        ),
    )
    (output_directory / "chennai_swd_map_2023_provenance.json").write_text(
        json.dumps(asdict(provenance), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return kml_path, provenance, features
