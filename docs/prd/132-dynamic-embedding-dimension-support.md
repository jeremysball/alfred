# PRD #132: Dynamic Embedding Dimension Support with Automatic Re-embedding

## Status

**Draft** - Ready for implementation

## Problem Statement

When switching between embedding models (e.g., BGE 768-dim to OpenAI 1536-dim), sqlite-vec tables have fixed dimensions. Current code either:

1. **Fails with dimension mismatch errors**: "Dimension mismatch for query vector... Expected 768 dimensions but received 1536"
2. **Silently drops existing vector data**: Recreates vec0 tables with new dimensions but doesn't re-embed existing content, breaking semantic search

This prevents users from switching embedding models without manually deleting and recreating their entire memory database.

## User Story

As an Alfred user, I want to switch from BGE embeddings (768-dim) to OpenAI embeddings (1536-dim) without losing my memories or breaking search functionality, so that I can use the best embedding model for my needs.

## Goals

1. Detect embedding dimension changes automatically at startup
2. Preserve all memory and session content during dimension changes
3. Re-embed all existing data with the new model's dimensions
4. Provide progress feedback during re-embedding (can be slow for large datasets)
5. Handle failures gracefully - don't lose data if re-embedding fails

## Non-Goals

1. Supporting mixed-dimension data in the same database
2. Incremental/partial re-embedding (all or nothing)
3. Allowing dimension changes without re-embedding
4. Supporting arbitrary dimension sizes beyond common models (768, 1536, etc.)

## Technical Context

### Current Architecture

- **SQLiteStore**: Creates vec0 virtual tables with hardcoded `FLOAT[768]` dimensions
- **Three vec0 tables**: `memory_embeddings`, `message_embeddings_vec`, `session_summaries_vec`
- **Base tables**: Store actual content + JSON embeddings (preserved during vec0 recreation)
- **Embedding providers**: BGE (768-dim), OpenAI (1536-dim)

### sqlite-vec Constraints

- Vec0 tables are virtual tables with fixed dimensions at creation time
- Cannot ALTER TABLE to change dimensions
- Must DROP and CREATE new table to change dimensions
- Data loss is acceptable for vec0 tables because base tables preserve content

## Proposed Solution

### Phase 1: Dynamic Dimension Detection

**Milestone 1.1**: Store embedding dimension metadata
- Add `embedding_dim` column to a metadata table (or use existing config)
- Store current dimension on initialization
- Compare stored vs actual on startup

**Milestone 1.2**: Detect dimension mismatch
- Query existing vec0 table schemas using `sqlite_master`
- Extract FLOAT[N] dimension using regex
- Compare with embedder.dimension
- Trigger re-embedding if mismatch detected

### Phase 2: Safe Re-embedding Pipeline

**Milestone 2.1**: Create re-embedding orchestrator
```python
class EmbeddingReembedder:
    """Handles re-embedding all data when dimension changes."""
    
    async def reembed_all(self, old_dim: int, new_dim: int) -> ReembedResult:
        # 1. Backup current state (optional but safe)
        # 2. Drop old vec0 tables
        # 3. Create new vec0 tables with correct dimension
        # 4. Re-embed memories
        # 5. Re-embed session summaries
        # 6. Re-embed message embeddings
        # 7. Update dimension metadata
```

**Milestone 2.2**: Re-embed memories
- Fetch all entries from `memories` base table
- Generate new embeddings with current embedder
- Insert into new `memory_embeddings` vec0 table
- Progress logging (e.g., "Re-embedding memory 50/200")

**Milestone 2.3**: Re-embed session summaries
- Fetch all summaries from `session_summaries` base table
- Re-embed summary_text
- Insert into new `session_summaries_vec` table

**Milestone 2.4**: Re-embed message embeddings
- Fetch all messages from `message_embeddings` base table
- Re-embed content_snippet
- Insert into new `message_embeddings_vec` table

### Phase 3: Integration and Safety

**Milestone 3.1**: Integrate into AlfredCore initialization
```python
# In AlfredCore._init_services() or SQLiteStore._init()
if dimension_mismatch_detected():
    logger.warning(f"Embedding dimension changed from {old_dim} to {new_dim}")
    logger.warning("Re-embedding all existing data...")
    await reembedder.reembed_all(old_dim, new_dim)
```

**Milestone 3.2**: Add failure handling
- Transaction wrapper - rollback if any step fails
- Don't delete old vec0 tables until new ones are populated
- Graceful fallback: if re-embedding fails, keep old tables and warn user

**Milestone 3.3**: Add progress feedback
- Log progress percentage during re-embedding
- For large datasets, this could take minutes
- Consider adding callback for UI progress bar

## Implementation Details

### Schema Changes

No schema changes needed - reuse existing base tables.

Add dimension tracking:
```sql
-- Option 1: Add to existing metadata table
CREATE TABLE IF NOT EXISTS store_metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);
INSERT INTO store_metadata (key, value) VALUES ('embedding_dim', '768');

-- Option 2: Query vec0 table schema directly (preferred - no extra table)
```

### Key Algorithm

```python
async def _ensure_vec0_dimension(self, db: Any, table_name: str, id_column: str) -> None:
    """Ensure vec0 table exists with correct dimension."""
    dim = self._embedding_dim
    
    # Check if table exists with different dimension
    existing_dim = await self._get_vec0_dimension(db, table_name)
    
    if existing_dim is None:
        # Table doesn't exist - create it
        await self._create_vec0_table(db, table_name, id_column, dim)
    elif existing_dim != dim:
        # Dimension mismatch - trigger re-embedding
        logger.warning(f"{table_name}: dimension changed {existing_dim} -> {dim}")
        await self._reembed_table(db, table_name, id_column, existing_dim, dim)
    # else: dimension matches, nothing to do

async def _reembed_table(self, db, table_name, id_column, old_dim, new_dim) -> None:
    """Re-embed all data when dimension changes."""
    # 1. Create temporary new table
    temp_name = f"{table_name}_new"
    await self._create_vec0_table(db, temp_name, id_column, new_dim)
    
    # 2. Fetch all content from base table
    base_table = self._get_base_table_name(table_name)
    rows = await self._fetch_all_for_reembedding(base_table)
    
    # 3. Re-embed and insert
    for i, row in enumerate(rows):
        embedding = await self.embedder.embed(row['content'])
        await self._insert_vec0(db, temp_name, row['id'], embedding)
        if i % 10 == 0:
            logger.info(f"Re-embedding {table_name}: {i}/{len(rows)}")
    
    # 4. Swap tables (atomic rename or drop+rename)
    await db.execute(f"DROP TABLE {table_name}")
    await db.execute(f"ALTER TABLE {temp_name} RENAME TO {table_name}")
```

## Success Criteria

- [ ] Can switch from BGE (768) to OpenAI (1536) without errors
- [ ] All memories remain searchable after dimension change
- [ ] All session summaries remain searchable after dimension change
- [ ] Progress is logged during re-embedding
- [ ] Failed re-embedding doesn't lose data
- [ ] Works with both sync and async embedding providers

## Testing Strategy

- Unit tests for dimension detection logic
- Integration tests with small dataset
- Test both BGE→OpenAI and OpenAI→BGE transitions
- Test failure scenarios (network errors during re-embedding)

## Open Questions

1. Should we backup the database before re-embedding?
2. Should re-embedding be async background task or blocking startup?
3. How to handle very large datasets (10k+ memories)?
4. Should we provide a `--skip-reembed` flag for emergency startup?

## Related Issues

- PR #132: Previous incomplete implementation (reverted)
- sqlite-vec documentation on vec0 constraints

## Milestones

| Milestone | Description | Est. Time |
|-----------|-------------|-----------|
| M1 | Dimension detection and comparison | 2h |
| M2 | Re-embedding orchestrator scaffold | 2h |
| M3 | Memory re-embedding implementation | 3h |
| M4 | Session summary re-embedding | 2h |
| M5 | Message embedding re-embedding | 2h |
| M6 | Integration with AlfredCore | 2h |
| M7 | Error handling and safety | 3h |
| M8 | Testing | 4h |
| **Total** | | **~20h** |

## Notes

- This is a data migration feature, not a user-facing feature
- Consider adding a CLI command `/rebuild-vectors` for manual triggering
- Document that dimension changes require re-embedding all data
- Consider warning users before they switch embedding models