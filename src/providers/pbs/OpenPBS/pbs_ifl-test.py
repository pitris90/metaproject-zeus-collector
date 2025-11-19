import sys
import pbs_ifl
from typing import Any

server = "pbs-m1.metacentrum.cz"

c = None

try:
    c = pbs_ifl.pbs_connect(server)
except Exception:
    print("failed to connect to the server")
    exit(1)

try:
    server_info = pbs_ifl.pbs_statserver(c, None, None)
    # print(server_info)
except Exception:
    print("failed to get server info")
    exit(1)
try:
    queue_info: Any = pbs_ifl.pbs_statque(c, None, None, None) # pyright: ignore[reportUnknownVariableType]
    # print(queue_info)
except Exception:
    print("failed to get queues info")
    exit(1)
    exit(1)

try:
    node_info = pbs_ifl.pbs_statvnode(c, None, None, None)
    # print(node_info)
except Exception:
    print("failed to get nodes info")
    exit(1)

try:
    job_info = pbs_ifl.pbs_statjob(c, None, None, "xt")
    # print(job_info)
    group_jobs = []
    for job in job_info:
        if "group_list" in job or "group" in job:
            group_jobs.append(job)
    print("pepa")
    
    not_same_owner = []
    for job in job_info:
        if job.get("Job_Owner", "") != job.get("credential_id", ""):
            not_same_owner.append(job)
    print("f")
except Exception:
    print("failed to get jobs info")
    exit(1)


try:
    pbs_ifl.pbs_disconnect(c)
finally:
    c = None
