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


class TestGenerateSessionSummaryReusesExistingId:
    """Test that generate_session_summary reuses existing summary ID."""

    @pytest.mark.asyncio
    async def test_reuses_existing_summary_id(self, tmp_path):
        """Verify existing summary ID is reused on regeneration."""
        # Arrange
        session_id = "sess_test789012"
        existing_summary_id = "sum_existing123"
        storage = MagicMock(spec=SessionStorage)
        
        # Mock messages
        storage.load_messages.return_value = [
            Message(idx=0, role=Role.USER, content="Question 1"),
            Message(idx=1, role=Role.ASSISTANT, content="Answer 1"),
            Message(idx=2, role=Role.USER, content="Question 2"),
        ]
        
        # Create existing summary to return
        existing_summary = SessionSummary(
            id=existing_summary_id,
            session_id=session_id,
            timestamp=datetime.now(UTC),
            message_range=(0, 2),
            message_count=2,
            summary_text="Old summary",
            embedding=[0.1, 0.2],
            version=1,
        )
        storage.get_summary = AsyncMock(return_value=existing_summary)
        storage.store_summary = AsyncMock()
        
        # Mock embedder
        mock_embedder = MagicMock()
        mock_embedder.embed = AsyncMock(return_value=[0.3, 0.4, 0.5])
        
        # Mock summarize_conversation
        with patch("src.llm.summarize_conversation") as mock_summarize:
            mock_summarize.return_value = "Updated summary with more messages"
            
            # Act
            summary = await generate_session_summary(session_id, storage, mock_embedder)
        
        # Assert
        assert summary.id == existing_summary_id
        storage.get_summary.assert_called_once_with(session_id)


class TestGenerateSessionSummarySetsCorrectMessageRange:
    """Test that generate_session_summary sets correct message range."""

    @pytest.mark.asyncio
    async def test_sets_full_message_range(self, tmp_path):
        """Verify message_range is (0, len(messages))."""
        # Arrange
        session_id = "sess_range_test"
        storage = MagicMock(spec=SessionStorage)
        
        # Create exactly 5 messages
        messages = [
            Message(idx=i, role=Role.USER if i % 2 == 0 else Role.ASSISTANT, content=f"Message {i}")
            for i in range(5)
        ]
        storage.load_messages.return_value = messages
        storage.get_summary = AsyncMock(return_value=None)
        storage.store_summary = AsyncMock()
        
        # Mock embedder
        mock_embedder = MagicMock()
        mock_embedder.embed = AsyncMock(return_value=[0.1, 0.2])
        
        # Mock summarize_conversation
        with patch("src.llm.summarize_conversation") as mock_summarize:
            mock_summarize.return_value = "Summary of 5 messages"
            
            # Act
            summary = await generate_session_summary(session_id, storage, mock_embedder)
        
        # Assert
        assert summary.message_range == (0, 5)
        assert summary.message_count == 5
