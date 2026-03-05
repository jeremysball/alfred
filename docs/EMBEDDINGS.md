# Embeddings and FAISS

Alfred supports two embedding backends and two memory stores. This document covers setup, configuration, migration, and performance tuning.

---

## Quick Summary

| | Default | Local (BGE) |
|---|---|---|
| **Provider** | OpenAI API | BAAI/bge-base-en-v1.5 |
| **Cost** | ~$0.02/1M tokens | Free |
| **Query latency** | ~270ms | ~52ms |
| **Store** | JSONL (linear scan) | FAISS (ANN index) |
| **Search at 100K** | ~5 seconds | <100ms |
| **RAM required** | Minimal | ~4 GB |
| **Disk required** | Minimal | ~2 GB (model download) |

---

## Setup

### New Installations

No extra steps. Dependencies install automatically:

```bash
uv sync
```

`sentence-transformers` and `faiss-cpu` are included in `pyproject.toml`. The BGE model downloads on first use (~400 MB).

### Switching from OpenAI to Local Embeddings

1. **Edit `~/.config/alfred/config.toml`:**

   ```toml
   [embeddings]
   provider = "local"
   local_model = "bge-base"   # or bge-small, bge-large

   [memory]
   store = "faiss"
   ```

2. **Migrate existing memories:**

   ```bash
   alfred memory migrate
   ```

3. **Verify:**

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
| `store` | string | `"jsonl"` | Memory backend: `"jsonl"` or `"faiss"` |
| `budget` | int | `32000` | Max tokens of memory loaded into context |
| `ttl_days` | int | `90` | Days before non-permanent memories expire |
| `warning_threshold` | int | `1000` | Warn when memory count exceeds this |
| `faiss_index_type` | string | `"auto"` | FAISS index: `"flat"`, `"ivf"`, or `"auto"` |
| `faiss_ivf_threshold` | int | `10000` | Switch from Flat to IVF at this entry count |
| `faiss_backup_jsonl` | bool | `true` | Keep JSONL backup when using FAISS store |

### Full example

```toml
[embeddings]
provider = "local"
local_model = "bge-base"

[memory]
store = "faiss"
ttl_days = 90
warning_threshold = 1000
faiss_index_type = "auto"
faiss_ivf_threshold = 10000
faiss_backup_jsonl = true
```

---

## Migration Guide

For users upgrading from JSONL to FAISS.

### What migration does

1. Reads all entries from `memories.jsonl`
2. Re-embeds each entry using the new provider (BGE or OpenAI)
3. Builds a FAISS index at `data/memory/faiss/`
4. Renames the original file to `memories.jsonl.bak`

All memory content and metadata (timestamps, tags, `permanent` flag) is preserved. Only embeddings are regenerated — this is required because BGE and OpenAI produce vectors of different dimensions (768 vs 1536).

### Run migration

```bash
alfred memory migrate
```

Options:

```bash
alfred memory migrate --provider local     # Use BGE (default)
alfred memory migrate --provider openai    # Use OpenAI for re-embedding
alfred memory migrate --no-backup          # Skip creating .bak file
alfred memory migrate --jsonl-path /path/to/memories.jsonl
alfred memory migrate --faiss-path /path/to/faiss/dir
```

### After migration

Update `config.toml` to use the FAISS store:

```toml
[memory]
store = "faiss"
```

Without this change, Alfred continues reading from JSONL even after migration.

### Roll back

If you want to revert:

1. Rename `memories.jsonl.bak` back to `memories.jsonl`
2. Set `store = "jsonl"` in `config.toml`

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

### FAISS index type

| Scale | Index | Build time | Search speed | Notes |
|-------|-------|------------|--------------|-------|
| < 10K entries | `flat` | Instant | ~0.1ms | Exact nearest neighbour |
| 10K–100K | `ivf` | ~1s | ~0.5ms | Approximate, saves RAM |
| > 100K | `ivf` | ~3s | ~1ms | Required at this scale |

`faiss_index_type = "auto"` (the default) starts with Flat and switches to IVF automatically at `faiss_ivf_threshold` entries. Set `faiss_index_type = "flat"` to force exact search regardless of size.

### Startup time

The BGE model loads once at startup and stays resident. On a modern CPU, cold load takes 5–15 seconds. Subsequent queries run at full speed (~52ms). If startup time matters, use `bge-small`.

### Disk layout

After migration, memory storage looks like this:

```
data/memory/
├── memories.jsonl.bak     # Original backup (safe to delete after verification)
└── faiss/
    ├── index.faiss        # FAISS index (~30 MB for 10K entries)
    └── metadata.json      # Entry metadata (timestamps, tags, content)
```

---

## CLI Reference

```bash
alfred memory status    # Show store type, entry count, config
alfred memory migrate   # Convert JSONL → FAISS
alfred memory prune     # Remove expired memories (dry-run by default)
```

---

## Related

- [Memory System](MEMORY.md) — Three-layer memory architecture
- [Architecture](ARCHITECTURE.md) — System design overview
- [Roadmap](ROADMAP.md) — Development progress
