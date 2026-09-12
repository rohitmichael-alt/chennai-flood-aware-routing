"""Dated OpenStreetMap snapshot acquisition and GCC clipping for Stage 3."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import networkx as nx
import requests
import shapely

USER_AGENT = "chennai-routing-research/0.1 (reproducible academic data acquisition)"
GEOFABRIK_INDIA_PBF_URL = "https://download.geofabrik.de/asia/india-260901.osm.pbf"
GEOFABRIK_INDIA_MD5_URL = "https://download.geofabrik.de/asia/india-260901.osm.pbf.md5"
GEOFABRIK_INDIA_PBF_FILENAME = "india-260901.osm.pbf"
OSM_LICENSE = "ODbL 1.0"
OSM_LICENSE_URL = "https://www.openstreetmap.org/copyright"
OSM_ATTRIBUTION = "Map data © OpenStreetMap contributors"
NETWORK_TYPE = "driving"
DOWNLOAD_CONNECT_TIMEOUT_SECONDS = 30.0
DOWNLOAD_READ_TIMEOUT_SECONDS = 300.0


@dataclass(frozen=True)
class OsmSnapshotProvenance:
    """Provider and integrity record for one dated OSM extract."""

    source_url: str
    checksum_url: str
    filename: str
    retrieved_at_utc: str
    last_modified_header: str
    etag_header: str
    declared_content_length: int | None
    downloaded_bytes: int
    provider_md5: str
    computed_md5: str
    reused_existing_pbf: bool
    osm_license: str
    osm_license_url: str
    osm_attribution: str
    clip_boundary_resource_id: str
    clipped_pbf_bytes: int
    clipped_pbf_sha256: str
    osmium_version: str
    extract_strategy: str
    network_type: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_geofabrik_md5(text: str) -> str:
    """Parse `md5  filename` lines from a Geofabrik checksum file."""

    line = text.strip().splitlines()[0] if text.strip() else ""
    token = line.split()[0] if line else ""
    if len(token) != 32 or any(ch not in "0123456789abcdef" for ch in token.lower()):
        raise ValueError("Geofabrik checksum file did not contain a 32-character MD5.")
    return token.lower()


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(
    url: str,
    destination: Path,
    *,
    session: requests.Session | None = None,
    timeout_seconds: float | tuple[float, float] = (
        DOWNLOAD_CONNECT_TIMEOUT_SECONDS,
        DOWNLOAD_READ_TIMEOUT_SECONDS,
    ),
) -> requests.Response:
    """Stream a file to a temporary path, then replace the destination."""

    connect_timeout, read_timeout = (
        (timeout_seconds, timeout_seconds)
        if isinstance(timeout_seconds, (int, float))
        else timeout_seconds
    )
    if connect_timeout <= 0 or read_timeout <= 0:
        raise ValueError("timeout_seconds must be positive.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    client = session or requests.Session()
    partial = destination.with_name(destination.name + ".partial")
    with client.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=(connect_timeout, read_timeout),
        stream=True,
    ) as response:
        response.raise_for_status()
        with partial.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
        partial.replace(destination)
        return response


def require_osmium() -> str:
    binary = shutil.which("osmium")
    if binary is None:
        raise RuntimeError("osmium-tool is required to clip the dated OSM extract.")
    # Conda's Windows build dispatches on argv[0] and rejects the uppercase
    # ``osmium.EXE`` spelling returned by ``shutil.which`` on this platform.
    # Normalising only the basename preserves the resolved executable.
    if Path(binary).name == "osmium.EXE":
        binary = str(Path(binary).with_name("osmium.exe"))
    completed = subprocess.run(
        [binary, "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    first_line = (completed.stdout or completed.stderr).splitlines()[0]
    return first_line.strip()


def write_clip_geojson(union: gpd.GeoDataFrame, path: Path) -> Path:
    """Write an RFC 7946 GeoJSON polygon that osmium extract can read."""

    if len(union) != 1:
        raise ValueError("Clip geometry must be a single union feature.")
    path.parent.mkdir(parents=True, exist_ok=True)
    geometry = shapely.force_2d(union.to_crs("EPSG:4326").geometry.iloc[0])
    if geometry is None or geometry.is_empty:
        raise ValueError("Clip geometry is empty.")
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": shapely.geometry.mapping(geometry),
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def clip_pbf_to_polygon(
    source_pbf: Path,
    polygon_geojson: Path,
    output_pbf: Path,
    *,
    strategy: str = "smart",
) -> str:
    """Clip a PBF with osmium extract. Returns the osmium version string."""

    version = require_osmium()
    output_pbf.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            "osmium",
            "extract",
            "--strategy",
            strategy,
            "--polygon",
            str(polygon_geojson),
            "--overwrite",
            "--output",
            str(output_pbf),
            str(source_pbf),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"osmium extract failed: {detail}")
    if not output_pbf.is_file() or output_pbf.stat().st_size == 0:
        raise RuntimeError("osmium extract produced an empty PBF.")
    return version


def build_driving_graph_from_pbf(clipped_pbf: Path) -> nx.MultiDiGraph:
    """Parse a local PBF driving network without imputing missing speeds."""

    from pyrosm import OSM

    osm = OSM(str(clipped_pbf))
    extra_attributes = [
        "access",
        "bridge",
        "tunnel",
        "layer",
        "lanes",
        "maxspeed",
        "oneway",
        "name",
        "junction",
        "service",
    ]
    nodes, edges = osm.get_network(
        network_type=NETWORK_TYPE,
        nodes=True,
        extra_attributes=extra_attributes,
    )
    if nodes is None or edges is None or len(edges) == 0:
        raise ValueError("Clipped OSM extract contains no driving-network edges.")
    graph = osm.to_graph(nodes, edges, graph_type="networkx", network_type=NETWORK_TYPE)
    if not isinstance(graph, nx.MultiDiGraph):
        graph = nx.MultiDiGraph(graph)
    graph.graph["crs"] = "EPSG:4326"
    graph.graph["stage3_osm_source"] = str(clipped_pbf)
    graph.graph["stage3_network_type"] = NETWORK_TYPE
    graph.graph["stage3_speed_policy"] = (
        "Only unambiguous explicit OSM maxspeed values are parsed; missing values stay unavailable."
    )
    return graph


def _timeout_pair(
    timeout_seconds: float | tuple[float, float],
) -> tuple[float, float]:
    if isinstance(timeout_seconds, (int, float)):
        return (float(timeout_seconds), float(timeout_seconds))
    return timeout_seconds


def _header_record(headers: Any) -> tuple[str, str, int | None]:
    length_header = headers.get("Content-Length") if headers else None
    declared = int(length_header) if length_header else None
    last_modified = headers.get("Last-Modified", "") if headers else ""
    etag = headers.get("ETag", "") if headers else ""
    return last_modified, etag, declared


def acquire_dated_india_pbf(
    output_directory: Path,
    *,
    session: requests.Session | None = None,
    timeout_seconds: float | tuple[float, float] = (
        DOWNLOAD_CONNECT_TIMEOUT_SECONDS,
        DOWNLOAD_READ_TIMEOUT_SECONDS,
    ),
    retrieved_at_utc: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Download the pinned Geofabrik India PBF and verify the provider MD5."""

    output_directory.mkdir(parents=True, exist_ok=True)
    client = session or requests.Session()
    timeout = _timeout_pair(timeout_seconds)
    checksum_response = client.get(
        GEOFABRIK_INDIA_MD5_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
    checksum_response.raise_for_status()
    provider_md5 = parse_geofabrik_md5(checksum_response.text)
    pbf_path = output_directory / GEOFABRIK_INDIA_PBF_FILENAME

    reused = False
    last_modified = ""
    etag = ""
    declared_content_length: int | None = None
    if pbf_path.is_file() and md5_file(pbf_path) == provider_md5:
        reused = True
        try:
            head = client.head(
                GEOFABRIK_INDIA_PBF_URL,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
                allow_redirects=True,
            )
            head.raise_for_status()
            last_modified, etag, declared_content_length = _header_record(head.headers)
        except requests.RequestException:
            last_modified, etag, declared_content_length = "", "", None
    else:
        response = download_file(
            GEOFABRIK_INDIA_PBF_URL,
            pbf_path,
            session=client,
            timeout_seconds=timeout,
        )
        last_modified, etag, declared_content_length = _header_record(response.headers)

    computed = md5_file(pbf_path)
    if computed != provider_md5:
        raise ValueError(
            f"Downloaded OSM PBF MD5 {computed} does not match provider MD5 {provider_md5}."
        )
    record = {
        "source_url": GEOFABRIK_INDIA_PBF_URL,
        "checksum_url": GEOFABRIK_INDIA_MD5_URL,
        "filename": GEOFABRIK_INDIA_PBF_FILENAME,
        "retrieved_at_utc": retrieved_at_utc or _utc_now(),
        "last_modified_header": last_modified,
        "etag_header": etag,
        "declared_content_length": declared_content_length,
        "downloaded_bytes": pbf_path.stat().st_size,
        "provider_md5": provider_md5,
        "computed_md5": computed,
        "reused_existing_pbf": reused,
        "osm_license": OSM_LICENSE,
        "osm_license_url": OSM_LICENSE_URL,
        "osm_attribution": OSM_ATTRIBUTION,
    }
    return pbf_path, record
