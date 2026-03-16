"""Tests for KimiProvider stream_chat_with_tools refactoring."""

from unittest.mock import MagicMock, patch

import pytest

from alfred.config import Config
from alfred.llm import ChatMessage, KimiProvider


class TestConvertMessagesToApiFormat:
    """Tests for _convert_messages_to_api_format method."""

    def test_convert_simple_message(self):
        """Test converting a simple user message."""
        from alfred.config import Config
        config = Config(kimi_api_key="test-key", chat_model="kimi-test")
        provider = KimiProvider(config)
        messages = [ChatMessage(role="user", content="Hello")]

        result = provider._convert_messages_to_api_format(messages)

        assert result == [{"role": "user", "content": "Hello"}]

    def test_convert_tool_message_with_id(self):
        """Test converting a tool message with tool_call_id."""
        from alfred.config import Config
        config = Config(kimi_api_key="test-key", chat_model="kimi-test")
        provider = KimiProvider(config)
        messages = [
            ChatMessage(role="tool", content="Result", tool_call_id="call_123")
        ]

        result = provider._convert_messages_to_api_format(messages)

        assert result == [
            {"role": "tool", "content": "Result", "tool_call_id": "call_123"}
        ]

    def test_convert_assistant_with_tool_calls(self):
        """Test converting assistant message with tool_calls."""
        from alfred.config import Config
        config = Config(kimi_api_key="test-key", chat_model="kimi-test")
        provider = KimiProvider(config)
        tool_calls = [{"id": "call_1", "type": "function"}]
        messages = [
            ChatMessage(role="assistant", content="Using tool", tool_calls=tool_calls)
        ]

        result = provider._convert_messages_to_api_format(messages)

        assert result == [
            {
                "role": "assistant",
                "content": "Using tool",
                "tool_calls": tool_calls,
            }
        ]

    def test_convert_assistant_with_reasoning(self):
        """Test converting assistant message with reasoning_content."""
        from alfred.config import Config
        config = Config(kimi_api_key="test-key", chat_model="kimi-test")
        provider = KimiProvider(config)
        messages = [
            ChatMessage(
                role="assistant",
                content="Answer",
                reasoning_content="Let me think...",
            )
        ]

        result = provider._convert_messages_to_api_format(messages)

        assert result == [
            {
                "role": "assistant",
                "content": "Answer",
                "reasoning_content": "Let me think...",
            }
        ]

    def test_convert_multiple_messages(self):
        """Test converting multiple messages of different types."""
        from alfred.config import Config
        config = Config(kimi_api_key="test-key", chat_model="kimi-test")
        provider = KimiProvider(config)
        messages = [
            ChatMessage(role="system", content="You are helpful"),
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi"),
        ]

        result = provider._convert_messages_to_api_format(messages)

        assert len(result) == 3
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        assert result[2]["role"] == "assistant"


class TestExtractUsageData:
    """Tests for _extract_usage_data method."""

    def _create_provider(self):
        from alfred.config import Config
        config = Config(kimi_api_key="test-key", chat_model="kimi-test")
        return KimiProvider(config)

    def test_basic_usage_data(self):
        """Test extracting basic usage data."""
        provider = self._create_provider()

        usage = MagicMock()
        usage.prompt_tokens = 100
        usage.completion_tokens = 50
        usage.prompt_tokens_details = None
        usage.completion_tokens_details = None

        result = provider._extract_usage_data(usage, "", None)

        assert result["prompt_tokens"] == 100
        assert result["completion_tokens"] == 50

    def test_usage_with_cached_tokens(self):
        """Test extracting usage with cached tokens."""
        provider = self._create_provider()

        usage = MagicMock()
        usage.prompt_tokens = 100
        usage.completion_tokens = 50
        usage.prompt_tokens_details = MagicMock()
        usage.prompt_tokens_details.cached_tokens = 20
        usage.completion_tokens_details = None

        result = provider._extract_usage_data(usage, "", None)

        assert result["prompt_tokens_details"]["cached_tokens"] == 20

    def test_usage_with_reasoning_from_api(self):
        """Test extracting usage when API provides reasoning tokens."""
        provider = self._create_provider()

        usage = MagicMock()
        usage.prompt_tokens = 100
        usage.completion_tokens = 50
        usage.prompt_tokens_details = None
        usage.completion_tokens_details = MagicMock()
        usage.completion_tokens_details.reasoning_tokens = 15

        result = provider._extract_usage_data(usage, "", None)

        assert result["completion_tokens_details"]["reasoning_tokens"] == 15

    @patch("tiktoken.get_encoding")
    def test_usage_with_fallback_reasoning_counting(self, mock_get_encoding):
        """Test fallback to manual reasoning token counting."""
        provider = self._create_provider()

        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens
        mock_get_encoding.return_value = mock_encoder

        usage = MagicMock()
        usage.prompt_tokens = 100
        usage.completion_tokens = 50
        usage.prompt_tokens_details = None
        usage.completion_tokens_details = None

        result = provider._extract_usage_data(usage, "some reasoning text", mock_encoder)

        assert result["completion_tokens_details"]["reasoning_tokens"] == 5


class TestAccumulateToolCalls:
    """Tests for _accumulate_tool_calls method."""

    def _create_provider(self):
        from alfred.config import Config
        config = Config(kimi_api_key="test-key", chat_model="kimi-test")
        return KimiProvider(config)

    def test_new_tool_call_with_id(self):
        """Test accumulating a new tool call when ID is present."""
        provider = self._create_provider()
        state = {"tool_calls_data": [], "current_tool_call": None}

        tc = MagicMock()
        tc.id = "call_123"
        tc.function = MagicMock()
        tc.function.name = "read_file"
        tc.function.arguments = None

        provider._accumulate_tool_calls([tc], state)

        assert len(state["tool_calls_data"]) == 1
        assert state["tool_calls_data"][0]["id"] == "call_123"
        assert state["tool_calls_data"][0]["function"]["name"] == "read_file"

    def test_accumulate_arguments_without_id(self):
        """Test accumulating arguments for existing tool call."""
        provider = self._create_provider()
        state = {
            "tool_calls_data": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": ""},
                }
            ],
            "current_tool_call": {
                "id": "call_123",
                "type": "function",
                "function": {"name": "read_file", "arguments": ""},
            },
        }

        tc = MagicMock()
        tc.id = None  # No ID means continue previous tool call
        tc.function = MagicMock()
        tc.function.name = None
        tc.function.arguments = '{"path": "test.txt"}'

        provider._accumulate_tool_calls([tc], state)

        assert state["current_tool_call"]["function"]["arguments"] == '{"path": "test.txt"}'

    def test_accumulate_partial_arguments(self):
        """Test accumulating partial arguments over multiple chunks."""
        provider = self._create_provider()
        state = {
            "tool_calls_data": [],
            "current_tool_call": None,
        }

        # First chunk - new tool call
        tc1 = MagicMock()
        tc1.id = "call_123"
        tc1.function = MagicMock()
        tc1.function.name = "read_file"
        tc1.function.arguments = '{"path": "'

        provider._accumulate_tool_calls([tc1], state)

        # Second chunk - continue arguments
        tc2 = MagicMock()
        tc2.id = None
        tc2.function = MagicMock()
        tc2.function.name = None
        tc2.function.arguments = 'test.txt"}'

        provider._accumulate_tool_calls([tc2], state)

        assert state["current_tool_call"]["function"]["arguments"] == '{"path": "test.txt"}'


class TestProcessStreamChunk:
    """Tests for _process_stream_chunk method."""

    def test_usage_chunk_without_choices(self):
        """Test processing usage chunk with no choices."""
        provider = KimiProvider(Config(kimi_api_key="test-key", chat_model="kimi-test"))

        chunk = MagicMock()
        chunk.choices = []
        chunk.usage = MagicMock()
        chunk.usage.prompt_tokens = 100
        chunk.usage.completion_tokens = 50
        chunk.usage.prompt_tokens_details = None
        chunk.usage.completion_tokens_details = None

        state = {
            "tool_calls_data": [],
            "current_tool_call": None,
            "full_content": "",
            "full_reasoning": "",
        }

        results = list(provider._process_stream_chunk(chunk, state, None))

        assert len(results) == 1
        assert results[0].startswith("[USAGE]")

    def test_content_chunk(self):
        """Test processing content chunk."""
        provider = KimiProvider(Config(kimi_api_key="test-key", chat_model="kimi-test"))

        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta = MagicMock()
        chunk.choices[0].delta.content = "Hello"
        chunk.choices[0].delta.reasoning_content = None
        chunk.choices[0].delta.tool_calls = None

        state = {
            "tool_calls_data": [],
            "current_tool_call": None,
            "full_content": "",
            "full_reasoning": "",
        }

        results = list(provider._process_stream_chunk(chunk, state, None))

        assert results == ["Hello"]
        assert state["full_content"] == "Hello"

    def test_reasoning_content_chunk(self):
        """Test processing reasoning content chunk."""
        provider = KimiProvider(Config(kimi_api_key="test-key", chat_model="kimi-test"))

        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta = MagicMock()
        chunk.choices[0].delta.content = None
        chunk.choices[0].delta.reasoning_content = "Let me think..."
        chunk.choices[0].delta.tool_calls = None

        state = {
            "tool_calls_data": [],
            "current_tool_call": None,
            "full_content": "",
            "full_reasoning": "",
        }

        results = list(provider._process_stream_chunk(chunk, state, None))

        assert len(results) == 1
        assert results[0].startswith("[REASONING]")
        assert "Let me think..." in results[0]
        assert state["full_reasoning"] == "Let me think..."

    def test_tool_calls_chunk(self):
        """Test processing tool calls chunk."""
        provider = KimiProvider(Config(kimi_api_key="test-key", chat_model="kimi-test"))

        tc = MagicMock()
        tc.id = "call_123"
        tc.function = MagicMock()
        tc.function.name = "read_file"
        tc.function.arguments = None

        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta = MagicMock()
        chunk.choices[0].delta.content = None
        chunk.choices[0].delta.reasoning_content = None
        chunk.choices[0].delta.tool_calls = [tc]

        state = {
            "tool_calls_data": [],
            "current_tool_call": None,
            "full_content": "",
            "full_reasoning": "",
        }

        results = list(provider._process_stream_chunk(chunk, state, None))

        # Tool calls don't yield output immediately, just accumulate
        assert results == []
        assert len(state["tool_calls_data"]) == 1


class TestKimiProviderIntegration:
    """Integration tests for KimiProvider."""

    @patch("alfred.llm._retry_async")
    @patch("openai.AsyncOpenAI")
    async def test_stream_chat_with_tools_success(self, mock_client_class, mock_retry):
        """Test successful streaming with tool calls."""
        provider = KimiProvider(Config(kimi_api_key="test-key", chat_model="kimi-test"))

        # Mock the stream
        mock_stream = MagicMock()
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta.content = "Let me check"
        mock_chunk1.choices[0].delta.reasoning_content = None
        mock_chunk1.choices[0].delta.tool_calls = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = []
        mock_chunk2.usage = MagicMock()
        mock_chunk2.usage.prompt_tokens = 100
        mock_chunk2.usage.completion_tokens = 50
        mock_chunk2.usage.prompt_tokens_details = None
        mock_chunk2.usage.completion_tokens_details = None

        mock_stream.__aiter__ = MagicMock(return_value=iter([mock_chunk1, mock_chunk2]))
        mock_retry.return_value = mock_stream

        messages = [ChatMessage(role="user", content="Read a file")]
        results = []
        async for chunk in provider.stream_chat_with_tools(messages, tools=None):
            results.append(chunk)

        assert "Let me check" in results
        assert any("[USAGE]" in r for r in results)
