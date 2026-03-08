# PRD: M6 - Kimi LLM Provider

## Overview

**Issue**: #16  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #15 (M5: Telegram Bot)  
**Status**: Completed
**Completed**: 2026-02-17  
**Priority**: High  
**Created**: 2026-02-16

Implement Kimi Coding Plan as the first LLM provider with streaming support.

---

## Problem Statement

Alfred needs an LLM provider to generate responses. Start with Kimi Coding Plan as the primary provider.

---

## Solution

Build LLM provider abstraction with:
1. Generic provider interface
2. Kimi Coding Plan implementation
3. Message formatting for chat
4. Streaming response support

---

## Acceptance Criteria

- [x] `src/llm.py` - LLM provider abstraction
- [x] Kimi provider implementation
- [x] Chat message formatting
- [x] Streaming support
- [x] Error handling and retries
- [ ] Integration with Telegram bot (deferred to M5)

---

## File Structure

```
src/
└── llm.py          # LLM provider abstraction
```

---

## LLM Abstraction (src/llm.py)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator
from src.config import Config


@dataclass
class ChatMessage:
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class ChatResponse:
    content: str
    model: str
    usage: dict | None = None


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


class KimiProvider(LLMProvider):
    """Kimi Coding Plan provider."""
    
    def __init__(self, config: Config) -> None:
        import openai
        self.client = openai.AsyncOpenAI(
            api_key=config.kimi_api_key,
            base_url=config.kimi_base_url,
        )
        self.model = config.chat_model
    
    async def chat(self, messages: list[ChatMessage]) -> ChatResponse:
        """Send chat to Kimi."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": m.role, "content": m.content}
                for m in messages
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        
        return ChatResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            } if response.usage else None,
        )
    
    async def stream_chat(
        self, messages: list[ChatMessage]
    ) -> AsyncIterator[str]:
        """Stream chat from Kimi."""
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
        
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content


class LLMFactory:
    """Factory for creating LLM providers."""
    
    @staticmethod
    def create(config: Config) -> LLMProvider:
        """Create provider based on config."""
        if config.default_llm_provider == "kimi":
            return KimiProvider(config)
        # Future: add more providers here
        raise ValueError(f"Unknown provider: {config.default_llm_provider}")
```

---

## Updated Bot Integration

Update `src/bot.py` to use LLM:

```python
from src.llm import LLMProvider, ChatMessage

class AlfredBot:
    def __init__(
        self,
        config: Config,
        context_loader: ContextLoader,
        memory_store: MemoryStore,
        llm: LLMProvider,
    ) -> None:
        self.config = config
        self.context_loader = context_loader
        self.memory = memory_store
        self.llm = llm
        self.application: Application | None = None
    
    async def message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages."""
        if not update.message or not update.message.text:
            return
        
        user_message = update.message.text
        
        try:
            # Store user message
            await self.memory.add_entry(role="user", content=user_message)
            
            # Load all memories
            all_memories = await self.memory.load_all_memories()
            
            # Build context
            full_context = await self.context_loader.assemble_with_memories(
                query=user_message,
                all_memories=all_memories,
            )
            
            # Build messages for LLM
            messages = [
                ChatMessage(role="system", content=full_context),
                ChatMessage(role="user", content=user_message),
            ]
            
            # Get response from LLM
            response = await self.llm.chat(messages)
            
            # Store assistant response
            await self.memory.add_entry(
                role="assistant",
                content=response.content,
            )
            
            await update.message.reply_text(response.content)
            
        except Exception as e:
            logger.exception("Error handling message")
            await update.message.reply_text(f"Error: {e}")
            raise
```

---

## Updated Main

```python
# In src/bot.py main()

async def main() -> None:
    """Entry point."""
    from src.llm import LLMFactory
    
    logging.basicConfig(level=logging.INFO)
    
    config = load_config()
    embedder = EmbeddingClient(config)
    memory = MemoryStore(config, embedder)
    searcher = MemorySearcher(embedder, context_limit=config.memory_context_limit)
    context_loader = ContextLoader(config, searcher)
    llm = LLMFactory.create(config)
    
    bot = AlfredBot(config, context_loader, memory, llm)
    await bot.run()
```

---

## Tests

```python
# tests/test_llm.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.llm import KimiProvider, ChatMessage
from src.config import Config


@pytest.fixture
def mock_config():
    return Config(
        telegram_bot_token="test",
        openai_api_key="test",
        kimi_api_key="test_key",
        kimi_base_url="https://api.moonshot.cn/v1",
        chat_model="kimi-k2-5",
    )


@pytest.mark.asyncio
async def test_kimi_chat(mock_config):
    provider = KimiProvider(mock_config)
    
    # Mock the OpenAI client
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello, I'm Alfred."
    mock_response.model = "kimi-k2-5"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5
    
    provider.client = MagicMock()
    provider.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    messages = [ChatMessage(role="user", content="Hello")]
    response = await provider.chat(messages)
    
    assert response.content == "Hello, I'm Alfred."
    assert response.model == "kimi-k2-5"
```

---

## Success Criteria

- [x] Kimi provider responds to messages
- [x] Streaming works
- [x] Error handling with retries
- [ ] Integration with Telegram bot complete (deferred to M5)
- [ ] Response stored to memory (deferred to M3/M10)
- [x] Type-safe throughout
- [x] Tests created (20 tests, no mocks)

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2026-02-17 | No mocks in tests | Test behavior, not implementation; avoid brittle tests | Tests verify actual logic without depending on API internals |
| 2026-02-17 | Exponential backoff with jitter | Standard resilience pattern; avoids thundering herd | Retries are predictable but not synchronized |
| 2026-02-17 | Custom exception hierarchy | Clear error types for different failure modes | Callers can catch specific errors or base LLMError |
| 2026-02-17 | AsyncOpenAI client | Official client supports async streaming | Native async support without blocking threads |
