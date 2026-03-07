"""Tests for summarize_sessions_job cron task."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cron.session_summarizer import ActiveSessionInfo, summarize_sessions_job
from src.session import SessionMeta, SessionSummary
from src.session_storage import SessionStorage


@pytest.mark.asyncio
async def test_summarize_sessions_job_calls_get_active_sessions() -> None:
    """Should scan for active sessions before summarizing."""
    config = MagicMock()
    config.session_summarize_idle_minutes = 30
    config.session_summarize_message_threshold = 20

    storage = MagicMock(spec=SessionStorage)
    embedder = MagicMock()

    with patch(
        "src.cron.session_summarizer.get_active_sessions",
        new=AsyncMock(return_value=[]),
    ) as mock_get_active:
        result = await summarize_sessions_job(config, storage, embedder)

    mock_get_active.assert_awaited_once_with(storage)
    assert result == 0


@pytest.mark.asyncio
async def test_summarize_sessions_job_updates_meta_for_eligible_sessions() -> None:
    """Should generate summaries and update SessionMeta for eligible sessions."""
    now = datetime.now(UTC)
    active_sessions = [
        ActiveSessionInfo(session_id="sess_one", message_count=10, last_message_time=now),
        ActiveSessionInfo(session_id="sess_two", message_count=5, last_message_time=now),
    ]

    meta_one = SessionMeta(
        session_id="sess_one",
        created_at=now,
        last_active=now,
        status="active",
        current_count=10,
        last_summarized_count=0,
        summary_version=0,
    )
    meta_two = SessionMeta(
        session_id="sess_two",
        created_at=now,
        last_active=now,
        status="active",
        current_count=5,
        last_summarized_count=0,
        summary_version=0,
    )

    summary = SessionSummary(
        id="sum_test",
        session_id="sess_one",
        timestamp=now,
        message_range=(0, 10),
        message_count=10,
        summary_text="Summary text",
        embedding=[0.1, 0.2],
        version=2,
    )

    config = MagicMock()
    config.session_summarize_idle_minutes = 30
    config.session_summarize_message_threshold = 20

    storage = MagicMock(spec=SessionStorage)
    storage.get_meta.side_effect = [meta_one, meta_two]
    storage.save_meta = MagicMock()

    embedder = MagicMock()

    with patch(
        "src.cron.session_summarizer.get_active_sessions",
        new=AsyncMock(return_value=active_sessions),
    ), patch(
        "src.cron.session_summarizer.should_summarize",
        side_effect=[True, False],
    ) as mock_should, patch(
        "src.cron.session_summarizer.generate_session_summary",
        new=AsyncMock(return_value=summary),
    ) as mock_generate:
        result = await summarize_sessions_job(config, storage, embedder)

    assert result == 1
    assert mock_should.call_count == 2
    mock_generate.assert_awaited_once_with("sess_one", storage, embedder)
    storage.save_meta.assert_called_once()

    saved_meta = storage.save_meta.call_args[0][0]
    assert saved_meta.last_summarized_count == summary.message_count
    assert saved_meta.summary_version == summary.version
