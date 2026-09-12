"""Historical Chennai flood dataset access for the Stage 1 proof of concept."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import LineString, Point, Polygon


OPENCITY_2015_PACKAGE_API = (
    "https://data.opencity.in/api/3/action/package_show?id=chennai-floods-2015-data"
)
OPENCITY_FLOODING_PACKAGE_API = (
    "https://data.opencity.in/api/3/action/package_show?id=chennai-flooding-data"
)
GCC_2015_HOTSPOTS_RESOURCE_ID = "8e1c5b2d-322c-4dbd-bd64-6da2d1a8681d"
GCC_2015_INUNDATION_ZONE_RESOURCE_ID = "2056abd6-26d7-413b-9dfa-e63cbbf41ee7"
INUNDATION_POINTS_DEPTH_RESOURCE_ID = "ceddf53f-03c0-4866-8ba8-5e84c8007a85"
FLOODING_POINTS_2015_RESOURCE_ID = "80ed2fa7-1150-4f55-8125-682ab55282ac"
USER_AGENT = "chennai-routing-research/0.1 (reproducible academic data acquisition)"
KML_NAMESPACE = {"kml": "http://www.opengis.net/kml/2.2"}


@dataclass(frozen=True)
class FloodDatasetMetadata:
    """Provenance for a downloaded OpenCity flood resource."""

    dataset_name: str
    resource_name: str
    resource_id: str
    source_url: str
    source: str | None
    license_title: str | None
    downloaded_at_utc: str
    data_classification: str = "HISTORICAL"


@dataclass(frozen=True)
class PinnedFloodResource:
    """One OpenCity flood KML that Stage 4 pins by resource ID."""

    package_api: str
    resource_id: str
    filename: str
    evidence_class: str
    geometry_kind: str


PINNED_STAGE4_FLOOD_RESOURCES = (
    PinnedFloodResource(
        package_api=OPENCITY_2015_PACKAGE_API,
        resource_id=GCC_2015_HOTSPOTS_RESOURCE_ID,
        filename="chennai_2015_gcc_area_flood_hotspots.kml",
        evidence_class="HISTORICAL_INVENTORY",
        geometry_kind="point",
    ),
    PinnedFloodResource(
        package_api=OPENCITY_2015_PACKAGE_API,
        resource_id=GCC_2015_INUNDATION_ZONE_RESOURCE_ID,
        filename="chennai_2015_floods_inundation_zone.kml",
        evidence_class="HISTORICAL_INVENTORY",
        geometry_kind="polygon",
    ),
    PinnedFloodResource(
        package_api=OPENCITY_FLOODING_PACKAGE_API,
        resource_id=INUNDATION_POINTS_DEPTH_RESOURCE_ID,
        filename="chennai_inundation_points_with_depth.kml",
        evidence_class="HISTORICAL_INVENTORY",
        geometry_kind="point",
    ),
    PinnedFloodResource(
        package_api=OPENCITY_FLOODING_PACKAGE_API,
        resource_id=FLOODING_POINTS_2015_RESOURCE_ID,
        filename="chennai_flooding_points_2015.kml",
        evidence_class="HISTORICAL_INVENTORY",
        geometry_kind="point",
    ),
)


@dataclass(frozen=True)
class FloodResourceProvenance:
    """Checksummed record for one pinned OpenCity flood resource."""

    package_api: str
    resource_id: str
    resource_name: str
    source_url: str
    license_title: str | None
    retrieved_at_utc: str
    filename: str
    content_sha256: str
    content_bytes: int
    feature_count: int
    evidence_class: str
    geometry_kind: str
    claim_limit: str


def get_opencity_resource_metadata(
    resource_id: str = GCC_2015_HOTSPOTS_RESOURCE_ID,
) -> tuple[FloodDatasetMetadata, str]:
    """Read CKAN metadata and return the selected resource provenance and URL."""

    response = requests.get(OPENCITY_2015_PACKAGE_API, timeout=30)
    response.raise_for_status()
    package = response.json()["result"]

    resources = package.get("resources", [])
    resource = next((item for item in resources if item.get("id") == resource_id), None)
    if resource is None:
        raise ValueError(f"OpenCity resource not found: {resource_id}")

    metadata = FloodDatasetMetadata(
        dataset_name=package.get("title") or package.get("name", ""),
        resource_name=resource.get("name", ""),
        resource_id=resource_id,
        source_url=resource.get("url", ""),
        source=resource.get("source") or package.get("source"),
        license_title=package.get("license_title"),
        downloaded_at_utc=datetime.now(UTC).isoformat(),
    )
    return metadata, metadata.source_url


def download_opencity_flood_kml(
    output_dir: Path,
    resource_id: str = GCC_2015_HOTSPOTS_RESOURCE_ID,
) -> tuple[Path, Path, FloodDatasetMetadata]:
    """Download the public-domain OpenCity 2015 Chennai flood hotspots KML."""

    output_dir.mkdir(parents=True, exist_ok=True)
    metadata, download_url = get_opencity_resource_metadata(resource_id)

    response = requests.get(download_url, timeout=60)
    response.raise_for_status()

    kml_path = output_dir / "chennai_2015_gcc_area_flood_hotspots.kml"
    metadata_path = output_dir / "chennai_2015_gcc_area_flood_hotspots_provenance.json"

    kml_path.write_bytes(response.content)
    metadata_path.write_text(
        json.dumps(metadata.__dict__, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return kml_path, metadata_path, metadata


def parse_kml_points(kml_path: Path) -> gpd.GeoDataFrame:
    """Parse point Placemarks from a KML file into EPSG:4326 GeoDataFrame rows."""

    tree = ET.parse(kml_path)
    root = tree.getroot()
    namespace = {"kml": "http://www.opengis.net/kml/2.2"}

    rows: list[dict[str, object]] = []
    for index, placemark in enumerate(root.findall(".//kml:Placemark", namespace)):
        coord_text = placemark.findtext(".//kml:Point/kml:coordinates", namespaces=namespace)
        if not coord_text:
            continue

        lon_text, lat_text, *_ = coord_text.strip().split(",")
        name = placemark.findtext("kml:name", default=f"flood_hotspot_{index}", namespaces=namespace)
        description = placemark.findtext("kml:description", default="", namespaces=namespace)
        rows.append(
            {
                "flood_id": f"opencity_2015_gcc_hotspot_{index}",
                "name": name,
                "description": description,
                "source": "OpenCity Chennai Floods 2015 Data",
                "data_classification": "HISTORICAL",
                "geometry": Point(float(lon_text), float(lat_text)),
            }
        )

    if not rows:
        raise ValueError(f"No point placemarks found in KML file: {kml_path}")

    return gpd.GeoDataFrame(pd.DataFrame(rows), geometry="geometry", crs="EPSG:4326")


def _parse_kml_coordinate_text(text: str) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for token in text.replace("\n", " ").split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        points.append((float(parts[0]), float(parts[1])))
    return points


def _geometry_from_placemark(placemark: ET.Element) -> object | None:
    point_text = placemark.findtext(".//kml:Point/kml:coordinates", namespaces=KML_NAMESPACE)
    if point_text:
        coords = _parse_kml_coordinate_text(point_text)
        if coords:
            return Point(coords[0])
    line_text = placemark.findtext(".//{http://www.opengis.net/kml/2.2}LineString/{http://www.opengis.net/kml/2.2}coordinates")
    if line_text is None:
        line_text = placemark.findtext(".//kml:LineString/kml:coordinates", namespaces=KML_NAMESPACE)
    if line_text:
        coords = _parse_kml_coordinate_text(line_text)
        if len(coords) >= 2:
            return LineString(coords)
    ring_text = placemark.findtext(
        ".//kml:Polygon/kml:outerBoundaryIs/kml:LinearRing/kml:coordinates",
        namespaces=KML_NAMESPACE,
    )
    if ring_text:
        coords = _parse_kml_coordinate_text(ring_text)
        if len(coords) >= 4:
            return Polygon(coords)
    return None


def parse_kml_features(
    kml_path: Path,
    *,
    source: str,
    evidence_class: str,
    id_prefix: str,
) -> gpd.GeoDataFrame:
    """Parse KML points, lines, and polygons without imputing missing attributes."""

    tree = ET.parse(kml_path)
    root = tree.getroot()
    rows: list[dict[str, object]] = []
    for index, placemark in enumerate(root.findall(".//kml:Placemark", KML_NAMESPACE)):
        geometry = _geometry_from_placemark(placemark)
        if geometry is None:
            continue
        name = placemark.findtext("kml:name", default=f"{id_prefix}_{index}", namespaces=KML_NAMESPACE)
        description = placemark.findtext("kml:description", default="", namespaces=KML_NAMESPACE)
        rows.append(
            {
                "feature_id": f"{id_prefix}_{index}",
                "name": name,
                "description": description,
                "source": source,
                "evidence_class": evidence_class,
                "geometry_type": geometry.geom_type,
                "geometry": geometry,
            }
        )
    if not rows:
        raise ValueError(f"No supported geometries found in KML file: {kml_path}")
    return gpd.GeoDataFrame(pd.DataFrame(rows), geometry="geometry", crs="EPSG:4326")


def download_pinned_flood_resources(
    output_directory: Path,
    *,
    session: requests.Session | None = None,
    retrieved_at_utc: str | None = None,
    timeout_seconds: float = 60.0,
) -> list[tuple[Path, FloodResourceProvenance, gpd.GeoDataFrame]]:
    """Download every pinned Stage 4 flood KML and parse its geometries."""

    output_directory.mkdir(parents=True, exist_ok=True)
    client = session or requests.Session()
    results: list[tuple[Path, FloodResourceProvenance, gpd.GeoDataFrame]] = []
    for spec in PINNED_STAGE4_FLOOD_RESOURCES:
        package_response = client.get(
            spec.package_api,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout_seconds,
        )
        package_response.raise_for_status()
        package = package_response.json()["result"]
        resource = next(
            (item for item in package.get("resources", []) if item.get("id") == spec.resource_id),
            None,
        )
        if resource is None:
            raise ValueError(f"OpenCity flood resource not found: {spec.resource_id}")
        content_response = client.get(
            resource["url"],
            headers={"User-Agent": USER_AGENT},
            timeout=timeout_seconds,
        )
        content_response.raise_for_status()
        content = content_response.content
        kml_path = output_directory / spec.filename
        kml_path.write_bytes(content)
        features = parse_kml_features(
            kml_path,
            source=resource.get("name", spec.filename),
            evidence_class=spec.evidence_class,
            id_prefix=spec.resource_id[:8],
        )
        provenance = FloodResourceProvenance(
            package_api=spec.package_api,
            resource_id=spec.resource_id,
            resource_name=resource.get("name", ""),
            source_url=resource["url"],
            license_title=package.get("license_title"),
            retrieved_at_utc=retrieved_at_utc or datetime.now(UTC).isoformat(),
            filename=spec.filename,
            content_sha256=sha256(content).hexdigest(),
            content_bytes=len(content),
            feature_count=len(features),
            evidence_class=spec.evidence_class,
            geometry_kind=spec.geometry_kind,
            claim_limit=(
                "OpenCity flood KMLs are historical inventories or modelled hazard layers. "
                "They are not current road closures."
            ),
        )
        (output_directory / f"{kml_path.stem}_provenance.json").write_text(
            json.dumps(asdict(provenance), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        results.append((kml_path, provenance, features))
    return results
