# Embeddings

Alfred supports OpenAI and local BGE embeddings. The memory store is JSONL today. A SQLite vector store is planned.

---

## Quick Summary

| | Default | Local (BGE) |
|---|---|---|
| **Provider** | OpenAI API | BAAI/bge-base-en-v1.5 |
| **Cost** | ~$0.02/1M tokens | Free |
| **Query latency** | ~270ms | ~52ms |
| **Store** | JSONL (linear scan) | JSONL (linear scan) |
| **Search at 100K** | ~5 seconds | ~5 seconds |
| **RAM required** | Minimal | ~4 GB |
| **Disk required** | Minimal | ~2 GB (model download) |

---

## Setup

### New Installations

No extra steps. Dependencies install automatically:

```bash
uv sync
```

`sentence-transformers` is included in `pyproject.toml`. The BGE model downloads on first use (~400 MB).

### Switching from OpenAI to Local Embeddings

1. **Edit `~/.config/alfred/config.toml`:**

   ```toml
   [embeddings]
   provider = "local"
   local_model = "bge-base"   # or bge-small, bge-large
   ```

2. **Verify:**

   ```bash
   alfred memory status
   ```

`OPENAI_API_KEY` is still required for LLM calls but is no longer used for embeddings when `provider = "local"`.

---

## Configuration Reference

All settings live in `~/.config/alfred/config.toml`.

### `[embeddings]` section

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `provider` | string | `"openai"` | Embedding backend: `"openai"` or `"local"` |
| `model` | string | `"text-embedding-3-small"` | OpenAI model (ignored when `provider = "local"`) |
| `local_model` | string | `"bge-base"` | BGE variant: `"bge-small"`, `"bge-base"`, or `"bge-large"` |

### `[memory]` section

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `budget` | int | `32000` | Max tokens of memory loaded into context |
| `ttl_days` | int | `90` | Days before non-permanent memories expire |
| `warning_threshold` | int | `1000` | Warn when memory count exceeds this |

### Full example

```toml
[embeddings]
provider = "local"
local_model = "bge-base"

[memory]
ttl_days = 90
warning_threshold = 1000
```

---

## Performance Tuning

### Model selection

| Model | Dimension | RAM | Speed | Quality |
|-------|-----------|-----|-------|---------|
| `bge-small` | 384 | ~1 GB | Fastest | Good |
| `bge-base` | 768 | ~2 GB | Fast | Better (recommended) |
| `bge-large` | 1024 | ~4 GB | Slower | Best |

`bge-base` is the default. It delivers better retrieval quality than OpenAI `text-embedding-3-small` at ~52ms per query.

Use `bge-small` on memory-constrained machines (less than 4 GB RAM available to Alfred). Use `bge-large` when retrieval precision matters more than latency.

### Startup time

The BGE model loads once at startup and stays resident. On a modern CPU, cold load takes 5–15 seconds. Subsequent queries run at full speed (~52ms). If startup time matters, use `bge-small`.

### Disk layout

Memory storage looks like this:

```
data/memory/
└── memories.jsonl
```

---

## CLI Reference

```bash
alfred memory status    # Show JSONL entry count and disk usage
alfred memory prune     # Remove expired memories (dry-run by default)
```

---

## Related

- [Memory System](MEMORY.md) — Three-layer memory architecture
- [Architecture](ARCHITECTURE.md) — System design overview
- [Roadmap](ROADMAP.md) — Development progress
