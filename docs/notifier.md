# Notifier Architecture

This document describes the notifier pattern for sending messages from jobs and other background processes to users.

## Overview

The notifier provides a bridge between background jobs and user-facing interfaces (Telegram, CLI). It allows:

- Jobs to send notifications to users
- System processes to alert users of events
- Decoupled communication between execution context and UI layer

## Current Status

**✅ Implemented**: The notifier infrastructure is fully wired up. Jobs can call `await notify("message")` to send notifications to users via Telegram (when running in Telegram mode) or CLI output (when running in CLI mode).

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Job Code                             │
│                  await notify("Hello!")                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              ExecutionContext.notify()                      │
│              (src/cron/executor.py)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Notifier (ABC)                            │
│              (src/cron/notifier.py)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
┌──────────────────┐      ┌──────────────────┐
│ TelegramNotifier │      │   CLINotifier    │
│  Bot.send_       │      │  stdout write    │
│  message()       │      │                  │
└──────────────────┘      └──────────────────┘
```

### ExecutionContext

The `ExecutionContext` class provides the `notify()` method to jobs:

```python
@dataclass
class ExecutionContext:
    job_id: str
    job_name: str
    notifier: Notifier | None = None
    chat_id: int | None = None  # Per-job routing

    async def notify(self, message: str) -> None:
        if self.notifier:
            await self.notifier.send(message, chat_id=self.chat_id)
```

### Injection Points

The scheduler creates `ExecutionContext` with the notifier injected by Alfred:

```python
# src/cron/scheduler.py
context = ExecutionContext(
    job_id=job.job_id,
    job_name=job.name,
    notifier=self._notifier,
    chat_id=job_model.chat_id if job_model else None,
)
```

## Implementation Details

### Notifier Interface

```python
from abc import ABC, abstractmethod

class Notifier(ABC):
    @abstractmethod
    async def send(self, message: str, chat_id: int | None = None) -> None:
        """Send a notification message to the user."""
        pass
```

### Concrete Notifiers

**Telegram Notifier:**
```python
class TelegramNotifier(Notifier):
    def __init__(self, bot: Bot, default_chat_id: int | None = None):
        self.bot = bot
        self.default_chat_id = default_chat_id

    async def send(self, message: str, chat_id: int | None = None) -> None:
        target = chat_id or self.default_chat_id
        if target is None:
            logger.warning("No chat_id available for notification")
            return

        # Truncate if needed (Telegram limit is 4096)
        if len(message) > 4093:
            message = message[:4093] + "..."

        try:
            await self.bot.send_message(chat_id=target, text=message)
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
```

**CLI Notifier:**
```python
class CLINotifier(Notifier):
    def __init__(self, output_stream: TextIO | None = None):
        self.output = output_stream or sys.stdout

    async def send(self, message: str, chat_id: int | None = None) -> None:
        # Formats with timestamp and writes to output stream
        self.output.write(f"[{timestamp} JOB NOTIFICATION] {message}\n")
```

### Alfred Integration

```python
class Alfred:
    def __init__(self, config: Config, telegram_mode: bool = False):
        # Create notifier based on mode
        if telegram_mode:
            self._telegram_bot = Bot(token=config.telegram_bot_token)
            # Read chat_id from telegram state file
            chat_id = ...  # From data/telegram_state.json
            notifier = TelegramNotifier(bot=self._telegram_bot, default_chat_id=chat_id)
        else:
            notifier = CLINotifier()

        # Pass to scheduler
        self.cron_scheduler = CronScheduler(
            store=CronStore(data_dir),
            data_dir=data_dir,
            notifier=notifier,
        )
```

### Chat ID Tracking

The `TelegramInterface` tracks incoming chat IDs and persists them to `data/telegram_state.json`:

```python
class TelegramInterface:
    def _track_chat_id(self, update: Update) -> None:
        if update.effective_chat:
            new_chat_id = update.effective_chat.id
            if new_chat_id != self._chat_id:
                self._chat_id = new_chat_id
                self._save_state()
```

## Design Decisions

### Why Injection?

The notifier is injected rather than being a singleton to support:
- Multiple interfaces (Telegram, CLI, HTTP API)
- Different chat/user contexts per session
- Testing with mock notifiers

### Why Async?

`notify()` is async because:
- Telegram API calls are network I/O
- Allows batching or rate limiting
- Prevents blocking job execution

### Security Considerations

- Jobs cannot impersonate Alfred's responses
- Notifications are clearly marked as "from job"
- Rate limiting may be needed to prevent spam

## Related Code

- `src/cron/notifier.py` — Notifier ABC, TelegramNotifier, CLINotifier
- `src/cron/executor.py` — ExecutionContext implementation
- `src/cron/scheduler.py` — CronScheduler, creates ExecutionContext
- `src/alfred.py` — Creates and injects notifier
- `src/interfaces/telegram.py` — Chat ID tracking

## Related Documentation

- [Job API Reference](job-api.md) — Functions available to job code
- [Cron Jobs](cron-jobs.md) — Overview of the cron system
- [Architecture](ARCHITECTURE.md) — System design
