# Execution Plan: M5 - Memory System Simplification

**PRD**: #102 (Unified Memory System)
**Milestone**: M5 - Memory System Simplification
**Approach**: Test-Driven Development (Red → Green → Commit)

---

## Design Decisions (Confirmed)

1. **Prune on startup** - Automatic pruning when Alfred starts
2. **Threshold warning via toast** - Show in TUI on startup
3. **Support permanent in update_memory** - Allow changing permanent flag
4. **End of 90th day TTL** - Memory expires at end of day 90
5. **Dry run mode** - Add dry_run parameter to pruning

---

## Execution Tasks

### 1. MemoryEntry Schema

- [ ] Test: `test_memory_entry_has_permanent_field()` - verify MemoryEntry has `permanent: bool = False`
- [ ] Implement: Add `permanent: bool = False` to MemoryEntry schema in `src/memory.py`
- [ ] Commit: `feat(memory): add permanent flag to MemoryEntry schema`

- [ ] Test: `test_memory_entry_permanent_defaults_to_false()` - verify default value
- [ ] Implement: Field already defaults to False from previous task
- [ ] Commit: `test: verify MemoryEntry permanent defaults to False`

- [ ] Test: `test_memory_entry_permanent_can_be_set_true()` - verify can create with permanent=True
- [ ] Implement: No changes needed (Pydantic handles this)
- [ ] Commit: `test: verify MemoryEntry permanent can be set to True`

### 2. MemoryStore Serialization

- [ ] Test: `test_entry_to_jsonl_includes_permanent()` - verify serialization includes permanent field
- [ ] Implement: Update `_entry_to_jsonl()` to include `"permanent": entry.permanent`
- [ ] Commit: `feat(memory): serialize permanent field to JSONL`

- [ ] Test: `test_entry_from_jsonl_parses_permanent()` - verify deserialization parses permanent
- [ ] Implement: Update `_entry_from_jsonl()` to parse `data.get("permanent", False)`
- [ ] Commit: `feat(memory): deserialize permanent field from JSONL`

- [ ] Test: `test_entry_from_jsonl_backward_compatible()` - verify old data without permanent defaults to False
- [ ] Implement: Already handled by `data.get("permanent", False)` from previous task
- [ ] Commit: `test: verify backward compatibility for permanent field`

### 3. MemoryStore Count Method

- [ ] Test: `test_get_memory_count_empty_store()` - verify returns 0 when no memories
- [ ] Implement: Add `async def get_memory_count(self) -> int` method in MemoryStore
- [ ] Commit: `feat(memory): add get_memory_count() method`

- [ ] Test: `test_get_memory_count_with_entries()` - verify returns correct count after adding entries
- [ ] Implement: Method already works from previous task
- [ ] Commit: `test: verify get_memory_count() with entries`

### 4. MemoryStore TTL Pruning

- [ ] Test: `test_prune_expired_memories_removes_old_non_permanent()` - verify removes non-permanent > 90 days old
- [ ] Implement: Add `async def prune_expired_memories(self, ttl_days: int = 90, dry_run: bool = False) -> int`
- [ ] Commit: `feat(memory): add prune_expired_memories() method`

- [ ] Test: `test_prune_expired_memories_keeps_permanent()` - verify permanent memories are never pruned
- [ ] Implement: Logic already in place from previous task (check permanent flag)
- [ ] Commit: `test: verify permanent memories are not pruned`

- [ ] Test: `test_prune_expired_memories_keeps_recent()` - verify memories < 90 days are kept
- [ ] Implement: Logic already in place from previous task (date comparison)
- [ ] Commit: `test: verify recent memories are not pruned`

- [ ] Test: `test_prune_expired_memories_dry_run()` - verify dry_run=True returns count without deleting
- [ ] Implement: Add dry_run parameter that skips `_rewrite_entries()` call
- [ ] Commit: `feat(memory): add dry_run mode to prune_expired_memories()`

- [ ] Test: `test_prune_expired_memories_boundary()` - verify exactly 90 days old is kept (end of day)
- [ ] Implement: Adjust date comparison to use `entry.timestamp.date() < (today - timedelta(days=ttl_days))`
- [ ] Commit: `fix(memory): use end-of-day boundary for TTL pruning`

### 5. MemoryStore Threshold Check

- [ ] Test: `test_check_memory_threshold_below_threshold()` - verify returns False when count < threshold
- [ ] Implement: Add `def check_memory_threshold(self, threshold: int = 1000) -> tuple[bool, int]` method
- [ ] Commit: `feat(memory): add check_memory_threshold() method`

- [ ] Test: `test_check_memory_threshold_at_threshold()` - verify returns False when count == threshold
- [ ] Implement: Logic already in place (only True when count > threshold)
- [ ] Commit: `test: verify threshold check at exact threshold`

- [ ] Test: `test_check_memory_threshold_above_threshold()` - verify returns True when count > threshold
- [ ] Implement: Logic already in place from previous task
- [ ] Commit: `test: verify threshold check above threshold`

### 6. Config Parameters

- [ ] Test: `test_config_has_memory_ttl_days()` - verify Config has memory_ttl_days with default 90
- [ ] Implement: Add `memory_ttl_days: int = 90` to Config class in `src/config.py`
- [ ] Commit: `feat(config): add memory_ttl_days parameter`

- [ ] Test: `test_config_has_memory_warning_threshold()` - verify Config has memory_warning_threshold with default 1000
- [ ] Implement: Add `memory_warning_threshold: int = 1000` to Config class
- [ ] Commit: `feat(config): add memory_warning_threshold parameter`

### 7. RememberTool Permanent Parameter

- [ ] Test: `test_remember_tool_params_has_permanent_field()` - verify RememberToolParams has permanent field
- [ ] Implement: Add `permanent: bool = Field(False, description="Mark as permanent (skip 90-day TTL)")`
- [ ] Commit: `feat(tools): add permanent parameter to RememberTool`

- [ ] Test: `test_remember_tool_creates_permanent_entry()` - verify permanent=True is passed to MemoryEntry
- [ ] Implement: Update RememberTool.execute_stream() to pass `permanent=kwargs.get("permanent", False)`
- [ ] Commit: `feat(tools): pass permanent flag to MemoryEntry in RememberTool`

- [ ] Test: `test_remember_tool_default_permanent_false()` - verify default behavior creates non-permanent entry
- [ ] Implement: Already handled by default False in schema
- [ ] Commit: `test: verify RememberTool defaults to non-permanent`

### 8. UpdateMemoryTool Permanent Parameter

- [ ] Test: `test_update_memory_tool_params_has_permanent_field()` - verify UpdateMemoryToolParams has permanent field
- [ ] Implement: Add `permanent: bool | None = Field(None, description="Change permanent status (None = no change)")`
- [ ] Commit: `feat(tools): add permanent parameter to UpdateMemoryTool`

- [ ] Test: `test_update_memory_can_change_to_permanent()` - verify can set permanent=True on existing memory
- [ ] Implement: Update MemoryStore.update_entry() to accept `new_permanent` parameter
- [ ] Commit: `feat(memory): support updating permanent flag in update_entry()`

- [ ] Test: `test_update_memory_can_change_to_non_permanent()` - verify can set permanent=False on existing memory
- [ ] Implement: Logic already in place from previous task
- [ ] Commit: `test: verify can demote permanent memory to non-permanent`

- [ ] Test: `test_update_memory_permanent_none_no_change()` - verify permanent=None leaves flag unchanged
- [ ] Implement: Logic already in place (only update if new_permanent is not None)
- [ ] Commit: `test: verify permanent=None preserves existing flag`

### 9. Startup Pruning and Warning

- [ ] Test: `test_startup_prunes_expired_memories()` - verify pruning runs on startup
- [ ] Implement: Add pruning call in Alfred initialization (find where context/memory is initialized)
- [ ] Commit: `feat(startup): prune expired memories on startup`

- [ ] Test: `test_startup_shows_threshold_warning()` - verify toast shown when threshold exceeded
- [ ] Implement: Add threshold check and toast notification in startup sequence
- [ ] Commit: `feat(startup): show memory threshold warning via toast`

- [ ] Test: `test_startup_no_warning_below_threshold()` - verify no toast when below threshold
- [ ] Implement: Logic already in place (only show if exceeded)
- [ ] Commit: `test: verify no warning when below threshold`

### 10. Integration Tests

- [ ] Test: `test_full_memory_lifecycle()` - create memory, mark permanent, prune, verify kept
- [ ] Implement: No changes (integration test)
- [ ] Commit: `test: integration test for full memory lifecycle`

- [ ] Test: `test_memory_expires_after_90_days()` - create memory, advance time, prune, verify removed
- [ ] Implement: No changes (integration test with mocked time)
- [ ] Commit: `test: integration test for 90-day TTL expiration`

- [ ] Test: `test_backward_compatibility_with_old_data()` - load old JSONL without permanent field
- [ ] Implement: No changes (test verifies existing backward compat)
- [ ] Commit: `test: backward compatibility with old memory format`

### 11. Documentation

- [ ] Update: `src/tools/remember.py` docstring to mention permanent parameter
- [ ] Update: `src/tools/update_memory.py` docstring to mention permanent parameter
- [ ] Update: `templates/SYSTEM.md` to document 90-day TTL and permanent flag in tool reference
- [ ] Commit: `docs: update tool documentation for permanent flag and TTL`

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/memory.py` | Add `permanent` field, `get_memory_count()`, `prune_expired_memories()`, `check_memory_threshold()` |
| `src/config.py` | Add `memory_ttl_days`, `memory_warning_threshold` |
| `src/tools/remember.py` | Add `permanent` parameter |
| `src/tools/update_memory.py` | Add `permanent` parameter |
| `src/alfred.py` (or initialization file) | Add startup pruning and threshold check |
| `templates/SYSTEM.md` | Update tool reference with permanent flag and TTL |
| `tests/test_memory.py` | Add tests for all new functionality |
| `tests/test_memory_crud.py` | Add tests for permanent flag in CRUD operations |
| `tests/test_tools.py` (if exists) | Add tests for tool parameter changes |

---

## Success Criteria

- [ ] All tests pass (existing + new)
- [ ] MemoryEntry has `permanent: bool = False` field
- [ ] Serialization/deserialization handles permanent field
- [ ] `get_memory_count()` works
- [ ] `prune_expired_memories()` removes non-permanent > 90 days
- [ ] `prune_expired_memories(dry_run=True)` returns count without deleting
- [ ] Permanent memories never pruned
- [ ] Threshold warning shows via toast on startup
- [ ] RememberTool supports permanent parameter
- [ ] UpdateMemoryTool supports changing permanent flag
- [ ] Backward compatible with old JSONL data
- [ ] Documentation updated

---

## Notes

- Follow TDD: Write test first, see it fail, implement minimally, commit
- Each commit should be atomic and pass all tests
- Use conventional commit format: `feat`, `fix`, `test`, `docs`, `refactor`
- Run tests after each commit: `uv run pytest tests/test_memory.py -v`
