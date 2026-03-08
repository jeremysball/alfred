# PRD: AlfredCore Refactoring and Standalone Cron Daemon

## Overview

**Issue**: #119
**Parent**: #76 (Session Summarization)
**Status**: Planning
**Priority**: High
**Created**: 2026-03-07

Extract common service initialization into `AlfredCore` class shared between Alfred CLI and LittleAlfred (standalone cron daemon). Enables reliable background session summarization without requiring running Alfred instance.

---

## Problem Statement

Current architecture has tight coupling between cron jobs and Alfred:

```
Current Flow (Broken):
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Cron Daemon   │────▶│  ServiceLocator  │────▶│   Alfred    │
│   (no services) │     │  (empty if no    │     │  (must be   │
│                 │     │   Alfred running)│     │   running)  │
└─────────────────┘     └──────────────────┘     └─────────────┘
```

**Issues:**
- Cron jobs fail if Alfred isn't running (ServiceLocator empty)
- Can't run session summarization in background
- No clean separation between UI and background worker concerns
- Future client/server split blocked by monolithic Alfred class

---

## Solution

### New Architecture

```
Proposed Architecture:
┌─────────────────────────────────────────────────────────────┐
│                      AlfredCore                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ SQLiteStore │  │  LLMClient  │  │  SessionSummarizer  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │Embedder     │  │MemoryStore  │  │  SessionManager     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         ▲                           ▲
         │                           │
┌────────┴────────┐        ┌────────┴────────┐
│     Alfred      │        │   LittleAlfred  │
│  (CLI/Telegram) │        │  (Background)   │
└─────────────────┘        └─────────────────┘
```

### AlfredCore Responsibilities

- Initialize all shared services (SQLiteStore, LLM, embedder, etc.)
- Populate ServiceLocator for dependency injection
- Provide property accessors for common components
- No UI/telegram/cron logic - pure services

### Alfred Responsibilities (Reduced)

- Create AlfredCore instance
- Initialize UI layer (TUI or Telegram)
- Handle user input/output
- Register UI-specific tools

### LittleAlfred Responsibilities (New)

- Create AlfredCore instance
- Initialize CronScheduler
- Run background job loop
- No UI components

---

## Acceptance Criteria

- [x] `AlfredCore` class extracted with all shared services
- [x] `Alfred` refactored to use `AlfredCore`
- [x] `AlfredDaemon` class created using `AlfredCore`
- [x] Cron daemon can run standalone (no Alfred running)
- [x] Session summarization works in background daemon
- [x] No code duplication between Alfred and AlfredDaemon
- [x] ServiceLocator populated by AlfredCore (not Alfred)
- [x] Tests for AlfredCore initialization
- [x] Tests for AlfredDaemon standalone operation

---

## Architecture

### AlfredCore Class

```python
# src/alfred/core.py
class AlfredCore:
    """Core Alfred services (shared between CLI, Telegram, and daemon)."""
    
    def __init__(self, config: Config) -> None:
        self.config = config
        self._init_services()
        self._register_in_locator()
    
    def _init_services(self) -> None:
        """Initialize all shared services."""
        self.sqlite_store = SQLiteStore(self.config.data_dir / "alfred.db")
        self.embedder = create_provider(self.config)
        self.llm = LLMFactory.create(self.config)
        self.memory_store = create_memory_store(self.config, self.embedder)
        
        SessionManager.initialize(data_dir=self.config.data_dir)
        self.session_manager = SessionManager.get_instance()
        
        self.summarizer = SummarizerFactory(
            store=self.sqlite_store,
            llm_client=self.llm,
            embedder=self.embedder,
        ).create()
    
    def _register_in_locator(self) -> None:
        """Register services in ServiceLocator for cron jobs."""
        ServiceLocator.register(SQLiteStore, self.sqlite_store)
        ServiceLocator.register(EmbeddingProvider, self.embedder)
        ServiceLocator.register(LLMProvider, self.llm)
        ServiceLocator.register(SessionManager, self.session_manager)
        ServiceLocator.register(SessionSummarizer, self.summarizer)
    
    @property
    def cron_scheduler(self) -> CronScheduler:
        """Get configured cron scheduler."""
        return CronScheduler(
            store=CronStore(self.config.data_dir),
            data_dir=self.config.data_dir,
        )
```

### Refactored Alfred

```python
# src/alfred/alfred.py
class Alfred:
    """Alfred with UI (CLI or Telegram)."""
    
    def __init__(self, config: Config, telegram_mode: bool = False) -> None:
        # Core services
        self.core = AlfredCore(config)
        
        # UI-specific initialization
        self._init_ui(telegram_mode)
        
        # Tools that need core services
        self._init_tools()
        
        # Agent with LLM from core
        self.agent = Agent(self.core.llm, self.tools)
```

### New LittleAlfred

```python
# src/alfred/cron/daemon_runner.py
class LittleAlfred:
    """Standalone cron daemon (no UI)."""
    
    def __init__(self, config: Config) -> None:
        self.core = AlfredCore(config)
        self.scheduler = self.core.cron_scheduler
    
    async def run(self) -> None:
        """Start the daemon and run forever."""
        await self.scheduler.start()
        
        # Keep running until signal
        while True:
            await asyncio.sleep(1)
```

### CLI Entry Point

```python
# src/alfred/cli/cron.py
@cli.command()
def daemon():
    """Run standalone cron daemon."""
    config = load_config()
    daemon = LittleAlfred(config)
    asyncio.run(daemon.run())
```

---

## Implementation Phases

### Phase 1: Create AlfredCore

- Create `src/alfred/core.py` with `AlfredCore` class
- Extract service initialization from `Alfred.__init__`
- Move ServiceLocator registration to `AlfredCore`
- Tests for `AlfredCore` initialization

### Phase 2: Refactor Alfred

- Update `Alfred` to use `AlfredCore`
- Remove duplicate initialization code
- Ensure all existing functionality works
- Tests pass

### Phase 3: Create LittleAlfred

- Create `src/alfred/cron/daemon_runner.py`
- Implement `LittleAlfred` class using `AlfredCore`
- Add CLI command: `alfred cron daemon`
- Tests for standalone daemon operation

### Phase 4: Verification

- Cron daemon runs without Alfred
- Session summarization works in background
- Alfred CLI still works normally
- Telegram mode still works
- All tests pass

---

## File Structure

```
src/alfred/
├── core.py                    # NEW: AlfredCore class
├── alfred.py                  # REFACTORED: Uses AlfredCore
├── cron/
│   ├── daemon_runner.py       # NEW: LittleAlfred class
│   └── ...
└── ...
```

---

## Configuration

No new config needed. Uses existing `Config` class.

Optional future enhancement:
```toml
[cron]
enabled = true                 # Enable background cron
run_as_daemon = true          # Run standalone vs in-process
```

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-07 | Extract AlfredCore | Share services between CLI and daemon without duplication |
| 2026-03-07 | ServiceLocator in AlfredCore | Single point of registration, works for both modes |
| 2026-03-07 | Standalone LittleAlfred | Enables background processing without running Alfred |
| 2026-03-07 | Keep CronScheduler shared | Both modes use same scheduler, just different lifecycles |

---

## Dependencies

- ✅ PRD #76 (Session Summarization) - Services already exist
- Existing: ServiceLocator pattern
- Existing: CronScheduler infrastructure

---

## Future: Client-Server Architecture

This refactoring enables future client-server split:

```
┌─────────────┐         ┌──────────────────┐
│ AlfredClient│◄───────►│   AlfredServer   │
│  (UI only)  │  HTTP   │  (AlfredCore +   │
│             │         │   LittleAlfred)    │
└─────────────┘         └──────────────────┘
```

AlfredCore becomes the server-side service container.

---

## Acceptance Criteria (Detailed)

- [ ] `src/alfred/core.py` exists with `AlfredCore` class
- [ ] `AlfredCore` initializes: SQLiteStore, embedder, LLM, memory store, SessionManager, summarizer
- [ ] `AlfredCore` registers all services in ServiceLocator
- [ ] `Alfred` uses `self.core = AlfredCore(config)`
- [ ] No service initialization code duplicated in `Alfred`
- [ ] `src/alfred/cron/daemon_runner.py` exists with `LittleAlfred` class
- [ ] `LittleAlfred` uses `self.core = AlfredCore(config)`
- [ ] CLI command `alfred cron daemon` starts standalone daemon
- [ ] Daemon runs session summarization without Alfred running
- [ ] All existing tests pass
- [ ] New tests for AlfredCore initialization
- [ ] New tests for LittleAlfred standalone operation
