"""Pydantic models for resource usage events."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ResourceUsageMetrics(BaseModel):
    """Metrics for resource usage across different compute resources."""

    cpu_time_seconds: int = Field(
        ..., description="Total CPU time consumed in seconds", ge=0
    )
    gpu_time_seconds: Optional[int] = Field(
        None, description="Total GPU time consumed in seconds", ge=0
    )
    ram_bytes_allocated: Optional[int] = Field(
        None, description="RAM allocated in bytes", ge=0
    )
    ram_bytes_used: Optional[int] = Field(
        None, description="RAM actually used in bytes", ge=0
    )
    storage_bytes_allocated: Optional[int] = Field(
        None, description="Storage allocated in bytes", ge=0
    )
    vcpus_allocated: Optional[int] = Field(
        None, description="Virtual CPUs allocated", ge=0
    )
    used_cpu_percent: Optional[int] = Field(
        None, description="Average CPU utilization percent", ge=0
    )
    walltime_allocated: Optional[int] = Field(
        None, description="Requested walltime in seconds", ge=0
    )
    walltime_used: Optional[int] = Field(
        None, description="Actual walltime consumed in seconds", ge=0
    )


class ResourceIdentity(BaseModel):
    """Identities associated with the usage subject."""

    scheme: str = Field(..., description="Identifier scheme, e.g., perun_user")
    value: str = Field(..., description="Identifier value")
    authority: Optional[str] = Field(
        None, description="Authority issuing the identity"
    )


class ResourceUsageEvent(BaseModel):
    """A single resource usage event from a specific source."""

    schema_version: str = Field(
        default="1.0", description="Schema version for compatibility"
    )
    source: Literal["pbs", "openstack"] = Field(
        ..., description="Data source identifier"
    )
    time_window_start: datetime = Field(
        ..., description="Start of the measurement window"
    )
    time_window_end: datetime = Field(..., description="End of the measurement window")
    collected_at: datetime = Field(
        ..., description="Timestamp when data was collected"
    )
    project_name: Optional[str] = Field(
        None, description="Project name extracted from context"
    )
    metrics: ResourceUsageMetrics = Field(
        ..., description="Resource usage metrics"
    )
    identities: list[ResourceIdentity] = Field(
        default_factory=list,
        description="List of identities the usage belongs to",
    )
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional contextual information"
    )
    extra: Optional[dict[str, Any]] = Field(
        None, description="Extra data for debugging or future use"
    )
