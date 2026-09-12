"""Integer travel-time quantization and overflow bounds for CCH.

Stage 3 leaves missing OSM maxspeed unresolved. A complete CCH metric still
needs a weight on every arc, so missing speeds are filled with a labelled
SCENARIO default. That default is not an observed Chennai free-flow speed.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, ceil, cos, isfinite, radians, sin, sqrt

ROUTINGKIT_INFINITY = 2**31 - 1
QUANTIZATION_UNIT = "millisecond"
SECONDS_TO_MS = 1000
SCENARIO_DEFAULT_SPEED_KPH = 30.0
GEOGRAPHIC_DETOUR_FACTOR = 4.0
MEAN_EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True)
class QuantizationPolicy:
    """Declared conversion from travel time in seconds to integer CCH weights."""

    unit: str = QUANTIZATION_UNIT
    scale: int = SECONDS_TO_MS
    rounding: str = "round"
    scenario_default_speed_kph: float = SCENARIO_DEFAULT_SPEED_KPH
    geographic_detour_factor: float = GEOGRAPHIC_DETOUR_FACTOR

    @property
    def per_arc_error_bound_ms(self) -> float:
        if self.rounding != "round":
            raise ValueError("Only round-to-nearest quantization is implemented.")
        return 0.5


def travel_time_seconds(length_m: float, speed_kph: float) -> float:
    """Return free-flow time in seconds from metres and kilometres per hour."""

    if length_m <= 0 or speed_kph <= 0:
        raise ValueError("Length and speed must be positive.")
    return length_m / (speed_kph / 3.6)


def quantize_seconds(seconds: float, policy: QuantizationPolicy | None = None) -> int:
    """Round a non-negative duration to integer milliseconds."""

    chosen = policy or QuantizationPolicy()
    if not isfinite(seconds) or seconds < 0:
        raise ValueError("Travel time must be finite and non-negative.")
    if chosen.rounding != "round":
        raise ValueError("Only round-to-nearest quantization is implemented.")
    quantized = int(round(seconds * chosen.scale))
    if quantized < 0:
        raise ValueError("Quantized travel time must be non-negative.")
    return quantized


def quantize_travel_time_ms(
    length_m: float,
    speed_kph: float,
    policy: QuantizationPolicy | None = None,
) -> int:
    """Quantize one arc travel time, keeping a minimum of 1 ms for positive length."""

    chosen = policy or QuantizationPolicy()
    quantized = quantize_seconds(travel_time_seconds(length_m, speed_kph), chosen)
    return max(1, quantized)


def path_quantization_error_bound_ms(
    arc_count: int,
    policy: QuantizationPolicy | None = None,
) -> float:
    """Worst-case additive rounding error for a path of ``arc_count`` arcs."""

    if arc_count < 0:
        raise ValueError("arc_count must be non-negative.")
    chosen = policy or QuantizationPolicy()
    return arc_count * chosen.per_arc_error_bound_ms


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in metres on a spherical Earth."""

    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lon2 - lon1)
    chord = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return 2 * MEAN_EARTH_RADIUS_M * atan2(sqrt(chord), sqrt(max(0.0, 1.0 - chord)))


def bbox_diameter_m(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> float:
    """Return the longer geodesic diagonal of a WGS84 bounding box."""

    south_west_north_east = haversine_m(min_lon, min_lat, max_lon, max_lat)
    north_west_south_east = haversine_m(min_lon, max_lat, max_lon, min_lat)
    return max(south_west_north_east, north_west_south_east)


def geographic_overflow_bound_ms(
    *,
    diameter_m: float,
    min_speed_kph: float,
    max_arc_ms: int,
    policy: QuantizationPolicy | None = None,
) -> dict[str, object]:
    """Bound RoutingKit overflow using geography rather than n-1 hop products.

    The simple-path bound (n-1) * max_arc is far larger than any realistic
    Chennai shortest path and would reject millisecond weights. This bound uses
    the study-area diameter, the slowest metric speed, and a labelled detour
    factor. It is an overflow-safety scenario, not a traffic calibration.
    """

    chosen = policy or QuantizationPolicy()
    if diameter_m <= 0 or min_speed_kph <= 0 or max_arc_ms < 0:
        raise ValueError("Diameter, speed, and max_arc_ms must be positive/non-negative.")
    geodesic_ms = travel_time_seconds(diameter_m, min_speed_kph) * chosen.scale
    detoured_ms = int(ceil(geodesic_ms * chosen.geographic_detour_factor))
    bound_ms = max(max_arc_ms, detoured_ms)
    if bound_ms >= ROUTINGKIT_INFINITY:
        raise ValueError(
            "Geographic overflow bound meets RoutingKit's infinity sentinel; "
            "choose a coarser quantization unit."
        )
    return {
        "policy": "geographic_diameter",
        "classification": "SCENARIO",
        "unit": chosen.unit,
        "bbox_diameter_m": diameter_m,
        "min_speed_kph": min_speed_kph,
        "geodesic_travel_ms": geodesic_ms,
        "detour_factor": chosen.geographic_detour_factor,
        "max_arc_ms": max_arc_ms,
        "bound_ms": bound_ms,
        "routingkit_infinity": ROUTINGKIT_INFINITY,
        "claim_limit": (
            "This bound keeps represented shortest-path sums below RoutingKit's "
            "32-bit infinity for geographically plausible Chennai detours. It does "
            "not prove that an adversarial walk of every arc is representable."
        ),
    }
