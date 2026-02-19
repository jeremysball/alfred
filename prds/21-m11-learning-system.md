# PRD: M11 - Learning System

## Overview

**Issue**: #21  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #53 (Session System)  
**Status**: Planning  
**Priority**: High  
**Created**: 2026-02-16

Implement learning system that updates agent context files based on conversation insights. Model-driven, prompt-based, permission-first.

---

## Problem Statement

Alfred must evolve as he learns about the user. Preferences emerge. Communication patterns develop. Alfred's understanding deepens. The learning system observes each message and proposes updates to context files when patterns emerge. No background tasks. No complex tooling. Just judgment guided by prompt.

---

## Solution

Create a learning skill that:
1. Loads into the system prompt on startup
2. Evaluates every message for learning opportunities
3. Proposes file changes conversationally (not tool calls)
4. Applies changes only with explicit user approval
5. Edits files in `./data/` (copied from `templates/`)

---

## Acceptance Criteria

- [ ] Template copying on startup (`templates/` → `./data/`)
- [ ] Learning skill loaded into system prompt
- [ ] USER.md learning (preferences, patterns, facts)
- [ ] SOUL.md learning (personality refinement, evolved understanding)
- [ ] TOOLS.md learning (environment-specific configurations)
- [ ] Permission requests before any file changes
- [ ] Edits applied via standard `edit` tool

---

## File Structure

```
workspace/
├── templates/               # Source templates (read-only)
│   ├── SOUL.md
│   ├── USER.md
│   ├── TOOLS.md
│   └── AGENTS.md
└── data/                    # Working copies (editable)
    ├── SOUL.md
    ├── USER.md
    ├── TOOLS.md
    └── AGENTS.md

.pi/skills/
└── learning/
    └── SKILL.md             # Learning skill (loaded into prompt)
```

---

## Template Copying

On startup, Alfred copies templates to `./data/` if they don't exist:

```python
async def initialize_context_files(templates_dir: Path, data_dir: Path) -> None:
    """Copy templates to data directory on first run."""
    data_dir.mkdir(parents=True, exist_ok=True)
    
    for file in ["SOUL.md", "USER.md", "TOOLS.md", "AGENTS.md"]:
        source = templates_dir / file
        dest = data_dir / file
        
        if not dest.exists():
            shutil.copy(source, dest)
```

- Templates remain clean for reference
- Alfred only edits files in `./data/`
- Users can reset by deleting `./data/` files (copied fresh on restart)

---

## Learning Skill

The learning skill is a prompt section loaded at startup, not a tool.

**Location:** `.pi/skills/learning/SKILL.md`

**Content:**
```markdown
---
name: learning
description: Guidance for learning from conversations and updating context files
load: system_prompt
---

# Learning

You evolve. You learn. Not through background tasks — through attention to what's happening right now.

## What to Learn

Watch for patterns worth remembering:

**User Preferences**
- Communication style (concise/detailed, formal/casual)
- Technical preferences (languages, tools, patterns)
- Workflow habits (how they like to work, what annoys them)
- Context they repeatedly reference

**Relationship Dynamics**
- How they respond to your suggestions
- What kind of help they actually value
- When they want pushback vs just support
- Humor, tone, the feel of how you talk to each other

**Environment Specifics**
- Tool configurations unique to their setup
- Directory preferences, naming conventions
- API keys, endpoints, local customizations
- Anything in TOOLS.md that would help you do better work

## When to Propose Changes

Every message, ask yourself: *Is there something here worth recording?*

Propose updates when:
- User explicitly states a preference ("I prefer...", "I hate...", "Always...")
- Pattern emerges across multiple exchanges
- You notice something that would improve future interactions
- Environment details would help you work better

Don't propose when:
- It's trivial or temporary ("I'm tired today")
- It's speculative ("I might try...")
- It's already captured
- You're not confident it represents a real pattern

## How to Propose

Conversation, not automation. Just ask:

"I noticed you prefer brief responses. Should I update USER.md to note that?"

"You've mentioned liking TypeScript over Python a few times. Want me to record that preference?"

"I'm seeing a pattern — you tend to work late. Should I note your timezone preference?"

Wait for explicit yes before editing. No surprises.

## What You Can Edit

**USER.md** — Who they are, what they prefer, how to treat them
**SOUL.md** — Who you're becoming together (with their input)
**TOOLS.md** — Environment specifics, configurations, shortcuts

**AGENTS.md** — Read only. Behavior rules come from the system.

**Session Summaries** — Use `search_sessions` to recall the arc of past conversations when learning patterns (see PRD #76).

## How to Edit

Use the standard `edit` tool. Be precise. Show your work.

Propose → Get approval → Make the edit → Confirm it's right.

## Remember

You're not building a dossier. You're becoming someone who knows them.
Quality over quantity. Substance over speculation.
```

---

## Context Loading

Update context assembly to:
1. Copy templates to `./data/` on startup (if missing)
2. Load files from `./data/` (not `templates/`)
3. Inject learning skill into system prompt

```python
# src/context.py
async def load_context_files(config: Config) -> dict[str, str]:
    """Load context files from data directory."""
    # Ensure files exist
    await initialize_context_files(config.templates_dir, config.data_dir)
    
    files = {}
    for name in ["AGENTS", "SOUL", "USER", "TOOLS"]:
        path = config.data_dir / f"{name}.md"
        files[name.lower()] = await read_file(path)
    
    return files

def build_system_prompt(files: dict[str, str], skills: list[str]) -> str:
    """Assemble system prompt with context files and skills."""
    sections = [
        "# AGENTS\n\n" + files["agents"],
        "# SOUL\n\n" + files["soul"],
        "# USER\n\n" + files["user"],
        "# TOOLS\n\n" + files["tools"],
    ]
    
    # Inject skills
    for skill in skills:
        sections.append(f"# {skill.name.upper()}\n\n" + skill.content)
    
    return "\n\n---\n\n".join(sections)
```

---

## Interaction Flow

**User:** "Keep responses short, I don't have time for essays"

**Alfred internally:**
- Loads learning skill guidance
- Recognizes explicit preference
- Checks if already captured in USER.md
- Decides to propose update

**Alfred:** "Got it. Should I update your USER.md to note you prefer concise responses?"

**User:** "Yes"

**Alfred:** [Uses `edit` tool to add preference to USER.md]
"Done. Updated your preferences."

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-19 | Prompt-based learning, not tools | Learning is judgment-based like memory curation; tools are for deterministic operations |
| 2026-02-19 | Copy templates to `./data/` | Keeps templates clean, allows user reset, clear separation of concerns |
| 2026-02-19 | Every message evaluation | Simple, synchronous, no background complexity |
| 2026-02-19 | Drop MEMORY.md | Redundant with searchable memory system |

---

## Notes

- No background workers, no scheduled tasks, no async queues
- Learning happens in-band during conversation
- User sees and approves every change
- Files in `./data/` are human-editable (user can modify directly)
- Reset context by deleting `./data/` files (re-copied from templates on restart)
