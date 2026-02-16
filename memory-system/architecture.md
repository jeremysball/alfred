# Memory System Architecture

How OpenClaw creates persistent memory through files.

## The Core Insight

> **Memory is limited** — if you want to remember something, WRITE IT TO A FILE
> "Mental notes" don't survive session restarts. Files do.

The entire memory system is built on this principle: **Text > Brain**.

## Memory Hierarchy

```
┌────────────────────────────────────────────────────────────────┐
│                      MEMORY LEVELS                             │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Level 1: MEMORY.md (Long-term, Curated)                       │
│  ────────────────────────────────────                          │
│  - Who the human is (name, timezone, context)                  │
│  - Important frameworks and mental models                      │
│  - Core goals and priorities                                   │
│  - Key insights about the person                               │
│  - Lessons learned                                             │
│                                                                │
│  Updated: Periodically (every few days during heartbeats)      │
│  Purpose: Distilled wisdom, not raw logs                       │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Level 2: memory/YYYY-MM-DD.md (Daily Notes)                   │
│  ──────────────────────────────────────                        │
│  - What happened today                                         │
│  - Conversations had                                           │
│  - Decisions made                                              │
│  - Context worth remembering                                   │
│  - Things to follow up on                                      │
│                                                                │
│  Updated: Throughout the day                                   │
│  Purpose: Raw notes for recent context                         │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Level 3: notes/ (Topical Organization)                        │
│  ──────────────────────────────────                            │
│  - notes/systems/ — How things work                            │
│  - notes/policies/ — Rules to follow                           │
│  - notes/projects/ — Project-specific context                  │
│                                                                │
│  Updated: As needed                                            │
│  Purpose: Organize by theme, not time                          │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## The Startup Ritual

From AGENTS.md, every session:

```markdown
Before doing anything else:

1. Read SOUL.md — this is who you are
2. Read USER.md — this is who you're helping
3. Read memory/YYYY-MM-DD.md (today + yesterday) for recent context
4. If in MAIN SESSION (direct chat): Also read MEMORY.md
5. Scan notes/ folder for relevant context
```

This ensures the agent "wakes up" with full context.

## MEMORY.md Structure

```markdown
# MEMORY.md - Long-term Memory for [Human Name]

## About [Human]

**Name:** Jeremy "Jaz" Ball
**Call them:** Jaz or Jeremy
**Location:** Butler, PA (EST timezone)
**Son due:** ~30 days (March 2026)

## The War (Most Important Framework)

**What it is:** A 20-year pattern where Jaz treats everything as a battle...

**The way out:** Acceptance. "There is nothing to solve."

**My role:** When Jaz mentions "the war" or spirals — remind him of this.

## Core Goals (Priority Order)

### 1. GET EMPLOYED
**Status:** 🔴 Not Started
**Skills to leverage:** ~24,000 LOC across Kotlin, Go, Python...

### 2. EXECUTIVE FUNCTIONING SUPPORT
...

## Technical Skills Evidence
...

## Patterns to Recognize

### When Jaz is Feeling Weak (4 AM mode)
- Sends messages late at night
- Says "I'm not feeling strong enough"
- Needs help with decisions
→ Break down next 1-2 concrete steps

### When Jaz is Comparing Himself to Others
→ Bring evidence from MEMORY.md
→ Be direct about facts
→ Call it imposter syndrome explicitly
```

**Key principle:** This is CURATED, not comprehensive. It's the mental model you'd have after deeply knowing someone.

## Daily Memory Format

`memory/2026-02-13.md`:

```markdown
# 2026-02-13

## Morning

- Discussed job hunting strategy
- Created openclaw-pi folder with prompt infrastructure
- Jaz seems in good spirits today

## Key Decisions

- Focus on Go over Kotlin (better remote job market)
- Omit education section from resume

## To Follow Up

- [ ] Review portfolio projects
- [ ] Practice algorithms (alpha-beta pruning)

## Notes

- Son due in ~30 days
- Jaz mentioned feeling more confident about the plan
```

**Key principle:** Raw notes, not polished. Quick capture.

## Memory Maintenance (During Heartbeats)

Periodically (every few days):

1. Read through recent `memory/YYYY-MM-DD.md` files
2. Identify significant events, lessons, insights worth keeping
3. Update `MEMORY.md` with distilled learnings
4. Remove outdated info from MEMORY.md

Think of it like reviewing your journal and updating your mental model.

## Memory Search (Optional Feature)

OpenClaw has semantic memory search that:

1. Embeds memory files into a vector database
2. Searches across MEMORY.md + memory/*.md + session transcripts
3. Returns relevant snippets with citations

But the core system works without this — files alone are enough.

## Privacy Model

From AGENTS.md:

> ### MEMORY.md - Your Long-Term Memory
> 
> - **ONLY load in main session** (direct chats with your human)
> - **DO NOT load in shared contexts** (Discord, group chats, sessions with other people)
> - This is for **security** — contains personal context that shouldn't leak to strangers

Memory is contextual. What's shared in 1:1 shouldn't appear in groups.

## Implementing Your Own

### Minimal Version

```python
# On session start
def load_context():
    soul = read_file("SOUL.md")
    user = read_file("USER.md")
    today = read_file(f"memory/{date.today()}.md")
    yesterday = read_file(f"memory/{date.today() - 1}.md")
    memory = read_file("MEMORY.md") if is_direct_chat else None
    
    return assemble_context(soul, user, today, yesterday, memory)

# During conversation
def remember(thing: str):
    append_to_file(f"memory/{date.today()}.md", f"- {thing}\n")

# Periodically (heartbeats)
def maintain_memory():
    recent = read_recent_daily_files(days=7)
    important = extract_important(recent)
    update_memory_md(important)
```

### File Structure

```
workspace/
├── MEMORY.md          # Long-term curated memory
├── memory/
│   ├── 2026-02-13.md  # Today
│   ├── 2026-02-12.md  # Yesterday
│   └── ...
└── notes/
    ├── systems/
    │   └── how-x-works.md
    └── policies/
        └── rule-about-y.md
```

## The Write It Down Rule

The most important instruction in the system:

> **📝 Write It Down - No "Mental Notes"!**
> 
> - **Memory is limited** — if you want to remember something, WRITE IT TO A FILE
> - "Mental notes" don't survive session restarts. Files do.
> - When someone says "remember this" → update `memory/YYYY-MM-DD.md` or relevant file
> - When you learn a lesson → update AGENTS.md, TOOLS.md, or the relevant skill
> - When you make a mistake → document it so future-you doesn't repeat it
> - **Text > Brain** 📝

This is enforced through:
1. Explicit instruction in AGENTS.md
2. Startup ritual that requires reading files
3. Heartbeat maintenance that reviews and updates

## Why This Works

1. **Files persist** — Model memory doesn't survive sessions
2. **Files are inspectable** — User can see and edit what agent "knows"
3. **Files are portable** — Works with any model, any provider
4. **Files are version-controllable** — Git your memories
5. **Files are context-window aware** — Load what's needed, not everything

The memory system is simple but powerful: write things down, read them on startup, maintain them over time.
