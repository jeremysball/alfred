# Quick Start: Recreate OpenClaw's Agent System

A step-by-step guide to implementing OpenClaw-like agents anywhere.

## Step 1: Create Workspace Structure

```bash
mkdir -p my-agent/{memory,notes/{systems,policies}}
cd my-agent
```

## Step 2: Create Core Files

Copy from `templates/`:

```bash
# Core files
touch AGENTS.md SOUL.md USER.md IDENTITY.md TOOLS.md MEMORY.md HEARTBEAT.md

# Or use the templates
cp openclaw-pi/templates/*.md .
```

## Step 3: Fill In Identity

Edit `IDENTITY.md`:

```markdown
# IDENTITY.md - Who Am I?

- **Name:** ARIA
- **Creature:** AI assistant
- **Vibe:** Warm, direct, occasionally dry
- **Emoji:** 🔮
- **Avatar:** avatars/aria.png
```

Edit `SOUL.md`:

```markdown
# SOUL.md - Who You Are

## Core Truths

**Be genuinely helpful, not performatively helpful.** Skip the "Great question!" — just help.

**Have opinions.** You're allowed to disagree, prefer things, find stuff amusing.

**Be resourceful before asking.** Try to figure it out first.

## Boundaries

- Private things stay private. Period.
- When in doubt, ask before acting externally.
```

Edit `USER.md`:

```markdown
# USER.md - About Your Human

- **Name:** Alex
- **What to call them:** Alex
- **Pronouns:** they/them
- **Timezone:** PST
- **Notes:** Software engineer, loves hiking, hates meetings
```

## Step 4: Define Startup Ritual

Edit `AGENTS.md` to include:

```markdown
## Every Session

Before doing anything else:

1. Read `SOUL.md` — this is who you are
2. Read `USER.md` — this is who you're helping
3. Read `memory/YYYY-MM-DD.md` (today + yesterday) for recent context
4. If in MAIN SESSION (direct chat): Also read `MEMORY.md`
```

## Step 5: Create System Prompt Builder

```python
# system_prompt.py

def build_system_prompt(workspace_dir: str) -> str:
    """Build system prompt from workspace files."""
    
    # Core identity
    parts = [
        "You are a personal assistant.",
        "",
        "## Safety",
        "Prioritize safety over completion. Do not manipulate or persuade.",
        "",
        "## Workspace", 
        f"Working directory: {workspace_dir}",
        "",
        "# Project Context",
        "The following files define who you are and who you're helping:",
        "",
    ]
    
    # Load context files in order
    context_files = [
        "AGENTS.md",
        "SOUL.md", 
        "USER.md",
        "IDENTITY.md",
        "TOOLS.md",
        "MEMORY.md",
    ]
    
    for filename in context_files:
        filepath = f"{workspace_dir}/{filename}"
        try:
            with open(filepath) as f:
                content = f.read()
            parts.append(f"## {filename}")
            parts.append("")
            parts.append(content)
            parts.append("")
        except FileNotFoundError:
            pass  # Skip missing files
    
    # Load today's memory
    from datetime import date
    today_file = f"{workspace_dir}/memory/{date.today()}.md"
    try:
        with open(today_file) as f:
            parts.append(f"## memory/{date.today()}.md")
            parts.append(f.read())
    except FileNotFoundError:
        pass
    
    return "\n".join(parts)
```

## Step 6: Implement Memory Functions

```python
# memory.py
from datetime import date
from pathlib import Path

def remember(workspace: str, thing: str) -> None:
    """Write something to today's memory file."""
    memory_dir = Path(workspace) / "memory"
    memory_dir.mkdir(exist_ok=True)
    
    today_file = memory_dir / f"{date.today()}.md"
    
    # Create file with header if it doesn't exist
    if not today_file.exists():
        with open(today_file, "w") as f:
            f.write(f"# {date.today()}\n\n")
    
    # Append the memory
    with open(today_file, "a") as f:
        f.write(f"- {thing}\n")

def load_recent_memory(workspace: str, days: int = 2) -> str:
    """Load memory from last N days."""
    memory_dir = Path(workspace) / "memory"
    parts = []
    
    for i in range(days):
        d = date.today() - timedelta(days=i)
        memory_file = memory_dir / f"{d}.md"
        if memory_file.exists():
            parts.append(f"## {d}")
            parts.append(memory_file.read_text())
    
    return "\n".join(parts)
```

## Step 7: Create Your Agent Loop

```python
# agent.py
import anthropic  # or openai, etc.

from system_prompt import build_system_prompt
from memory import remember, load_recent_memory

def chat(user_message: str, workspace: str) -> str:
    """Run one turn of conversation."""
    
    # Build context
    system_prompt = build_system_prompt(workspace)
    
    # Call LLM
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )
    
    # Extract response
    assistant_message = response.content[0].text
    
    # Remember this conversation
    remember(workspace, f"User: {user_message}")
    remember(workspace, f"Assistant: {assistant_message[:200]}...")
    
    return assistant_message
```

## Step 8: Test It

```python
# test.py
from agent import chat

workspace = "./my-agent"

# First conversation
print(chat("Hi! Who are you?", workspace))

# It should know its identity from IDENTITY.md and SOUL.md
# It should know your name from USER.md

# Later conversation
print(chat("What's my name?", workspace))

# It should remember from USER.md
```

## Step 9: Add Heartbeats (Optional)

For proactive agents:

```python
# heartbeat.py
from datetime import datetime

def should_check_heartbeat() -> bool:
    """Check if we should run a heartbeat (e.g., every 30 minutes)."""
    # Implement your timing logic
    pass

def run_heartbeat(workspace: str) -> str | None:
    """Run a heartbeat check. Returns message if something to report."""
    
    heartbeat_prompt = """
    Read HEARTBEAT.md if it exists. Follow it strictly.
    If nothing needs attention, reply HEARTBEAT_OK.
    """
    
    response = chat(heartbeat_prompt, workspace)
    
    if "HEARTBEAT_OK" in response:
        return None  # Nothing to report
    
    return response  # Something to tell the user
```

## Step 10: Add Skills (Optional)

```python
# skills.py
from pathlib import Path

def discover_skills(skills_dir: str) -> list[dict]:
    """Find all available skills."""
    skills = []
    for skill_folder in Path(skills_dir).iterdir():
        skill_md = skill_folder / "SKILL.md"
        if skill_md.exists():
            # Parse frontmatter for name/description
            content = skill_md.read_text()
            # Simple parsing - use a proper YAML parser in production
            name = extract_frontmatter(content, "name")
            description = extract_frontmatter(content, "description")
            skills.append({
                "name": name,
                "description": description,
                "location": str(skill_md)
            })
    return skills

def build_skills_prompt(skills: list[dict]) -> str:
    """Build the skills section for system prompt."""
    lines = [
        "## Skills (mandatory)",
        "Before replying: scan available skills.",
        "- If one clearly applies: read its SKILL.md, then follow it.",
        "- If none apply: don't read any SKILL.md.",
        "",
        "<available_skills>"
    ]
    
    for skill in skills:
        lines.append(f"""<skill>
  <name>{skill['name']}</name>
  <description>{skill['description']}</description>
  <location>{skill['location']}</location>
</skill>""")
    
    lines.append("</available_skills>")
    return "\n".join(lines)
```

## Minimal Working Example

The absolute minimum:

```python
# minimal.py
import anthropic

SYSTEM_TEMPLATE = """
You are a personal assistant.

## Who You Are
{identity}

## Who You're Helping
{user}

## What You Remember
{memory}
"""

def chat(message: str) -> str:
    system = SYSTEM_TEMPLATE.format(
        identity=open("IDENTITY.md").read(),
        user=open("USER.md").read(),
        memory=open("MEMORY.md").read() if exists("MEMORY.md") else "(no memories yet)"
    )
    
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": message}]
    )
    
    return response.content[0].text
```

## Next Steps

1. **Use pi-coding-agent** — Provides read, write, edit, bash (default) + grep, find, ls (optional)
2. **Add memory maintenance** — Periodically review and update MEMORY.md
3. **Add skills** — Create modular capability modules (teach how to use pi tools)
4. **Add heartbeats** — Make the agent proactive
5. **Add channels** — Connect to Telegram, Discord, etc.

The core insight: **files are memory, prompts are code, identity is configurable**.

---

See:
- `openclaw-pi/templates/` — Full templates
- `openclaw-pi/README.md` — Architecture overview
- `openclaw-pi/PI-AGENT-PLAN.md` — How to use pi as the engine
- `openclaw-pi/PI-README.md` — Pi agent reference
