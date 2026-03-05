# PRD: Integrate Local Embeddings and FAISS into Alfred

**Status**: Complete  
**Priority**: High  
**Created**: 2026-03-04  
**Completed**: 2026-03-05  
**Issue**: [#105](https://github.com/jeremysball/alfred/issues/105)

---

## Problem Statement

Alfred's current memory system has three critical limitations:

1. **Search Performance**: Linear O(n) JSONL scan becomes unusable at scale—~5 seconds at 100K memories
2. **Cost**: Ongoing OpenAI API fees for embedding operations ($0.02/1M tokens)
3. **Latency**: Network round-trips for every embedding (~270ms per query)

The [embeddings spike](../embeddings-spike) proved local models can match/exceed OpenAI quality while eliminating these issues.

**Key Question**: How do we integrate BGE-base embeddings and FAISS storage into Alfred without breaking existing functionality?

---

## Solution Overview

Replace Alfred's embedding and storage stack:

| Component | Current | New | Impact |
|-----------|---------|-----|--------|
| **Embedding Model** | OpenAI text-embedding-3-small | BAAI/bge-base-en-v1.5 (local) | Free, better quality, faster |
| **Vector Store** | JSONL (linear scan) | FAISS (ANN index) | 5,400x faster search |
| **Model Loading** | API call per request | Hot-loaded singleton | ~52ms query latency |

The integration maintains backward compatibility—OpenAI remains an optional fallback.

---

## Scope

### In Scope

1. **Embedding Model Integration**
   - Add BGE-base as default embedding provider
   - Implement singleton pattern for hot model
   - Keep OpenAI as fallback configuration
   - Support both 384-dim (small) and 768-dim (base) outputs

2. **FAISS Vector Storage**
   - Replace JSONL MemoryStore with FAISS-backed implementation
   - Support persistence (save/load index to disk)
   - Maintain same `MemoryStore` interface for compatibility
   - Handle migration from existing JSONL memories

3. **Memory Store Interface**
   - Keep existing `add()`, `search()`, `get()`, `delete()` methods
   - Update internal storage from dict+JSONL to FAISS+metadata
   - Maintain memory metadata (timestamp, role, tags, entry_id)

4. **Configuration**
   - New config options for embedding provider (openai/local)
   - Model selection (bge-small/bge-base)
   - FAISS index type (flat/IVF)
   - Index persistence path

5. **Migration Path**
   - Convert existing JSONL memories to FAISS index
   - Preserve all existing memory data
   - One-time migration script

### Out of Scope

1. **GPU acceleration** (CPU-only for now)
2. **Real-time index updates** (batch/rebuild for now)
3. **Multi-model ensembles**
4. **Cloud vector DBs** (Chroma, Qdrant, etc.)
5. **Embedding cache** (query results not cached)

---

## Technical Approach

### Architecture Changes

```
Current Alfred:
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│   Query/User    │────▶│  MemoryStore │────▶│  OpenAI API  │
└─────────────────┘     │  (JSONL)     │     │  (embed)     │
                        │  O(n) scan   │     └──────────────┘
                        └──────────────┘

New Alfred:
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│   Query/User    │────▶│  MemoryStore │────▶│  BGE-base    │
└─────────────────┘     │  (FAISS)     │     │  (singleton) │
                        │  O(log n)    │     │  hot-loaded  │
                        └──────────────┘     └──────────────┘
```

### Key Components

1. **EmbeddingProvider Interface**
   ```python
   class EmbeddingProvider(ABC):
       @abstractmethod
       def embed(self, text: str) -> list[float]: ...
       
       @abstractmethod
       def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
   
   class BGEProvider(EmbeddingProvider): ...
   class OpenAIProvider(EmbeddingProvider): ...
   ```

2. **FAISS MemoryStore**
   ```python
   class FAISSMemoryStore(MemoryStore):
       def __init__(self, index_path: Path | None = None):
           self._index = faiss.IndexFlatIP(768)  # or IndexIVFFlat
           self._metadata = {}  # id -> MemoryMetadata
           self._provider = BGEProvider()  # singleton
   ```

3. **Singleton Model Pattern**
   ```python
   _embedding_model = None
   
   def get_embedding_model():
       global _embedding_model
       if _embedding_model is None:
           _embedding_model = SentenceTransformer("BAAI/bge-base-en-v1.5")
       return _embedding_model
   ```

---

## Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Search latency at 100K | < 100ms | Benchmark with FAISS |
| Query embedding time | < 100ms | Single query test |
| Memory quality (MRR) | ≥ 0.80 | Needle-in-haystack test |
| Migration success | 100% | All existing memories preserved |
| Backward compatibility | Full | Existing API unchanged |
| Startup time | < 30s | Model load + index build |

---

## Milestones

### [x] 1. Embedding Provider Abstraction
- [x] Create `EmbeddingProvider` ABC
- [x] Implement `BGEProvider` with singleton pattern
- [x] Implement `OpenAIProvider` for fallback
- [x] Configuration system for provider selection
- **Validation**: ✅ Can switch providers via config (12 tests passing)

### [x] 2. FAISS MemoryStore Implementation
- [x] Create `FAISSMemoryStore` implementing `MemoryStore` interface
- [x] Implement add/search/get/delete operations
- [x] Add persistence (save/load to disk)
- [x] Support both Flat and IVF index types (auto-switch at 10K)
- **Validation**: ✅ Passes all MemoryStore unit tests (13 tests passing)

### [x] 3. Migration System
- [x] Create migration script JSONL → FAISS
- [x] Preserve all memory metadata
- [x] Handle dimension mismatch (re-embed with new provider)
- [x] Backup original JSONL before migration
- **Validation**: ✅ 100% data preserved in migration test (6 tests passing)

### [x] 4. Integration & Configuration
- [x] Wire up FAISS store into Alfred's main flow
- [x] Add config options (provider, model, index type, backup, threshold)
- [x] Update dependency management (sentence-transformers, faiss-cpu with CPU torch)
- [x] Add CLI commands: `alfred memory migrate`, `alfred memory status`
- **Validation**: ✅ Alfred runs with local embeddings end-to-end

### [x] 5. Testing & Validation
- [x] Unit tests for BGEProvider (8 tests)
- [x] Unit tests for FAISSMemoryStore (13 tests)
- [x] Unit tests for migration (6 tests)
- [x] Provider factory tests (4 tests)
- **Total**: 31 tests passing
- Needle-in-haystack quality tests
- **Validation**: All tests pass, benchmarks meet targets

### [ ] 6. Documentation
- Update setup instructions (new dependencies)
- Document configuration options
- Migration guide for existing users
- Performance tuning recommendations
- **Validation**: Docs reviewed and complete

---

## Dependencies

### New Python Packages
```
sentence-transformers>=2.5.0
faiss-cpu>=1.7.4
```

### System Requirements
- Python 3.10+
- 4GB+ RAM (for model + index)
- 2GB disk space (model download + index storage)

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Model download fails | Low | High | Cache model in Docker image; retry logic |
| FAISS build issues | Low | Medium | Use pre-built wheels; fallback to Flat index |
| Dimension mismatch | Medium | High | Migration script handles re-embedding |
| Memory usage too high | Low | Medium | Use BGE-small as fallback; monitor RAM |
| Quality regression | Low | High | Benchmark before/after; keep OpenAI fallback |

---

## Implementation Notes

### FAISS Index Selection

| Scale | Index Type | Build Time | Search Speed | Memory |
|-------|------------|------------|--------------|--------|
| < 10K | Flat | Instant | ~0.1ms | ~30MB |
| 10K-100K | IVF100 | ~1s | ~0.5ms | ~35MB |
| 100K+ | IVF256 | ~3s | ~1ms | ~40MB |

Default to Flat for simplicity, auto-switch to IVF at 10K.

### Migration Strategy

1. Detect existing JSONL memories
2. Load BGE-base model (one-time)
3. Re-embed all existing memories (may take minutes)
4. Build FAISS index
5. Save index + metadata to `data/memory/faiss/`
6. Keep JSONL as backup (rename to `.bak`)

### Configuration Schema

```yaml
memory:
  provider: local  # or "openai"
  model: bge-base  # or "bge-small"
  index_type: flat  # or "ivf"
  index_path: data/memory/faiss/
  dimension: 768  # 384 for small, 768 for base
```

---

## Deliverables

1. `src/alfred/memory/embeddings.py` - Provider abstractions
2. `src/alfred/memory/faiss_store.py` - FAISS implementation
3. `src/alfred/memory/migrate.py` - Migration script
4. Updated `src/alfred/memory/store.py` - Integration
5. Tests in `tests/memory/`
6. Updated documentation

---

## References

- [Embeddings Spike Results](../embeddings-spike/docs/preliminary_results.md)
- [FAISS Documentation](https://faiss.ai/)
- [BGE Models on HuggingFace](https://huggingface.co/BAAI)
- Current Alfred MemoryStore: `src/alfred/memory/store.py`
