"""Utility converters shared across resource usage transforms."""

from __future__ import annotations

import re
from typing import Any, Optional

_MEMORY_MULTIPLIERS = {
    "b": 1,
    "kb": 1024,
    "mb": 1024**2,
    "gb": 1024**3,
    "tb": 1024**4,
}


def _resolve_multiplier(unit: Optional[str]) -> Optional[int]:
    if unit is None:
        return _MEMORY_MULTIPLIERS["b"]
    return _MEMORY_MULTIPLIERS.get(unit.lower())


def parse_memory_bytes(value: Any, default_unit: Optional[str] = None) -> Optional[int]:
    """Parse memory specification (e.g., "4gb", 1024, value + unit) into bytes."""
    if value in (None, ""):
        return None

    multiplier = _resolve_multiplier(default_unit)

    if isinstance(value, (int, float)):
        if multiplier is None:
            return None
        return int(float(value) * multiplier)

    normalized = str(value).strip().lower()
    if not normalized:
        return None

    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*([a-z]+)?", normalized)
    if not match:
        return None

    number_str, unit = match.groups()
    effective_multiplier = _resolve_multiplier(unit or default_unit)
    if effective_multiplier is None:
        return None

    try:
        base_value = float(number_str)
    except ValueError:
        return None

    return int(base_value * effective_multiplier)


__all__ = ["parse_memory_bytes"]
