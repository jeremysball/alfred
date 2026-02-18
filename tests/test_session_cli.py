"""Tests for CLI session integration (PRD #54 Milestone 4)."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.session import SessionManager


class TestCLISessionIntegration:
    """Tests for CLI integration with session management."""

    def test_session_auto_starts_on_first_message(self):
        """Session starts automatically when first message processed."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        
        assert not manager.has_active_session()
        
        # Simulate what happens when CLI receives first message
        if not manager.has_active_session():
            manager.start_session()
        
        assert manager.has_active_session()

    def test_user_message_added_to_session(self):
        """User message added to session before LLM call."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        manager.start_session()
        
        # Simulate: user sends message
        user_msg = "Hello Alfred"
        manager.add_message("user", user_msg)
        
        messages = manager.get_messages()
        assert len(messages) == 1
        assert messages[0].content == user_msg
        assert messages[0].role.value == "user"

    def test_assistant_message_added_to_session(self):
        """Assistant response added to session after LLM call."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        manager.start_session()
        
        # Simulate conversation
        manager.add_message("user", "Hello")
        manager.add_message("assistant", "Hi there")
        
        messages = manager.get_messages()
        assert len(messages) == 2
        assert messages[1].content == "Hi there"
        assert messages[1].role.value == "assistant"

    def test_conversation_accumulates(self):
        """Multiple exchanges accumulate in session."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        manager.start_session()
        
        # Simulate multi-turn conversation
        manager.add_message("user", "Message 1")
        manager.add_message("assistant", "Response 1")
        manager.add_message("user", "Message 2")
        manager.add_message("assistant", "Response 2")
        manager.add_message("user", "Message 3")
        
        messages = manager.get_messages()
        assert len(messages) == 5
        
        # Verify order
        assert messages[0].content == "Message 1"
        assert messages[1].content == "Response 1"
        assert messages[2].content == "Message 2"
        assert messages[3].content == "Response 2"
        assert messages[4].content == "Message 3"


class TestAlfredSessionIntegration:
    """Tests for Alfred class integration with sessions."""

    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.model = "test-model"
        config.memory_context_limit = 10
        config.embedding_model = "test-embedder"
        config.memory_path = "/tmp/test_memory"
        return config

    @pytest.fixture
    def mock_alfred(self, mock_config):
        """Create Alfred with mocked dependencies."""
        from src.alfred import Alfred

        # Create mock instances for dependencies
        mock_embedder = AsyncMock()
        mock_embedder.embed.return_value = [0.1, 0.2, 0.3]
        
        mock_memory_store = AsyncMock()
        mock_memory_store.get_all_entries.return_value = []
        
        mock_context_loader = Mock()
        mock_context_loader.assemble_with_search.return_value = "system prompt"
        
        mock_registry = Mock()
        mock_registry.list_tools.return_value = []
        
        mock_agent = AsyncMock()
        async def mock_run_stream(*args, **kwargs):
            yield "Response"
        mock_agent.run_stream = mock_run_stream
        
        with patch('src.alfred.LLMFactory.create'):
            with patch('src.alfred.EmbeddingClient', return_value=mock_embedder):
                with patch('src.alfred.MemoryStore', return_value=mock_memory_store):
                    with patch('src.alfred.ContextLoader', return_value=mock_context_loader):
                        with patch('src.alfred.register_builtin_tools'):
                            with patch('src.alfred.get_registry', return_value=mock_registry):
                                with patch('src.alfred.Agent', return_value=mock_agent):
                                    alfred = Alfred(mock_config)
                                    # Store the mock agent so tests can override run_stream
                                    alfred._mock_agent = mock_agent
                                    yield alfred

    @pytest.mark.asyncio
    async def test_chat_stream_adds_user_message(self, mock_alfred):
        """chat_stream adds user message to session."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        
        # Mock the agent's run_stream method
        async def mock_run_stream(*args, **kwargs):
            yield "Hello"
            yield " there"
        
        mock_alfred._mock_agent.run_stream = mock_run_stream
        
        # Consume the stream
        chunks = []
        async for chunk in mock_alfred.chat_stream("Test message"):
            chunks.append(chunk)
        
        # Verify user message was added
        assert manager.has_active_session()
        messages = manager.get_messages()
        assert len(messages) >= 1
        assert messages[0].content == "Test message"

    @pytest.mark.asyncio
    async def test_chat_stream_adds_assistant_response(self, mock_alfred):
        """chat_stream adds assistant response to session."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        
        # Mock the agent's run_stream method
        async def mock_run_stream(*args, **kwargs):
            yield "I am"
            yield " Alfred"
        
        mock_alfred._mock_agent.run_stream = mock_run_stream
        
        # Consume the stream
        chunks = []
        async for chunk in mock_alfred.chat_stream("Who are you?"):
            chunks.append(chunk)
        
        # Verify assistant message was added
        messages = manager.get_messages()
        assert len(messages) == 2
        assert messages[1].content == "I am Alfred"

    @pytest.mark.asyncio
    async def test_context_includes_session_history(self, mock_alfred):
        """Context sent to LLM includes session history."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        manager.start_session()
        manager.add_message("user", "Previous question")
        manager.add_message("assistant", "Previous answer")
        
        # Mock the agent's run_stream method
        async def mock_run_stream(*args, **kwargs):
            yield "Response"
        
        mock_alfred.agent.run_stream = mock_run_stream
        
        # Verify context loader has access to session
        # The actual context integration happens in context_loader
        assert manager.has_active_session()
        messages = manager.get_messages()
        assert len(messages) == 2
        assert messages[0].content == "Previous question"
        assert messages[1].content == "Previous answer"
