# PRD #93: Pluggable Embeddings System

**Status**: Proposed
**Priority**: High
**Created**: 2026-02-25
**Related**: [embeddings-spike](../../embeddings-spike/)

---

## Problem

Alfred's current embedding system has two critical limitations:

1. **Vendor Lock-in**: Hardcoded to OpenAI's `text-embedding-3-small`. Users cannot switch models without code changes.
2. **Performance at Scale**: JSONL-based vector search is O(n) - the preliminary benchmarks show ~5 second search times at 100K memories. Users approaching this scale will experience unacceptable latency.

The embeddings spike investigation revealed:
- Local models (BGE-small) offer **same quality** as OpenAI (MRR 0.825 vs 0.725)
- FAISS provides **5,400x faster search** at 100K scale (0.93ms vs ~5s)
- Local models are **free** vs $0.02/1M tokens for OpenAI
- Local models have **5x higher throughput** (141/sec vs 27/sec)

---

## Solution

Implement a **pluggable embedding architecture** with:

1. **Provider Abstraction**: Interface-based system allowing any embedding model to be dropped in
2. **FAISS Integration**: Replace O(n) JSONL scan with O(log n) FAISS vector index
3. **OpenAI Fallback**: Keep OpenAI as a fallback option for reliability
4. **Configuration-Driven**: Switch providers via environment variables, no code changes

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    EmbeddingManager                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ LocalProvider│  │OpenAIProvider│  │(Future: Ollama)│  │
│  │ (BGE-small) │  │  (fallback)  │  │                 │  │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
│         │                │                  │           │
│         └────────────────┴──────────────────┘           │
│                          │                              │
│                    EmbeddingResult                      │
│                    (normalized interface)               │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                     VectorStore                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │                    FAISS Index                    │   │
│  │  - IVF for 10K+ vectors                          │   │
│  │  - Flat for <10K vectors                         │   │
│  │  - Disk persistence for fast restart             │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │                 Metadata Store                    │   │
│  │  - JSONL for memory content, timestamps, tags    │   │
│  │  - ID-based lookup for retrieval                 │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## User Stories

### Primary

1. **As a developer**, I want to switch embedding providers without changing code, so I can optimize for cost, speed, or quality as needed.

2. **As a power user** with 50K+ memories, I want sub-100ms search latency, so Alfred feels responsive.

3. **As a privacy-conscious user**, I want to run embeddings locally, so my memory content never leaves my machine.

4. **As a reliability-focused user**, I want OpenAI as a fallback, so Alfred works even if my local model fails.

### Secondary

5. **As a researcher**, I want to experiment with new embedding models, so I can find the best fit for my use case.

6. **As an ops person**, I want to configure providers via environment variables, so deployment is simple.

---

## Technical Design

### EmbeddingProvider Protocol

```python
from typing import Protocol

class EmbeddingProvider(Protocol):
    """Interface for embedding model providers."""

    @property
    def name(self) -> str:
        """Provider name for logging/config."""
        ...

    @property
    def dimension(self) -> int:
        """Vector dimension (e.g., 384 for BGE-small, 1536 for OpenAI)."""
        ...

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        ...

    async def is_healthy(self) -> bool:
        """Check if provider is available and functioning."""
        ...
```

### Provider Implementations

| Provider | Dimension | Startup | Latency | Cost | Use Case |
|----------|-----------|---------|---------|------|----------|
| `LocalProvider` (BGE-small) | 384 | ~1.1s | 19ms | Free | Default, privacy-first |
| `OpenAIProvider` | 1536 | ~0.1s | 270ms | $0.02/1M | Fallback, cloud |
| `OllamaProvider` (future) | varies | varies | varies | Free | GPU-accelerated local |

### VectorStore Interface

```python
class VectorStore(Protocol):
    """Interface for vector storage backends."""

    async def add(self, id: str, embedding: list[float], metadata: dict) -> None:
        """Add a vector with metadata."""
        ...

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        filter: dict | None = None,
    ) -> list[tuple[str, float, dict]]:
        """Search for similar vectors. Returns (id, score, metadata)."""
        ...

    async def delete(self, id: str) -> bool:
        """Delete a vector by ID."""
        ...

    async def save(self) -> None:
        """Persist index to disk."""
        ...

    async def load(self) -> bool:
        """Load index from disk. Returns True if loaded."""
        ...
```

### Configuration

All embedding settings live in `config.toml` (or `alfred.toml` after PRD #30):

```toml
[embeddings]
# Provider: "local" (BGE-small) | "openai" | "ollama"
provider = "local"

# Model name for local/ollama providers
model = "BAAI/bge-small-en-v1.5"

# Fallback provider if primary fails (optional)
fallback = "openai"

[embeddings.faiss]
# Index type: "flat" (exact) | "ivf" (approximate) | "auto" (ivf if >10K vectors)
index_type = "auto"

# IVF clusters (only used when index_type = "ivf")
nlist = 100

# Where to persist the index
index_path = "data/memory/index.faiss"
```

Environment variables remain supported for secrets only (`OPENAI_API_KEY`).

### Migration Strategy

1. **Backward Compatible**: New system reads existing JSONL files
2. **Lazy Migration**: Convert to FAISS on first search after upgrade
3. **No Data Loss**: Original JSONL preserved until explicit cleanup
4. **Rollback Safe**: Can revert to old system by changing config

---

## Milestones

### Milestone 1: Provider Abstraction Layer
**Definition**: EmbeddingProvider protocol and provider registry implemented

- [ ] Define `EmbeddingProvider` protocol in `alfred/embeddings/providers.py`
- [ ] Implement `LocalProvider` using sentence-transformers
- [ ] Implement `OpenAIProvider` wrapping existing OpenAI client
- [ ] Create `EmbeddingManager` with fallback logic
- [ ] Unit tests for all providers with mocked backends
- [ ] Configuration parsing for `EMBEDDING_PROVIDER` env vars

**Validation**: Can switch between local and OpenAI via config, both work

### Milestone 2: FAISS Vector Store
**Definition**: FAISS-based vector storage integrated with MemoryStore

- [ ] Implement `FAISSVectorStore` class
- [ ] Automatic index type selection (flat vs IVF)
- [ ] Metadata storage alongside FAISS index
- [ ] Persistence (save/load index to disk)
- [ ] Integration with existing `MemoryStore` class
- [ ] Benchmarks confirming <100ms search at 100K scale

**Validation**: Search latency <100ms with 100K vectors

### Milestone 3: Migration & Backward Compatibility
**Definition**: Seamless upgrade from JSONL-only to FAISS

- [ ] Migration script: JSONL → FAISS + metadata
- [ ] Lazy migration on first search
- [ ] Preserve original JSONL during migration
- [ ] Fallback to JSONL if FAISS fails to load
- [ ] Integration tests with real Alfred memories

**Validation**: Existing Alfred installation upgrades without data loss

### Milestone 4: Health Checks & Fallback
**Definition**: Robust fallback from local to OpenAI

- [ ] `is_healthy()` checks for each provider
- [ ] Automatic fallback on provider failure
- [ ] Retry logic with exponential backoff
- [ ] Logging/metrics for provider health
- [ ] Graceful degradation messages to user

**Validation**: Alfred continues working if local model crashes

### Milestone 5: Documentation & Polish
**Definition**: Users can configure and troubleshoot independently

- [ ] Update README with embedding configuration
- [ ] Update ARCHITECTURE.md with new components
- [ ] Add `alfred embeddings info` CLI command
- [ ] Troubleshooting guide for common issues
- [ ] Performance tuning guide

**Validation**: New user can switch providers without asking for help

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Search latency at 100K | ~5s | <100ms |
| Embedding cost (1M tokens) | $0.02 | $0 (local) or same (OpenAI) |
| Provider switch | Code change | Config change |
| Quality (MRR) | 0.725 | ≥0.725 (maintain or improve) |
| Startup time | ~0.1s | <2s (including local model load) |

---

## Out of Scope

- **Multi-user embeddings**: Each user would need separate indices (future PRD)
- **Embedding caching**: Could add later if redundant embedding calls become an issue
- **Quantized models**: Could add for even faster inference, but not required
- **GPU acceleration**: CPU-only FAISS is sufficient for Alfred's scale
- **Cloud vector DBs**: Pinecone, Weaviate, etc. - overkill for local-first Alfred

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Local model quality regression | Search returns irrelevant results | A/B testing, quality benchmarks in CI |
| FAISS index corruption | Data loss | Atomic saves, backup before write |
| Dimension mismatch on provider switch | Search fails | Clear error message, re-index command |
| Memory usage at 100K | OOM on small machines | Benchmark memory, document requirements |
| Sentence-transformers dependency bloat | Larger install size | Optional dependency group |

---

## Dependencies

- `sentence-transformers` - For local embedding models
- `faiss-cpu` - For vector indexing
- Existing `openai` package - Already installed

---

## Open Questions

1. **Re-indexing strategy**: When switching providers, should we auto-re-index or require manual trigger?
2. **Embedding versioning**: How to handle model updates that change embedding space?
3. **Hybrid search**: Should we combine semantic + keyword search for better recall?

---

## References

- [Embeddings Spike Preliminary Results](../../embeddings-spike/docs/preliminary_results.md)
- [Alfred ROADMAP - Local Embedding Models](../docs/ROADMAP.md) (Milestone #25)
- [FAISS Documentation](https://github.com/facebookresearch/faiss/wiki)
- [Sentence Transformers](https://www.sbert.net/)
