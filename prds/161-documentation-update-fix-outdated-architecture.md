# PRD #161: Documentation Update - Fix Outdated Architecture

## Problem Statement

The architecture documentation is severely outdated and misleading:

- **ARCHITECTURE.md** describes JSONL storage that was migrated to SQLite (PRD #117)
- Missing Web UI and PyPiTUI interfaces entirely
- Missing AlfredCore abstraction (PRD #119)
- Incorrect file paths (e.g., `src/config.py` → `src/alfred/config.py`)
- Still references `TOOLS.md` which was phased out (PRD #102)
- No mention of local embeddings (BGE provider, PRD #105)
- Missing unified memory system changes

This misleads new developers and creates confusion about the actual system design.

## Success Criteria

- [ ] ARCHITECTURE.md accurately reflects current codebase structure
- [ ] All interfaces (Telegram, PyPiTUI, Web UI) documented
- [ ] Storage layer correctly describes SQLite (not JSONL)
- [ ] New core components (AlfredCore, self_model, observability) covered
- [ ] Embedding providers (OpenAI + BGE) documented
- [ ] Related outdated docs identified and updated/archived

## Milestones

### M1: Audit Current Documentation
**Objective**: Create comprehensive inventory of documentation gaps

**Deliverables**:
- [ ] Document-by-document comparison with codebase
- [ ] List of all outdated claims vs. current reality
- [ ] Prioritization of docs needing updates

**Validation**:
- [ ] Spreadsheet/list of all docs with status (current/stale/obsolete)
- [ ] Specific outdated claims identified with line references

---

### M2: Rewrite ARCHITECTURE.md
**Objective**: Complete rewrite of primary architecture document

**Deliverables**:
- [ ] Update system component diagram (include all 3 interfaces)
- [ ] Document AlfredCore abstraction and factory pattern
- [ ] Correct storage section: SQLite, not JSONL
- [ ] Document unified memory system (Files + Memories + Sessions)
- [ ] Add embeddings module with both providers
- [ ] Update all file paths to correct locations
- [ ] Document new modules: observability, self_model, placeholders

**Validation**:
- [ ] Every file path in ARCHITECTURE.md exists in codebase
- [ ] All interfaces mentioned have corresponding code
- [ ] Storage description matches `storage/sqlite.py` implementation

---

### M3: Update Supporting Documentation
**Objective**: Fix or archive related outdated docs

**Deliverables**:
- [ ] Update `API.md` to match current module structure
- [ ] Verify `MEMORY.md` reflects SQLite storage
- [ ] Verify `EMBEDDINGS.md` includes BGE provider
- [ ] Archive or update `CAS_*.md` files (CAS was replaced by SQLite)
- [ ] Verify `cron-jobs.md` reflects socket API (PRD #120)

**Validation**:
- [ ] No document references deprecated JSONL storage
- [ ] All code examples in docs are syntactically valid
- [ ] Cross-references between docs are accurate

---

### M4: Add Missing Interface Documentation
**Objective**: Document PyPiTUI and Web UI interfaces

**Deliverables**:
- [ ] Document PyPiTUI architecture (`interfaces/pypitui/`)
- [ ] Document Web UI architecture (`interfaces/webui/`)
- [ ] Document ANSI interface (`interfaces/ansi.py`)
- [ ] Document command structure for PyPiTUI

**Validation**:
- [ ] New developer can understand interface architecture from docs
- [ ] All interface modules have corresponding documentation

---

### M5: Documentation Review and Integration
**Objective**: Ensure consistency across all documentation

**Deliverables**:
- [ ] Cross-reference check: all internal links valid
- [ ] Terminology consistency (e.g., "memory" vs "memories" vs "sessions")
- [ ] Decision log updated with doc refresh rationale
- [ ] ROADMAP.md updated to mark doc update complete

**Validation**:
- [ ] No broken internal links
- [ ] Consistent terminology throughout
- [ ] ROADMAP.md reflects updated documentation status

## Outdated Documentation Inventory

| Document | Status | Issues |
|----------|--------|--------|
| ARCHITECTURE.md | 🔴 Critical | JSONL→SQLite, missing interfaces, wrong paths |
| API.md | 🟡 Likely stale | Module structure changed |
| MEMORY.md | 🟡 Verify | May reference JSONL |
| EMBEDDINGS.md | 🟡 Verify | May not cover BGE provider |
| CAS_DESIGN.md | 🟡 Obsolete | CAS replaced by SQLite |
| CAS_ATOMICITY.md | 🟡 Obsolete | CAS replaced by SQLite |
| cron-jobs.md | 🟡 Verify | Pre-socket API |
| job-api.md | 🟡 Verify | Pre-socket API |

## Key Changes to Document

### Storage Layer (PRD #117)
- **Before**: JSONL files with CAS atomicity
- **After**: Unified SQLite with ACID transactions
- **Files**: `storage/sqlite.py` (80KB, main storage module)

### Interfaces (PRDs #94, #95, #97, Web UI)
- **Telegram**: `interfaces/telegram.py` (existing)
- **PyPiTUI**: `interfaces/pypitui/` package with 15+ modules
- **Web UI**: `interfaces/webui/` package with server, protocol, validation

### Core Abstraction (PRD #119)
- **AlfredCore**: `core.py` - shared services container
- **Factories**: `factories.py` - dependency injection

### Memory System (PRD #102)
- **Before**: Three-tier (memories, session summaries, session messages)
- **After**: Files + Memories (90-day TTL) + Session Archive
- **Storage**: All in SQLite

### Embeddings (PRD #105)
- **OpenAI**: `embeddings/openai_provider.py`
- **BGE Local**: `embeddings/bge_provider.py`

### New Modules (Post-ARCHITECTURE.md)
- `observability.py` - logging and monitoring
- `self_model.py` - Alfred's self-awareness
- `placeholders.py` - template variable system
- `context_display.py` - context visualization

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-27 | Create documentation refresh PRD | ARCHITECTURE.md is critically outdated and misleading |
| | Archive CAS docs | CAS storage replaced by SQLite in PRD #117 |
| | Keep API.md | Update rather than replace; still valuable reference |

## Dependencies

None - this is a documentation-only change.

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Docs still drift after update | Add "last verified" dates; include doc review in PR template |
| Incomplete coverage | Systematic audit checklist (M1) |
| Conflicting with in-flight PRs | Coordinate with active PR authors |
