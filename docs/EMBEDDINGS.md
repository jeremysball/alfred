# Embeddings and Vector Search

Alfred currently supports **two embedding providers** and uses **SQLite + sqlite-vec** for vector search.

This is the current runtime shape:
- embeddings can come from **OpenAI** or a **local BGE model**
- vector search lives in SQLite-backed stores
- the old JSONL / FAISS migration flow is no longer the current architecture

---

## Quick Summary

| | OpenAI | Local BGE |
|---|---|---|
| Provider | `OpenAIProvider` | `BGEProvider` |
| Config value | `provider = "openai"` | `provider = "local"` |
| Default model | `text-embedding-3-small` | `bge-base` |
| Network | Remote API | Local model |
| Cost | API usage | Local compute only |
| Typical use | lowest setup friction | local-first retrieval |

---

## Current Storage Model

Alfred's current embedding-backed retrieval uses SQLite-based storage.

Relevant pieces:
- `src/alfred/embeddings/` — embedding providers
- `src/alfred/memory/sqlite_store.py` — memory-store adapter
- `src/alfred/storage/sqlite.py` — sqlite-vec-backed vector tables and search

Important points:
- `memory_store = "sqlite"` is the supported runtime backend
- there is no current JSONL-vs-FAISS store choice in normal runtime configuration
- vector schema drift is handled by runtime rebuild logic rather than a JSONL→FAISS migration command

---

## Configuration

All settings live in `config.toml`.

Default location:
- `~/.config/alfred/config.toml`

### Embeddings section

```toml
[embeddings]
provider = "openai"          # or "local"
model = "text-embedding-3-small"
local_model = "bge-base"
```

### Memory section

```toml
[memory]
store = "sqlite"
budget = 32000
ttl_days = 90
warning_threshold = 1000
```

### Supported values

#### `[embeddings]`

| Key | Meaning |
|-----|---------|
| `provider` | `"openai"` or `"local"` |
| `model` | OpenAI embedding model |
| `local_model` | Local BGE variant: `bge-small`, `bge-base`, or `bge-large` |

#### `[memory]`

| Key | Meaning |
|-----|---------|
| `store` | supported runtime value is `"sqlite"` |
| `budget` | memory token budget used during context assembly |
| `ttl_days` | default TTL for non-permanent memories |
| `warning_threshold` | warn when memory volume gets high |

---

## Provider Selection

### OpenAI embeddings

Use when you want the simplest setup:

```toml
[embeddings]
provider = "openai"
model = "text-embedding-3-small"
```

### Local embeddings

Use when you want local-first retrieval:

```toml
[embeddings]
provider = "local"
local_model = "bge-base"
```

Available local models:
- `bge-small`
- `bge-base`
- `bge-large`

The BGE model downloads on first use.

---

## Switching Providers

Switching providers can also change embedding dimensions.

Examples:
- OpenAI `text-embedding-3-small` → 1536 dimensions
- `bge-base` → 768 dimensions

Alfred's current runtime handles this by detecting vector-schema mismatch and rebuilding affected sqlite-vec tables automatically.

What that means in practice:
- you do **not** use the old FAISS migration flow
- you do **not** need a JSONL backup dance for the current runtime path
- startup may take longer when Alfred needs to rebuild vector indexes

If Alfred logs a vec-schema mismatch and rebuild on startup, let the rebuild finish.

---

## Disk Layout

By default Alfred uses XDG data paths.

Typical locations:
- `~/.local/share/alfred/alfred.db` — core SQLite store
- `~/.local/share/alfred/memories.db` — memory store database
- `~/.local/share/alfred/workspace/` — editable markdown context files

If you override `XDG_DATA_HOME`, those files move with it.

---

## Operational Notes

- Local embeddings reduce network dependence but increase local CPU/RAM usage.
- OpenAI embeddings are simpler to start with but require API access.
- The current `Config` model still expects `OPENAI_API_KEY`, even if embeddings are local.
- Retrieval quality depends on the provider, model choice, and the quality of stored memory content.

---

## Verifying the Active Setup

There is no dedicated `alfred memory migrate` or `alfred memory status` workflow in the current runtime.

Useful ways to verify the active setup today:
- inspect startup logs
- use `/health` in the TUI to inspect runtime state
- inspect `config.toml`
- inspect the SQLite files in Alfred's XDG data directory

Example:

```bash
sqlite3 "${XDG_DATA_HOME:-$HOME/.local/share}/alfred/memories.db" 'select count(*) from memories;'
```

---

## Related Docs

- [`MEMORY.md`](MEMORY.md)
- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`ROADMAP.md`](ROADMAP.md)
- [`prds/132-dynamic-embedding-dimension-support.md`](prd/132-dynamic-embedding-dimension-support.md)
