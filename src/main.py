"""ZEUS Collector - Resource usage data collection for PBS and OpenStack."""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any, cast

from providers.OpenStack.openstack_collector import collect_openstack_inventory
from providers.pbs.OpenPBS.pbs_collect import fetch_pbs_jobs
from providers.pbs.accounting_db.accounting_db_collect import fetch_accounting_records
from transform.openstack import build_project_usage_from_openstack
from transform.pbs import (
    build_project_usage_from_pbs_jobs,
    build_project_usage_from_accounting,
    combine_pbs_project_usage,
)
from zeus_client import ZeusClient


def main() -> None:
    """Main collector entry point - fetch PBS and accounting data in 24h loop."""

    while True:
        try:
            # Define time window for accounting data (last 24 hours)
            window_end = datetime.now()
            window_start = window_end - timedelta(hours=24)

            print(f"[collector] Starting collection cycle at {window_end}", flush=True)

            print("[collector] Fetching OpenStack datasets...", flush=True)
            openstack_data = cast(
                dict[str, list[dict[str, Any]]],
                collect_openstack_inventory(),
            )
            print("[collector] Building OpenStack usage events...", flush=True)
            openstack_events = cast(
                list[Any],
                build_project_usage_from_openstack(
                    openstack_data=openstack_data,
                    window_start=window_start,
                    window_end=window_end,
                ),
            )
            print(f"[collector] Built {len(openstack_events)} OpenStack events", flush=True)

            print("[collector] Fetching PBS jobs...", flush=True)
            pbs_jobs = cast(list[dict[str, Any]], fetch_pbs_jobs())
            print(f"[collector] Fetched {len(pbs_jobs)} PBS jobs", flush=True)

            print(
                "[collector] Fetching accounting records from "
                f"{window_start} to {window_end}...",
                flush=True,
            )
            accounting_records = cast(
                list[dict[str, Any]],
                fetch_accounting_records(window_start, window_end),
            )
            print(
                f"[collector] Fetched {len(accounting_records)} accounting records",
                flush=True,
            )

            # Variables available for debugging
            print("[collector] Building PBS job usage events...", flush=True)
            pbs_events = cast(
                list[Any],
                build_project_usage_from_pbs_jobs(
                    pbs_jobs=pbs_jobs,
                    window_start=window_start,
                    window_end=window_end,
                ),
            )
            print(f"[collector] Built {len(pbs_events)} PBS job events", flush=True)

            print("[collector] Building accounting usage events...", flush=True)
            accounting_events = cast(
                list[Any],
                build_project_usage_from_accounting(
                    accounting_rows=accounting_records,
                    window_start=window_start,
                    window_end=window_end,
                ),
            )
            print(f"[collector] Built {len(accounting_events)} accounting events", flush=True)

            combined_pbs_events = cast(
                list[Any],
                combine_pbs_project_usage(
                    pbs_events,
                    accounting_events,
                ),
            )

            all_events = list(openstack_events)
            all_events.extend(combined_pbs_events)
            print(f"[collector] Total events prepared: {len(all_events)}", flush=True)

            if all_events:
                print("[collector] Sending events to ZEUS API...", flush=True)
                client = cast(Any, ZeusClient())
                client.send_resource_usage_events(all_events)
                print("[collector] Events sent successfully", flush=True)
            else:
                print("[collector] No events to send", flush=True)

            print("[collector] Collection cycle complete. Sleeping for 24 hours...", flush=True)
            time.sleep(24 * 60 * 60)  # Sleep for 24 hours

        except KeyboardInterrupt:
            print("[collector] Shutting down gracefully...", flush=True)
            break
        except Exception as e:
            print(f"[collector] Error in collection cycle: {e}", flush=True)
            print("[collector] Waiting 5 minutes before retry...", flush=True)
            time.sleep(5 * 60)  # Wait 5 minutes before retrying on error


if __name__ == "__main__":
    main()

