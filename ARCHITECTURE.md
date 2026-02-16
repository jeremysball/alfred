# OpenClaw Pi - Architecture

## Core Principles

### 1. Dispatcher-First Design

The outermost layer is a **dispatcher LLM session** that never blocks. Its job:
- Route incoming messages to correct context
- Spawn sub-agents for tasks
- Handle timeouts gracefully
- Report status even when everything else hangs

```
┌─────────────────────────────────────────────────────────────┐
│                    DISPATCHER (LLM)                         │
│                                                             │
│  - Never hangs (enforced timeouts)                         │
│  - Routes to correct thread/session                        │
│  - Spawns sub-agents                                       │
│  - Reports errors/status to user                           │
│  - Survives subprocess failures                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   ┌─────────┐         ┌─────────┐         ┌─────────┐
   │ Thread 1│         │ Thread 2│         │ Thread N│
   │ (Main)  │         │ (Sub    │         │ (Sub    │
   │         │         │  agent) │         │  agent) │
   └─────────┘         └─────────┘         └─────────┘
        │                   │                   │
        ▼                   ▼                   ▼
   [Context 1]         [Context 2]         [Context N]
   AGENTS.md           AGENTS.md           AGENTS.md
   MEMORY.md           memory/             memory/
   memory/             skills/             skills/
```

### 2. Thread Isolation (Telegram)

Each Telegram thread = isolated context:
- Own workspace directory
- Own MEMORY.md
- Own daily memory files
- Own skill set
- Own pi subprocess

Threads can be:
- **Main** — User's primary conversation
- **Sub-agent** — Spawned for specific tasks
- **Worker** — Background tasks (research, etc.)

### 3. First-Class Sub-Sessions

Sub-agents are NOT second-class citizens:
- Full tool access (not limited subset)
- Can spawn their own sub-agents (with depth limit)
- Can write to shared memory (with namespacing)
- Report progress back to parent
- Independent timeouts

```
Main Thread
    │
    ├── Sub-agent: "Research X" (timeout: 5min)
    │       │
    │       └── Sub-agent: "Deep dive Y" (timeout: 2min)
    │
    └── Sub-agent: "Implement Z" (timeout: 10min)
```

### 4. Fault Isolation

**Nothing hangs the dispatcher:**
- All pi calls have enforced timeouts
- Subprocess failures are caught
- Network issues don't block
- User can always send commands to dispatcher

**Failure modes handled:**
- Pi process hangs → kill after timeout, report error
- LLM API timeout → fallback model or report
- Context too large → automatic compaction
- Sub-agent crash → report failure, continue

## Components

### 1. Dispatcher (`dispatcher/`)

The orchestrator process:
- Telegram bot interface
- Message routing to threads
- Sub-agent lifecycle management
- Timeout enforcement
- Health monitoring

```python
# dispatcher/main.py (conceptual)
async def handle_message(update):
    thread_id = update.message.message_thread_id or "main"
    
    # Route to correct thread
    response = await dispatcher.route(thread_id, update.message.text)
    
    # Always respond (even on error)
    await send_response(update, response)
```

### 2. Thread Manager (`thread_manager/`)

Manages isolated contexts:
- Create/destroy thread workspaces
- Load/save thread state
- Switch between threads
- Namespace memory

```
threads/
├── main/
│   ├── workspace/
│   │   ├── AGENTS.md
│   │   ├── MEMORY.md
│   │   └── memory/
│   └── state.json
├── thread_123/
│   ├── workspace/
│   └── state.json
└── thread_456/
    └── ...
```

### 3. Sub-Agent Spawner (`spawner/`)

Spawns and manages sub-agents:
- Create isolated subprocess
- Inject context from parent
- Stream output back
- Enforce timeouts
- Clean up on completion/failure

```python
class SubAgent:
    def __init__(self, task, parent_context, timeout=300):
        self.process = None
        self.timeout = timeout
    
    async def run(self):
        self.process = await asyncio.create_subprocess_exec(
            "pi", "--context", self.context_path,
            stdout=asyncio.subprocess.PIPE
        )
        
        try:
            return await asyncio.wait_for(
                self.collect_output(),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            self.process.kill()
            return "Sub-agent timed out"
```

### 4. Memory System (`memory/`)

Two-tier memory per thread:
- **Long-term:** MEMORY.md (curated)
- **Daily:** memory/YYYY-MM-DD.md (raw logs)

Optional semantic search:
- `memory-search.py` — Embedding-based lookup
- Fallback to grep-based search

### 5. Telegram Interface (`telegram/`)

- Bot with thread support
- Message routing
- Inline commands for dispatcher
- Status/health reporting

**Dispatcher commands (always available):**
- `/status` — Show thread status, sub-agents
- `/kill <agent>` — Kill hanging sub-agent
- `/new <type>` — Spawn new thread/sub-agent
- `/threads` — List all threads
- `/cleanup` — Remove old/stale threads

## Message Flow

```
User sends message in Telegram thread
        │
        ▼
Telegram Bot receives update
        │
        ▼
Dispatcher classifies message:
        │
        ├─── Dispatcher command (/status, /kill, etc.)
        │         │
        │         ▼
        │    Handle immediately, respond
        │
        ├─── Regular message
        │         │
        │         ▼
        │    Route to thread context
        │         │
        │         ▼
        │    Load thread workspace
        │         │
        │         ▼
        │    Run pi with context
        │         │
        │         ├── Timeout → Report error
        │         ├── Success → Stream response
        │         └── Spawn sub-agent → Parallel execution
        │
        └─── Response sent back to user
```

## Sub-Agent Lifecycle

```
1. SPAWN
   - Clone parent context (or subset)
   - Create isolated workspace
   - Start pi subprocess
   - Register with dispatcher

2. RUN
   - Stream output to parent (optional)
   - Heartbeat checks
   - Timeout countdown

3. COMPLETE / FAIL
   - Collect final output
   - Merge memory back to parent (if needed)
   - Cleanup workspace
   - Unregister from dispatcher
   - Report status to user
```

## Configuration

```yaml
# config.yaml
telegram:
  bot_token: ${TELEGRAM_BOT_TOKEN}
  
dispatcher:
  model: claude-sonnet-4-20250514
  timeout: 30s  # Max time for dispatcher decisions
  
threads:
  default_timeout: 5m
  max_concurrent: 10
  cleanup_after: 24h
  
sub_agents:
  default_timeout: 5m
  max_depth: 3
  model: claude-sonnet-4-20250514
  
memory:
  semantic_search: true
  embedding_model: sentence-transformers/all-MiniLM-L6-v2
```

## Implementation Priorities

### Phase 1: Core Dispatcher
- [ ] Telegram bot with thread routing
- [ ] Basic pi subprocess spawning
- [ ] Timeout enforcement
- [ ] Thread workspace isolation

### Phase 2: Sub-Agents
- [ ] First-class sub-agent spawning
- [ ] Context inheritance
- [ ] Output streaming
- [ ] Independent timeouts

### Phase 3: Memory
- [ ] Per-thread memory namespaces
- [ ] Semantic search (optional)
- [ ] Memory sync between parent/child

### Phase 4: Robustness
- [ ] Health monitoring
- [ ] Automatic recovery
- [ ] Dead thread cleanup
- [ ] Metrics/logging

## Why This Design?

**Problem with OpenClaw:**
- Sub-agents are limited (reduced tools, constrained)
- Single hang blocks everything
- No true thread isolation
- Dispatcher is same session as main

**This design:**
- Dispatcher is always responsive
- Sub-agents have full power
- Threads are truly isolated
- Failures are contained
