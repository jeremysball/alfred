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


class TestShouldSummarizeMessageThreshold:
    """Test should_summarize with message threshold."""

    def test_returns_true_when_message_threshold_met(self):
        """Verify True when 20+ new messages since last summary."""
        # Arrange
        last_active = datetime.now(UTC) - timedelta(minutes=5)
        session_info = ActiveSessionInfo(
            session_id="sess_msgs",
            message_count=30,
            last_message_time=last_active,
        )
        meta = SessionMeta(
            session_id="sess_msgs",
            created_at=datetime.now(UTC),
            last_active=last_active,
            status="active",
            current_count=30,
            last_summarized_count=5,
        )

        # Act
        result = should_summarize(session_info, meta)

        # Assert
        assert result is True


class TestShouldSummarizeBelowThresholds:
    """Test should_summarize when thresholds are not met."""

    def test_returns_false_when_below_thresholds(self):
        """Verify False when idle and message thresholds are not met."""
        # Arrange
        last_active = datetime.now(UTC) - timedelta(minutes=10)
        session_info = ActiveSessionInfo(
            session_id="sess_low",
            message_count=12,
            last_message_time=last_active,
        )
        meta = SessionMeta(
            session_id="sess_low",
            created_at=datetime.now(UTC),
            last_active=last_active,
            status="active",
            current_count=12,
            last_summarized_count=8,
        )

        # Act
        result = should_summarize(session_info, meta)

        # Assert
        assert result is False
