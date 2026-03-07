"""Tests for should_summarize threshold function."""

import pytest
from datetime import datetime, UTC, timedelta

from src.cron.session_summarizer import should_summarize, ActiveSessionInfo
from src.session import SessionMeta


class TestShouldSummarizeIdleThreshold:
    """Test should_summarize with idle threshold."""

    def test_returns_true_when_idle_threshold_met(self):
        """Verify True when 30+ minutes since last message."""
        # Arrange
        last_active = datetime.now(UTC) - timedelta(minutes=35)  # 35 min ago
        session_info = ActiveSessionInfo(
            session_id="sess_test",
            message_count=10,
            last_message_time=last_active,
        )
        meta = SessionMeta(
            session_id="sess_test",
            created_at=datetime.now(UTC),
            last_active=last_active,
            status="active",
            current_count=10,
            last_summarized_count=0,
        )

        # Act
        result = should_summarize(session_info, meta)

        # Assert
        assert result is True
