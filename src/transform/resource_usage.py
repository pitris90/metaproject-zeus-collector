"""Base helpers for building ResourceUsageEvent objects."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..models.resource_usage import (
        ResourceIdentity,
        ResourceUsageEvent,
        ResourceUsageMetrics,
    )
else:  # pragma: no cover - runtime import flexibility
    try:
        from ..models.resource_usage import (
            ResourceIdentity,
            ResourceUsageEvent,
            ResourceUsageMetrics,
        )
    except ImportError:
        from models.resource_usage import (  # type: ignore[import]
            ResourceIdentity,
            ResourceUsageEvent,
            ResourceUsageMetrics,
        )


def build_resource_usage_event(
    source: Literal["pbs", "openstack"],
    time_window_start: datetime,
    time_window_end: datetime,
    metrics: ResourceUsageMetrics,
    context: dict[str, Any],
    extra: Optional[dict[str, Any]] = None,
    identities: Optional[List[ResourceIdentity]] = None,
) -> ResourceUsageEvent:
    """
    Build a ResourceUsageEvent from components.

    Args:
        source: Data source identifier
        time_window_start: Start of measurement window
        time_window_end: End of measurement window
        metrics: Resource usage metrics
        context: Additional contextual information
        extra: Optional extra data

    Returns:
        ResourceUsageEvent object
    """
    return ResourceUsageEvent(
        schema_version="1.0",
        source=source,
        time_window_start=time_window_start,
        time_window_end=time_window_end,
        collected_at=datetime.now(timezone.utc),
        metrics=metrics,
        context=context,
        extra=extra,
        identities=identities or [],
    )


def aggregate_metrics(
    cpu_time_seconds: int = 0,
    gpu_time_seconds: Optional[int] = None,
    ram_bytes_allocated: Optional[int] = None,
    ram_bytes_used: Optional[int] = None,
    storage_bytes_allocated: Optional[int] = None,
    vcpus_allocated: Optional[int] = None,
    used_cpu_percent: Optional[int] = None,
    walltime_allocated: Optional[int] = None,
    walltime_used: Optional[int] = None,
) -> ResourceUsageMetrics:
    """
    Create ResourceUsageMetrics from individual values.

    Args:
        cpu_time_seconds: Total CPU time in seconds
        gpu_time_seconds: Total GPU time in seconds
        ram_bytes_allocated: RAM allocated in bytes
        ram_bytes_used: RAM used in bytes
        storage_bytes_allocated: Storage allocated in bytes
        vcpus_allocated: Virtual CPUs allocated
        used_cpu_percent: Average CPU utilization percent
        walltime_allocated: Requested walltime in seconds
        walltime_used: Actual walltime consumed in seconds

    Returns:
        ResourceUsageMetrics object
    """
    return ResourceUsageMetrics(
        cpu_time_seconds=cpu_time_seconds,
        gpu_time_seconds=gpu_time_seconds,
        ram_bytes_allocated=ram_bytes_allocated,
        ram_bytes_used=ram_bytes_used,
        storage_bytes_allocated=storage_bytes_allocated,
        vcpus_allocated=vcpus_allocated,
        used_cpu_percent=used_cpu_percent,
        walltime_allocated=walltime_allocated,
        walltime_used=walltime_used,
    )
