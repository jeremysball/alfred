# Notifier Architecture

This document describes the notifier pattern for sending messages from jobs and other background processes to users.

## Overview

The notifier provides a bridge between background jobs and user-facing interfaces (Telegram, CLI). It allows:

- Jobs to send notifications to users
- System processes to alert users of events
- Decoupled communication between execution context and UI layer

## Current Status

**⚠️ Not Implemented**: The notifier infrastructure exists but is not yet wired up. Jobs calling `notify()` will silently do nothing.

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
│                   Notifier Interface                        │
│              (needs to be defined/injected)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
┌──────────────────┐      ┌──────────────────┐
│  Telegram Bot    │      │      CLI         │
│  send_message()  │      │  print/output    │
└──────────────────┘      └──────────────────┘
```

### ExecutionContext

The `ExecutionContext` class provides the `notify()` method to jobs:

```python
@dataclass
class ExecutionContext:
    job_id: str
    job_name: str
    memory_store: Any | None = None
    notifier: Any | None = None  # Currently always None

    async def notify(self, message: str) -> None:
        if self.notifier:
            await self.notifier.send(message)
```

### Injection Points

Currently, the scheduler creates `ExecutionContext` with `notifier=None`:

```python
# src/cron/scheduler.py
context = ExecutionContext(
    job_id=job.job_id,
    job_name=job.name,
    memory_store=self._store,
    notifier=None,  # TODO: Inject notifier when available
)
```

## Implementation Path

To make `notify()` work, the following steps are needed:

### 1. Define Notifier Interface

```python
from abc import ABC, abstractmethod

class Notifier(ABC):
    @abstractmethod
    async def send(self, message: str) -> None:
        """Send a notification message to the user."""
        pass
```

### 2. Create Concrete Notifiers

**Telegram Notifier:**
```python
class TelegramNotifier(Notifier):
    def __init__(self, bot, chat_id: int):
        self.bot = bot
        self.chat_id = chat_id
    
    async def send(self, message: str) -> None:
        await self.bot.send_message(chat_id=self.chat_id, text=message)
```

**CLI Notifier:**
```python
class CLINotifier(Notifier):
    def send(self, message: str) -> None:
        print(f"[NOTIFICATION] {message}")
```

### 3. Wire Up in Alfred

```python
class Alfred:
    def __init__(self, config: Config):
        # ... existing initialization ...
        
        # Create notifier based on interface
        if telegram_bot:
            self.notifier = TelegramNotifier(telegram_bot, chat_id)
        else:
            self.notifier = CLINotifier()
        
        # Pass to scheduler
        self.cron_scheduler = CronScheduler(
            store=CronStore(data_dir),
            data_dir=data_dir,
            notifier=self.notifier,  # Inject here
        )
```

### 4. Update CronScheduler

```python
class CronScheduler:
    def __init__(self, ..., notifier: Notifier | None = None):
        # ...
        self._notifier = notifier
    
    async def _execute_job(self, job: RunnableJob) -> None:
        context = ExecutionContext(
            job_id=job.job_id,
            job_name=job.name,
            memory_store=self._store,
            notifier=self._notifier,  # Pass through
        )
        # ... execute with context
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

- `src/cron/executor.py` - ExecutionContext implementation
- `src/cron/scheduler.py` - CronScheduler, creates ExecutionContext
- `docs/job-api.md` - User-facing job documentation
