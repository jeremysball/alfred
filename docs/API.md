# Alfred API Documentation

## Core Modules

### Config (`src.config`)

#### `Config`

Application configuration with environment variable support.

```python
from src.config import Config, load_config

# Load with defaults from config.json, override from env
config = load_config(Path("config.json"))
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `telegram_bot_token` | `str` | Telegram Bot API token |
| `openai_api_key` | `str` | OpenAI API key |
| `kimi_api_key` | `str` | Kimi API key |
| `kimi_base_url` | `str` | Kimi API base URL |
| `default_llm_provider` | `str` | Provider to use ("kimi") |
| `chat_model` | `str` | Model identifier |
| `embedding_model` | `str` | Embedding model identifier |
| `memory_context_limit` | `int` | Max memories to include |
| `workspace_dir` | `Path` | Workspace directory |
| `memory_dir` | `Path` | Memory storage directory |
| `context_files` | `dict[str, Path]` | Map of context file names |

---

### Context (`src.context`)

#### `ContextLoader`

Async context file loading and assembly.

```python
from src.context import ContextLoader
from src.config import load_config

config = load_config()
loader = ContextLoader(config, cache_ttl=60)

# Load single file (auto-creates from template if missing)
file = await loader.load_file("soul", Path("data/SOUL.md"))

# Load all configured files
files = await loader.load_all()
# Returns: {"agents": ContextFile, "soul": ContextFile, ...}

# Assemble complete context
context = await loader.assemble(memories=memory_list)
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `load_file(name, path)` | `ContextFile` | Load single file with caching, auto-create from template |
| `load_all()` | `dict[str, ContextFile]` | Load all configured files concurrently |
| `assemble(memories)` | `AssembledContext` | Build complete prompt context |
| `add_context_file(name, path)` | `None` | Add custom context file |
| `remove_context_file(name)` | `None` | Remove context file |

#### `ContextCache`

TTL-based file cache.

```python
from src.context import ContextCache

cache = ContextCache(ttl_seconds=60)

# Get cached file
cached = cache.get("agents")
if cached:
    return cached

# Set cache
cache.set("agents", context_file)

# Invalidate
cache.invalidate("agents")

# Clear all
cache.clear()
```

---

### LLM (`src.llm`)

#### `LLMProvider` (ABC)

Abstract base for LLM implementations.

```python
from src.llm import LLMProvider, ChatMessage, ChatResponse

class MyProvider(LLMProvider):
    async def chat(self, messages: list[ChatMessage]) -> ChatResponse:
        ...
    
    async def stream_chat(
        self, messages: list[ChatMessage], system_prompt: str
    ) -> AsyncIterator[str]:
        ...
```

#### `KimiProvider`

Kimi API implementation.

```python
from src.llm import KimiProvider, ChatMessage
from src.config import load_config

config = load_config()
provider = KimiProvider(config)

# Non-streaming chat
response = await provider.chat([
    ChatMessage(role="system", content="You are Alfred..."),
    ChatMessage(role="user", content="Hello!"),
])

print(response.content)  # Assistant response
print(response.model)    # Model used
print(response.usage)    # Token counts

# Streaming chat
async for chunk in provider.stream_chat(messages, system_prompt):
    print(chunk, end="")
```

#### `LLMFactory`

Provider factory.

```python
from src.llm import LLMFactory
from src.config import load_config

config = load_config()
provider = LLMFactory.create(config)
```

#### Exceptions

| Exception | Description |
|-----------|-------------|
| `LLMError` | Base exception |
| `RateLimitError` | Rate limit exceeded |
| `APIError` | API returned error |
| `TimeoutError` | Request timed out |

#### Retry Decorator

```python
from src.llm import retry_with_backoff

@retry_with_backoff(max_retries=3, base_delay=1.0)
async def my_api_call():
    # Retries on failure with exponential backoff
    ...
```

**Parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_retries` | 3 | Max retry attempts |
| `base_delay` | 1.0 | Initial delay (seconds) |
| `max_delay` | 60.0 | Maximum delay (seconds) |
| `exponential_base` | 2.0 | Exponential factor |
| `jitter` | True | Add random jitter |

---

### Types (`src.types`)

#### `MemoryEntry`

Single memory with metadata.

```python
from src.types import MemoryEntry
from datetime import datetime

memory = MemoryEntry(
    timestamp=datetime.now(),
    role="assistant",
    content="I'll help you with that...",
    embedding=[0.1, 0.2, ...],  # Optional
    tags=["coding", "python"],
)
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `datetime` | When created |
| `role` | `Literal["user", "assistant", "system"]` | Speaker role |
| `content` | `str` | Message content |
| `embedding` | `list[float] \| None` | Vector embedding |
| `tags` | `list[str]` | Categorization tags |
| `entry_id` | `str \| None` | Unique identifier |

#### `ContextFile`

Loaded context file.

```python
from src.types import ContextFile
from datetime import datetime

file = ContextFile(
    name="agents",
    path="data/AGENTS.md",
    content="# Agent Behavior Rules...",
    last_modified=datetime.now(),
)
```

#### `AssembledContext`

Complete context for LLM.

```python
from src.types import AssembledContext

context = AssembledContext(
    agents="# Agent Behavior...",
    soul="# Personality...",
    user="# User Preferences...",
    tools="# Available Tools...",
    memories=[memory1, memory2],
    system_prompt="# Combined prompt...",
)
```

---

## Usage Examples

### Basic Chat Flow

```python
import asyncio
from src.config import load_config
from src.context import ContextLoader
from src.llm import LLMFactory, ChatMessage

async def chat():
    # Initialize
    config = load_config()
    loader = ContextLoader(config)
    provider = LLMFactory.create(config)
    
    # Assemble context
    context = await loader.assemble()
    
    # Build messages
    messages = [
        ChatMessage(role="system", content=context.system_prompt),
        ChatMessage(role="user", content="Hello Alfred!"),
    ]
    
    # Get response
    response = await provider.chat(messages)
    return response.content

asyncio.run(chat())
```

### Custom Context File

```python
# Add custom context
loader.add_context_file("project", Path("PROJECT.md"))

# Access in loader
file = await loader.load_file("project", Path("PROJECT.md"))
```

### Error Handling

```python
from src.llm import RateLimitError, APIError, TimeoutError

try:
    response = await provider.chat(messages)
except RateLimitError:
    # Handle rate limit - wait and retry
    await asyncio.sleep(60)
except APIError as e:
    # Log API error
    logger.error(f"API error: {e}")
except TimeoutError:
    # Handle timeout
    logger.warning("Request timed out")
```

---

## Configuration Reference

### config.json

```json
{
  "default_llm_provider": "kimi",
  "chat_model": "kimi-k2-5",
  "embedding_model": "text-embedding-3-small",
  "memory_context_limit": 20,
  "workspace_dir": "data",
  "memory_dir": "data/memory",
  "context_files": {
    "agents": "data/AGENTS.md",
    "soul": "data/SOUL.md",
    "user": "data/USER.md",
    "tools": "data/TOOLS.md"
  }
}
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram Bot API token |
| `OPENAI_API_KEY` | Yes | OpenAI API key (embeddings) |
| `KIMI_API_KEY` | Yes | Kimi API key |
| `KIMI_BASE_URL` | Yes | Kimi API endpoint |

---

## Related Documentation

- [Architecture](ARCHITECTURE.md) — System design
- [Deployment](DEPLOYMENT.md) — Production setup
- [Cron Jobs](cron-jobs.md) — Scheduled tasks
