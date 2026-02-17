"""Tests for LLM provider (non-API tests only)."""

import asyncio

import pytest

from src.llm import (
    APIError,
    ChatMessage,
    ChatResponse,
    KimiProvider,
    LLMError,
    LLMFactory,
    RateLimitError,
    TimeoutError,
    retry_with_backoff,
)
from src.config import Config


# Fixtures
@pytest.fixture
def sample_config():
    """Create a sample config for testing."""
    # This config won't be used for real API calls
    return Config(
        telegram_bot_token="test_token",
        openai_api_key="test_openai_key",
        kimi_api_key="test_kimi_key",
        kimi_base_url="https://api.moonshot.cn/v1",
        default_llm_provider="kimi",
        embedding_model="text-embedding-3-small",
        chat_model="kimi-k2-5",
        memory_context_limit=20,
        memory_dir="memory",
        context_files={},
    )


@pytest.fixture
def sample_messages():
    """Create sample chat messages."""
    return [
        ChatMessage(role="system", content="You are Alfred."),
        ChatMessage(role="user", content="Hello!"),
    ]


# Tests for dataclasses
class TestChatMessage:
    """Test ChatMessage dataclass."""

    def test_creation(self):
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_system_message(self):
        msg = ChatMessage(role="system", content="You are helpful.")
        assert msg.role == "system"
        assert msg.content == "You are helpful."

    def test_assistant_message(self):
        msg = ChatMessage(role="assistant", content="I can help!")
        assert msg.role == "assistant"
        assert msg.content == "I can help!"


class TestChatResponse:
    """Test ChatResponse dataclass."""

    def test_creation_minimal(self):
        resp = ChatResponse(content="Hi!", model="kimi-k2-5")
        assert resp.content == "Hi!"
        assert resp.model == "kimi-k2-5"
        assert resp.usage is None

    def test_creation_with_usage(self):
        resp = ChatResponse(
            content="Hello",
            model="kimi-k2-5",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )
        assert resp.content == "Hello"
        assert resp.model == "kimi-k2-5"
        assert resp.usage["prompt_tokens"] == 10
        assert resp.usage["completion_tokens"] == 5

    def test_creation_empty_content(self):
        resp = ChatResponse(content="", model="kimi-k2-5")
        assert resp.content == ""
        assert resp.model == "kimi-k2-5"


# Tests for exception classes
class TestExceptions:
    """Test LLM exception classes."""

    def test_llm_error_is_exception(self):
        err = LLMError("Something went wrong")
        assert isinstance(err, Exception)
        assert str(err) == "Something went wrong"

    def test_rate_limit_error_is_llm_error(self):
        err = RateLimitError("Rate limit hit")
        assert isinstance(err, LLMError)
        assert str(err) == "Rate limit hit"

    def test_api_error_is_llm_error(self):
        err = APIError("API failed")
        assert isinstance(err, LLMError)
        assert str(err) == "API failed"

    def test_timeout_error_is_llm_error(self):
        err = TimeoutError("Request timed out")
        assert isinstance(err, LLMError)
        assert str(err) == "Request timed out"


# Tests for retry decorator
class TestRetryWithBackoff:
    """Test retry decorator logic."""

    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        """Test function that succeeds on first attempt."""
        call_count = 0

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await success_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_then_success(self):
        """Test function that succeeds after retries."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = await flaky_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test function that always fails."""
        call_count = 0

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Persistent failure")

        with pytest.raises(ConnectionError):
            await always_fails()
        
        assert call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_no_retry_on_value_error(self):
        """Test that ValueError is not retried."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        async def value_error_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Programming error")

        with pytest.raises(ValueError):
            await value_error_func()
        
        assert call_count == 1  # No retries for ValueError

    @pytest.mark.asyncio
    async def test_no_retry_on_type_error(self):
        """Test that TypeError is not retried."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        async def type_error_func():
            nonlocal call_count
            call_count += 1
            raise TypeError("Type mismatch")

        with pytest.raises(TypeError):
            await type_error_func()
        
        assert call_count == 1  # No retries for TypeError


# Tests for LLMFactory
class TestLLMFactory:
    """Test LLMFactory without making API calls."""

    def test_create_kimi_provider(self, sample_config):
        """Test creating Kimi provider."""
        provider = LLMFactory.create(sample_config)
        assert isinstance(provider, KimiProvider)
        assert provider.model == "kimi-k2-5"

    def test_create_unknown_provider(self, sample_config):
        """Test error on unknown provider."""
        sample_config.default_llm_provider = "unknown_provider"
        
        with pytest.raises(ValueError, match="Unknown provider: unknown_provider"):
            LLMFactory.create(sample_config)

    def test_create_openai_provider_placeholder(self, sample_config):
        """Test that only 'kimi' is supported currently."""
        sample_config.default_llm_provider = "openai"
        
        with pytest.raises(ValueError, match="Unknown provider: openai"):
            LLMFactory.create(sample_config)


# Tests for KimiProvider instantiation (without API calls)
class TestKimiProviderInstantiation:
    """Test KimiProvider setup without calling APIs."""

    def test_provider_creation(self, sample_config):
        """Test provider can be instantiated."""
        provider = KimiProvider(sample_config)
        assert provider.model == "kimi-k2-5"
        # Client is created but not used for API calls

    def test_provider_stores_config(self, sample_config):
        """Test provider stores configuration."""
        provider = KimiProvider(sample_config)
        # The provider should have the config values
        assert provider.model == sample_config.chat_model
