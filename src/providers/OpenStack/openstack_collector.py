"""OpenStack resource usage collector backed by Thanos queries."""

from __future__ import annotations

import os
from typing import Any, Optional, cast

import httpx


OPENSTACK_THANOS_ENDPOINT = os.getenv("OPENSTACK_THANOS_ENDPOINT")
OPENSTACK_THANOS_USERNAME = os.getenv("OPENSTACK_THANOS_USERNAME")
OPENSTACK_THANOS_PASSWORD = os.getenv("OPENSTACK_THANOS_PASSWORD")
OPENSTACK_THANOS_VERIFY_TLS = os.getenv("OPENSTACK_THANOS_VERIFY_TLS", "false")
OPENSTACK_THANOS_TIMEOUT = float(os.getenv("OPENSTACK_THANOS_TIMEOUT", "30"))


PROM_QUERIES = {
    "domains": "custom_openstack_domain_info",
    "project_servers": "custom_openstack_project_info",
    "projects": "openstack_identity_project_info",
    "servers": "custom_openstack_server_info",
    "vcpu": "count by (uuid) (libvirtd_domain_vcpu_time)",
    "cpu_usage_per_day": "sum by (uuid) (rate(libvirtd_domain_vcpu_time[24h])) / 1e9",
    "cpu_time_seconds": "sum by (uuid)(libvirtd_domain_vcpu_time) / 1e9",
    "memory_current": "libvirtd_domain_balloon_current",
    "memory_maximum": "libvirtd_domain_balloon_maximum",
    "storage_allocated": "sum by (uuid) (libvirtd_domain_block_capacity)",
}


class OpenStackCollectorError(RuntimeError):
    """Raised when OpenStack collection fails."""


def _env_flag(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "on"}


def _get_thanos_client() -> httpx.Client:
    if not OPENSTACK_THANOS_ENDPOINT:
        raise ValueError("OPENSTACK_THANOS_ENDPOINT environment variable is required")

    auth: Optional[tuple[str, str]] = None
    if OPENSTACK_THANOS_USERNAME and OPENSTACK_THANOS_PASSWORD:
        auth = (OPENSTACK_THANOS_USERNAME, OPENSTACK_THANOS_PASSWORD)

    verify = _env_flag(OPENSTACK_THANOS_VERIFY_TLS)
    return httpx.Client(
        base_url=OPENSTACK_THANOS_ENDPOINT.rstrip("/"),
        auth=auth,
        timeout=OPENSTACK_THANOS_TIMEOUT,
        verify=verify,
    )


def _query_thanos(query: str) -> list[dict[str, Any]]:
    try:
        with _get_thanos_client() as client:
            response = client.get("/api/v1/query", params={"query": query})
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:  # pragma: no cover - network path
        raise OpenStackCollectorError(f"Thanos query failed: {exc}") from exc

    status = payload.get("status")
    if status != "success":
        raise OpenStackCollectorError(
            f"Thanos query '{query}' failed with status {status}"
        )

    data = payload.get("data", {})
    results = data.get("result", [])
    if not isinstance(results, list):
        raise OpenStackCollectorError(
            f"Unexpected result format for query '{query}': {results}"
        )
    return cast(list[dict[str, Any]], results)


def collect_openstack_inventory() -> dict[str, list[dict[str, Any]]]:
    """Collect raw Thanos query outputs for OpenStack-related datasets."""

    return {
        "domains": _query_thanos(PROM_QUERIES["domains"]),
        "projects": _query_thanos(PROM_QUERIES["projects"]),
        "project_servers": _query_thanos(PROM_QUERIES["project_servers"]),
        "servers": _query_thanos(PROM_QUERIES["servers"]),
        "vcpu": _query_thanos(PROM_QUERIES["vcpu"]),
        "cpu_usage_per_day": _query_thanos(PROM_QUERIES["cpu_usage_per_day"]),
        "cpu_time_seconds": _query_thanos(PROM_QUERIES["cpu_time_seconds"]),
        "memory_current": _query_thanos(PROM_QUERIES["memory_current"]),
        "memory_maximum": _query_thanos(PROM_QUERIES["memory_maximum"]),
        "storage_allocated": _query_thanos(PROM_QUERIES["storage_allocated"]),
    }


__all__ = ["collect_openstack_inventory", "OpenStackCollectorError"]
