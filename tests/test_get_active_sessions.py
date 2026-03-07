"""Tests for get_active_sessions function."""

import pytest
from datetime import datetime, UTC
from unittest.mock import MagicMock

from src.session_storage import SessionStorage
from src.cron.session_summarizer import get_active_sessions, ActiveSessionInfo
from src.session import SessionMeta


class TestGetActiveSessionsReturnsActiveOnly:
    """Test that get_active_sessions filters to active sessions only."""

    @pytest.mark.asyncio
    async def test_returns_only_active_sessions(self):
        """Verify only sessions with status='active' are returned."""
        # Arrange
        storage = MagicMock(spec=SessionStorage)
        
        # Mock list_sessions to return multiple session IDs
        storage.list_sessions.return_value = [
            "sess_active1",
            "sess_archived",
            "sess_active2",
        ]
        
        # Mock get_meta to return different statuses
        storage.get_meta.side_effect = lambda sid: {
            "sess_active1": SessionMeta(
                session_id="sess_active1",
                created_at=datetime.now(UTC),
                last_active=datetime.now(UTC),
                status="active",
                current_count=5,
            ),
            "sess_archived": SessionMeta(
                session_id="sess_archived",
                created_at=datetime.now(UTC),
                last_active=datetime.now(UTC),
                status="archived",
                current_count=3,
            ),
            "sess_active2": SessionMeta(
                session_id="sess_active2",
                created_at=datetime.now(UTC),
                last_active=datetime.now(UTC),
                status="active",
                current_count=8,
            ),
        }.get(sid)
        
        # Act
        result = await get_active_sessions(storage)
        
        # Assert
        assert len(result) == 2
        session_ids = [info.session_id for info in result]
        assert "sess_active1" in session_ids
        assert "sess_active2" in session_ids
        assert "sess_archived" not in session_ids


class TestGetActiveSessionsIncludesMessageCounts:
    """Test that get_active_sessions includes message counts and timestamps."""

    @pytest.mark.asyncio
    async def test_includes_message_count_and_last_active(self):
        """Verify message_count and last_message_time are populated correctly."""
        # Arrange
        storage = MagicMock(spec=SessionStorage)
        
        # Create specific timestamps
        last_active_1 = datetime(2026, 3, 6, 14, 30, 0, tzinfo=UTC)
        last_active_2 = datetime(2026, 3, 6, 15, 45, 0, tzinfo=UTC)
        
        storage.list_sessions.return_value = [
            "sess_with_msgs",
            "sess_empty",
        ]
        
        storage.get_meta.side_effect = lambda sid: {
            "sess_with_msgs": SessionMeta(
                session_id="sess_with_msgs",
                created_at=datetime.now(UTC),
                last_active=last_active_1,
                status="active",
                current_count=42,
                archive_count=0,
            ),
            "sess_empty": SessionMeta(
                session_id="sess_empty",
                created_at=datetime.now(UTC),
                last_active=last_active_2,
                status="active",
                current_count=0,
                archive_count=0,
            ),
        }.get(sid)
        
        # Act
        result = await get_active_sessions(storage)
        
        # Assert
        assert len(result) == 2
        
        # Find sessions by ID
        by_id = {info.session_id: info for info in result}
        
        assert by_id["sess_with_msgs"].message_count == 42
        assert by_id["sess_with_msgs"].last_message_time == last_active_1
        
        assert by_id["sess_empty"].message_count == 0
        assert by_id["sess_empty"].last_message_time == last_active_2
