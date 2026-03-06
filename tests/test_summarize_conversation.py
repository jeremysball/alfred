"""Tests for summarize_conversation LLM interface."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.llm import summarize_conversation
from src.session import Message, Role


class TestSummarizeConversationCallsLLM:
    """Test that summarize_conversation properly invokes LLM."""

    @pytest.mark.asyncio
    async def test_summarize_conversation_calls_llm_chat(self):
        """Verify that llm.chat is invoked with messages."""
        # Arrange
        messages = [
            Message(idx=0, role=Role.USER, content="Hello, how do I install Python?"),
            Message(idx=1, role=Role.ASSISTANT, content="You can download it from python.org"),
        ]

        mock_response = MagicMock()
        mock_response.content = "User asked about Python installation. Assistant recommended python.org."

        with patch("src.llm.LLMFactory.create") as mock_factory:
            mock_llm = MagicMock()
            mock_llm.chat = AsyncMock(return_value=mock_response)
            mock_factory.return_value = mock_llm

            # Act
            result = await summarize_conversation(messages)

            # Assert
            mock_llm.chat.assert_called_once()
            call_args = mock_llm.chat.call_args[0][0]  # First positional arg (messages list)
            assert len(call_args) == 2  # System prompt + user content
            assert call_args[0].role == "system"
            assert call_args[1].role == "user"
