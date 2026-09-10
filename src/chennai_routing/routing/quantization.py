"""Integer travel-time quantization for the certificate engines.

Stage 1 uses float seconds. Stage 2 requires non-negative integers. This
module is the declared conversion: round to milliseconds.
"""

from __future__ import annotations

import math

QUANTIZATION_UNIT = "millisecond"
SECONDS_TO_MS = 1000


def quantize_seconds(seconds: float) -> int:
    """Round a finite non-negative duration to integer milliseconds."""

    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError("Only finite non-negative seconds can be quantized.")
    return max(0, int(round(seconds * SECONDS_TO_MS)))
