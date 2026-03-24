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

    # Query session store for sessions ready to compact
    # For now, just log that we ran
    print("Session TTL check completed")
''',
    ),
    "session_summarizer": (
        "*/5 * * * *",
        '''"""Summarize sessions: always do most recent 3 if changed, then threshold-based for rest."""

from datetime import datetime, UTC

from alfred.container import ServiceLocator
from alfred.session import SessionManager
from alfred.tools.search_sessions import SessionSummarizer

IDLE_THRESHOLD_MINUTES = 30
MESSAGE_THRESHOLD = 20
MAX_RECENT_SESSIONS = 3

async def run():
    """Summarize recent sessions always if changed, then threshold-based for rest."""
    print("Running session summarization job")

    try:
        # Get services from locator
        summarizer = ServiceLocator.resolve(SessionSummarizer)
        session_manager = ServiceLocator.resolve(SessionManager)

        sessions = session_manager.list_sessions()
        if not sessions:
            print("No sessions found")
            return

        # Sort by last_active (most recent first)
        sorted_sessions = sorted(sessions, key=lambda m: m.last_active or datetime.min.replace(tzinfo=UTC), reverse=True)

        summarized = 0
        for idx, meta in enumerate(sorted_sessions):
            messages_since_summary = meta.message_count - meta.last_summarized_count

            # Skip if no changes since last summary
            if messages_since_summary <= 0:
                continue

            # First 3 sessions: always summarize if changed
            if idx < MAX_RECENT_SESSIONS:
                should_summarize = True
            else:
                # Remaining sessions: use threshold-based logic
                minutes_idle = (datetime.now(UTC) - meta.last_active).total_seconds() / 60
                should_summarize = (
                    minutes_idle > IDLE_THRESHOLD_MINUTES or
                    messages_since_summary >= MESSAGE_THRESHOLD
                )

            if should_summarize:
                print(f"Summarizing session {meta.session_id}")
                session = session_manager.load_session(meta.session_id)
                if session and session.messages:
                    summary = await summarizer.generate_summary(session)
                    await summarizer.save_summary(summary)
                    print(f"Saved summary for session {meta.session_id}")
                    summarized += 1

        print(f"Session summarization complete: {summarized} sessions summarized")
    except Exception as e:
        print(f"Error in session summarization: {e}")
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
