# PRD: M5 - Telegram Bot Integration

## Overview

**Issue**: #15
**Parent**: #10 (Alfred - The Rememberer)
**Depends On**: #12 (M2: Core Infrastructure)
**Status**: Planning
**Priority**: High
**Created**: 2026-02-16

Implement async Telegram bot as a thin interface layer.

---

## Problem Statement

Alfred needs a Telegram interface for user interaction. The bot should be a thin adapter that passes messages to the core Alfred engine and returns responses.

---

## Solution

Build async Telegram bot as a thin interface:
1. Message handler for text input
2. Delegation to core Alfred engine (memory, context, LLM)
3. Error handling with user feedback
4. Support for slash commands

**Architecture Principle**: The bot is just one interface. It could be replaced with CLI, web, or any other interface without changing core Alfred logic.

---

## Acceptance Criteria

- [ ] `src/interfaces/telegram.py` - Telegram bot implementation
- [ ] `src/interfaces/cli.py` - CLI interface (parallel implementation)
- [ ] Async message handling
- [ ] Delegation to core Alfred engine (not direct memory/context access)
- [ ] Error handling with user feedback
- [ ] Support for `/compact` command

---

## File Structure

```
src/
├── alfred.py           # Core Alfred engine (handles memory, context, LLM)
└── interfaces/
    ├── __init__.py
    ├── telegram.py     # Telegram interface
    └── cli.py          # CLI interface
```

---

## Core Alfred Engine (src/alfred.py)

The bot delegates to this core engine. Other interfaces (CLI, web) will use the same engine.

```python
from dataclasses import dataclass
from src.config import Config


@dataclass
class ChatResponse:
    content: str
    tokens_used: int | None = None


class Alfred:
    """Core Alfred engine - handles memory, context, and LLM."""
    
    def __init__(self, config: Config) -> None:
        self.config = config
        # Memory, context, LLM initialized here or lazily
    
    async def chat(self, message: str) -> ChatResponse:
        """Process a message and return response.
        
        This is the main entry point for any interface.
        Handles: store message → load context → call LLM → store response
        """
        # TODO: Wire up memory, context, LLM
        # For now, just pass through to LLM
        return ChatResponse(content=f"You said: {message}")
    
    async def compact(self) -> str:
        """Trigger conversation compaction."""
        # TODO: Implement in M9
        return "Compaction not yet implemented"
```

---

## Telegram Interface (src/interfaces/telegram.py)

Thin adapter - just handles Telegram-specific concerns.

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
from src.alfred import Alfred


logger = logging.getLogger(__name__)


class TelegramInterface:
    """Thin Telegram interface - delegates to Alfred engine."""
    
    def __init__(self, config: Config, alfred: Alfred) -> None:
        self.config = config
        self.alfred = alfred
        self.application: Application | None = None
    
    def setup(self) -> Application:
        """Initialize telegram application."""
        self.application = Application.builder().token(
            self.config.telegram_bot_token
        ).build()
        
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
        
        result = await self.alfred.compact()
        await update.message.reply_text(result)
    
    async def message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages - delegate to Alfred."""
        if not update.message or not update.message.text:
            return
        
        try:
            response = await self.alfred.chat(update.message.text)
            await update.message.reply_text(response.content)
        except Exception as e:
            logger.exception("Error handling message")
            await update.message.reply_text(
                f"Error: {e}. Please try again."
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
        
        await self.application.updater.stop()
        await self.application.stop()


async def main() -> None:
    """Entry point."""
    import asyncio
    from src.config import load_config
    
    logging.basicConfig(level=logging.INFO)
    
    config = load_config()
    alfred = Alfred(config)
    interface = TelegramInterface(config, alfred)
    
    await interface.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## CLI Interface (src/interfaces/cli.py)

Same Alfred engine, different interface.

```python
import asyncio
import logging
from src.config import Config
from src.alfred import Alfred


logger = logging.getLogger(__name__)


class CLIInterface:
    """CLI interface - delegates to Alfred engine."""
    
    def __init__(self, config: Config, alfred: Alfred) -> None:
        self.config = config
        self.alfred = alfred
    
    async def run(self) -> None:
        """Run interactive CLI."""
        print("Alfred CLI. Type 'exit' to quit, 'compact' to compact.\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break
            
            if not user_input:
                continue
            
            if user_input.lower() == "exit":
                print("Goodbye!")
                break
            
            if user_input.lower() == "compact":
                result = await self.alfred.compact()
                print(f"Alfred: {result}\n")
                continue
            
            response = await self.alfred.chat(user_input)
            print(f"Alfred: {response.content}\n")


async def main() -> None:
    """Entry point."""
    logging.basicConfig(level=logging.INFO)
    
    config = Config.from_env()
    alfred = Alfred(config)
    interface = CLIInterface(config, alfred)
    
    await interface.run()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Tests

```python
# tests/test_telegram.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import Update, Message, Chat
from src.interfaces.telegram import TelegramInterface
from src.alfred import Alfred
from src.config import Config


@pytest.fixture
def mock_config():
    return Config(
        telegram_bot_token="test_token",
        openai_api_key="test",
        kimi_api_key="test",
    )


@pytest.fixture
def mock_alfred():
    alfred = MagicMock(spec=Alfred)
    alfred.chat = AsyncMock(return_value=MagicMock(content="Response"))
    alfred.compact = AsyncMock(return_value="Compacted")
    return alfred


@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.text = "Hello Alfred"
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    return update


@pytest.mark.asyncio
async def test_message_delegates_to_alfred(mock_config, mock_alfred, mock_update):
    interface = TelegramInterface(mock_config, mock_alfred)
    
    mock_context = MagicMock()
    await interface.message(mock_update, mock_context)
    
    # Should delegate to Alfred
    mock_alfred.chat.assert_called_once_with("Hello Alfred")
    mock_update.message.reply_text.assert_called_once_with("Response")


@pytest.mark.asyncio
async def test_compact_delegates_to_alfred(mock_config, mock_alfred, mock_update):
    interface = TelegramInterface(mock_config, mock_alfred)
    
    mock_context = MagicMock()
    await interface.compact(mock_update, mock_context)
    
    mock_alfred.compact.assert_called_once()
```

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2026-02-17 | Bot is thin interface | Interfaces should be interchangeable (Telegram, CLI, web) | Removed dependency on M4, added Alfred engine |
| 2026-02-17 | CLI parallel to Telegram | Validate architecture with simple interface first | Added cli.py |
| 2026-02-17 | Session-based threading | Each Telegram thread starts fresh, loads from files | Memory loading strategy |

---

## Docker Integration

Templates are copied into the container at build time. Memory files persist via volumes.

```yaml
services:
  alfred:
    build: .
    volumes:
      - ./memory:/app/memory
    env_file:
      - .env
    command: uv run python -m src.interfaces.telegram
```

---

## Success Criteria

- [ ] Bot responds to /start
- [ ] Bot delegates all chat to Alfred.chat()
- [ ] CLI interface works with same Alfred engine
- [ ] /compact command delegates to Alfred.compact()
- [ ] Errors surface to user
- [ ] All async operations work correctly
- [ ] Type-safe throughout
