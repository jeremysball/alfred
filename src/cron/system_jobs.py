"""System jobs for cron scheduler.

Pre-built jobs that run without human approval.
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class JobContext:
    """Context passed to job handlers."""

    memory_store: Any | None = None
    session_store: Any | None = None
    alfred: Any | None = None


# System job definitions: name -> (cron_expression, code)
SYSTEM_JOBS: dict[str, tuple[str, str]] = {
    "session_ttl": (
        "*/5 * * * *",
        '''"""Check for sessions ready to compact."""

async def run():
    """Check sessions and trigger compaction for those ready."""
    print("Running session TTL check")

    # TODO: Query session store for sessions ready to compact
    # For now, just log that we ran
    print("Session TTL check completed")
''',
    ),
}


def get_system_job_code(job_id: str) -> tuple[str, str] | None:
    """Get the cron expression and code for a system job.

    Args:
        job_id: System job identifier (e.g., "session_ttl")

    Returns:
        Tuple of (cron_expression, code) or None if not found
    """
    return SYSTEM_JOBS.get(job_id)


def list_system_jobs() -> list[str]:
    """List available system job IDs."""
    return list(SYSTEM_JOBS.keys())
