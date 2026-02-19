# PRD: Implement notify() Function for Jobs

## Overview

**Issue**: #73  
**Status**: Open  
**Priority**: High  
**Created**: 2026-02-19

Implement the `notify()` function so jobs can send messages to users via Telegram or CLI. Currently the function exists in `ExecutionContext` but is not wired up to any notifier implementation.

---

## Problem Statement

Jobs can call `await notify("message")` in their code, but:

1. `ExecutionContext.notifier` is always `None`
2. The `notify()` method checks for notifier existence but does nothing if missing
3. Users cannot receive messages from their scheduled jobs
4. The job API documentation already promises this functionality

### Current Code State

```python
# src/cron/executor.py
@dataclass
class ExecutionContext:
    notifier: Any | None = None  # Always None

    async def notify(self, message: str) -> None:
        if self.notifier:  # Never true
            await self.notifier.send(message)

# src/cron/scheduler.py
context = ExecutionContext(
    job_id=job.job_id,
    job_name=job.name,
    memory_store=self._store,
    notifier=None,  # TODO: Inject notifier when available
)
```

---

## Solution Overview

### Architecture

Create a notifier abstraction that can send messages through different channels (Telegram, CLI). Wire it through the dependency injection chain from Alfred → Scheduler → ExecutionContext.

### Components

1. **Notifier Interface** - Abstract base class for all notifiers
2. **TelegramNotifier** - Sends messages via Telegram bot
3. **CLINotifier** - Outputs to console (for CLI interface)
4. **Wiring** - Pass notifier through Alfred → Scheduler → ExecutionContext

---

## Technical Design

### 1. Notifier Interface

```python
# src/cron/notifier.py
from abc import ABC, abstractmethod

class Notifier(ABC):
    """Abstract interface for sending notifications to users."""
    
    @abstractmethod
    async def send(self, message: str) -> None:
        """Send a notification message."""
        pass
```

### 2. Concrete Notifiers

```python
class TelegramNotifier(Notifier):
    """Send notifications via Telegram bot."""
    
    def __init__(self, bot, chat_id: int):
        self.bot = bot
        self.chat_id = chat_id
    
    async def send(self, message: str) -> None:
        await self.bot.send_message(chat_id=self.chat_id, text=message)

class CLINotifier(Notifier):
    """Send notifications to CLI output."""
    
    def __init__(self, output_stream=None):
        self.output = output_stream or sys.stdout
    
    async def send(self, message: str) -> None:
        self.output.write(f"[JOB NOTIFICATION] {message}\n")
```

### 3. Wiring

```python
# Alfred creates and passes notifier
class Alfred:
    def __init__(self, config: Config):
        # ... existing init ...
        
        # Create notifier based on interface
        if self.telegram_bot:
            self.notifier = TelegramNotifier(self.telegram_bot, self.chat_id)
        else:
            self.notifier = CLINotifier()
        
        # Pass to scheduler
        self.cron_scheduler = CronScheduler(
            store=CronStore(data_dir),
            data_dir=data_dir,
            notifier=self.notifier,
        )
```

---

## Milestones

| # | Milestone | Status | Description |
|---|-----------|--------|-------------|
| M1 | Notifier Interface | 🔲 Todo | Create `Notifier` ABC in `src/cron/notifier.py` |
| M2 | Telegram Notifier | 🔲 Todo | Implement `TelegramNotifier` class |
| M3 | CLI Notifier | 🔲 Todo | Implement `CLINotifier` class |
| M4 | Scheduler Wiring | 🔲 Todo | Add `notifier` parameter to `CronScheduler`, pass to `ExecutionContext` |
| M5 | Alfred Integration | 🔲 Todo | Create notifier in `Alfred.__init__`, inject into scheduler |
| M6 | Testing | 🔲 Todo | Unit tests for notifiers, integration test for notify() flow |
| M7 | Documentation | 🔲 Todo | Update `docs/job-api.md` to remove "not implemented" warnings |

---

## Success Criteria

- [ ] Jobs can call `await notify("message")` and message reaches user
- [ ] Telegram interface: messages appear in chat
- [ ] CLI interface: messages appear in console output
- [ ] Notifier is properly injected through dependency chain
- [ ] Tests cover all notifier implementations
- [ ] Documentation updated to reflect working feature

---

## Integration Points

| Component | Change |
|-----------|--------|
| `src/cron/notifier.py` | New file with Notifier ABC and implementations |
| `src/cron/scheduler.py` | Accept `notifier` parameter, pass to ExecutionContext |
| `src/cron/executor.py` | Import Notifier type, add type hints |
| `src/alfred.py` | Create notifier instance, inject into CronScheduler |
| `src/interfaces/telegram.py` | May need to expose bot for notifier |
| `docs/job-api.md` | Remove "not implemented" warnings |
| `docs/notifier.md` | Update to reflect implemented status |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-19 | Notifier ABC | Allows multiple implementations (Telegram, CLI, future HTTP) |
| 2026-02-19 | Inject via constructor | Follows existing pattern for memory_store, keeps testable |

---

## Notes

- The `ExecutionContext.notifier` field already exists and is typed as `Any | None`
- After implementation, change type hint to `Notifier | None`
- Consider rate limiting for notify() to prevent spam from misbehaving jobs
