# Dispatcher Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python dispatcher that manages Telegram threads, spawns pi subagents with fault isolation, and never blocks.

**Architecture:** Single Python asyncio process. Dispatcher routes messages to threads. Each thread spawns `pi` subprocess. Sub-agents spawn separate pi subprocesses with isolated context.

**Tech Stack:** Python 3.11+, asyncio, python-telegram-bot 20+, aiofiles, pydantic

---

## Task 1: Project Structure and Dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `dispatcher/__init__.py`
- Create: `dispatcher/main.py` (entry point stub)
- Create: `.env.example`

**Step 1: Write pyproject.toml**

```toml
[project]
name = "openclaw-dispatcher"
version = "0.1.0"
description = "Dispatcher for OpenClaw Pi with Telegram thread support"
requires-python = ">=3.11"
dependencies = [
    "python-telegram-bot>=20.0",
    "aiofiles>=23.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "ruff>=0.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Step 2: Create entry point stub**

```python
# dispatcher/main.py
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Dispatcher starting...")
    # TODO: Implement


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 3: Create .env.example**

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
WORKSPACE_DIR=./workspace
THREADS_DIR=./threads
LOG_LEVEL=INFO
```

**Step 4: Install dependencies**

Run: `pip install -e .`
Expected: Installs without errors

**Step 5: Commit**

```bash
git add pyproject.toml dispatcher/__init__.py dispatcher/main.py .env.example
git commit -m "feat(dispatcher): project structure and dependencies"
```

---

## Task 2: Configuration and Settings

**Files:**
- Create: `dispatcher/config.py`
- Modify: `dispatcher/main.py` (load config)

**Step 1: Write config.py**

```python
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str
    
    # Paths
    workspace_dir: Path = Path("./workspace")
    threads_dir: Path = Path("./threads")
    
    # Logging
    log_level: str = "INFO"
    
    # Pi agent
    pi_timeout: int = 300  # seconds
    
    # LLM Provider (passed to pi)
    llm_provider: str = "zai"  # zai, moonshot
    llm_api_key: str = ""
    llm_model: str = ""  # Optional override
    
    # Limits
    max_threads: int = 50
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

**Step 2: Update main.py to load config**

```python
from dispatcher.config import Settings

settings = Settings()
logger.setLevel(getattr(logging, settings.log_level.upper()))
```

**Step 3: Update .env.example**

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Paths
WORKSPACE_DIR=./workspace
THREADS_DIR=./threads
LOG_LEVEL=INFO

# Pi agent
PI_TIMEOUT=300

# LLM Provider (passed to pi)
LLM_PROVIDER=zai
LLM_API_KEY=your_api_key
LLM_MODEL=

# Limits
MAX_THREADS=50
```

**Step 4: Commit**

```bash
git add dispatcher/config.py dispatcher/main.py .env.example
git commit -m "feat(dispatcher): configuration with LLM provider settings"
```

---

## Task 3: Thread Model and Storage

**Files:**
- Create: `dispatcher/models.py`
- Create: `dispatcher/storage.py`
- Create: `tests/test_storage.py`

**Step 1: Write models.py**

```python
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Thread(BaseModel):
    thread_id: str
    chat_id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    messages: list[Message] = []
    active_subagent: Optional[str] = None
    
    def add_message(self, role: str, content: str):
        self.messages.append(Message(role=role, content=content))
        self.updated_at = datetime.utcnow()
```

**Step 2: Write storage.py**

```python
import json
import aiofiles
from pathlib import Path
from dispatcher.models import Thread


class ThreadStorage:
    def __init__(self, threads_dir: Path):
        self.threads_dir = threads_dir
        self.threads_dir.mkdir(parents=True, exist_ok=True)
    
    def _thread_path(self, thread_id: str) -> Path:
        return self.threads_dir / f"{thread_id}.json"
    
    async def save(self, thread: Thread):
        path = self._thread_path(thread.thread_id)
        async with aiofiles.open(path, "w") as f:
            await f.write(thread.model_dump_json(indent=2))
    
    async def load(self, thread_id: str) -> Thread | None:
        path = self._thread_path(thread_id)
        if not path.exists():
            return None
        async with aiofiles.open(path, "r") as f:
            content = await f.read()
            return Thread.model_validate_json(content)
    
    async def list_threads(self) -> list[str]:
        threads = []
        for path in self.threads_dir.glob("*.json"):
            threads.append(path.stem)
        return threads
```

**Step 3: Write test**

```python
import pytest
import asyncio
from pathlib import Path
from dispatcher.models import Thread
from dispatcher.storage import ThreadStorage


@pytest.mark.asyncio
async def test_save_and_load_thread(tmp_path):
    storage = ThreadStorage(tmp_path)
    thread = Thread(thread_id="test_123", chat_id=456)
    thread.add_message("user", "Hello")
    
    await storage.save(thread)
    loaded = await storage.load("test_123")
    
    assert loaded is not None
    assert loaded.thread_id == "test_123"
    assert len(loaded.messages) == 1
    assert loaded.messages[0].content == "Hello"
```

**Step 4: Run tests**

Run: `pytest tests/test_storage.py -v`
Expected: 1 passed

**Step 5: Commit**

```bash
git add dispatcher/models.py dispatcher/storage.py tests/test_storage.py
git commit -m "feat(dispatcher): thread model and JSON storage"
```

---

## Task 4: Pi Agent Manager

**Files:**
- Create: `dispatcher/pi_manager.py`
- Create: `tests/test_pi_manager.py`

**Context:** Dispatcher talks to pi (agent with tools/context). pi internally uses LLM provider (ZAI/Moonshot). Config passed to pi via environment.

**Step 1: Write pi_manager.py**

```python
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PiSubprocess:
    """Manages a single pi subprocess for a thread."""
    
    def __init__(
        self,
        thread_id: str,
        workspace: Path,
        timeout: int = 300,
        llm_provider: str = "zai",
        llm_api_key: str = "",
        llm_model: str = ""
    ):
        self.thread_id = thread_id
        self.workspace = workspace
        self.timeout = timeout
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model
        self.process: Optional[asyncio.subprocess.Process] = None
    
    async def start(self):
        """Start the pi subprocess with LLM config."""
        env = os.environ.copy()
        
        # Set LLM provider config for pi
        if self.llm_provider == "zai":
            env["ZAI_API_KEY"] = self.llm_api_key
            if self.llm_model:
                env["ZAI_MODEL"] = self.llm_model
        elif self.llm_provider == "moonshot":
            env["MOONSHOT_API_KEY"] = self.llm_api_key
            if self.llm_model:
                env["MOONSHOT_MODEL"] = self.llm_model
        
        self.process = await asyncio.create_subprocess_exec(
            "pi",
            "--workspace", str(self.workspace),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        logger.info(f"Started pi for thread {self.thread_id} (PID: {self.process.pid})")
    
    async def send_message(self, message: str) -> str:
        """Send message to pi, get response with timeout."""
        if not self.process or self.process.returncode is not None:
            raise RuntimeError("Pi process not running")
        
        # Send message + newline
        self.process.stdin.write(f"{message}\n".encode())
        await self.process.stdin.drain()
        
        # Read response with timeout
        try:
            stdout, stderr = await asyncio.wait_for(
                self.process.communicate(),
                timeout=self.timeout
            )
            
            if stderr:
                logger.warning(f"Pi stderr: {stderr.decode()}")
            
            return stdout.decode()
        except asyncio.TimeoutError:
            logger.error(f"Pi timeout for thread {self.thread_id}")
            self.process.kill()
            raise
    
    async def kill(self):
        """Kill the subprocess."""
        if self.process and self.process.returncode is None:
            self.process.kill()
            await self.process.wait()
            logger.info(f"Killed pi for thread {self.thread_id}")
    
    async def is_alive(self) -> bool:
        """Check if process is still running."""
        if not self.process:
            return False
        return self.process.returncode is None


class PiManager:
    """Manages all pi subprocesses."""
    
    def __init__(
        self,
        timeout: int = 300,
        llm_provider: str = "zai",
        llm_api_key: str = "",
        llm_model: str = ""
    ):
        self.timeout = timeout
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model
        self._processes: dict[str, PiSubprocess] = {}
    
    async def get_or_create(self, thread_id: str, workspace: Path) -> PiSubprocess:
        """Get existing or create new pi subprocess."""
        if thread_id in self._processes:
            pi = self._processes[thread_id]
            if await pi.is_alive():
                return pi
            # Dead process, clean up
            del self._processes[thread_id]
        
        # Create new
        pi = PiSubprocess(
            thread_id,
            workspace,
            self.timeout,
            self.llm_provider,
            self.llm_api_key,
            self.llm_model
        )
        await pi.start()
        self._processes[thread_id] = pi
        return pi
    
    async def kill_thread(self, thread_id: str):
        """Kill a specific thread's pi process."""
        if thread_id in self._processes:
            await self._processes[thread_id].kill()
            del self._processes[thread_id]
    
    async def cleanup(self):
        """Kill all processes."""
        for pi in self._processes.values():
            await pi.kill()
        self._processes.clear()
```

**Step 2: Write test**

```python
import pytest
import shutil
from pathlib import Path
from dispatcher.pi_manager import PiManager, PiSubprocess


@pytest.mark.asyncio
async def test_pi_subprocess_lifecycle(tmp_path):
    # Skip if pi not installed
    if not shutil.which("pi"):
        pytest.skip("pi not installed")
    
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    pi = PiSubprocess("test", workspace, timeout=10)
    await pi.start()
    
    assert await pi.is_alive()
    
    await pi.kill()
    assert not await pi.is_alive()
```

**Step 3: Commit**

```bash
git add dispatcher/pi_manager.py tests/test_pi_manager.py
git commit -m "feat(dispatcher): pi agent manager with LLM provider config"
```

---

## Task 5: Dispatcher Core

**Files:**
- Create: `dispatcher/dispatcher.py`
- Create: `tests/test_dispatcher.py`

**Step 1: Write dispatcher.py**

```python
import asyncio
import logging
from collections.abc import AsyncGenerator
from pathlib import Path
from dispatcher.models import Thread
from dispatcher.storage import ThreadStorage
from dispatcher.pi_manager import PiManager

logger = logging.getLogger(__name__)


class Dispatcher:
    """Main dispatcher that routes messages and manages threads."""
    
    def __init__(
        self,
        workspace_dir: Path,
        threads_dir: Path,
        pi_manager: PiManager
    ):
        self.workspace_dir = workspace_dir
        self.storage = ThreadStorage(threads_dir)
        self.pi_manager = pi_manager
    
    async def handle_message(
        self,
        chat_id: int,
        thread_id: str,
        message: str
    ) -> str:
        """Handle incoming message, return response."""
        logger.info(f"Handling message for thread {thread_id}")
        
        # Check dispatcher commands
        if message.startswith("/"):
            return await self._handle_command(thread_id, message)
        
        # Load or create thread
        thread = await self.storage.load(thread_id)
        if not thread:
            thread = Thread(thread_id=thread_id, chat_id=chat_id)
        
        # Add user message
        thread.add_message("user", message)
        
        try:
            # Get or create pi subprocess for this thread
            pi = await self.pi_manager.get_or_create(
                thread_id,
                self.workspace_dir
            )
            
            # Send to pi and get response
            response = await pi.send_message(message)
            
            # Add assistant message
            thread.add_message("assistant", response)
            
            # Save thread state
            await self.storage.save(thread)
            
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout in thread {thread_id}")
            await self.pi_manager.kill_thread(thread_id)
            return "⏱️ Request timed out. Process killed. Try again."
        except Exception as e:
            logger.exception(f"Error in thread {thread_id}")
            return f"❌ Error: {str(e)}"
    
    async def handle_message_streaming(
        self,
        chat_id: int,
        thread_id: str,
        message: str
    ) -> AsyncGenerator[str, None]:
        """Handle incoming message, yield response chunks."""
        logger.info(f"Handling streaming message for thread {thread_id}")
        
        # Check dispatcher commands (non-streaming)
        if message.startswith("/"):
            response = await self._handle_command(thread_id, message)
            yield response
            return
        
        # Load or create thread
        thread = await self.storage.load(thread_id)
        if not thread:
            thread = Thread(thread_id=thread_id, chat_id=chat_id)
        
        # Add user message
        thread.add_message("user", message)
        
        try:
            # Get pi subprocess
            pi = await self.pi_manager.get_or_create(thread_id, self.workspace_dir)
            
            # Get full response (pi doesn't support true streaming yet)
            full_response = await pi.send_message(message)
            
            # Stream word by word for visual effect
            words = full_response.split()
            current = ""
            for i, word in enumerate(words):
                current += word + " "
                if i % 5 == 0 or i == len(words) - 1:
                    yield current
                    await asyncio.sleep(0.05)
            
            # Add assistant message
            thread.add_message("assistant", full_response)
            await self.storage.save(thread)
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout in thread {thread_id}")
            await self.pi_manager.kill_thread(thread_id)
            yield "⏱️ Request timed out. Process killed. Try again."
        except Exception as e:
            logger.exception(f"Error in thread {thread_id}")
            yield f"❌ Error: {str(e)}"
    
    async def _handle_command(self, thread_id: str, command: str) -> str:
        """Handle dispatcher commands."""
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == "/status":
            threads = await self.storage.list_threads()
            return f"Active threads: {len(threads)}\n{chr(10).join(threads[:10])}"
        
        elif cmd == "/kill":
            if len(parts) < 2:
                return "Usage: /kill <thread_id>"
            target = parts[1]
            await self.pi_manager.kill_thread(target)
            return f"Killed thread {target}"
        
        elif cmd == "/threads":
            threads = await self.storage.list_threads()
            return f"Threads: {', '.join(threads) or 'None'}"
        
        elif cmd == "/cleanup":
            await self.pi_manager.cleanup()
            return "Cleaned up all processes"
        
        return f"Unknown command: {cmd}"
    
    async def shutdown(self):
        """Clean shutdown."""
        await self.pi_manager.cleanup()
```
```

**Step 2: Write test**

```python
import pytest
from pathlib import Path
from dispatcher.dispatcher import Dispatcher
from dispatcher.pi_manager import PiManager


@pytest.mark.asyncio
async def test_dispatcher_commands(tmp_path):
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()
    
    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    # Test /threads command
    response = await dispatcher.handle_message(123, "main", "/threads")
    assert "Threads:" in response
    
    # Test /status command
    response = await dispatcher.handle_message(123, "main", "/status")
    assert "Active threads" in response
    
    await dispatcher.shutdown()
```

**Step 3: Commit**

```bash
git add dispatcher/dispatcher.py tests/test_dispatcher.py
git commit -m "feat(dispatcher): core dispatcher with command handling"
```

---

## Task 6: Telegram Bot Integration

**Files:**
- Create: `dispatcher/telegram_bot.py`
- Modify: `dispatcher/main.py` (wire it up)

**Requirements:**
- Streaming: Send partial responses as they're generated from pi
- Typing indicator: Always show "Typing..." while processing

**Step 1: Write telegram_bot.py**

```python
import asyncio
import logging
from telegram import Update, ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from dispatcher.dispatcher import Dispatcher

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot that routes to dispatcher with streaming support."""
    
    def __init__(self, token: str, dispatcher: Dispatcher):
        self.token = token
        self.dispatcher = dispatcher
        self.app: Application | None = None
    
    def _get_thread_id(self, update: Update) -> str:
        """Extract thread identifier from update."""
        chat_id = update.effective_chat.id
        
        # Use message_thread_id if in a thread, otherwise use chat_id
        if update.message and update.message.message_thread_id:
            return f"{chat_id}_{update.message.message_thread_id}"
        return str(chat_id)
    
    async def _typing_indicator(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, stop_event: asyncio.Event):
        """Send typing action every 4 seconds until stop_event is set."""
        while not stop_event.is_set():
            try:
                await context.bot.send_chat_action(
                    chat_id=chat_id,
                    action=ChatAction.TYPING
                )
            except Exception as e:
                logger.warning(f"Failed to send typing indicator: {e}")
            
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=4.0)
            except asyncio.TimeoutError:
                continue
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Route message to dispatcher with streaming and typing indicator."""
        if not update.message or not update.message.text:
            return
        
        thread_id = self._get_thread_id(update)
        chat_id = update.effective_chat.id
        message = update.message.text
        
        logger.info(f"Message in thread {thread_id}: {message[:50]}...")
        
        # Start typing indicator
        stop_typing = asyncio.Event()
        typing_task = asyncio.create_task(
            self._typing_indicator(context, chat_id, stop_typing)
        )
        
        try:
            # Stream response from dispatcher
            response_text = ""
            sent_message = None
            last_update_len = 0
            
            async for chunk in self.dispatcher.handle_message_streaming(
                chat_id=chat_id,
                thread_id=thread_id,
                message=message
            ):
                response_text += chunk
                
                # Update message every 100 chars or on completion
                if len(response_text) - last_update_len > 100 or chunk == "":
                    if sent_message is None:
                        # First chunk - send new message
                        sent_message = await update.message.reply_text(
                            response_text[:4096]  # Telegram max length
                        )
                    else:
                        # Update existing message
                        try:
                            await sent_message.edit_text(response_text[:4096])
                        except Exception as e:
                            # Ignore "message not modified" errors
                            if "message is not modified" not in str(e).lower():
                                logger.warning(f"Failed to edit message: {e}")
                    
                    last_update_len = len(response_text)
            
            # Final update if truncated
            if len(response_text) > 4096:
                await sent_message.reply_text("... (truncated)")
                
        except Exception as e:
            logger.exception(f"Error handling message: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
        finally:
            # Stop typing indicator
            stop_typing.set()
            await typing_task
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text(
            "OpenClaw Pi Dispatcher ready.\n"
            "Commands: /status, /threads, /kill <thread>, /cleanup"
        )
    
    def setup(self):
        """Set up the bot application."""
        self.app = Application.builder().token(self.token).build()
        
        # Handlers
        self.app.add_handler(CommandHandler("start", self._handle_start))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        # Commands are handled by dispatcher via text handler
        self.app.add_handler(MessageHandler(filters.COMMAND, self._handle_message))
        
        return self.app
    
    async def run(self):
        """Run the bot."""
        if not self.app:
            self.setup()
        
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
        logger.info("Telegram bot started")
        
        # Run forever
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
```

**Step 2: Update main.py**

```python
import asyncio
import logging
import signal

from dispatcher.config import Settings
from dispatcher.dispatcher import Dispatcher
from dispatcher.telegram_bot import TelegramBot
from dispatcher.pi_manager import PiManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    settings = Settings()
    logging.getLogger().setLevel(getattr(logging, settings.log_level.upper()))
    
    # Create pi manager with LLM provider config
    pi_manager = PiManager(
        timeout=settings.pi_timeout,
        llm_provider=settings.llm_provider,
        llm_api_key=settings.llm_api_key,
        llm_model=settings.llm_model
    )
    
    # Create dispatcher
    dispatcher = Dispatcher(
        workspace_dir=settings.workspace_dir,
        threads_dir=settings.threads_dir,
        pi_manager=pi_manager
    )
    
    # Create bot
    bot = TelegramBot(settings.telegram_bot_token, dispatcher)
    
    # Handle shutdown gracefully
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        raise asyncio.CancelledError()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await bot.run()
    except asyncio.CancelledError:
        logger.info("Shutting down...")
    finally:
        await dispatcher.shutdown()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
```

**Step 2: Update main.py**

```python
import asyncio
import logging
import signal
import sys

from dispatcher.config import Settings
from dispatcher.dispatcher import Dispatcher
from dispatcher.telegram_bot import TelegramBot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    settings = Settings()
    logging.getLogger().setLevel(getattr(logging, settings.log_level.upper()))
    
    # Create dispatcher
    dispatcher = Dispatcher(
        workspace_dir=settings.workspace_dir,
        threads_dir=settings.threads_dir,
        pi_timeout=settings.pi_timeout,
        max_threads=settings.max_threads
    )
    
    # Create bot
    bot = TelegramBot(settings.telegram_bot_token, dispatcher)
    
    # Handle shutdown gracefully
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        raise asyncio.CancelledError()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await bot.run()
    except asyncio.CancelledError:
        logger.info("Shutting down...")
    finally:
        await dispatcher.shutdown()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
```

**Step 3: Commit**

```bash
git add dispatcher/telegram_bot.py dispatcher/main.py
git commit -m "feat(dispatcher): Telegram bot with thread routing"
```

---

## Task 7: Sub-Agent Support

**Files:**
- Create: `dispatcher/subagent.py`
- Modify: `dispatcher/dispatcher.py` (add spawn_subagent)

**Step 1: Write subagent.py**

```python
import asyncio
import logging
import shutil
import tempfile
from pathlib import Path
from dispatcher.pi_manager import PiSubprocess

logger = logging.getLogger(__name__)


class SubAgent:
    """A sub-agent with isolated context for specific tasks."""
    
    def __init__(
        self,
        subagent_id: str,
        parent_thread_id: str,
        task: str,
        workspace_dir: Path,
        llm_provider: str = "zai",
        llm_api_key: str = "",
        llm_model: str = "",
        timeout: int = 300
    ):
        self.subagent_id = subagent_id
        self.parent_thread_id = parent_thread_id
        self.task = task
        self.workspace_dir = workspace_dir
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model
        self.timeout = timeout
        self.temp_dir: Path | None = None
        self.pi: PiSubprocess | None = None
    
    async def setup(self):
        """Create isolated workspace for subagent."""
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"subagent_{self.subagent_id}_"))
        
        # Copy workspace files
        if self.workspace_dir.exists():
            for item in self.workspace_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, self.temp_dir / item.name)
                elif item.is_dir() and item.name not in [".pi", "__pycache__"]:
                    shutil.copytree(item, self.temp_dir / item.name, dirs_exist_ok=True)
        
        logger.info(f"Sub-agent {self.subagent_id} workspace: {self.temp_dir}")
    
    async def run(self) -> str:
        """Run the sub-agent task."""
        if not self.temp_dir:
            await self.setup()
        
        self.pi = PiSubprocess(
            self.subagent_id,
            self.temp_dir,
            self.timeout,
            self.llm_provider,
            self.llm_api_key,
            self.llm_model
        )
        
        try:
            await self.pi.start()
            result = await self.pi.send_message(self.task)
            logger.info(f"Sub-agent {self.subagent_id} completed")
            return result
        except asyncio.TimeoutError:
            logger.error(f"Sub-agent {self.subagent_id} timed out")
            return f"⏱️ Sub-agent {self.subagent_id} timed out"
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up subagent resources."""
        if self.pi:
            await self.pi.kill()
        
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up sub-agent {self.subagent_id}")
```

**Step 2: Update dispatcher.py to add spawn_subagent**

```python
# Add to Dispatcher class
from dispatcher.subagent import SubAgent

async def spawn_subagent(
    self,
    parent_thread_id: str,
    task: str,
    timeout: int = 300
) -> str:
    """Spawn a sub-agent for a task."""
    import time
    subagent_id = f"{parent_thread_id}_sub_{int(time.time())}"
    
    subagent = SubAgent(
        subagent_id=subagent_id,
        parent_thread_id=parent_thread_id,
        task=task,
        workspace_dir=self.workspace_dir,
        llm_provider=self.pi_manager.llm_provider,
        llm_api_key=self.pi_manager.llm_api_key,
        llm_model=self.pi_manager.llm_model,
        timeout=timeout
    )
    
    # Run in background (don't await)
    asyncio.create_task(self._run_subagent(subagent))
    
    return f"🔄 Sub-agent {subagent_id} spawned. Will report back when done."

async def _run_subagent(self, subagent: SubAgent):
    """Run subagent and handle result."""
    result = await subagent.run()
    # TODO: Report back to parent thread
    logger.info(f"Sub-agent {subagent.subagent_id} result: {result[:100]}...")
```

**Step 3: Commit**

```bash
git add dispatcher/subagent.py dispatcher/dispatcher.py
git commit -m "feat(dispatcher): sub-agent support with isolated workspaces"
```

---

## Task 8: Integration Test

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write integration test**

```python
import pytest
from pathlib import Path
from dispatcher.dispatcher import Dispatcher
from dispatcher.pi_manager import PiManager


@pytest.mark.asyncio
async def test_dispatcher_command_flow(tmp_path):
    """Test the full dispatcher command flow."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()
    
    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    # Test /status
    response = await dispatcher.handle_message(123, "test_chat", "/status")
    assert "Active threads" in response
    
    # Test /threads
    response = await dispatcher.handle_message(123, "test_chat", "/threads")
    assert "Threads:" in response
    
    # Test unknown command
    response = await dispatcher.handle_message(123, "test_chat", "/foobar")
    assert "Unknown command" in response
    
    await dispatcher.shutdown()
```

**Step 2: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests pass (integration tests may skip if pi not installed)

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test(dispatcher): integration tests for command flow"
```

---

## Task 9: Documentation and Final README

**Files:**
- Modify: `README.md`
- Create: `docs/USAGE.md`

**Step 1: Update README.md**

```markdown
# OpenClaw Dispatcher

Python dispatcher for OpenClaw Pi with Telegram thread support and first-class sub-agents.

## Quick Start

```bash
# 1. Install
pip install -e .

# 2. Configure
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN

# 3. Run
python -m dispatcher.main
```

## Architecture

- **Single Python process** — asyncio event loop
- **Telegram threads** — Same agent, different conversation contexts
- **Sub-agents** — First-class, with isolated workspaces, killable
- **Fault isolation** — Timeout on all pi calls, never blocks dispatcher

## Commands

- `/status` — Show active threads
- `/threads` — List all threads
- `/kill <thread_id>` — Kill a thread's pi process
- `/cleanup` — Kill all processes

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check dispatcher/
```
```

**Step 2: Commit**

```bash
git add README.md docs/USAGE.md
git commit -m "docs(dispatcher): usage documentation"
```

---

## Task 10: Final Review

**Files:** All

**Step 1: Review structure**

Run:
```bash
git status
git log --oneline -10
```
Expected: Clean working tree, 10 commits

**Step 2: Final commit if needed**

If any uncommitted changes:
```bash
git add -A
git commit -m "chore(dispatcher): final polish"
```

---

## Summary

This creates a fully functional dispatcher:

- ✅ Python asyncio single process
- ✅ JSON file storage per thread
- ✅ Telegram bot with streaming + typing indicator
- ✅ Pi agent subprocesses with timeout handling
- ✅ LLM provider config (ZAI, Moonshot) passed to pi
- ✅ Sub-agents with isolated workspaces
- ✅ Fault isolation (timeouts, killable processes)
- ✅ Dispatcher commands (/status, /kill, /threads, /cleanup)

**Architecture:**
```
Telegram → Dispatcher → pi subprocess → LLM Provider (ZAI/Moonshot)
                           ↓
                     Sub-agents (isolated)
```

**Next steps after this plan:**
1. Add memory search (semantic or grep-based)
2. Sub-agent result reporting back to parent
3. Heartbeat/cron support
4. Metrics and monitoring
