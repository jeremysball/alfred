"""System jobs for cron scheduler.

Pre-built jobs that run without human approval.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from src.cron.models import Job

logger = logging.getLogger(__name__)

SYSTEM_JOB_CODE_TEMPLATE = "# system job: {handler_id}"


@dataclass(frozen=True)
class SystemJobDefinition:
    """Definition for a built-in system job."""

    job_id: str
    name: str
    expression: str
    handler_id: str
    handler: Callable[[], Awaitable[None]]

    def to_job(self) -> Job:
        """Create Job model for persistence."""
        return Job(
            job_id=self.job_id,
            name=self.name,
            expression=self.expression,
            code=SYSTEM_JOB_CODE_TEMPLATE.format(handler_id=self.handler_id),
            status="active",
            handler_id=self.handler_id,
        )


async def _session_ttl_job() -> None:
    """Check sessions and trigger compaction for those ready."""
    logger.info("Running session TTL check")

    # TODO: Query session store for sessions ready to compact
    # For now, just log that we ran
    logger.info("Session TTL check completed")


async def _session_summarizer_job() -> None:
    """Summarize sessions that meet idle or message thresholds."""
    from src.config import load_config
    from src.cron.session_summarizer import summarize_sessions_job
    from src.embeddings import create_provider
    from src.session_storage import SessionStorage

    config = load_config()
    embedder = create_provider(config)
    storage = SessionStorage(embedder, data_dir=config.data_dir)

    await summarize_sessions_job(config, storage, embedder)


SYSTEM_JOBS: dict[str, SystemJobDefinition] = {
    "session_ttl": SystemJobDefinition(
        job_id="session_ttl",
        name="Session Ttl",
        expression="*/5 * * * *",
        handler_id="session_ttl",
        handler=_session_ttl_job,
    ),
    "session_summarizer": SystemJobDefinition(
        job_id="session_summarizer",
        name="Session Summarizer",
        expression="*/5 * * * *",
        handler_id="session_summarizer",
        handler=_session_summarizer_job,
    ),
}


def get_system_job(job_id: str) -> SystemJobDefinition | None:
    """Get a system job definition.

    Args:
        job_id: System job identifier (e.g., "session_ttl")

    Returns:
        SystemJobDefinition or None if not found
    """
    return SYSTEM_JOBS.get(job_id)


def get_system_job_handler(handler_id: str) -> Callable[[], Awaitable[None]] | None:
    """Get handler for system job by handler_id."""
    job = SYSTEM_JOBS.get(handler_id)
    return job.handler if job else None


def list_system_jobs() -> list[str]:
    """List available system job IDs."""
    return list(SYSTEM_JOBS.keys())
