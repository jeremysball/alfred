"""Tests for Alfred tool call capturing (PRD #101)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent import ToolEnd, ToolOutput, ToolStart
from src.alfred import Alfred


class TestAlfredToolCallCapturing:
    """Test that Alfred captures tool calls during chat_stream."""

    @pytest.fixture
    def mock_alfred(self):
        """Create an Alfred instance with mocked dependencies."""
        with patch("src.alfred.LLMFactory"), \
             patch("src.alfred.EmbeddingClient") as mock_embedder_class, \
             patch("src.alfred.MemoryStore") as mock_memory_class, \
             patch("src.alfred.MemorySearcher"), \
             patch("src.alfred.ContextLoader") as mock_context_loader, \
             patch("src.alfred.CronScheduler"), \
             patch("src.alfred.SessionStorage"), \
             patch("src.alfred.SessionManager") as mock_session_manager_class:

            # Mock context loader
            mock_loader = MagicMock()
            mock_loader.assemble_with_search.return_value = ("system prompt", 5)
            mock_context_loader.return_value = mock_loader

            # Mock embedder with async embed method
            mock_embedder = MagicMock()
            mock_embedder.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
            mock_embedder_class.return_value = mock_embedder

            # Mock memory store with async get_all_entries
            mock_memory = MagicMock()
            mock_memory.get_all_entries = AsyncMock(return_value=[])
            mock_memory_class.return_value = mock_memory

            # Mock session manager
            mock_session_manager = MagicMock()
            mock_session_manager.get_or_create_session.return_value = MagicMock()
            mock_session_manager.get_current_cli_session.return_value = MagicMock()
            mock_session_manager.has_active_session.return_value = True
            mock_session_manager.get_session_messages.return_value = []
            mock_session_manager.add_message = MagicMock()
            mock_session_manager_class.get_instance.return_value = mock_session_manager
            mock_session_manager_class.initialize = MagicMock()

            # Mock config
            mock_config = MagicMock()
            mock_config.default_llm_provider = "test"
            mock_config.chat_model = "test-model"
            mock_config.data_dir = MagicMock()
            mock_config.telegram_bot_token = None

            alfred = Alfred(mock_config)

            # Set up the mocked session manager on the instance
            alfred.session_manager = mock_session_manager
            alfred.memory_store = mock_memory
            alfred.embedder = mock_embedder

            # Mock the agent's run_stream
            alfred.agent = MagicMock()

            return alfred

    def _setup_mock_session(self, mock_alfred):
        """Helper to set up a mock session that captures messages."""
        mock_session = MagicMock()
        mock_session.messages = []
        mock_session.meta = MagicMock()
        mock_session.meta.session_id = "test_session"
        mock_session.meta.last_active = datetime.now(UTC)
        mock_session.meta.current_count = 0
        mock_alfred.session_manager.get_current_cli_session.return_value = mock_session
        mock_alfred.session_manager._spawn_persist_task = MagicMock()
        return mock_session

    @pytest.mark.asyncio
    async def test_tool_calls_captured_and_attached_to_message(self, mock_alfred):
        """Test that tool calls are captured and attached to assistant message."""

        async def mock_run_stream(messages, system_prompt, usage_callback=None, tool_callback=None):
            """Mock agent that simulates streaming with tool calls."""
            # Simulate some text output
            yield "I'll check the files for you."

            # Simulate tool execution
            if tool_callback:
                # Tool starts
                tool_callback(ToolStart(
                    tool_call_id="call_abc123",
                    tool_name="bash",
                    arguments={"command": "ls /tmp"},
                ))

                # Tool output chunks
                tool_callback(ToolOutput(
                    tool_call_id="call_abc123",
                    tool_name="bash",
                    chunk="file1.txt\n",
                ))
                tool_callback(ToolOutput(
                    tool_call_id="call_abc123",
                    tool_name="bash",
                    chunk="file2.txt",
                ))

                # Tool ends
                tool_callback(ToolEnd(
                    tool_call_id="call_abc123",
                    tool_name="bash",
                    result="file1.txt\nfile2.txt",
                    is_error=False,
                ))

            # Continue with final response
            yield " I found 2 files."

        mock_alfred.agent.run_stream = mock_run_stream
        mock_session = self._setup_mock_session(mock_alfred)

        # Run chat_stream
        chunks = []
        async for chunk in mock_alfred.chat_stream("What files are in /tmp?"):
            chunks.append(chunk)

        # Verify chunks were yielded
        assert "".join(chunks) == "I'll check the files for you. I found 2 files."

        # Verify assistant message was added to session
        assert len(mock_session.messages) == 1
        assistant_msg = mock_session.messages[0]

        # Verify tool_calls were attached
        assert assistant_msg.tool_calls is not None
        assert len(assistant_msg.tool_calls) == 1

        tc = assistant_msg.tool_calls[0]
        assert tc.tool_call_id == "call_abc123"
        assert tc.tool_name == "bash"
        assert tc.arguments == {"command": "ls /tmp"}
        assert tc.output == "file1.txt\nfile2.txt"
        assert tc.status == "success"
        assert tc.insert_position == len("I'll check the files for you.")

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_sequenced(self, mock_alfred):
        """Test multiple tool calls with correct sequence ordering."""

        async def mock_run_stream(messages, system_prompt, usage_callback=None, tool_callback=None):
            """Mock agent with multiple tool calls."""
            yield "Checking files and directories."

            if tool_callback:
                # First tool
                tool_callback(ToolStart(
                    tool_call_id="call_1",
                    tool_name="bash",
                    arguments={"command": "ls /tmp"},
                ))
                tool_callback(ToolEnd(
                    tool_call_id="call_1",
                    tool_name="bash",
                    result="files...",
                    is_error=False,
                ))

                # Second tool
                tool_callback(ToolStart(
                    tool_call_id="call_2",
                    tool_name="read",
                    arguments={"path": "/tmp/file.txt"},
                ))
                tool_callback(ToolEnd(
                    tool_call_id="call_2",
                    tool_name="read",
                    result="content",
                    is_error=False,
                ))

            yield " Done."

        mock_alfred.agent.run_stream = mock_run_stream
        mock_session = self._setup_mock_session(mock_alfred)

        # Run chat_stream
        chunks = []
        async for chunk in mock_alfred.chat_stream("List files and read one"):
            chunks.append(chunk)

        # Verify tool calls
        assert len(mock_session.messages) == 1
        assistant_msg = mock_session.messages[0]

        assert assistant_msg.tool_calls is not None
        assert len(assistant_msg.tool_calls) == 2

        # Check sequence numbers
        assert assistant_msg.tool_calls[0].sequence == 0
        assert assistant_msg.tool_calls[1].sequence == 1

        # Both at same insert position
        insert_pos = len("Checking files and directories.")
        assert assistant_msg.tool_calls[0].insert_position == insert_pos
        assert assistant_msg.tool_calls[1].insert_position == insert_pos

    @pytest.mark.asyncio
    async def test_tool_call_with_error_status(self, mock_alfred):
        """Test that error tool calls are marked with error status."""

        async def mock_run_stream(messages, system_prompt, usage_callback=None, tool_callback=None):
            yield "Let me try that."

            if tool_callback:
                tool_callback(ToolStart(
                    tool_call_id="call_err",
                    tool_name="bash",
                    arguments={"command": "invalid_command"},
                ))
                # Tool output with error message
                tool_callback(ToolOutput(
                    tool_call_id="call_err",
                    tool_name="bash",
                    chunk="Error: command not found",
                ))
                tool_callback(ToolEnd(
                    tool_call_id="call_err",
                    tool_name="bash",
                    result="Error: command not found",
                    is_error=True,
                ))

            yield " That didn't work."

        mock_alfred.agent.run_stream = mock_run_stream
        mock_session = self._setup_mock_session(mock_alfred)

        chunks = []
        async for chunk in mock_alfred.chat_stream("Run invalid command"):
            chunks.append(chunk)

        assert len(mock_session.messages) == 1
        assistant_msg = mock_session.messages[0]

        assert assistant_msg.tool_calls is not None
        assert len(assistant_msg.tool_calls) == 1
        assert assistant_msg.tool_calls[0].status == "error"
        assert "Error" in assistant_msg.tool_calls[0].output

    @pytest.mark.asyncio
    async def test_no_tool_calls_when_none_used(self, mock_alfred):
        """Test that messages without tool calls have tool_calls=None."""

        async def mock_run_stream(messages, system_prompt, usage_callback=None, tool_callback=None):
            """Mock agent with no tool calls."""
            yield "I don't need any tools for this."

        mock_alfred.agent.run_stream = mock_run_stream
        mock_session = self._setup_mock_session(mock_alfred)

        chunks = []
        async for chunk in mock_alfred.chat_stream("Simple question"):
            chunks.append(chunk)

        assert len(mock_session.messages) == 1
        assistant_msg = mock_session.messages[0]

        assert assistant_msg.tool_calls is None

    @pytest.mark.asyncio
    async def test_external_tool_callback_still_called(self, mock_alfred):
        """Test that external tool_callback is still invoked."""
        external_calls = []

        def external_callback(event):
            external_calls.append(type(event).__name__)

        async def mock_run_stream(messages, system_prompt, usage_callback=None, tool_callback=None):
            yield "Testing."

            if tool_callback:
                tool_callback(ToolStart(
                    tool_call_id="call_test",
                    tool_name="bash",
                    arguments={"command": "test"},
                ))
                tool_callback(ToolEnd(
                    tool_call_id="call_test",
                    tool_name="bash",
                    result="result",
                    is_error=False,
                ))

        mock_alfred.agent.run_stream = mock_run_stream
        self._setup_mock_session(mock_alfred)

        chunks = []
        async for chunk in mock_alfred.chat_stream("Test", tool_callback=external_callback):
            chunks.append(chunk)

        # Verify external callback was called
        assert "ToolStart" in external_calls
        assert "ToolEnd" in external_calls
