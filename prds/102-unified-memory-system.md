# PRD: Unified Memory System

## Overview

**Issue**: #102  
**Replaces**: #77 (Contextual Retrieval System), #21 (Learning System) - concepts merged  
**Parent**: #10 (Alfred - The Rememberer)  
**Status**: Planning  
**Priority**: High  
**Created**: 2026-03-04

Simplified memory architecture: Files (always loaded, durable) + Memories (curated, 90-day TTL) + Session Archive (searchable history). Model decides all writes. Placeholder system for modular prompts.

---

## Problem Statement

Alfred's memory is fragmented and over-engineered:
- Three-tier architecture confuses users and model
- Auto-capture creates noise
- Consolidation flows add complexity
- AGENTS.md mixes system instructions with behavior rules
- No way to modularize prompts

We need a simpler model the user and LLM can both understand intuitively.

---

## Solution

### Core Philosophy

**You have three places to store information. Pick the right tool for the job.**

```
┌─────────────────────────────────────────────────────────────┐
│  FILES (USER.md, SOUL.md, SYSTEM.md, AGENTS.md)             │
│  • Always loaded in every prompt                            │
│  • Expensive (full content) but always available            │
│  • Durable - never expire                                   │
│  • YOU decide when to write                                 │
│  • Use for: core identity, enduring preferences, rules      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  MEMORIES (remember tool → memories.jsonl)                  │
│  • Semantic search available                                │
│  • Curated - YOU decide what to remember                    │
│  • 90-day TTL (warn user at X memories)                     │
│  • Use for: facts, preferences, context worth recalling     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  SESSION ARCHIVE (automatic)                                │
│  • Full conversation history                                │
│  • Searchable via search_sessions                           │
│  • Use for: "what did we discuss last Tuesday?"             │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Model decides everything** - No auto-capture, no auto-consolidation. You choose what to remember and when to update files.

2. **Files are expensive but reliable** - Always loaded means you can always reference them. Use sparingly for what truly matters.

3. **Memories are curated** - Use `remember` tool for facts worth recalling. Search with `search_memories`. They expire after 90 days unless you explicitly mark permanent.

4. **Session archive is automatic** - Full history for deep recall. Search it when you need specific past conversations.

---

## File Architecture

### File Types and Loading

Files are loaded in this order (all from `~/.local/share/alfred/workspace/`):

1. **SYSTEM.md** - Memory system architecture + cron capabilities (teaches Alfred how to use the system)
2. **AGENTS.md** - Minimal behavior rules (Permission First, Conventional Commits, etc.)
3. **USER.md** - User profile, preferences (LLM prefs, notification settings)
4. **SOUL.md** - Alfred's personality, voice, relationship with user

Plus any additional `.md` files in the workspace (loaded alphabetically).

**Note:** TOOLS.md is phased out. Content moved to SYSTEM.md (cron capabilities) and USER.md (preferences).

### Placeholder System

Any file can include content from other files using placeholders:

```markdown
# USER.md

{{prompts/communication-style.md}}

## Technical Preferences
{{prompts/tech-stack.md}}
```

**Syntax:** `{{relative/path/from/workspace.md}}`

**Resolution rules:**
- Path is relative to `~/.local/share/alfred/workspace/`
- Can reference `.md` files or any text file
- Nested placeholders allowed (A includes B, B includes C)
- Circular references detected and error shown
- Missing files logged but don't crash

**Example structure:**
```
workspace/
├── SYSTEM.md              # Memory architecture + cron capabilities
├── AGENTS.md              # Minimal behavior rules
├── USER.md                # User preferences (includes prompts/...)
├── SOUL.md                # Alfred's personality (includes prompts/...)
├── prompts/               # Modular prompt components
│   ├── communication-style.md
│   ├── tech-stack.md
│   ├── voice.md
│   └── memory-guidance.md
└── memories.jsonl         # Curated memories
```

### SYSTEM.md (New)

Memory system architecture + cron capabilities. Teaches Alfred how the system works:

```markdown
# System

## Memory Architecture

You have three storage mechanisms. Understanding how they work helps you use them effectively.

### Files (USER.md, SOUL.md, SYSTEM.md, AGENTS.md)

- Always loaded in full every time you respond
- Expensive but always available
- Durable - never expire
- Use for: core identity, enduring preferences, critical rules

**When to write:** Ask user first. "Should I add this to USER.md?"

**Cost:** High (loaded every prompt). Use sparingly.

### Memories (remember tool)

- Semantic search available via search_memories
- You decide what to remember - no auto-capture
- 90-day TTL unless marked permanent
- Use for: facts worth recalling, preferences that might evolve

**When to remember:** User says "remember this" or you decide a fact is worth keeping.

**Cost:** Low (only relevant memories retrieved). Use liberally.

**When to search:** Before asking user to repeat themselves.

### Session Archive (search_sessions)

- Full conversation history
- Searchable via two-stage contextual retrieval
- Use for: "what did we discuss last Tuesday?"

**When to search:** When memories are insufficient and you need specific past conversations.

## Decision Framework

| Information Type | Store In | Example |
|-----------------|----------|---------|
| Core identity | USER.md/SOUL.md | "I always prefer concise answers" |
| Specific fact | remember() | "Using FastAPI for this project" |
| Past conversation | search_sessions | "What did we discuss Tuesday?" |
| Temporary state | remember() | "Currently debugging auth" |
| Enduring preference | USER.md | "I'm a Python developer" |

## Cron Job Capabilities

When writing cron jobs, these functions are automatically available:

### `await notify(message)`
Send notification to user (CLI toast or Telegram message).

### `print()`
Output is captured in job execution history.

## Tool Reference

**remember(content, tags=None)** - Save to curated memory
**search_memories(query, top_k=5)** - Semantic search of memories
**search_sessions(query, top_k=3)** - Search full session history
```

### AGENTS.md (Minimal)

Essential behavior rules only:

```markdown
# Agent Behavior

## Rules

1. **Permission First**: Ask before editing files, deleting data, making API calls, or running destructive commands.

2. **Conventional Commits**: Follow conventionalcommits.org format for all commits.

3. **Simple Correctness**: Temper the drive to over-engineer. Ask: "Is this the simplest thing that could work?" Avoid premature abstraction.

## Communication

Be concise. Confirm ambiguous requests. Admit uncertainty.
```

---

## Memory System Details

### Memories (Curated Store)

**Storage:** `~/.local/share/alfred/memory/memories.jsonl`

**Schema:**
```python
@dataclass
class Memory:
    id: str                    # UUID
    timestamp: datetime        # Created
    content: str               # The memory text
    embedding: list[float]     # For semantic search
    tags: list[str]            # Optional organization
    permanent: bool            # Skip TTL if True
    session_id: str | None     # Link to source session
```

**TTL Behavior:**
- Default: 90 days from creation
- Permanent memories: Never expire
- Warning threshold: X memories (configurable, default 1000)
- When threshold hit: "You have 1000 memories. Consider reviewing old ones or marking important memories as permanent."

**Search:**
- Semantic similarity via cosine distance on embeddings
- Optional tag filtering: `search_memories(query="auth", tags=["project"])`
- Direct lookup: `search_memories(entry_id="uuid")`

### Session Archive

**Storage:** `~/.local/share/alfred/sessions/{session_id}/`

**Structure:**
```
sessions/
├── {session_id}/
│   ├── messages.jsonl       # All messages with embeddings
│   └── summary.json         # Session summary + embedding
```

**Search:** Contextual retrieval pattern:
1. Search session summaries for relevant sessions
2. Search messages within those sessions only
3. Return hierarchical results (session + messages)

---

## Prompt for Model: How to Use Memory

This prompt section is injected into the system prompt:

```markdown
## Memory System

You have three ways to store and retrieve information. Choose wisely:

### 1. FILES (USER.md, SOUL.md) - Durable Identity

These files are **always loaded in full** every time you respond. They're expensive but reliable.

**Write to files when:**
- The user explicitly states something core to their identity ("I always...", "I never...")
- A pattern is so fundamental it should shape every future interaction
- You're capturing "who they are" not "what they said"

**Always ask first:** "Should I add this to USER.md?"

**Examples for files:**
- "I prefer concise responses" → USER.md
- "I'm a night owl, often work 11pm-2am" → USER.md  
- "Be direct with me, I hate fluff" → SOUL.md (shapes how you relate)

### 2. MEMORIES (remember tool) - Curated Facts

Memories are **searched on demand** - cheap to store, cheap to retrieve.

**Remember when:**
- User says "remember this" or "don't forget..."
- Specific detail worth recalling later (project name, technical decision)
- Preference that might evolve over time
- Anything you'd want to search for later

**Don't ask** - just remember. That's what the tool is for.

**Examples for memories:**
- "We're using PostgreSQL for this project" → remember
- "I hate the color blue" → remember (might be joking)
- "My laptop keeps overheating" → remember (temporary issue)
- User mentions a specific bug or error → remember

**Search memories when:**
- User asks "what did I say about..."
- You're unsure if you've discussed something before
- You need context from previous sessions

**Pattern:** search_memories(query="...") before asking user to repeat themselves.

### 3. SESSION ARCHIVE (search_sessions) - Full History

Every conversation is recorded. Use this for deep recall.

**Search sessions when:**
- "What did we discuss last Tuesday?"
- "Remind me of that idea I had..."
- Memories don't have what you need, but you know you discussed it

**Pattern:** search_sessions(query="...", top_k=3) for historical context.

### Decision Framework

| Information Type | Store In | Example |
|-----------------|----------|---------|
| Core identity | USER.md/SOUL.md | "I always prefer concise answers" |
| Specific fact | remember() | "Using FastAPI for this project" |
| Past conversation | search_sessions | "What did we discuss Tuesday?" |
| Temporary state | remember() | "Currently debugging auth" |
| Enduring preference | USER.md | "I'm a Python developer" |

### TTL Warning

Memories expire after 90 days unless marked permanent. This is intentional - stale context fades away. If something is still true after 90 days, either:
- The user will remind you
- It's important enough to mark permanent
- It wasn't that important

At X memories, the user gets a warning. They can review and clean up, or mark important ones permanent.
```

---

## File Loading with Placeholders

### Implementation

```python
class ResolutionContext:
    """Context passed through placeholder resolution."""

    def __init__(self, base_dir: Path, max_depth: int = 5):
        self.base_dir = base_dir
        self.max_depth = max_depth
        self._loaded: set[Path] = set()
        self._depth: int = 0

    def with_loaded(self, path: Path) -> ResolutionContext:
        """Create new context with path added to loaded set."""
        ctx = ResolutionContext(self.base_dir, self.max_depth)
        ctx._loaded = self._loaded | {path}
        ctx._depth = self._depth
        return ctx

    def with_incremented_depth(self) -> ResolutionContext:
        """Create new context with depth + 1."""
        ctx = ResolutionContext(self.base_dir, self.max_depth)
        ctx._loaded = self._loaded.copy()
        ctx._depth = self._depth + 1
        return ctx

    def is_depth_exceeded(self) -> bool:
        """Check if max depth exceeded (log, don't raise)."""
        if self._depth > self.max_depth:
            logger.warning(f"Max placeholder depth ({self.max_depth}) exceeded")
            return True
        return False

    def is_circular(self, path: Path) -> bool:
        """Check for circular references (log, don't raise)."""
        if path in self._loaded:
            logger.error(f"Circular reference detected: {path}")
            return True
        return False


class PlaceholderResolver(Protocol):
    """Protocol for placeholder resolvers."""
    pattern: re.Pattern

    def resolve(self, match: re.Match, context: ResolutionContext) -> str:
        """Resolve a placeholder match to its replacement text."""
        ...


def resolve_placeholders(
    text: str,
    context: ResolutionContext,
    resolvers: list[PlaceholderResolver] | None = None,
) -> str:
    """Resolve all placeholders in text."""
    # Implementation handles all placeholder types
    # Supports file includes {{path}} and colors {color}
```

### Placeholder Comments

Resolved placeholders are wrapped in HTML comments for transparency:

```markdown
<!-- included: prompts/communication-style.md -->
## Communication Style

- Prefers concise responses
- Appreciates code examples
<!-- end: prompts/communication-style.md -->
```

This helps debug what's actually loaded in the prompt.

---

## Milestones

### M1: SYSTEM.md Creation
**Scope:** Create SYSTEM.md with memory architecture, simplify AGENTS.md

- [ ] Create `templates/SYSTEM.md` with memory system architecture + cron capabilities
- [ ] Create `templates/AGENTS.md` with minimal behavior rules (3 rules + communication)
- [ ] Remove operational details (uv dotenv, workspace paths) from AGENTS.md
- [ ] Update template copying to include SYSTEM.md
- [ ] Test both files load correctly

**Success Criteria:**
- SYSTEM.md contains memory architecture + cron capabilities
- AGENTS.md has minimal behavior rules only
- No operational details (uv, paths) in AGENTS.md
- Both copied to workspace on first run

### M2: AGENTS.md Atomic Unit Extraction
**Scope:** Extract atomic sections from AGENTS.md into separate files

**Identify atomic units** (self-contained sections that can stand alone):
- Memory system guidance (detailed how-to-use-memory section)
- Tool reference section (list of all tools with descriptions)
- Communication guidelines
- Best practices section
- Code style / commit conventions

**Process:**
- [ ] Audit AGENTS.md and identify atomic sections
- [ ] Create `prompts/agents/` subdirectory for extracted sections
- [ ] Extract each atomic unit to its own `.md` file:
  - `prompts/agents/memory-system.md`
  - `prompts/agents/tool-reference.md`
  - `prompts/agents/communication.md`
  - `prompts/agents/best-practices.md`
- [ ] Replace extracted content in AGENTS.md with placeholders:
  ```markdown
  # Agent Behavior

  ## Memory System
  {{prompts/agents/memory-system.md}}

  ## Tool Reference
  {{prompts/agents/tool-reference.md}}
  ```
- [ ] Ensure each extracted file is self-contained and makes sense standalone
- [ ] Tests for each extracted file loading correctly

**Success Criteria:**
- AGENTS.md uses placeholders for major sections
- Each extracted file is atomic (self-contained, understandable alone)
- All placeholders resolve correctly
- Total prompt content is identical before/after extraction

### M3: Placeholder System
**Scope:** Implement unified placeholder system for files and colors

- [x] Create `src/placeholders.py` module
- [x] Implement `ResolutionContext` class with parameter-based recursion
- [x] Implement `PlaceholderResolver` Protocol
- [x] Implement `FileIncludeResolver` for `{{path}}` placeholders
- [x] Implement `ColorResolver` for `{color}` placeholders
- [x] Add circular reference detection (log, don't raise)
- [x] Add max depth protection (log, don't raise)
- [x] Handle missing files gracefully (log warning, insert comment)
- [x] Add HTML comment wrappers for transparency
- [x] Create convenience functions: `resolve_file_includes()`, `resolve_colors()`, `resolve_all()`
- [x] Update `ContextLoader` to use new system
- [x] Tests for all resolver types

**Success Criteria:**
- `{{prompts/example.md}}` resolves and includes content
- `{cyan}text{reset}` resolves to ANSI codes
- Circular references log error and return `<!-- circular: path -->` comment
- Missing files log warning and return `<!-- missing: path -->` comment
- Nested placeholders work (depth <= 5)
- Max depth exceeded logs warning, returns original placeholder

### M4: Prompts Folder Structure
**Scope:** Support modular prompts in `prompts/` subdirectory

- [x] Create `templates/prompts/` directory
- [x] Move reusable prompt sections to individual files
- [x] Update USER.md and SOUL.md to use placeholders
- [x] Example: `prompts/communication-style.md`, `prompts/voice.md`
- [x] Tests for loading prompts folder

**Success Criteria:**
- `templates/prompts/` created with example files
- SOUL.md includes `{{prompts/voice.md}}` and `{{prompts/boundaries.md}}`
- All placeholders resolve correctly

### M5: Memory System Simplification
**Scope:** Remove three-tier complexity, implement simplified model

- [ ] Remove auto-capture logic
- [ ] Remove auto-consolidation logic  
- [ ] Change TTL from 30 to 90 days
- [ ] Add `permanent` flag to memory schema
- [ ] Add warning threshold X (default 1000 memories)
- [ ] Update memory guidance in AGENTS.md (now extracted to prompts/agents/memory-system.md)
- [ ] Update all memory-related tests

**Success Criteria:**
- No auto-capture or auto-consolidation
- 90-day TTL active
- Warning shown at X memories
- Permanent flag works to skip TTL

### M6: Model Memory Guidance
**Scope:** Create and inject "How to Use Memory" prompt section

- [ ] Write comprehensive memory guidance prompt (see "Prompt for Model" section)
- [ ] Save to `prompts/agents/memory-system.md` (or `prompts/memory-guidance.md`)
- [ ] Reference from AGENTS.md via placeholder
- [ ] Include decision framework table
- [ ] Include TTL explanation
- [ ] Test that model follows guidance

**Success Criteria:**
- Memory guidance appears in every system prompt
- Model uses remember() appropriately
- Model asks before editing USER.md
- Model searches memories before asking

### M7: Session Archive Contextual Retrieval
**Scope:** Implement search_sessions with contextual narrowing

- [ ] Store session summaries with embeddings
- [ ] Implement two-stage search (summaries → messages)
- [ ] Create `search_sessions` tool
- [ ] Return hierarchical results
- [ ] Tests for contextual retrieval

**Success Criteria:**
- `search_sessions(query)` finds relevant sessions
- Within-session message search works
- Results include session context + specific messages

### M8: Integration & Testing
**Scope:** Wire everything together, comprehensive tests

- [ ] Update context assembly to use new file loading
- [ ] Update all references to old three-tier model
- [ ] End-to-end test: file loading → placeholder resolution → memory usage
- [ ] Performance test: large prompt with many placeholders

**Success Criteria:**
- Full system works end-to-end
- All tests pass
- Ready for release

### M9: Migration (if needed)
**Scope:** Handle existing users with old memory format

- [ ] Detect old three-tier memory structure
- [ ] Migrate to new format (or clear with user permission)
- [ ] Handle old AGENTS.md (merge with new SYSTEM.md)
- [ ] Migration tests

**Success Criteria:**
- Existing users can upgrade smoothly
- Old memories preserved or migrated
- Clear migration message to user

### M10: Documentation Update
**Scope:** Update all documentation to reflect new architecture

**Files to update:**
- [ ] `docs/ROADMAP.md` - Update memory system section
- [ ] `docs/ARCHITECTURE.md` (if exists) - Update file descriptions
- [ ] `README.md` - Update quickstart and architecture overview
- [ ] `templates/README.md` (if exists) - Explain file purposes

**Content changes:**
- [ ] Document SYSTEM.md purpose and content
- [ ] Document AGENTS.md as minimal behavior rules only
- [ ] Document TOOLS.md phase-out (content moved)
- [ ] Update file loading order (SYSTEM.md first)
- [ ] Update memory system explanation (simplified model)
- [ ] Add placeholder system documentation
- [ ] Update decision log references

**Success Criteria:**
- All documentation reflects new file architecture
- No references to old three-tier model
- TOOLS.md phase-out explained
- Placeholder system documented
- Migration guide for existing users

---

## Acceptance Criteria

- [ ] SYSTEM.md and AGENTS.md separation clear and documented
- [x] Placeholder system works: `{{path}}` resolves correctly
- [x] Circular reference detection prevents infinite loops
- [ ] Memory TTL is 90 days (not 30)
- [ ] Warning at X memories (configurable threshold)
- [ ] Permanent flag skips TTL
- [ ] No auto-capture or auto-consolidation
- [ ] Model guidance prompt explains memory system clearly
- [ ] Session archive searchable with contextual retrieval
- [x] All existing tests pass or updated
- [x] New tests for placeholder system
- [x] All documentation updated (ROADMAP, README, etc.)
- [ ] TOOLS.md phase-out documented
- [ ] Migration guide for existing users

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-04 | Simplified two-store model | Three tiers confused users and model |
| 2026-03-04 | Model decides all writes | Auto-capture created noise, auto-consolidation was complex |
| 2026-03-04 | 90-day TTL (not 30) | Longer horizon for memories, warn at threshold instead |
| 2026-03-04 | Placeholder system | Modular prompts, separation of concerns |
| 2026-03-04 | SYSTEM.md extraction | Contains memory architecture + cron capabilities (the "programming") |
| 2026-03-04 | AGENTS.md stripped down | Minimal behavior rules only (no uv dotenv, no workspace details) |
| 2026-03-04 | Phase out TOOLS.md | Content moves to SYSTEM.md (cron) and USER.md (preferences) |
| 2026-03-04 | Tool definitions from code | Pydantic schemas define tools, not TOOLS.md |
| 2026-03-04 | Merge #21 concepts | Learning system = model deciding when to write (simpler) |
| 2026-03-04 | Unified placeholder system | Single API for file includes {{path}} and colors {color}, extensible via Protocol pattern |
| 2026-03-04 | Parameter-based recursion | Pass ResolutionContext through calls for clean state management |
| 2026-03-04 | Defensive error handling | Log warnings/errors instead of raising for circular refs and max depth |
| 2026-03-04 | No backward compatibility | Directly update ContextLoader, no legacy support needed |

---

## Open Questions

1. **Warning threshold X**: Default 1000 memories? Configurable?
2. **Permanent flag UI**: How does user mark memory permanent? Tool parameter or separate action?
3. **Migration strategy**: Auto-migrate or prompt user?
4. **Prompt size limits**: With placeholders, how to prevent oversized prompts?
