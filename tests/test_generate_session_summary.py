"""Tests for generate_session_summary pipeline function."""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

from src.session import Message, Role, SessionSummary
from src.session_storage import SessionStorage, generate_session_summary


class TestGenerateSessionSummaryCreatesEmbedding:
    """Test that generate_session_summary creates embedding for summary."""

    @pytest.mark.asyncio
    async def test_generate_session_summary_creates_embedding(self, tmp_path):
        """Verify embedding is created and stored in SessionSummary."""
        # Arrange
        session_id = "sess_test123456"
        storage = MagicMock(spec=SessionStorage)
        
        # Mock messages returned by storage
        storage.load_messages.return_value = [
            Message(idx=0, role=Role.USER, content="Hello, how do I install Python?"),
            Message(idx=1, role=Role.ASSISTANT, content="You can download it from python.org"),
        ]
        storage.get_summary = AsyncMock(return_value=None)  # No existing summary
        storage.store_summary = AsyncMock()  # Mock store
        
        # Mock embedder
        mock_embedder = MagicMock()
        mock_embedder.embed = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])
        
        # Mock summarize_conversation (imported inside function from src.llm)
        with patch("src.llm.summarize_conversation") as mock_summarize:
            mock_summarize.return_value = "User asked about Python installation"
            
            # Act
            summary = await generate_session_summary(session_id, storage, mock_embedder)
        
        # Assert
        mock_embedder.embed.assert_called_once_with("User asked about Python installation")
        assert summary.embedding == [0.1, 0.2, 0.3, 0.4]
        assert isinstance(summary, SessionSummary)
