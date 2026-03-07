"""Session summarization cron job logic (PRD #76).

Handles detection of sessions needing summarization and orchestration
of summary generation.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from src.embeddings.provider import EmbeddingProvider
from src.session import SessionMeta
from src.session_storage import SessionStorage, generate_session_summary

if TYPE_CHECKING:
    from src.config import Config

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


def should_summarize(
    session_info: ActiveSessionInfo,
    meta: SessionMeta,
    idle_threshold_minutes: int = 30,
    message_threshold: int = 20,
) -> bool:
    """Determine if a session should be summarized.

    Args:
        session_info: ActiveSessionInfo with message_count and last_message_time
        meta: SessionMeta with last_summarized_count
        idle_threshold_minutes: Minutes of inactivity before summarization
        message_threshold: New messages threshold for summarization

    Returns:
        True if either idle or message threshold is met
    """
    logger.debug(
        "Evaluating should_summarize for %s: msgs=%s, last_summary=%s",
        session_info.session_id,
        session_info.message_count,
        meta.last_summarized_count,
    )

    idle_met = False
    if session_info.last_message_time is None:
        logger.debug("Session %s has no last_message_time", session_info.session_id)
    else:
        idle_duration = datetime.now(UTC) - session_info.last_message_time
        idle_met = idle_duration >= timedelta(minutes=idle_threshold_minutes)
        logger.debug(
            "Session %s idle duration %s min (threshold %s)",
            session_info.session_id,
            idle_duration.total_seconds() / 60,
            idle_threshold_minutes,
        )

    new_messages = session_info.message_count - meta.last_summarized_count
    if new_messages < 0:
        logger.warning(
            "Session %s has negative new_messages (%s), clamping to 0",
            session_info.session_id,
            new_messages,
        )
        new_messages = 0

    message_met = new_messages >= message_threshold
    logger.debug(
        "Session %s new messages %s (threshold %s)",
        session_info.session_id,
        new_messages,
        message_threshold,
    )

    should = idle_met or message_met
    logger.debug("Session %s should_summarize=%s", session_info.session_id, should)
    return should


async def summarize_sessions_job(
    config: "Config",
    storage: SessionStorage,
    embedder: EmbeddingProvider,
) -> int:
    """Cron job: summarize sessions that meet threshold criteria.

    Args:
        config: Application configuration with session thresholds
        storage: SessionStorage instance for session access
        embedder: Embedding provider for summary embeddings

    Returns:
        Number of session summaries generated
    """
    logger.debug("summarize_sessions_job started")

    idle_minutes = getattr(config, "session_summarize_idle_minutes", 30)
    message_threshold = getattr(config, "session_summarize_message_threshold", 20)

    if not isinstance(idle_minutes, int) or idle_minutes <= 0:
        logger.warning("Invalid session_summarize_idle_minutes=%s, using default", idle_minutes)
        idle_minutes = 30

    if not isinstance(message_threshold, int) or message_threshold <= 0:
        logger.warning(
            "Invalid session_summarize_message_threshold=%s, using default",
            message_threshold,
        )
        message_threshold = 20

    active_sessions = await get_active_sessions(storage)
    summaries_created = 0

    for session_info in active_sessions:
        meta = storage.get_meta(session_info.session_id)
        if meta is None:
            logger.warning("No metadata found for session %s, skipping", session_info.session_id)
            continue

        if not should_summarize(
            session_info,
            meta,
            idle_threshold_minutes=idle_minutes,
            message_threshold=message_threshold,
        ):
            continue

        try:
            summary = await generate_session_summary(
                session_info.session_id,
                storage,
                embedder,
            )
        except Exception as exc:
            logger.warning("Failed to summarize session %s: %s", session_info.session_id, exc)
            continue

        meta.last_summarized_count = summary.message_count
        meta.summary_version = summary.version
        storage.save_meta(meta)
        summaries_created += 1

    logger.debug("summarize_sessions_job completed: %s summaries", summaries_created)
    return summaries_created
