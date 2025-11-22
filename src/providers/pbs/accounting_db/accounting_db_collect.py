import os
from datetime import datetime
from typing import Any
import psycopg2
from psycopg2.extras import RealDictCursor


def fetch_accounting_records(
    window_start: datetime,
    window_end: datetime
) -> list[dict[str, Any]]:
    """
    Connect to PBS accounting database, fetch job accounting records for the time window,
    and return structured data.

    Args:
        window_start: Start of the time window to fetch records for
        window_end: End of the time window to fetch records for

    Returns:
        List of accounting record dictionaries with job execution data.

    Raises:
        ConnectionError: If unable to connect to accounting database.
        RuntimeError: If unable to fetch accounting records.
    """
    # Get connection parameters from environment
    db_host = os.environ.get("ACCOUNTING_DB_HOST")
    db_port = int(os.environ.get("ACCOUNTING_DB_PORT", "5432"))
    db_name = os.environ.get("ACCOUNTING_DB_NAME")
    db_user = os.environ.get("ACCOUNTING_DB_USER")
    db_password = os.environ.get("ACCOUNTING_DB_PASSWORD")

    if not all([db_host, db_name, db_user, db_password]):
        raise ValueError(
            "Missing required accounting DB environment variables: "
            "ACCOUNTING_DB_HOST, ACCOUNTING_DB_NAME, ACCOUNTING_DB_USER, ACCOUNTING_DB_PASSWORD"
        )

    conn = None
    cursor = None

    try:
        # Connect to the accounting database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=10,
            gssencmode="disable",
        )

        # Use RealDictCursor to get results as dictionaries
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Convert datetime to Unix timestamp (bigint) for database query
        window_start_ts = int(window_start.timestamp())
        window_end_ts = int(window_end.timestamp())

        # Query PBS accounting records for the time window
        # Filter records first, then join with user table for better performance
        query = """
            SELECT
                apr.create_time,
                apr.date_time,
                apr.end_time,
                apr.jobname,
                apr.req_mem,
                apr.req_walltime,
                apr.start_time,
                apr.used_cpupercent,
                apr.used_cputime,
                apr.used_mem,
                apr.used_ncpus,
                apr.used_walltime,
                au.user_name
            FROM (
                SELECT *
                FROM acct_pbs_record
                WHERE end_time >= %s AND end_time < %s
            ) apr
            JOIN acct_user au ON apr.acct_user_id = au.acct_user_id
            ORDER BY apr.end_time
        """

        cursor.execute(query, (window_start_ts, window_end_ts))

        # Fetch all results
        records = cursor.fetchall()

        # Convert to list of dicts (RealDictCursor returns RealDictRow objects)
        return [dict(record) for record in records]

    except psycopg2.Error as e:
        raise RuntimeError(f"Database error while fetching accounting records: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Error fetching accounting records: {e}") from e

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def test_accounting_db_connection() -> bool:
    """
    Test connection to the accounting database.

    Returns:
        True if connection successful, False otherwise.
    """
    db_host = os.environ.get("ACCOUNTING_DB_HOST")
    db_port = int(os.environ.get("ACCOUNTING_DB_PORT", "5432"))
    db_name = os.environ.get("ACCOUNTING_DB_NAME")
    db_user = os.environ.get("ACCOUNTING_DB_USER")
    db_password = os.environ.get("ACCOUNTING_DB_PASSWORD")

    if not all([db_host, db_name, db_user, db_password]):
        print("Missing required accounting DB environment variables")
        return False

    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=10
        )
        conn.close()
        return True
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False
