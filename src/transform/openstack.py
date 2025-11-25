"""Transform OpenStack data to ResourceUsageEvent format."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, TYPE_CHECKING, Optional, cast

if TYPE_CHECKING:  # pragma: no cover
    from ..models.resource_usage import ResourceUsageEvent, ResourceIdentity
else:  # pragma: no cover
    try:
        from ..models.resource_usage import (
            ResourceUsageEvent,
            ResourceIdentity,
        )
    except ImportError:
        from models.resource_usage import (  # type: ignore[import]
            ResourceUsageEvent,
            ResourceIdentity,
        )

from .resource_usage import aggregate_metrics, build_resource_usage_event
from .convert import parse_memory_bytes


def is_personal_project(description: Optional[str]) -> bool:
    """
    Determine if a project is a personal project based on its description.

    Args:
        description: Project description text

    Returns:
        True if description starts with "Personal project", False otherwise
    """
    if not description:
        return False
    return description.strip().startswith("Personal project")


def _sample_value(sample: dict[str, Any]) -> Optional[float]:
    value = sample.get("value")
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    raw_value = cast(Any, value[1])
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Optional[float]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_emails_from_text(text: str) -> list[str]:
    """
    Extract email addresses from text using regex.

    Args:
        text: Text containing email addresses

    Returns:
        List of email addresses found
    """
    if not text:
        return []
    # Match email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    return [email.strip() for email in emails if email.strip()]


def _build_identities_from_project(
    project_name: Optional[str],
    description: Optional[str]
) -> list[ResourceIdentity]:
    """
    Build identity list from OpenStack project name and description.

    Personal projects (project description starts with "Personal project"):
      - Add oidc_sub identity with project_name as value
      - Parse email from description ending with "with contact address <email>"
      - Skip adding user_email if it's the same as project_name (oidc_sub)

    Other projects:
      - Parse emails from description ending with "Contacts: <email1>, <email2>, ..."

    Args:
        project_name: OpenStack project name
        description: OpenStack project description

    Returns:
        List of ResourceIdentity objects
    """
    identities: list[ResourceIdentity] = []

    # Check if it's a personal project
    personal_project = is_personal_project(description)
    if personal_project and project_name:
        identities.append(
            ResourceIdentity(
                scheme="oidc_sub",
                value=project_name,
                authority=None,
            )
        )
        return identities

    # Parse emails from description
    if description:
        emails = _parse_emails_from_text(description)
        for email in emails:
            identities.append(
                ResourceIdentity(
                    scheme="user_email",
                    value=email,
                    authority=None,
                )
            )

    return identities


def build_domain_map(domain_samples: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    Build a mapping of domain_id -> domain info for efficient lookups.

    Args:
        domain_samples: List of domain metric samples

    Returns:
        Dictionary mapping domain_id to domain information
    """
    domain_map: dict[str, dict[str, Any]] = {}
    for sample in domain_samples:
        metric = sample.get("metric", {})
        domain_id = metric.get("domain_id")
        if domain_id:
            domain_map[domain_id] = {
                "domain_id": domain_id,
                "domain_name": metric.get("domain_name"),
            }
    return domain_map


def build_project_map(project_samples: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    Build a mapping of project_id -> project info for efficient lookups.

    Args:
        project_samples: List of project metric samples

    Returns:
        Dictionary mapping project_id to project information
    """
    project_map: dict[str, dict[str, Any]] = {}
    for sample in project_samples:
        metric = sample.get("metric", {})
        project_id = metric.get("id")
        if project_id:
            project_map[project_id] = {
                "project_id": project_id,
                "project_name": metric.get("name"),
                "domain_id": metric.get("domain_id"),
                "region": metric.get("region"),
                "description": metric.get("description"),
            }
    return project_map


def build_server_map(server_samples: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """
    Build a mapping of project_id -> list of servers for efficient lookups.

    Args:
        server_samples: List of server metric samples

    Returns:
        Dictionary mapping project_id to list of server information
    """
    server_map: dict[str, list[dict[str, Any]]] = {}
    for sample in server_samples:
        metric = sample.get("metric", {})
        project_id = metric.get("project_id")
        server_id = metric.get("server_id")
        if not project_id or not server_id:
            continue

        server_info = {
            "server_id": server_id,
            "server_name": metric.get("server_name"),
            "region": metric.get("region"),
        }

        if project_id not in server_map:
            server_map[project_id] = []
        server_map[project_id].append(server_info)

    return server_map


def build_server_vcpu_map(vcpu_samples: list[dict[str, Any]]) -> dict[str, int]:
    """
    Build a mapping of server uuid -> vcpu count for efficient lookups.

    Args:
        vcpu_samples: List of vcpu metric samples

    Returns:
        Dictionary mapping server uuid to vcpu count
    """
    vcpu_map: dict[str, int] = {}
    for sample in vcpu_samples:
        metric = sample.get("metric", {})
        uuid = metric.get("uuid")
        if not uuid:
            continue
        value = _safe_int(_sample_value(sample))
        if value is not None:
            vcpu_map[uuid] = value
    return vcpu_map


def build_server_memory_map(
    memory_samples: list[dict[str, Any]], unit: str = "kb"
) -> dict[str, int]:
    """
    Build a mapping of server uuid -> memory bytes for efficient lookups.

    Args:
        memory_samples: List of memory metric samples
        unit: Default unit for memory values (e.g., "kb", "mb", "b")

    Returns:
        Dictionary mapping server uuid to memory in bytes
    """
    memory_map: dict[str, int] = {}
    for sample in memory_samples:
        metric = sample.get("metric", {})
        uuid = metric.get("uuid")
        if not uuid:
            continue
        value = _safe_int(_sample_value(sample))
        if value is None:
            continue
        memory_bytes = parse_memory_bytes(value, unit)
        if memory_bytes is not None:
            memory_map[uuid] = memory_bytes
    return memory_map


def build_server_cpu_time_map(
    cpu_samples: list[dict[str, Any]]
) -> dict[str, float]:
    """
    Build a mapping of server uuid -> CPU time in seconds for efficient lookups.

    Args:
        cpu_samples: List of CPU time metric samples

    Returns:
        Dictionary mapping server uuid to CPU time in seconds
    """
    cpu_map: dict[str, float] = {}
    for sample in cpu_samples:
        metric = sample.get("metric", {})
        uuid = metric.get("uuid")
        if not uuid:
            continue
        value = _sample_value(sample)
        if value is not None:
            cpu_map[uuid] = value
    return cpu_map


def build_project_usage_from_openstack(
    openstack_data: dict[str, list[dict[str, Any]]],
    window_start: datetime,
    window_end: datetime,
) -> list[ResourceUsageEvent]:
    """
    Transform OpenStack usage data into ResourceUsageEvent objects.

    This function aggregates usage data by OpenStack project, combining
    information from various OpenStack services (Nova, Cinder, etc.).

    Args:
        openstack_data: Mapping name -> raw Thanos query results
        window_start: Start of the collection window
        window_end: End of the collection window

    Returns:
        List of ResourceUsageEvent objects, one per project

    """

    openstack_data = openstack_data or {}
    domain_samples = openstack_data.get("domains", [])
    project_samples = openstack_data.get("projects", [])
    project_server_samples = openstack_data.get("project_servers", [])
    server_samples = openstack_data.get("servers", [])
    vcpu_samples = openstack_data.get("vcpu", [])
    cpu_usage_per_day_samples = openstack_data.get("cpu_usage_per_day", [])
    cpu_time_seconds_samples = openstack_data.get("cpu_time_seconds", [])
    memory_usable_samples = openstack_data.get("memory_usable", [])
    memory_maximum_samples = openstack_data.get("memory_maximum", [])
    storage_allocated_samples = openstack_data.get("storage_allocated", [])

    # Build efficient lookup maps
    domain_map = build_domain_map(domain_samples)
    project_map = build_project_map(project_samples)
    server_map = build_server_map(server_samples)
    vcpu_map = build_server_vcpu_map(vcpu_samples)
    cpu_usage_per_day_map = build_server_cpu_time_map(cpu_usage_per_day_samples)
    cpu_time_seconds_map = build_server_cpu_time_map(cpu_time_seconds_samples)
    memory_usable_map = build_server_memory_map(memory_usable_samples, unit="kb")
    memory_maximum_map = build_server_memory_map(memory_maximum_samples, unit="kb")
    storage_allocated_map = build_server_memory_map(storage_allocated_samples, unit="b")

    # Enrich project_map with data from project_server_samples
    for sample in project_server_samples:
        metric = sample.get("metric", {})
        project_id = metric.get("project_id")
        if project_id and project_id in project_map:
            if not project_map[project_id].get("project_name"):
                project_map[project_id]["project_name"] = metric.get("project_name")
            if not project_map[project_id].get("domain_name"):
                project_map[project_id]["domain_name"] = metric.get("domain_name")

    # Enrich project_map with domain names from domain_map
    for project_id, project_info in project_map.items():
        domain_id = project_info.get("domain_id")
        if domain_id and domain_id in domain_map and not project_info.get("domain_name"):
            project_info["domain_name"] = domain_map[domain_id].get("domain_name")

    events: list[ResourceUsageEvent] = []
    for project_id, project_info in project_map.items():
        project_name = project_info.get("project_name")
        domain_id = project_info.get("domain_id")
        domain_name = project_info.get("domain_name")
        description = project_info.get("description")
        region = project_info.get("region") or "unknown"

        # Build identities from project name and description
        identities = _build_identities_from_project(project_name, description)

        # Get servers for this project
        project_servers = server_map.get(project_id, [])

        server_context: list[dict[str, Any]] = []
        total_vcpus = 0
        total_ram_bytes_usable = 0
        total_ram_bytes_maximum = 0
        total_storage_bytes = 0
        total_cpu_time_seconds = 0.0
        total_cpu_usage_weighted = 0.0

        for srv in project_servers:
            uuid = srv.get("uuid")
            server_id = srv.get("server_id")

            # Lookup vcpus and memory using uuid or server_id
            vcpus = 0
            memory_usable_bytes = 0
            memory_maximum_bytes = 0
            storage_bytes = 0
            cpu_usage_per_day = 0.0
            cpu_time_seconds = 0.0

            if uuid:
                vcpus = vcpu_map.get(uuid, 0)
                memory_usable_bytes = memory_usable_map.get(uuid, 0)
                memory_maximum_bytes = memory_maximum_map.get(uuid, 0)
                storage_bytes = storage_allocated_map.get(uuid, 0)
                cpu_usage_per_day = cpu_usage_per_day_map.get(uuid, 0.0)
                cpu_time_seconds = cpu_time_seconds_map.get(uuid, 0.0)

            if not vcpus and server_id:
                vcpus = vcpu_map.get(server_id, 0)

            if not memory_usable_bytes and server_id:
                memory_usable_bytes = memory_usable_map.get(server_id, 0)

            if not memory_maximum_bytes and server_id:
                memory_maximum_bytes = memory_maximum_map.get(server_id, 0)

            if not storage_bytes and server_id:
                storage_bytes = storage_allocated_map.get(server_id, 0)

            if not cpu_usage_per_day and server_id:
                cpu_usage_per_day = cpu_usage_per_day_map.get(server_id, 0.0)

            if not cpu_time_seconds and server_id:
                cpu_time_seconds = cpu_time_seconds_map.get(server_id, 0.0)

            # Calculate used_cpu_percent for this server
            used_cpu_percent = None
            if vcpus and cpu_usage_per_day:
                used_cpu_percent = (cpu_usage_per_day * 100.0) / vcpus

            total_vcpus += vcpus
            total_ram_bytes_usable += memory_usable_bytes
            total_ram_bytes_maximum += memory_maximum_bytes
            total_storage_bytes += storage_bytes
            total_cpu_time_seconds += cpu_time_seconds
            # Weight CPU usage by vcpus for accurate project-level average
            if vcpus and cpu_usage_per_day:
                total_cpu_usage_weighted += cpu_usage_per_day * 100.0

            server_context.append(
                {
                    "server_id": server_id,
                    "uuid": uuid,
                    "name": srv.get("name"),
                    "region": srv.get("region"),
                    "vcpus": vcpus,
                    "memory_current_bytes": memory_maximum_bytes - memory_usable_bytes,
                    "memory_maximum_bytes": memory_maximum_bytes,
                    "storage_allocated_bytes": storage_bytes,
                    "used_cpu_percent": int(used_cpu_percent) if used_cpu_percent else None,
                    "cpu_time_seconds": int(cpu_time_seconds),
                }
            )

        # Calculate project-level used_cpu_percent
        project_used_cpu_percent = None
        if total_vcpus and total_cpu_usage_weighted:
            project_used_cpu_percent = int(total_cpu_usage_weighted / total_vcpus)

        metrics = aggregate_metrics(
            cpu_time_seconds=int(total_cpu_time_seconds) if total_cpu_time_seconds else 0,
            ram_bytes_allocated=total_ram_bytes_maximum,
            ram_bytes_used=total_ram_bytes_maximum - total_ram_bytes_usable,
            vcpus_allocated=total_vcpus,
            storage_bytes_allocated=total_storage_bytes,
            used_cpu_percent=project_used_cpu_percent,
        )

        is_personal = is_personal_project(description)

        context: dict[str, Any] = {
            "cloud": "openstack",
            "project": project_name or project_id,
            "project_id": project_id,
            "domain": domain_name,
            "domain_id": domain_id,
            "region": region,
            "vm_count": len(project_servers),
            "servers": server_context,
        }

        event = build_resource_usage_event(
            source="openstack",
            time_window_start=window_start,
            time_window_end=window_end,
            metrics=metrics,
            context=context,
            extra=None,
            identities=identities,
            project_name=project_name or project_id,  # Extract project from context
            is_personal=is_personal,
        )
        events.append(event)

    return events
