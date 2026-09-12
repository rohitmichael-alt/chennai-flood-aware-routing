"""No-key Open-Meteo ERA5 rainfall acquisition for Stage 4.

IMERG remains optional and credentialed. Rainfall is not street flood depth.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

USER_AGENT = "chennai-routing-research/0.1 (reproducible academic data acquisition)"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_LICENSE = "CC BY 4.0"
OPEN_METEO_ATTRIBUTION = "Rainfall from Open-Meteo ERA5 reanalysis (https://open-meteo.com/)"
CHENNAI_LATITUDE = 13.0827
CHENNAI_LONGITUDE = 80.2707
EVENT_START_DATE = "2015-11-01"
EVENT_END_DATE = "2015-12-15"
TIMEZONE = "Asia/Kolkata"
RAINFALL_MODEL = "era5"
PRECIPITATION_UNIT = "mm"


@dataclass(frozen=True)
class RainfallProvenance:
    """Provenance for one Open-Meteo ERA5 rainfall extract."""

    source_url: str
    retrieved_at_utc: str
    latitude: float
    longitude: float
    start_date: str
    end_date: str
    timezone: str
    model: str
    variable: str
    unit: str
    license: str
    attribution: str
    evidence_class: str
    claim_limit: str
    hourly_row_count: int
    total_precipitation_mm: float | None
    imerg_status: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def earthdata_imerg_status() -> str:
    """IMERG is optional; this environment does not assume Earthdata credentials."""

    netrc = Path.home() / ".netrc"
    if netrc.is_file() and "urs.earthdata.nasa.gov" in netrc.read_text(encoding="utf-8"):
        return "CREDENTIAL_FILE_PRESENT_BUT_IMERG_DOWNLOAD_NOT_RUN"
    return "UNAVAILABLE_NO_EARTHDATA_CREDENTIALS"


def fetch_open_meteo_era5_precipitation(
    output_directory: Path,
    *,
    session: requests.Session | None = None,
    latitude: float = CHENNAI_LATITUDE,
    longitude: float = CHENNAI_LONGITUDE,
    start_date: str = EVENT_START_DATE,
    end_date: str = EVENT_END_DATE,
    retrieved_at_utc: str | None = None,
    timeout_seconds: float = 60.0,
) -> tuple[Path, Path, RainfallProvenance]:
    """Download hourly ERA5 precipitation for the declared Chennai event window."""

    output_directory.mkdir(parents=True, exist_ok=True)
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "precipitation",
        "models": RAINFALL_MODEL,
        "timezone": TIMEZONE,
    }
    client = session or requests.Session()
    response = client.get(
        OPEN_METEO_ARCHIVE_URL,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    values = hourly.get("precipitation") or []
    if len(times) != len(values) or not times:
        raise ValueError("Open-Meteo rainfall payload did not contain matching hourly series.")

    raw_path = output_directory / "open_meteo_era5_chennai_2015.json"
    table_path = output_directory / "open_meteo_era5_chennai_2015.csv"
    raw_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    frame = pd.DataFrame(
        {
            "time_asia_kolkata": times,
            "precipitation_mm": values,
            "evidence_class": "MODELLED",
            "product": RAINFALL_MODEL,
            "claim_limit": "Retrospective reanalysis; not street flood depth.",
        }
    )
    frame.to_csv(table_path, index=False)
    numeric = [float(value) for value in values if value is not None]
    provenance = RainfallProvenance(
        source_url=response.url if hasattr(response, "url") else OPEN_METEO_ARCHIVE_URL,
        retrieved_at_utc=retrieved_at_utc or _utc_now(),
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
        timezone=TIMEZONE,
        model=RAINFALL_MODEL,
        variable="precipitation",
        unit=PRECIPITATION_UNIT,
        license=OPEN_METEO_LICENSE,
        attribution=OPEN_METEO_ATTRIBUTION,
        evidence_class="MODELLED",
        claim_limit=(
            "Open-Meteo ERA5 precipitation is retrospective reanalysis at a point. "
            "It is not contemporaneous sensing and does not prove street flooding."
        ),
        hourly_row_count=len(times),
        total_precipitation_mm=round(sum(numeric), 3) if numeric else None,
        imerg_status=earthdata_imerg_status(),
    )
    (output_directory / "open_meteo_era5_chennai_2015_provenance.json").write_text(
        json.dumps(asdict(provenance), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return raw_path, table_path, provenance
