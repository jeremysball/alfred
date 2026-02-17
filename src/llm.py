"""LLM provider abstraction and implementations."""

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Optional

from src.config import Config

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: list[dict] | None = None  # For assistant messages with tool calls
    tool_call_id: str | None = None  # For tool role messages
    reasoning_content: str | None = None  # For Kimi thinking mode


@dataclass
class ChatResponse:
    content: str
    model: str
    usage: dict | None = None
    tool_calls: list[dict] | None = None
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


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
):
    """Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delay
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Don't retry on certain errors (programming errors)
                    if isinstance(e, (ValueError, TypeError, AttributeError)):
                        raise

                    if attempt >= max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}"
                        )
                        raise last_exception

                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )

                    # Add jitter to avoid thundering herd (0.5x to 1.5x)
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    await asyncio.sleep(delay)

            raise last_exception

        return wrapper
    return decorator


class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def chat(self, messages: list[ChatMessage]) -> ChatResponse:
        """Send chat messages and get response."""
        pass

    @abstractmethod
    async def stream_chat(
        self, messages: list[ChatMessage]
    ) -> AsyncIterator[str]:
        """Stream chat response chunk by chunk."""
        pass

    @abstractmethod
    async def chat_with_tools(
        self,
        messages: list[ChatMessage],
        tools: Optional[list[dict]] = None,
    ) -> ChatResponse:
        """Send chat with tool definitions."""
        pass

    async def stream_chat_with_tools(
        self,
        messages: list[ChatMessage],
        tools: Optional[list[dict]] = None,
    ) -> AsyncIterator[str]:
        """Stream chat with tool support.

        Default implementation falls back to non-streaming chat.
        Override for true streaming with tool support.
        """
        # Default: use regular chat and yield result
        response = await self.chat_with_tools(messages, tools)

        # Check for tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            yield f"[TOOL_CALLS]{json.dumps(response.tool_calls)}"

        # Yield content
        if response.content:
            yield response.content


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

        logger.debug(f"Sending chat request to Kimi with {len(messages)} messages")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": m.role, "content": m.content}
                    for m in messages
                ],
                temperature=0.7,
                max_tokens=2000,
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

        return ChatResponse(
            content=content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            } if response.usage else None,
        )

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def chat_with_tools(
        self,
        messages: list[ChatMessage],
        tools: Optional[list[dict]] = None,
    ) -> ChatResponse:
        """Send chat with tool definitions."""
        import openai

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                tools=tools,
                temperature=0.7,
                max_tokens=4000,
            )

            message = response.choices[0].message
            content = message.content or ""
            tool_calls = None
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
            if hasattr(message, 'reasoning_content') and message.reasoning_content:
                reasoning_content = message.reasoning_content

            return ChatResponse(
                content=content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                } if response.usage else None,
                tool_calls=tool_calls,
                reasoning_content=reasoning_content,
            )

        except Exception as e:
            logger.error(f"Error in chat_with_tools: {e}")
            raise

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def stream_chat(
        self, messages: list[ChatMessage]
    ) -> AsyncIterator[str]:
        """Stream chat from Kimi with retry logic."""
        import openai

        logger.debug(f"Starting stream chat with Kimi, {len(messages)} messages")

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": m.role, "content": m.content}
                    for m in messages
                ],
                temperature=0.7,
                max_tokens=2000,
                stream=True,
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
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            logger.error(f"Error during stream: {e}")
            raise LLMError(f"Stream error: {e}") from e

    async def stream_chat_with_tools(
        self,
        messages: list[ChatMessage],
        tools: Optional[list[dict]] = None,
    ) -> AsyncIterator[str]:
        """Stream chat with tool support.
        
        For non-streaming responses with tool calls, yields [TOOL_CALLS] marker
        followed by JSON array of tool calls.
        """
        import json
        import openai
        
        try:
            # Convert messages to API format, including tool_call_id for tool messages
            # and reasoning_content for assistant messages
            api_messages = []
            for m in messages:
                msg = {"role": m.role, "content": m.content}
                if m.role == "tool" and m.tool_call_id:
                    msg["tool_call_id"] = m.tool_call_id
                if m.tool_calls:
                    msg["tool_calls"] = m.tool_calls
                if m.reasoning_content and m.role == "assistant":
                    msg["reasoning_content"] = m.reasoning_content
                api_messages.append(msg)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                tools=tools,
                temperature=0.7,
                max_tokens=4000,
            )
            
            # Check for tool calls
            message = response.choices[0].message
            
            # Yield reasoning content if present
            if hasattr(message, 'reasoning_content') and message.reasoning_content:
                yield f"[REASONING]{message.reasoning_content}"
            
            if message.tool_calls:
                # Yield tool calls as special marker
                tool_calls_data = [
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
                yield f"[TOOL_CALLS]{json.dumps(tool_calls_data)}"
            
            # Yield content if any
            if message.content:
                yield message.content
                
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
