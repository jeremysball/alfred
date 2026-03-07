"""Session summarization cron job logic (PRD #76).

Handles detection of sessions needing summarization and orchestration
of summary generation.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.session import SessionMeta
from src.session_storage import SessionStorage

logger = logging.getLogger(__name__)


@dataclass
class ActiveSessionInfo:
    """Information about an active session for cron processing."""

    session_id: str
    message_count: int
    last_message_time: datetime | None


async def get_active_sessions(storage: SessionStorage) -> list[ActiveSessionInfo]:
    """Scan sessions directory and return active sessions with metadata.

    Filters to only sessions with status="active" and includes message
    count and last activity time for threshold checking.

    Args:
        storage: SessionStorage instance for accessing sessions

    Returns:
        List of ActiveSessionInfo for active sessions only
    """
    logger.debug("Scanning for active sessions")

    session_ids = storage.list_sessions()
    logger.debug(f"Found {len(session_ids)} total sessions")

    active_sessions: list[ActiveSessionInfo] = []

    for session_id in session_ids:
        try:
            meta = storage.get_meta(session_id)
            if meta is None:
                logger.warning(f"No metadata found for session {session_id}, skipping")
                continue

            if meta.status != "active":
                logger.debug(f"Session {session_id} status={meta.status}, skipping")
                continue

            active_sessions.append(
                ActiveSessionInfo(
                    session_id=session_id,
                    message_count=meta.message_count,
                    last_message_time=meta.last_active,
                )
            )
            logger.debug(f"Added active session {session_id}: {meta.message_count} msgs")

        except Exception as e:
            logger.warning(f"Error loading metadata for session {session_id}: {e}")
            continue

    logger.debug(f"Found {len(active_sessions)} active sessions")
    return active_sessions
