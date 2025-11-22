import os
import pbs_ifl
from typing import Any


def fetch_pbs_jobs() -> list[dict[str, Any]]:
    """
    Connect to PBS server, fetch current job information about running jobs,
    and return structured job data.

    Returns:
        List of job dictionaries with PBS attributes.

    Raises:
        ConnectionError: If unable to connect to PBS server.
        RuntimeError: If unable to fetch job information.
    """
    server = os.environ.get("PBS_HOST", "pbs-m1.metacentrum.cz")
    c = None

    try:
        c = pbs_ifl.pbs_connect(server)
        if c < 0:
            raise ConnectionError(f"Failed to connect to PBS server: {server}")

        # Fetch all jobs with extended attributes
        jobs = pbs_ifl.pbs_statjob(c, None, None, "xt")
        if jobs is None:
            raise RuntimeError("Failed to fetch job information from PBS")

        # Convert to list of dictionaries for easier processing
        running_jobs = []
        for job in jobs:
            if job["job_state"] == "R":
                running_jobs.append(job)

        return running_jobs

    except Exception as e:
        raise RuntimeError(f"Error fetching PBS jobs: {e}") from e

    finally:
        if c is not None and c >= 0:
            try:
                pbs_ifl.pbs_disconnect(c)
            except Exception:
                pass  # Best effort disconnect
