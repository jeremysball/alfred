# PRD: M5 - Telegram Bot Integration

## Overview

**Issue**: #15  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #14 (M4: Vector Search)  
**Status**: Planning  
**Priority**: High  
**Created**: 2026-02-16

Implement async Telegram bot with message handling and conversation state.

---

## Problem Statement

Alfred needs a Telegram interface for user interaction. Handle text messages, maintain conversation state, and integrate with the memory system.

---

## Solution

Build async Telegram bot with:
1. Message handler for text input
2. Conversation state tracking
3. Integration with context loading
4. Error handling and retry logic

---

## Acceptance Criteria

- [ ] `src/bot.py` - Telegram bot implementation
- [ ] Async message handling
- [ ] Conversation state management
- [ ] Integration with MemoryStore and ContextLoader
- [ ] Error handling with user feedback
- [ ] Support for `/compact` command

---

## File Structure

```
src/
└── bot.py          # Telegram bot handler
```

---

## Bot Implementation (src/bot.py)

```python
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from src.config import Config
from src.context import ContextLoader
from src.memory import MemoryStore


logger = logging.getLogger(__name__)


class AlfredBot:
    def __init__(
        self,
        config: Config,
        context_loader: ContextLoader,
        memory_store: MemoryStore,
    ) -> None:
        self.config = config
        self.context_loader = context_loader
        self.memory = memory_store
        self.application: Application | None = None
    
    def setup(self) -> Application:
        """Initialize telegram application."""
        self.application = Application.builder().token(
            self.config.telegram_bot_token
        ).build()
        
        # Handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("compact", self.compact))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.message)
        )
        
        return self.application
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if not update.message:
            return
        
        await update.message.reply_text(
            "Hello, I'm Alfred. I remember our conversations."
        )
    
    async def compact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /compact command."""
        if not update.message:
            return
        
        await update.message.reply_text(
            "Compaction triggered. This will summarize our long conversation."
        )
        # TODO: Integrate with compaction system in M9
    
    async def message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages."""
        if not update.message or not update.message.text:
            return
        
        user_message = update.message.text
        chat_id = update.effective_chat.id if update.effective_chat else 0
        
        try:
            # Store user message
            await self.memory.add_entry(
                role="user",
                content=user_message,
            )
            
            # Load all memories
            all_memories = await self.memory.load_all_memories()
            
            # Build context with relevant memories
            full_context = await self.context_loader.assemble_with_memories(
                query=user_message,
                all_memories=all_memories,
            )
            
            # TODO: Send to LLM (M6)
            response = "I received your message. LLM integration coming in M6."
            
            # Store assistant response
            await self.memory.add_entry(
                role="assistant",
                content=response,
            )
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.exception("Error handling message")
            await update.message.reply_text(
                f"Error: {e}. Please try again or contact support."
            )
            raise  # Fail fast
    
    async def run(self) -> None:
        """Run the bot."""
        if not self.application:
            self.setup()
        
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("Bot started. Press Ctrl+C to stop.")
        
        # Run until interrupted
        await self.application.updater.stop()
        await self.application.stop()


async def main() -> None:
    """Entry point."""
    from src.config import load_config
    from src.embeddings import EmbeddingClient
    from src.search import MemorySearcher
    
    logging.basicConfig(level=logging.INFO)
    
    config = load_config()
    embedder = EmbeddingClient(config)
    memory = MemoryStore(config, embedder)
    searcher = MemorySearcher(embedder, context_limit=config.memory_context_limit)
    context_loader = ContextLoader(config, searcher)
    
    bot = AlfredBot(config, context_loader, memory)
    await bot.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## Tests

```python
# tests/test_bot.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, Chat
from src.bot import AlfredBot
from src.config import Config


@pytest.fixture
def mock_config():
    return Config(
        telegram_bot_token="test_token",
        openai_api_key="test",
        kimi_api_key="test",
    )


@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.text = "Hello Alfred"
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    return update


@pytest.mark.asyncio
async def test_message_stores_and_responds(mock_config, mock_update):
    context_loader = MagicMock()
    context_loader.assemble_with_memories = AsyncMock(return_value="context")
    
    memory_store = MagicMock()
    memory_store.add_entry = AsyncMock()
    memory_store.load_all_memories = AsyncMock(return_value=[])
    
    bot = AlfredBot(mock_config, context_loader, memory_store)
    
    mock_context = MagicMock()
    mock_context.bot = MagicMock()
    
    await bot.message(mock_update, mock_context)
    
    # Should store user message
    memory_store.add_entry.assert_called_once_with(
        role="user",
        content="Hello Alfred",
    )


@pytest.mark.asyncio
async def test_compact_command_triggers_compaction(mock_config, mock_update):
    context_loader = MagicMock()
    memory_store = MagicMock()
    
    bot = AlfredBot(mock_config, context_loader, memory_store)
    
    mock_context = MagicMock()
    
    await bot.compact(mock_update, mock_context)
    
    # Should acknowledge command
    mock_update.message.reply_text.assert_called_once()
    assert "Compaction" in mock_update.message.reply_text.call_args[0][0]
```

---

## Docker Integration

Update `docker-compose.yml`:

```yaml
services:
  alfred:
    build: .
    volumes:
      - ./memory:/app/memory
      - ./AGENTS.md:/app/AGENTS.md
      - ./SOUL.md:/app/SOUL.md
      - ./USER.md:/app/USER.md
      - ./TOOLS.md:/app/TOOLS.md
      - ./IMPORTANT.md:/app/IMPORTANT.md
    env_file:
      - .env
    command: uv run python -m src.bot
```

---

## Success Criteria

- [ ] Bot responds to /start
- [ ] Bot stores all messages to memory
- [ ] Bot loads context with relevant memories
- [ ] /compact command exists (integration in M9)
- [ ] Errors surface to user
- [ ] All async operations work correctly
- [ ] Type-safe throughout
