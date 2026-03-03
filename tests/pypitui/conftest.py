"""Shared fixtures for PyPiTUI tests."""

from collections.abc import AsyncIterator
from unittest.mock import Mock

import pytest
from pypitui import MockTerminal

from src.alfred import Alfred


@pytest.fixture
def mock_terminal():
    """Create a MockTerminal for testing."""
    return MockTerminal()


@pytest.fixture
def mock_alfred():
    """Create a mock Alfred instance with async chat_stream."""
    from src.token_tracker import TokenTracker

    alfred = Mock(spec=Alfred)

    # Create an async generator for chat_stream
    async def async_chat_stream(*args, **kwargs) -> AsyncIterator[str]:
        chunks = ["Hello", " ", "world", "!"]
        for chunk in chunks:
            yield chunk

    alfred.chat_stream = async_chat_stream
    alfred.model_name = "test-model"
    alfred.token_tracker = Mock(spec=TokenTracker)
    alfred.token_tracker.usage = Mock()
    alfred.token_tracker.usage.input_tokens = 100
    alfred.token_tracker.usage.output_tokens = 50
    alfred.token_tracker.usage.cache_read_tokens = 0
    alfred.token_tracker.usage.reasoning_tokens = 0
    alfred.token_tracker.context_tokens = 0

    # Add mock notifier
    alfred.notifier = Mock()
    alfred.notifier.use_toasts = False

    # Add mock session_manager
    alfred.session_manager = Mock()
    alfred.session_manager.has_active_session = Mock(return_value=False)
    alfred.session_manager.get_current_cli_session = Mock(return_value=None)

    # Add mock config
    alfred.config = Mock()
    alfred.config.use_markdown_rendering = True

    return alfred
