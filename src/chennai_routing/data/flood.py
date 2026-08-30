"""Historical Chennai flood dataset access for the Stage 1 proof of concept."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Point


OPENCITY_2015_PACKAGE_API = (
    "https://data.opencity.in/api/3/action/package_show?id=chennai-floods-2015-data"
)
GCC_2015_HOTSPOTS_RESOURCE_ID = "8e1c5b2d-322c-4dbd-bd64-6da2d1a8681d"


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
