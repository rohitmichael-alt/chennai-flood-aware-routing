"""Coarse Copernicus-DEM elevation context via the Open-Meteo elevation API.

This is terrain context, not street flood depth. Official SRTM/NASADEM remains
credentialed and is recorded as unavailable when Earthdata is absent.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Point

USER_AGENT = "chennai-routing-research/0.1 (reproducible academic data acquisition)"
OPEN_METEO_ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"
PRODUCT = "Open-Meteo elevation (Copernicus DEM GLO-90)"
VERTICAL_DATUM = "EGM2008"
RESOLUTION_NOTE = "Approximately 90 m DEM sampled at declared grid points"
LICENSE = "CC BY 4.0"


@dataclass(frozen=True)
class ElevationProvenance:
    """Provenance for the coarse Stage 4 elevation sample."""

    source_url: str
    retrieved_at_utc: str
    product: str
    vertical_datum: str
    resolution_note: str
    license: str
    evidence_class: str
    claim_limit: str
    grid_rows: int
    grid_cols: int
    point_count: int
    srtm_status: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_sample_grid(
    bounds_wgs84: tuple[float, float, float, float],
    *,
    rows: int = 8,
    cols: int = 8,
) -> list[tuple[float, float]]:
    """Build a regular lon/lat sample grid over the study bounds."""

    if rows < 2 or cols < 2:
        raise ValueError("Elevation sample grid requires at least a 2x2 lattice.")
    west, south, east, north = bounds_wgs84
    if east <= west or north <= south:
        raise ValueError("Elevation bounds must have positive width and height.")
    points: list[tuple[float, float]] = []
    for row in range(rows):
        lat = south + (north - south) * row / (rows - 1)
        for col in range(cols):
            lon = west + (east - west) * col / (cols - 1)
            points.append((lon, lat))
    return points


def fetch_open_meteo_elevation_grid(
    output_directory: Path,
    bounds_wgs84: tuple[float, float, float, float],
    *,
    session: requests.Session | None = None,
    rows: int = 8,
    cols: int = 8,
    retrieved_at_utc: str | None = None,
    timeout_seconds: float = 60.0,
) -> tuple[Path, ElevationProvenance]:
    """Sample Open-Meteo elevation at a coarse grid. This is not inundation."""

    output_directory.mkdir(parents=True, exist_ok=True)
    samples = build_sample_grid(bounds_wgs84, rows=rows, cols=cols)
    lats = ",".join(f"{lat:.6f}" for _, lat in samples)
    lons = ",".join(f"{lon:.6f}" for lon, _ in samples)
    client = session or requests.Session()
    response = client.get(
        OPEN_METEO_ELEVATION_URL,
        params={"latitude": lats, "longitude": lons},
        headers={"User-Agent": USER_AGENT},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    elevations = payload.get("elevation")
    if not isinstance(elevations, list) or len(elevations) != len(samples):
        raise ValueError("Open-Meteo elevation payload did not match the requested grid.")

    frame = gpd.GeoDataFrame(
        {
            "longitude": [lon for lon, _ in samples],
            "latitude": [lat for _, lat in samples],
            "elevation_m": elevations,
            "evidence_class": "PROXY",
            "product": PRODUCT,
            "vertical_datum": VERTICAL_DATUM,
        },
        geometry=[Point(lon, lat) for lon, lat in samples],
        crs="EPSG:4326",
    )
    geojson_path = output_directory / "open_meteo_elevation_gcc_grid.geojson"
    csv_path = output_directory / "open_meteo_elevation_gcc_grid.csv"
    frame.to_file(geojson_path, driver="GeoJSON")
    pd.DataFrame(frame.drop(columns="geometry")).to_csv(csv_path, index=False)
    raw_path = output_directory / "open_meteo_elevation_gcc_grid_raw.json"
    raw_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    provenance = ElevationProvenance(
        source_url=OPEN_METEO_ELEVATION_URL,
        retrieved_at_utc=retrieved_at_utc or _utc_now(),
        product=PRODUCT,
        vertical_datum=VERTICAL_DATUM,
        resolution_note=RESOLUTION_NOTE,
        license=LICENSE,
        evidence_class="PROXY",
        claim_limit=(
            "Coarse DEM samples are susceptibility/terrain context only. "
            "They are not observed street flood depth or road closures. "
            "Official SRTMGL1/NASADEM was not downloaded because Earthdata "
            "credentials are not assumed."
        ),
        grid_rows=rows,
        grid_cols=cols,
        point_count=len(samples),
        srtm_status="UNAVAILABLE_NO_EARTHDATA_CREDENTIALS",
    )
    (output_directory / "open_meteo_elevation_gcc_grid_provenance.json").write_text(
        json.dumps(asdict(provenance), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return geojson_path, provenance
