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
