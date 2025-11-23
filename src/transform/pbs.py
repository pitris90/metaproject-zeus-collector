"""Transform PBS and accounting data to ResourceUsageEvent format."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..models.resource_usage import ResourceUsageEvent, ResourceIdentity
else:  # pragma: no cover
    try:
        from ..models.resource_usage import ResourceUsageEvent, ResourceIdentity
    except ImportError:
        from models.resource_usage import (  # type: ignore[import]
            ResourceUsageEvent,
            ResourceIdentity,
        )

from .resource_usage import aggregate_metrics, build_resource_usage_event
from .convert import parse_memory_bytes


DEFAULT_PBS_PROJECT = "_pbs_project_default"


def _to_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_hms_to_seconds(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    parts = str(value).strip().split(":")
    if len(parts) != 3:
        return None
    try:
        hours, minutes, seconds = (int(part) for part in parts)
    except ValueError:
        return None
    return hours * 3600 + minutes * 60 + seconds


def _job_owner_to_username(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    username = str(value).strip()
    postfix = "@META"
    if username.upper().endswith(postfix):
        username = username[: -len(postfix)]
    return username or None


def build_project_usage_from_pbs_jobs(
    pbs_jobs: list[dict[str, Any]],
    window_start: datetime,
    window_end: datetime,
) -> list[ResourceUsageEvent]:
    """
    Transform PBS job data into ResourceUsageEvent objects.

    def _to_int(value: Any) -> Optional[int]:
    Args:
        pbs_jobs: List of PBS job dictionaries from OpenPBS
        window_start: Start of the collection window
        window_end: End of the collection window

    Returns:
        List of ResourceUsageEvent objects, one per PBS job entry
    """

    events: list[ResourceUsageEvent] = []

    for job in pbs_jobs:
        project = (job.get("project") or DEFAULT_PBS_PROJECT) or DEFAULT_PBS_PROJECT
        jobname = job.get("Job_Name")

        cpu_seconds = _parse_hms_to_seconds(job.get("resources_used.cput")) or 0
        walltime_allocated = _parse_hms_to_seconds(job.get("Resource_List.walltime"))
        walltime_used = _parse_hms_to_seconds(job.get("resources_used.walltime"))
        ram_allocated = parse_memory_bytes(job.get("Resource_List.mem"))
        ram_used = parse_memory_bytes(job.get("resources_used.mem"))
        vcpus_allocated = _to_int(job.get("resources_used.ncpus"))
        raw_cpu_percent = _to_int(job.get("resources_used.cpupercent"))

        # Convert cpupercent to 0-100 scale by dividing by vcpus
        used_cpu_percent = None
        if raw_cpu_percent is not None and vcpus_allocated:
            used_cpu_percent = int(raw_cpu_percent / vcpus_allocated)

        metrics = aggregate_metrics(
            cpu_time_seconds=cpu_seconds,
            ram_bytes_allocated=ram_allocated,
            ram_bytes_used=ram_used,
            vcpus_allocated=vcpus_allocated,
            used_cpu_percent=used_cpu_percent,
            walltime_allocated=walltime_allocated,
            walltime_used=walltime_used,
        )

        identities: list[ResourceIdentity] = []
        username = _job_owner_to_username(job.get("Job_Owner"))
        if username:
            identities.append(
                ResourceIdentity(
                    scheme="perun_username",
                    value=username,
                    authority=None,
                )
            )

        context: dict[str, Any] = {
            "jobname": jobname,
            "project": project,
        }

        events.append(
            build_resource_usage_event(
                source="pbs",
                time_window_start=window_start,
                time_window_end=window_end,
                metrics=metrics,
                context=context,
                extra=None,
                identities=identities,
                project_name=project,  # Extract project from context
            )
        )

    return events


def build_project_usage_from_accounting(
    accounting_rows: list[dict[str, Any]],
    window_start: datetime,
    window_end: datetime,
) -> list[ResourceUsageEvent]:
    """
    Convert each accounting DB row into a ResourceUsageEvent.

    Adds perun_username identities, captures project/job metadata inside
    the context, and maps PBS accounting metrics to the unified schema.
    """

    events: list[ResourceUsageEvent] = []

    for row in accounting_rows:
        project = (row.get("project") or DEFAULT_PBS_PROJECT) or DEFAULT_PBS_PROJECT
        jobname = row.get("jobname")

        start_dt = window_start
        end_dt = window_end
        if end_dt < start_dt:
            end_dt = start_dt

        cpu_seconds = _to_int(row.get("used_cputime"))
        if cpu_seconds is None:
            cpu_seconds = 0

        vcpus_allocated = _to_int(row.get("used_ncpus"))
        raw_cpu_percent = _to_int(row.get("used_cpupercent"))

        # Convert cpupercent to 0-100 scale by dividing by vcpus
        used_cpu_percent = None
        if raw_cpu_percent is not None and vcpus_allocated:
            used_cpu_percent = int(raw_cpu_percent / vcpus_allocated)

        metrics = aggregate_metrics(
            cpu_time_seconds=cpu_seconds,
            ram_bytes_allocated=_to_int(row.get("req_mem")),
            ram_bytes_used=_to_int(row.get("used_mem")),
            vcpus_allocated=vcpus_allocated,
            used_cpu_percent=used_cpu_percent,
            walltime_allocated=_to_int(row.get("req_walltime")),
            walltime_used=_to_int(row.get("used_walltime")),
        )

        identities: list[ResourceIdentity] = []
        user_name = row.get("user_name")
        if user_name:
            identities.append(
                ResourceIdentity(
                    scheme="perun_username",
                    value=str(user_name),
                    authority=None,
                )
            )

        context: dict[str, Any] = {
            "jobname": jobname,
            "project": project,
        }

        events.append(
            build_resource_usage_event(
                source="pbs",
                time_window_start=start_dt,
                time_window_end=end_dt,
                metrics=metrics,
                context=context,
                extra=None,
                identities=identities,
                project_name=project,  # Extract project from context
            )
        )

    return events


def combine_pbs_project_usage(
    openpbs_events: list[ResourceUsageEvent],
    accounting_events: list[ResourceUsageEvent],
) -> list[ResourceUsageEvent]:
    """
    Combine OpenPBS and accounting database events into a single list.

    Simply concatenates events from both sources since they represent
    the same type of data collected from different places (current jobs
    from OpenPBS, historical/deleted jobs from accounting database).

    Args:
        openpbs_events: Events from OpenPBS jobs (current/running)
        accounting_events: Events from accounting database (completed/deleted)

    Returns:
        Combined list of all ResourceUsageEvent objects
    """
    return openpbs_events + accounting_events
