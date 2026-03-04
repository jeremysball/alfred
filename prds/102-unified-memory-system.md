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

1. **SYSTEM.md** - Core system identity (extracted from old AGENTS.md)
2. **AGENTS.md** - Behavior rules and tool usage guidance
3. **USER.md** - User profile, preferences, communication style
4. **SOUL.md** - Alfred's personality, voice, relationship with user

Plus any additional `.md` files in the workspace (loaded alphabetically).

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
├── SYSTEM.md              # Core identity
├── AGENTS.md              # Behavior rules
├── USER.md                # Includes prompts/communication-style.md
├── SOUL.md                # Includes prompts/voice.md
├── TOOLS.md               # Tool definitions (optional)
├── prompts/               # Modular prompt components
│   ├── communication-style.md
│   ├── tech-stack.md
│   ├── voice.md
│   └── memory-guidance.md
└── memories.jsonl         # Curated memories
```

### SYSTEM.md (New)

Extracted from AGENTS.md - core identity not specific to behavior:

```markdown
# System

You are Alfred, a persistent memory-augmented LLM assistant.
You remember conversations across sessions and learn user preferences over time.

## Core Identity

- Long-term collaborator, not a servant
- Remember context, don't re-ask
- Propose ideas, don't just execute
- Concise but warm, technically precise

## Capabilities

- File operations (read, write, edit)
- Shell command execution (bash)
- Memory management (remember, search, update)
- Session history search

## Response Style

- Lead with the answer, explain if needed
- Use specific examples, not abstractions
- Admit uncertainty clearly
- Ask before destructive actions
```

### AGENTS.md (Simplified)

Behavior rules and tool guidance only:

```markdown
# Agent Behavior

## Rules

1. **Permission First**: Ask before editing files, deleting data, API calls, destructive commands
2. **Use uv run dotenv**: For commands needing secrets
3. **Conventional Commits**: Follow conventionalcommits.org format
4. **Your Workspace**: `~/.local/share/alfred/workspace/` - edit freely here

## Memory System: How to Use It

You have three storage mechanisms. Here's when to use each:

### Files (USER.md, SOUL.md) - Durable, Always Loaded

**When to write:**
- User explicitly states enduring preference ("I always prefer...")
- Pattern emerges you want to permanently shape interactions
- Core identity facts (name, role, communication style)

**How to write:**
- Ask user: "Should I add this to USER.md?"
- Use `edit` tool if approved
- Be concise - these load every time

**Cost:** High (loaded in full every prompt). Use sparingly.

### Memories (remember tool) - Curated, Searchable, 90-day TTL

**When to remember:**
- User says "remember this" or "don't forget..."
- Specific fact worth recalling later (project details, decisions)
- Preference that might evolve ("I currently use...")
- Anything you'd search for later

**How to remember:**
```
remember(content="User is migrating from PostgreSQL to SQLite", tags=["project", "database"])
```

**When to search:**
- User asks "what did I say about..."
- You need context from previous conversations
- Unsure if you already know something

**How to search:**
```
search_memories(query="database migration", top_k=5)
```

**Cost:** Low (only relevant memories retrieved). Feel free to use liberally.

**Warning:** At X memories, user is warned about storage. Memories expire after 90 days unless marked permanent.

### Session Archive (search_sessions) - Full History

**When to search:**
- "What did we discuss last Tuesday?"
- "Find that idea about cron system"
- Need specific conversation context from months ago

**How to search:**
```
search_sessions(query="cron system ideas", top_k=3)
```

**Cost:** Medium (searches full history). Use when memories insufficient.

## Tool Reference

### Memory Tools

**remember(content, tags=None)**
Save to curated memory. Use for facts worth recalling.

**search_memories(query, top_k=5)**
Semantic search of memories. Use before asking user what they already told you.

**update_memory(entry_id, new_content)**
Modify existing memory. Preview first, confirm with user.

**forget(query or entry_id)**
Delete memory. Preview first, confirm with user.

**search_sessions(query, top_k=3)**
Search full session history. Use for "what did we discuss..." questions.

### File Tools

**read(path)** - Read file contents
**write(path, content)** - Create/overwrite file
**edit(path, oldText, newText)** - Precise text replacement
**bash(command)** - Execute shell command

## Best Practices

1. **Search before asking** - Check memories before asking user to repeat themselves
2. **Prefer memories over files** - For facts that might change, use remember() not USER.md
3. **Files for identity, memories for facts** - USER.md = who they are; memories = what they said
4. **Expire gracefully** - 90-day TTL means stale memories fade; refresh important ones
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
class PromptLoader:
    """Load files with placeholder resolution."""
    
    PLACEHOLDER_PATTERN = re.compile(r'\{\{([^}]+)\}\}')
    MAX_DEPTH = 5  # Prevent infinite recursion
    
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.loaded = set()  # Track for circular detection
    
    async def load(self, filename: str, depth: int = 0) -> str:
        """Load file and resolve placeholders."""
        if depth > self.MAX_DEPTH:
            raise RecursionError(f"Max placeholder depth exceeded in {filename}")
        
        if filename in self.loaded:
            raise CircularReferenceError(f"Circular reference detected: {filename}")
        
        self.loaded.add(filename)
        
        try:
            file_path = self.workspace_dir / filename
            content = await self._read_file(file_path)
            
            # Resolve placeholders
            async def replace_placeholder(match: re.Match) -> str:
                include_path = match.group(1).strip()
                try:
                    included = await self.load(include_path, depth + 1)
                    return f"<!-- included: {include_path} -->\n{included}\n<!-- end: {include_path} -->"
                except FileNotFoundError:
                    logger.warning(f"Placeholder file not found: {include_path}")
                    return f"<!-- missing: {include_path} -->"
            
            content = await self.PLACEHOLDER_PATTERN.sub(replace_placeholder, content)
            return content
        finally:
            self.loaded.remove(filename)
    
    async def load_all_context(self) -> dict[str, str]:
        """Load all context files in order."""
        files = [
            "SYSTEM.md",
            "AGENTS.md", 
            "USER.md",
            "SOUL.md",
        ]
        
        # Add any other .md files in workspace
        for md_file in sorted(self.workspace_dir.glob("*.md")):
            if md_file.name not in files:
                files.append(md_file.name)
        
        context = {}
        for filename in files:
            if (self.workspace_dir / filename).exists():
                context[filename] = await self.load(filename)
        
        return context
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

### M1: SYSTEM.md Extraction
**Scope:** Create SYSTEM.md from AGENTS.md, simplify AGENTS.md

- [ ] Create `templates/SYSTEM.md` with core identity (from AGENTS.md)
- [ ] Simplify `templates/AGENTS.md` to behavior rules + memory guidance only
- [ ] Update template copying to include SYSTEM.md
- [ ] Test both files load correctly

**Success Criteria:**
- SYSTEM.md exists and contains core identity
- AGENTS.md focuses on behavior and tool usage
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
**Scope:** Implement `{{path}}` placeholder resolution

- [ ] Implement `PromptLoader` class with placeholder resolution
- [ ] Add circular reference detection
- [ ] Add max depth protection
- [ ] Handle missing files gracefully (log warning, insert comment)
- [ ] Add HTML comment wrappers for transparency
- [ ] Tests for placeholder resolution

**Success Criteria:**
- `{{prompts/example.md}}` resolves and includes content
- Circular references raise clear error
- Missing files log warning, don't crash
- Nested placeholders work (depth <= 5)

### M4: Prompts Folder Structure
**Scope:** Support modular prompts in `prompts/` subdirectory

- [ ] Create `templates/prompts/` directory
- [ ] Move reusable prompt sections to individual files
- [ ] Update USER.md and SOUL.md to use placeholders
- [ ] Example: `prompts/communication-style.md`, `prompts/voice.md`
- [ ] Tests for loading prompts folder

**Success Criteria:**
- `templates/prompts/` created with example files
- USER.md includes `{{prompts/communication-style.md}}`
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
- [ ] Update documentation

**Success Criteria:**
- Full system works end-to-end
- All tests pass
- Documentation updated
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

---

## Acceptance Criteria

- [ ] SYSTEM.md and AGENTS.md separation clear and documented
- [ ] Placeholder system works: `{{path}}` resolves correctly
- [ ] Circular reference detection prevents infinite loops
- [ ] Memory TTL is 90 days (not 30)
- [ ] Warning at X memories (configurable threshold)
- [ ] Permanent flag skips TTL
- [ ] No auto-capture or auto-consolidation
- [ ] Model guidance prompt explains memory system clearly
- [ ] Session archive searchable with contextual retrieval
- [ ] All existing tests pass or updated
- [ ] New tests for placeholder system

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-04 | Simplified two-store model | Three tiers confused users and model |
| 2026-03-04 | Model decides all writes | Auto-capture created noise, auto-consolidation was complex |
| 2026-03-04 | 90-day TTL (not 30) | Longer horizon for memories, warn at threshold instead |
| 2026-03-04 | Placeholder system | Modular prompts, separation of concerns |
| 2026-03-04 | SYSTEM.md extraction | Core identity separate from behavior rules |
| 2026-03-04 | Merge #21 concepts | Learning system = model deciding when to write (simpler) |

---

## Open Questions

1. **Warning threshold X**: Default 1000 memories? Configurable?
2. **Permanent flag UI**: How does user mark memory permanent? Tool parameter or separate action?
3. **Migration strategy**: Auto-migrate or prompt user?
4. **Prompt size limits**: With placeholders, how to prevent oversized prompts?
