"""LLM provider abstraction and implementations."""

import asyncio
import json
import logging
import random
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

import tiktoken

from src.config import Config
from src.type_defs import ChatRole, ToolCall, ToolSchema, UsageData

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.session import Message


@dataclass
class ChatMessage:
    role: ChatRole  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: list[ToolCall] | None = None  # For assistant messages with tool calls
    tool_call_id: str | None = None  # For tool role messages
    reasoning_content: str | None = None  # For Kimi thinking mode


@dataclass
class ChatResponse:
    content: str
    model: str
    usage: UsageData | None = None
    tool_calls: list[ToolCall] | None = None
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


async def _retry_async[T](
    operation: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    operation_name: str = "operation",
) -> T:
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


def retry_with_backoff[**P, T](
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
) -> Callable[
    [Callable[P, Coroutine[object, object, T]]],
    Callable[P, Coroutine[object, object, T]],
]:
    """Decorator for retrying async functions with exponential backoff.

    Uses _retry_async internally for consistent retry logic.
    """

    def decorator(
        func: Callable[P, Coroutine[object, object, T]],
    ) -> Callable[P, Coroutine[object, object, T]]:
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
        tools: list[ToolSchema] | None = None,
    ) -> ChatResponse:
        """Send chat with tool definitions."""
        pass

    def stream_chat_with_tools(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSchema] | None = None,
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

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def chat(self, messages: list[ChatMessage]) -> ChatResponse:
        """Send chat to Kimi with retry logic."""
        import openai
        from openai.types.chat import ChatCompletionMessageParam

        logger.debug(f"Sending chat request to Kimi with {len(messages)} messages")

        api_messages: list[ChatCompletionMessageParam] = [
            {"role": m.role, "content": m.content}  # type: ignore[misc]
            for m in messages
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                reasoning_effort="high",
            )
        except openai.RateLimitError as e:
            logger.error(f"Kimi rate limit exceeded: {e}")
            raise RateLimitError(f"Rate limit exceeded: {e}") from e
        except openai.APIError as e:
            logger.error(f"Kimi API error: {e}")
            raise APIError(f"API error: {e}") from e
        except openai.APITimeoutError as e:
            logger.error(f"Kimi request timed out: {e}")
            raise TimeoutError(f"Request timed out: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error calling Kimi: {e}")
            raise LLMError(f"Unexpected error: {e}") from e

        content = response.choices[0].message.content or ""
        logger.debug(f"Received response from Kimi: {len(content)} chars")

        usage: UsageData | None = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            }

        return ChatResponse(
            content=content,
            model=response.model,
            usage=usage,
        )

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def chat_with_tools(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSchema] | None = None,
    ) -> ChatResponse:
        """Send chat with tool definitions."""

        try:
            response = await self.client.chat.completions.create(  # type: ignore[call-overload]
                model=self.model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                tools=tools,
                reasoning_effort="high",
            )

            message = response.choices[0].message
            content = message.content or ""
            tool_calls: list[ToolCall] | None = None
            reasoning_content = None

            # Check for tool calls
            if message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ]

            # Capture reasoning_content for thinking mode
            if hasattr(message, "reasoning_content") and message.reasoning_content:
                reasoning_content = message.reasoning_content

            usage: UsageData | None = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                }

            return ChatResponse(
                content=content,
                model=response.model,
                usage=usage,
                tool_calls=tool_calls,
                reasoning_content=reasoning_content,
            )

        except Exception as e:
            logger.error(f"Error in chat_with_tools: {e}")
            raise

    async def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        """Stream chat from Kimi with retry logic."""
        import openai

        logger.debug(f"Starting stream chat with Kimi, {len(messages)} messages")

        from openai.types.chat import ChatCompletionChunk, ChatCompletionMessageParam

        async def _create_stream() -> AsyncIterator[ChatCompletionChunk]:
            api_messages: list[ChatCompletionMessageParam] = [
                {"role": m.role, "content": m.content}  # type: ignore[misc]
                for m in messages
            ]
            return await self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                stream=True,
                reasoning_effort="high",
            )

        try:
            stream = await _retry_async(
                _create_stream, max_retries=3, base_delay=1.0, operation_name="stream_chat"
            )
        except openai.RateLimitError as e:
            logger.error(f"Kimi rate limit exceeded: {e}")
            raise RateLimitError(f"Rate limit exceeded: {e}") from e
        except openai.APIError as e:
            logger.error(f"Kimi API error: {e}")
            raise APIError(f"API error: {e}") from e
        except openai.APITimeoutError as e:
            logger.error(f"Kimi request timed out: {e}")
            raise TimeoutError(f"Request timed out: {e}") from e
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

    async def stream_chat_with_tools(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSchema] | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat with tool support.

        For non-streaming responses with tool calls, yields [TOOL_CALLS] marker
        followed by JSON array of tool calls.
        """
        import openai
        from openai.types.chat import ChatCompletionChunk

        # Convert messages to API format, including tool_call_id for tool messages
        # and reasoning_content for assistant messages
        api_messages: list[dict[str, object]] = []
        for m in messages:
            msg: dict[str, object] = {"role": m.role, "content": m.content}
            if m.role == "tool" and m.tool_call_id:
                msg["tool_call_id"] = m.tool_call_id
            if m.tool_calls:
                msg["tool_calls"] = m.tool_calls
            if m.reasoning_content and m.role == "assistant":
                msg["reasoning_content"] = m.reasoning_content
            api_messages.append(msg)

        async def _create_stream() -> AsyncIterator[ChatCompletionChunk]:
            stream: AsyncIterator[ChatCompletionChunk] = await self.client.chat.completions.create(  # type: ignore[call-overload]
                model=self.model,
                messages=api_messages,
                tools=tools,
                stream=True,
                stream_options={"include_usage": True},
                reasoning_effort="high",
            )
            return stream

        try:
            stream = await _retry_async(
                _create_stream,
                max_retries=3,
                base_delay=1.0,
                operation_name="stream_chat_with_tools",
            )
        except openai.RateLimitError as e:
            logger.error(f"Kimi rate limit exceeded: {e}")
            raise RateLimitError(f"Rate limit exceeded: {e}") from e
        except openai.APIError as e:
            logger.error(f"Kimi API error: {e}")
            raise APIError(f"API error: {e}") from e
        except openai.APITimeoutError as e:
            logger.error(f"Kimi request timed out: {e}")
            raise TimeoutError(f"Request timed out: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error calling Kimi: {e}")
            raise LLMError(f"Unexpected error: {e}") from e

        # Collect streaming data
        tool_calls_data: list[ToolCall] = []
        current_tool_call: ToolCall | None = None
        full_content = ""
        full_reasoning = ""  # Accumulate reasoning content for token counting
        encoder = tiktoken.get_encoding("cl100k_base")  # Tokenizer for counting

        try:
            async for chunk in stream:
                # Handle usage chunk (comes when choices is empty)
                if not chunk.choices:
                    if hasattr(chunk, "usage") and chunk.usage:
                        usage_data: UsageData = {
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                        }
                        # Extract cache tokens (Kimi puts them at top level)
                        cached = 0
                        if hasattr(chunk.usage, "cached_tokens") and chunk.usage.cached_tokens:
                            cached = chunk.usage.cached_tokens
                        elif chunk.usage.prompt_tokens_details:
                            cached = chunk.usage.prompt_tokens_details.cached_tokens or 0
                        if cached > 0:
                            usage_data["prompt_tokens_details"] = {
                                "cached_tokens": cached,
                            }

                        # Extract reasoning tokens - first try API response, fallback to counting
                        reasoning = 0
                        details = chunk.usage.completion_tokens_details
                        if details and details.reasoning_tokens:
                            reasoning = details.reasoning_tokens
                        elif full_reasoning:
                            # Kimi doesn't return reasoning_tokens, count them ourselves
                            reasoning = len(encoder.encode(full_reasoning))

                        if reasoning > 0:
                            usage_data["completion_tokens_details"] = {
                                "reasoning_tokens": reasoning,
                            }
                        yield f"[USAGE]{json.dumps(usage_data)}"
                    continue

                delta = chunk.choices[0].delta

                # Handle content
                if delta.content:
                    full_content += delta.content
                    yield delta.content

                # Handle reasoning content (required for Kimi thinking mode with tool calls)
                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    full_reasoning += delta.reasoning_content
                    yield f"[REASONING]{delta.reasoning_content}"

                # Handle tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.id:
                            # New tool call
                            func_name = ""
                            if hasattr(tc, "function") and tc.function:
                                func_name = tc.function.name or ""
                            current_tool_call = {
                                "id": tc.id,
                                "type": "function",
                                "function": {"name": func_name, "arguments": ""},
                            }
                            tool_calls_data.append(current_tool_call)
                        if hasattr(tc, "function") and tc.function:
                            if tc.function.name and current_tool_call:
                                current_tool_call["function"]["name"] = tc.function.name
                            if tc.function.arguments and current_tool_call:
                                current_tool_call["function"]["arguments"] += tc.function.arguments

            # Yield tool calls if any were collected
            if tool_calls_data:
                yield f"[TOOL_CALLS]{json.dumps(tool_calls_data)}"

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


async def summarize_conversation(messages: Sequence["Message"]) -> str:
    """Generate summary text from conversation messages.

    Args:
        messages: List of Message objects to summarize

    Returns:
        Summary text string

    Raises:
        Exception: If LLM call fails
    """
    logger.debug(f"summarize_conversation called with {len(messages)} messages")

    # Build conversation transcript
    lines = []
    for msg in messages:
        role = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
        content = msg.content
        lines.append(f"{role}: {content}")

    transcript = "\n".join(lines)
    logger.debug(f"Built transcript: {len(transcript)} chars, {len(lines)} messages")

    # Create prompt messages
    prompt_messages = [
        ChatMessage(
            role="system",
            content="""You are a conversation summarization assistant.

Your task: Summarize a conversation transcript while preserving:
1. Key facts and decisions
2. User preferences revealed
3. Important context for future conversations
4. Specific details that matter (names, dates, preferences)

Be concise but complete. Omit pleasantries and filler. Focus on substance.

Provide a single paragraph summary suitable for semantic search retrieval.
            """.strip(),
        ),
        ChatMessage(
            role="user",
            content=f"Summarize this conversation:\n\n{transcript}",
        ),
    ]

    # Get LLM and generate summary
    logger.debug("Creating LLM and sending summarization request")
    from src.config import load_config

    config = load_config()
    llm = LLMFactory.create(config)
    response = await llm.chat(prompt_messages)

    summary = response.content
    logger.debug(f"Summary generated: {len(summary)} chars")

    return summary
