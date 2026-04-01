# Alfred API Overview

This document summarizes the main Python entrypoints used inside Alfred today.

It is a **developer-facing overview**, not a promise that every internal module is stable. When in doubt, prefer:
- the `alfred` CLI for normal usage
- high-level factories and models under `alfred.*`
- the source code for exact signatures

---

## Configuration

Module: `alfred.config`

### `Config`

Pydantic settings model for Alfred runtime configuration.

Important fields include:
- `default_llm_provider`
- `chat_model`
- `embedding_model`
- `embedding_provider`
- `local_embedding_model`
- `memory_budget`
- `memory_ttl_days`
- `memory_warning_threshold`
- `memory_store`
- `data_dir`
- `workspace_dir`
- `memory_dir`
- `context_files`
- tool-call context controls (`tool_calls_enabled`, `tool_calls_max_calls`, etc.)

### `load_config()`

Loads configuration from:
1. environment variables
2. `.env`
3. `config.toml`
4. XDG defaults

```python
from pathlib import Path

from alfred.config import Config, load_config

config = load_config()
custom = load_config(Path("/path/to/config.toml"))
```

### `config.toml` shape

```toml
[provider]
default = "kimi"
chat_model = "kimi-k2-5"

[embeddings]
provider = "openai"          # or "local"
model = "text-embedding-3-small"
local_model = "bge-base"

[memory]
store = "sqlite"
budget = 32000
ttl_days = 90
warning_threshold = 1000

[context.tool_calls]
enabled = true
max_calls = 5
max_tokens = 2000
include_output = true
include_arguments = true
```

By default Alfred uses XDG paths:
- config: `~/.config/alfred/config.toml`
- data: `~/.local/share/alfred/`
- cache: `~/.cache/alfred/`

---

## Context Assembly

Module: `alfred.context`

### Main models

- `ContextFile` — one loaded context file with metadata and block state
- `AssembledContext` — combined prompt context ready for the LLM
- `ContextCache` — TTL cache for loaded context files
- `ContextLoader` — orchestration layer for reading files and building prompt context

### `ContextLoader`

```python
from alfred.config import load_config
from alfred.context import ContextLoader

config = load_config()
loader = ContextLoader(config, cache_ttl=60)

files = await loader.load_all()
assembled = await loader.assemble()
```

Key methods:
- `load_file(name, path)`
- `load_all()`
- `assemble(memories=None)`
- `assemble_with_self_model(...)`
- `assemble_with_search(...)`
- `add_context_file(name, path)`
- `remove_context_file(name)`

### Managed context files

The default always-loaded context lives in the workspace directory and is centered on:
- `SYSTEM.md`
- `AGENTS.md`
- `SOUL.md`
- `USER.md`

Alfred can also load additional configured context sections when present.

---

## LLM Providers

Module: `alfred.llm`

### Main types

- `ChatMessage`
- `ChatResponse`
- `LLMProvider`
- `KimiProvider`
- `LLMFactory`

### Example

```python
from alfred.config import load_config
from alfred.llm import ChatMessage, LLMFactory

config = load_config()
provider = LLMFactory.create(config)

response = await provider.chat(
    [ChatMessage(role="user", content="Summarize this repo")]
)
print(response.content)
```

### Streaming

```python
async for chunk in provider.stream_chat(
    [ChatMessage(role="user", content="Think out loud")]
):
    print(chunk, end="")
```

### Errors

Common exception types:
- `LLMError`
- `RateLimitError`
- `APIError`
- `TimeoutError`

---

## Embeddings

Module: `alfred.embeddings`

### Main entrypoint

```python
from alfred.config import load_config
from alfred.embeddings import create_provider

config = load_config()
embedder = create_provider(config)
vector = await embedder.embed("important recurring context")
```

Current providers:
- `OpenAIProvider`
- `BGEProvider`

Selection is driven by `config.embedding_provider`:
- `"openai"`
- `"local"`

See [`EMBEDDINGS.md`](EMBEDDINGS.md) for the current storage and provider details.

---

## Memory Store

Modules:
- `alfred.memory`
- `alfred.memory.base`

### Main types

- `MemoryEntry`
- `MemoryStore`
- `SQLiteMemoryStore`
- `create_memory_store(config, embedder)`

### Example

```python
from datetime import datetime
from uuid import uuid4

from alfred.config import load_config
from alfred.embeddings import create_provider
from alfred.memory import MemoryEntry, create_memory_store

config = load_config()
embedder = create_provider(config)
store = create_memory_store(config, embedder)

entry = MemoryEntry(
    entry_id=str(uuid4()),
    content="User prefers concise technical summaries.",
    timestamp=datetime.now(),
    role="assistant",
    tags=["preference"],
)

await store.add(entry)
results, similarities, scores = await store.search("concise summaries")
```

The current memory backend is SQLite-backed vector search. The config field `memory_store` remains for configuration compatibility, but the supported runtime backend is `"sqlite"`.

---

## Runtime Self-Model

Module: `alfred.self_model`

### Main types

- `RuntimeSelfModel`
- `Identity`
- `Runtime`
- `World`
- `Capabilities`
- `ContextPressure`
- `build_runtime_self_model()`

### Example

```python
from alfred.self_model import build_runtime_self_model

self_model = build_runtime_self_model(alfred_instance)
print(self_model.to_prompt_section())
```

The self-model is internal-first. It helps Alfred reason from current runtime facts such as:
- interface
- session id
- tool availability
- memory/search availability
- current context pressure

See [`self-model.md`](self-model.md) for the product/runtime boundary.

---

## Cron

Modules:
- `alfred.cron.store`
- `alfred.cron.scheduler`

### `CronStore`

Persistent store for cron jobs and execution history.

```python
from alfred.cron.store import CronStore

store = CronStore()
jobs = await store.load_jobs()
```

### `CronScheduler`

Async scheduler that loads jobs, registers system jobs, and executes due work.

```python
from alfred.cron.scheduler import CronScheduler

scheduler = CronScheduler(store=store)
await scheduler.start()
```

Cron jobs remain a separate execution surface from tool calls. See [`cron-jobs.md`](cron-jobs.md) and [`job-api.md`](job-api.md) for the sandbox model.

---

## CLI Entrypoints

Primary entrypoint:
- `alfred.cli.main:app`

Installed console scripts:
- `alfred`
- `alfred-cron-runner`

Useful commands:

```bash
alfred
alfred webui
alfred cron list
alfred config update
```

---

## Related Docs

- [`README.md`](../README.md)
- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`MEMORY.md`](MEMORY.md)
- [`EMBEDDINGS.md`](EMBEDDINGS.md)
- [`self-model.md`](self-model.md)
- [`cron-jobs.md`](cron-jobs.md)
