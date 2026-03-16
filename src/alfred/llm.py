"""LLM provider abstraction and implementations."""

import asyncio
import json
import logging
import random
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable, Coroutine
from dataclasses import dataclass
from typing import Any, ParamSpec, TypeVar, cast

import tiktoken

from alfred.config import Config

T = TypeVar("T")
P = ParamSpec("P")
_AsyncFunc = Callable[P, Coroutine[Any, Any, T]]

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: list[dict[str, Any]] | None = None  # For assistant messages with tool calls
    tool_call_id: str | None = None  # For tool role messages
    reasoning_content: str | None = None  # For Kimi thinking mode


@dataclass
class ChatResponse:
    content: str
    model: str
    usage: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] | None = None
    reasoning_content: str | None = None  # For provider thinking/reasoning modes


# Exception classes for LLM errors
class LLMError(Exception):
    """Base exception for LLM errors."""

    pass


class RateLimitError(LLMError):
    """Raised when rate limit is hit."""

    pass


class APIError(LLMError):
    """Raised for API errors."""

    pass


class TimeoutError(LLMError):
    """Raised when request times out."""

    pass


async def _retry_async(
    operation: Callable[[], Any],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    operation_name: str = "operation",
) -> Any:
    """Retry an async operation with exponential backoff.

    Used both as a standalone function and as the core logic
    for the retry_with_backoff decorator.
    """
    last_exception: BaseException | None = None

    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except Exception as e:
            last_exception = e

            # Don't retry on programming errors
            if isinstance(e, (ValueError, TypeError, AttributeError)):
                raise

            if attempt >= max_retries:
                logger.error(f"Max retries ({max_retries}) exceeded for {operation_name}: {e}")
                if last_exception:
                    raise last_exception from e
                raise

            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base**attempt), max_delay)

            # Add jitter to avoid thundering herd
            if jitter:
                delay = delay * (0.5 + random.random())

            logger.warning(
                f"Attempt {attempt + 1}/{max_retries + 1} failed for {operation_name}: {e}. "
                f"Retrying in {delay:.2f}s..."
            )
            await asyncio.sleep(delay)

    # Should never reach here, but mypy needs it
    if last_exception:
        raise last_exception
    raise RuntimeError(f"All retries exhausted for {operation_name}")


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
) -> Callable[[Callable[P, Coroutine[Any, Any, T]]], Callable[P, Coroutine[Any, Any, T]]]:
    """Decorator for retrying async functions with exponential backoff.

    Uses _retry_async internally for consistent retry logic.
    """

    def decorator(
        func: Callable[P, Coroutine[Any, Any, T]],
    ) -> Callable[P, Coroutine[Any, Any, T]]:
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await _retry_async(
                operation=lambda: func(*args, **kwargs),
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                operation_name=func.__name__,
            )

        return wrapper

    return decorator


class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def chat(self, messages: list[ChatMessage]) -> ChatResponse:
        """Send chat messages and get response."""
        pass

    @abstractmethod
    def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        """Stream chat response chunk by chunk."""
        pass

    @abstractmethod
    async def chat_with_tools(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        """Send chat with tool definitions."""
        pass

    def stream_chat_with_tools(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat with tool support.

        Default implementation raises NotImplementedError.
        Override for streaming with tool support.
        """
        raise NotImplementedError("stream_chat_with_tools not implemented for this provider")


class KimiProvider(LLMProvider):
    """Kimi Coding Plan provider with retry logic."""

    def __init__(self, config: Config) -> None:
        import openai

        self.client = openai.AsyncOpenAI(
            api_key=config.kimi_api_key,
            base_url=config.kimi_base_url,
            default_headers={
                "User-Agent": "Kilo-Code/1.0",
            },
        )
        self.model = config.chat_model

    async def _retry(self, name: str, fn: "Callable[[], Coroutine[Any, Any, T]]") -> "T":
        """Run fn with exponential-backoff retry. Single source of retry logic."""
        return await _retry_async(fn, max_retries=3, base_delay=1.0, operation_name=name)

    async def chat(self, messages: list[ChatMessage]) -> ChatResponse:
        """Send chat to Kimi with retry logic."""
        import openai
        from openai.types.chat import ChatCompletionMessageParam

        api_messages = cast(
            list[ChatCompletionMessageParam],
            [{"role": m.role, "content": m.content} for m in messages],
        )

        async def _impl() -> ChatResponse:
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=api_messages,
                    extra_body={"reasoning_effort": "high"},
                )
            except openai.RateLimitError as e:
                raise RateLimitError(f"Rate limit exceeded: {e}") from e
            except openai.APITimeoutError as e:
                raise TimeoutError(f"Request timed out: {e}") from e
            except openai.APIError as e:
                raise APIError(f"API error: {e}") from e
            except Exception as e:
                raise LLMError(f"Unexpected error: {e}") from e

            content = response.choices[0].message.content or ""
            return ChatResponse(
                content=content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                }
                if response.usage
                else None,
            )

        return await self._retry("chat", _impl)

    async def chat_with_tools(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        """Send chat with tool definitions."""
        from openai import Omit
        from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolUnionParam

        cast_messages = cast(
            list[ChatCompletionMessageParam],
            [{"role": m.role, "content": m.content} for m in messages],
        )
        tools_param = cast(list[ChatCompletionToolUnionParam], tools) if tools else Omit()

        async def _impl() -> ChatResponse:
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=cast_messages,
                    tools=tools_param,
                    extra_body={"reasoning_effort": "high"},
                )
            except Exception as e:
                logger.error(f"Error in chat_with_tools: {e}")
                raise

            message = response.choices[0].message
            content = message.content or ""
            tool_calls = None

            if message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": getattr(getattr(tc, "function", None), "name", ""),
                            "arguments": getattr(getattr(tc, "function", None), "arguments", ""),
                        },
                    }
                    for tc in message.tool_calls
                ]

            reasoning_content: str | None = getattr(message, "reasoning_content", None) or None

            return ChatResponse(
                content=content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                }
                if response.usage
                else None,
                tool_calls=tool_calls,
                reasoning_content=reasoning_content,
            )

        return await self._retry("chat_with_tools", _impl)

    async def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        """Stream chat from Kimi with retry logic."""
        import openai

        logger.debug(f"Starting stream chat with Kimi, {len(messages)} messages")

        async def _create_stream() -> Any:
            from openai.types.chat import ChatCompletionMessageParam

            return await self.client.chat.completions.create(
                model=self.model,
                messages=cast(
                    list[ChatCompletionMessageParam],
                    [{"role": m.role, "content": m.content} for m in messages],
                ),
                stream=True,
                extra_body={"reasoning_effort": "high"},
            )

        try:
            stream = await _retry_async(
                _create_stream, max_retries=3, base_delay=1.0, operation_name="stream_chat"
            )
        except openai.RateLimitError as e:
            logger.error(f"Kimi rate limit exceeded: {e}")
            raise RateLimitError(f"Rate limit exceeded: {e}") from e
        except openai.APITimeoutError as e:
            logger.error(f"Kimi request timed out: {e}")
            raise TimeoutError(f"Request timed out: {e}") from e
        except openai.APIError as e:
            logger.error(f"Kimi API error: {e}")
            raise APIError(f"API error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error calling Kimi: {e}")
            raise LLMError(f"Unexpected error: {e}") from e

        try:
            async for chunk in stream:
                # Skip chunks with no choices (can happen with some providers)
                if not chunk.choices:
                    continue
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            logger.error(f"Error during stream: {e}")
            raise LLMError(f"Stream error: {e}") from e

    def _convert_messages_to_api_format(
        self, messages: list[ChatMessage]
    ) -> list[dict[str, Any]]:
        """Convert ChatMessage objects to API format.

        Args:
            messages: List of ChatMessage objects.

        Returns:
            List of API-formatted message dictionaries.
        """
        api_messages: list[dict[str, Any]] = []
        for m in messages:
            msg: dict[str, Any] = {"role": m.role, "content": m.content}
            if m.role == "tool" and m.tool_call_id:
                msg["tool_call_id"] = m.tool_call_id
            if m.tool_calls:
                msg["tool_calls"] = m.tool_calls
            if m.reasoning_content and m.role == "assistant":
                msg["reasoning_content"] = m.reasoning_content
            api_messages.append(msg)
        return api_messages

    def _extract_usage_data(
        self,
        usage: Any,
        full_reasoning: str,
        encoder: Any,
    ) -> dict[str, Any]:
        """Extract usage data from chunk, including cache and reasoning tokens.

        Args:
            usage: Usage object from API response.
            full_reasoning: Accumulated reasoning content for fallback counting.
            encoder: Token encoder for manual counting.

        Returns:
            Dictionary with usage statistics.
        """
        usage_data = {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
        }

        # Extract cache tokens
        cached = 0
        if hasattr(usage, "cached_tokens") and usage.cached_tokens:
            cached = usage.cached_tokens
        elif usage.prompt_tokens_details:
            cached = usage.prompt_tokens_details.cached_tokens or 0
        if cached > 0:
            usage_data["prompt_tokens_details"] = {"cached_tokens": cached}

        # Extract reasoning tokens
        reasoning = 0
        details = usage.completion_tokens_details
        if details and details.reasoning_tokens:
            reasoning = details.reasoning_tokens
        elif full_reasoning:
            reasoning = len(encoder.encode(full_reasoning))

        if reasoning > 0:
            usage_data["completion_tokens_details"] = {"reasoning_tokens": reasoning}

        return usage_data

    def _accumulate_tool_calls(
        self,
        tool_calls: list[Any],
        state: dict[str, Any],
    ) -> None:
        """Accumulate tool calls from delta into state.

        Args:
            tool_calls: List of tool call deltas from the stream.
            state: Mutable state dictionary for tracking accumulation.
        """
        for tc in tool_calls:
            if tc.id:
                # New tool call
                func_name = ""
                if hasattr(tc, "function") and tc.function:
                    func_name = tc.function.name or ""
                state["current_tool_call"] = {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": func_name, "arguments": ""},
                }
                state["tool_calls_data"].append(state["current_tool_call"])

            if hasattr(tc, "function") and tc.function:
                current = state["current_tool_call"]
                if tc.function.name and current:
                    current["function"]["name"] = tc.function.name
                if tc.function.arguments and current:
                    current["function"]["arguments"] += tc.function.arguments

    def _process_stream_chunk(
        self,
        chunk: Any,
        state: dict[str, Any],
        encoder: Any,
    ) -> Iterator[str]:
        """Process a single stream chunk and yield outputs.

        Args:
            chunk: The stream chunk from the API.
            state: Mutable state dict for tracking accumulation.
            encoder: Token encoder for counting.

        Yields:
            Content, reasoning markers, and usage data.
        """
        # Handle usage chunk (no choices)
        if not chunk.choices:
            if hasattr(chunk, "usage") and chunk.usage:
                usage_data = self._extract_usage_data(
                    chunk.usage, state["full_reasoning"], encoder
                )
                yield f"[USAGE]{json.dumps(usage_data)}"
            return

        delta = chunk.choices[0].delta

        # Handle content
        if delta.content:
            state["full_content"] += delta.content
            yield delta.content

        # Handle reasoning content
        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
            state["full_reasoning"] += delta.reasoning_content
            yield f"[REASONING]{delta.reasoning_content}"

        # Handle tool calls
        if delta.tool_calls:
            self._accumulate_tool_calls(delta.tool_calls, state)

    async def _create_stream_with_retry(
        self,
        api_messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
    ) -> Any:
        """Create stream with retry logic and error handling.

        Args:
            api_messages: Messages in API format.
            tools: Optional tool definitions.

        Returns:
            Stream object from API.

        Raises:
            RateLimitError: On rate limit exceeded.
            TimeoutError: On request timeout.
            APIError: On API error.
            LLMError: On unexpected error.
        """
        import openai
        from openai import Omit
        from openai.types.chat import (
            ChatCompletionMessageParam,
            ChatCompletionToolUnionParam,
        )

        async def _create_stream() -> Any:
            tools_param = (
                cast(list[ChatCompletionToolUnionParam], tools) if tools else Omit()
            )
            return await self.client.chat.completions.create(
                model=self.model,
                messages=cast(list[ChatCompletionMessageParam], api_messages),
                tools=tools_param,
                stream=True,
                stream_options={"include_usage": True},
                extra_body={"reasoning_effort": "high"},
            )

        try:
            return await _retry_async(
                _create_stream,
                max_retries=3,
                base_delay=1.0,
                operation_name="stream_chat_with_tools",
            )
        except openai.RateLimitError as e:
            logger.error(f"Kimi rate limit exceeded: {e}")
            raise RateLimitError(f"Rate limit exceeded: {e}") from e
        except openai.APITimeoutError as e:
            logger.error(f"Kimi request timed out: {e}")
            raise TimeoutError(f"Request timed out: {e}") from e
        except openai.APIError as e:
            logger.error(f"Kimi API error: {e}")
            raise APIError(f"API error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error calling Kimi: {e}")
            raise LLMError(f"Unexpected error: {e}") from e

    async def stream_chat_with_tools(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat with tool support.

        For non-streaming responses with tool calls, yields [TOOL_CALLS] marker
        followed by JSON array of tool calls.
        """
        import tiktoken

        # Convert messages and create stream
        api_messages = self._convert_messages_to_api_format(messages)
        stream = await self._create_stream_with_retry(api_messages, tools)

        # Initialize state for streaming
        state = {
            "tool_calls_data": [],
            "current_tool_call": None,
            "full_content": "",
            "full_reasoning": "",
        }
        encoder = tiktoken.get_encoding("cl100k_base")

        try:
            async for chunk in stream:
                for output in self._process_stream_chunk(chunk, state, encoder):
                    yield output

            # Yield collected tool calls
            if state["tool_calls_data"]:
                yield f"[TOOL_CALLS]{json.dumps(state['tool_calls_data'])}"

        except Exception as e:
            logger.error(f"Error in stream_chat_with_tools: {e}")
            raise


class LLMFactory:
    """Factory for creating LLM providers."""

    @staticmethod
    def create(config: Config) -> LLMProvider:
        """Create provider based on config."""
        if config.default_llm_provider == "kimi":
            return KimiProvider(config)
        # Future: add more providers here
        raise ValueError(f"Unknown provider: {config.default_llm_provider}")
