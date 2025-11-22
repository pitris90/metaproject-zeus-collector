"""HTTP client for sending resource usage events to ZEUS API."""

import os
from typing import Any

import httpx
from rich.console import Console

from models.resource_usage import ResourceUsageEvent

console = Console()


class ZeusClient:
    """Client for interacting with ZEUS API."""

    def __init__(self):
        """Initialize ZEUS client with configuration from environment."""
        self.endpoint = os.getenv("ZEUS_ENDPOINT")
        self.api_key = os.getenv("ZEUS_API_KEY")
        self.batch_max = int(os.getenv("COLLECTOR_BATCH_MAX", "100"))

        if not self.endpoint:
            raise ValueError("ZEUS_ENDPOINT environment variable is required")
        if not self.api_key:
            raise ValueError("ZEUS_API_KEY environment variable is required")

        # Ensure endpoint doesn't have trailing slash
        self.endpoint = self.endpoint.rstrip("/")

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for ZEUS API requests."""
        return {
            "Content-Type": "application/json",
            "X-Zeus-Collector-Key": self.api_key,
        }

    def send_resource_usage_events(self, events: list[ResourceUsageEvent]) -> None:
        """
        Send resource usage events to ZEUS API.

        Args:
            events: List of ResourceUsageEvent objects to send

        Raises:
            httpx.HTTPError: If the request fails
        """
        if not events:
            console.log("[yellow]No events to send[/yellow]")
            return

        total_events = len(events)
        console.log(f"[cyan]Sending {total_events} events to ZEUS API[/cyan]")

        # Split events into batches
        batches = [
            events[i : i + self.batch_max]
            for i in range(0, len(events), self.batch_max)
        ]

        total_sent = 0
        total_failed = 0

        for batch_idx, batch in enumerate(batches, start=1):
            console.log(
                f"[cyan]Processing batch {batch_idx}/{len(batches)} "
                f"({len(batch)} events)[/cyan]"
            )

            try:
                self._send_batch(batch)
                total_sent += len(batch)
                console.log(
                    f"[green]✓ Batch {batch_idx} sent successfully[/green]"
                )
            except Exception as e:
                total_failed += len(batch)
                console.log(
                    f"[red]✗ Batch {batch_idx} failed: {e}[/red]"
                )

        console.log(
            f"[bold]Summary: {total_sent} sent, {total_failed} failed[/bold]"
        )

        if total_failed > 0:
            raise RuntimeError(
                f"Failed to send {total_failed} events to ZEUS API"
            )

    def _send_batch(self, batch: list[ResourceUsageEvent]) -> None:
        """
        Send a single batch of events to ZEUS API.

        Args:
            batch: List of events to send in this batch

        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{self.endpoint}/collector/resource-usage"
        payload = {
            "events": [event.model_dump(mode="json") for event in batch]
        }
        
        headers = self._get_headers()
        console.log(f"[dim]Sending to {url}[/dim]")
        console.log(f"[dim]Headers being sent: {headers}[/dim]")
        if self.api_key:
            console.log(f"[dim]API Key (first 16 chars): {self.api_key[:16]}...[/dim]")

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                json=payload,
                headers=headers,
            )

            # Raise exception for 4xx/5xx status codes
            response.raise_for_status()

            # Log response
            result = response.json()
            console.log(
                f"[dim]ZEUS response: {result.get('message', 'OK')}[/dim]"
            )
