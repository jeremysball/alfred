"""Tests for embedding error handling and retry logic."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.embeddings import EmbeddingClient, EmbeddingError, _is_transient_error


class TestIsTransientError:
    """Test classification of transient vs non-transient errors."""

    def test_rate_limit_is_transient(self):
        """Rate limit errors (429) are transient."""
        from openai import RateLimitError

        error = RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429),
            body=None,
        )
        assert _is_transient_error(error) is True

    def test_service_unavailable_is_transient(self):
        """503 errors are transient."""
        from openai import APIStatusError

        error = APIStatusError(
            message="Service unavailable",
            response=MagicMock(status_code=503),
            body=None,
        )
        assert _is_transient_error(error) is True

    def test_gateway_timeout_is_transient(self):
        """504 errors are transient."""
        from openai import APIStatusError

        error = APIStatusError(
            message="Gateway timeout",
            response=MagicMock(status_code=504),
            body=None,
        )
        assert _is_transient_error(error) is True

    def test_timeout_error_is_transient(self):
        """TimeoutError is transient."""
        assert _is_transient_error(TimeoutError()) is True

    def test_connection_error_is_transient(self):
        """ConnectionError is transient."""
        assert _is_transient_error(ConnectionError()) is True

    def test_auth_error_is_not_transient(self):
        """401 auth errors are not transient."""
        from openai import AuthenticationError

        error = AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401),
            body=None,
        )
        assert _is_transient_error(error) is False

    def test_bad_request_is_not_transient(self):
        """400 bad request errors are not transient."""
        from openai import BadRequestError

        error = BadRequestError(
            message="Invalid request",
            response=MagicMock(status_code=400),
            body=None,
        )
        assert _is_transient_error(error) is False


class TestRetryLogic:
    """Test retry behavior with backoff."""

    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        """Successful calls don't retry."""
        mock_func = AsyncMock(return_value=[0.1, 0.2, 0.3])

        from src.embeddings import _with_retry

        result = await _with_retry("test_op", mock_func, max_retries=3)

        assert result == [0.1, 0.2, 0.3]
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_transient_error_then_success(self):
        """Retry on transient error, then succeed."""
        from openai import RateLimitError

        mock_response = MagicMock(status_code=429)
        error = RateLimitError(
            message="Rate limit", response=mock_response, body=None
        )

        # Fail once, then succeed
        mock_func = AsyncMock(side_effect=[error, [0.1, 0.2, 0.3]])

        from src.embeddings import _with_retry

        result = await _with_retry(
            "test_op", mock_func, max_retries=3, base_delay=0.01
        )

        assert result == [0.1, 0.2, 0.3]
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_fail_fast_on_non_transient_error(self):
        """Don't retry on non-transient errors."""
        from openai import AuthenticationError

        mock_response = MagicMock(status_code=401)
        error = AuthenticationError(
            message="Invalid API key", response=mock_response, body=None
        )

        mock_func = AsyncMock(side_effect=error)

        from src.embeddings import _with_retry

        with pytest.raises(EmbeddingError) as exc_info:
            await _with_retry("test_op", mock_func, max_retries=3)

        assert "non-transient" in str(exc_info.value)
        assert mock_func.call_count == 1  # No retries

    @pytest.mark.asyncio
    async def test_exhaust_retries_and_fail(self):
        """Fail after exhausting all retries."""
        from openai import RateLimitError

        mock_response = MagicMock(status_code=429)
        error = RateLimitError(
            message="Rate limit", response=mock_response, body=None
        )

        mock_func = AsyncMock(side_effect=[error, error, error, error])

        from src.embeddings import _with_retry

        with pytest.raises(EmbeddingError) as exc_info:
            await _with_retry(
                "test_op", mock_func, max_retries=2, base_delay=0.01
            )

        assert "failed after 3 attempts" in str(exc_info.value)
        assert mock_func.call_count == 3  # Initial + 2 retries


class TestEmbeddingClientErrorHandling:
    """Test EmbeddingClient error handling."""

    @pytest.fixture
    def mock_config(self, monkeypatch):
        from src.config import Config

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        monkeypatch.setenv("KIMI_API_KEY", "test")
        monkeypatch.setenv("KIMI_BASE_URL", "https://test.moonshot.cn/v1")

        return Config(
            telegram_bot_token="test",
            openai_api_key="test",
            kimi_api_key="test",
            kimi_base_url="https://test.moonshot.cn/v1",
            default_llm_provider="kimi",
            embedding_model="text-embedding-3-small",
            chat_model="kimi-k2-5",
            memory_context_limit=20,
            workspace_dir=Path("."),
            memory_dir=Path("./memory"),
            context_files={},
        )

    @pytest.mark.asyncio
    async def test_embed_retries_on_rate_limit(self, mock_config):
        """embed() retries on rate limit errors."""
        from openai import RateLimitError

        client = EmbeddingClient(mock_config, max_retries=2, base_delay=0.01)

        mock_response = MagicMock(status_code=429)
        error = RateLimitError(
            message="Rate limit", response=mock_response, body=None
        )

        # Fail twice, then succeed
        mock_data = MagicMock(data=[MagicMock(embedding=[0.1, 0.2])])
        with patch.object(
            client.client.embeddings,
            "create",
            AsyncMock(side_effect=[error, error, mock_data]),
        ):
            result = await client.embed("test text")

        assert result == [0.1, 0.2]

    @pytest.mark.asyncio
    async def test_embed_fails_fast_on_auth_error(self, mock_config):
        """embed() fails fast on auth errors."""
        from openai import AuthenticationError

        client = EmbeddingClient(mock_config, max_retries=3, base_delay=0.01)

        mock_response = MagicMock(status_code=401)
        error = AuthenticationError(
            message="Invalid key", response=mock_response, body=None
        )

        with patch.object(
            client.client.embeddings, "create", AsyncMock(side_effect=error)
        ), pytest.raises(EmbeddingError) as exc_info:
            await client.embed("test text")

        assert "non-transient" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_embed_batch_retries_on_transient_error(self, mock_config):
        """embed_batch() retries on transient errors."""
        from openai import APIStatusError

        client = EmbeddingClient(mock_config, max_retries=1, base_delay=0.01)

        mock_response = MagicMock(status_code=503)
        error = APIStatusError(
            message="Service unavailable", response=mock_response, body=None
        )

        mock_result = MagicMock(data=[MagicMock(embedding=[0.1]), MagicMock(embedding=[0.2])])

        with patch.object(
            client.client.embeddings,
            "create",
            AsyncMock(side_effect=[error, mock_result]),
        ):
            result = await client.embed_batch(["text1", "text2"])

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_embed_batch_fails_fast_on_bad_request(self, mock_config):
        """embed_batch() fails fast on bad request."""
        from openai import BadRequestError

        client = EmbeddingClient(mock_config, max_retries=3, base_delay=0.01)

        mock_response = MagicMock(status_code=400)
        error = BadRequestError(
            message="Invalid request", response=mock_response, body=None
        )

        with patch.object(
            client.client.embeddings, "create", AsyncMock(side_effect=error)
        ), pytest.raises(EmbeddingError) as exc_info:
            await client.embed_batch(["text1", "text2"])

        assert "non-transient" in str(exc_info.value)


class TestEmbeddingError:
    """Test EmbeddingError exception."""

    def test_error_with_original_exception(self):
        """EmbeddingError preserves original exception."""
        original = ValueError("Something went wrong")
        error = EmbeddingError("Embedding failed", original)

        assert str(error) == "Embedding failed"
        assert error.original_error is original

    def test_error_without_original_exception(self):
        """EmbeddingError works without original exception."""
        error = EmbeddingError("Embedding failed")

        assert str(error) == "Embedding failed"
        assert error.original_error is None
