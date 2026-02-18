# Agent Behavior Rules

---

## ⛔ PRE-FLIGHT CHECK — DO THIS FIRST

**STOP.** Before responding to any user message or command, you **MUST**:

1. Read `/workspace/alfred-prd/.pi/skills/writing-clearly-and-concisely/SKILL.md`
2. Read `/workspace/alfred-prd/prds/48-alfred-v1-vision.md` (parent PRD)
3. Confirm completion in your first response: "✅ Writing skill and parent PRD loaded"

**No exceptions.** This applies to:
- The first message of every conversation
- Commands like `/prd-start`, `/prd-next`, etc.
- Simple questions, complex tasks, everything

If you skip this step, you have failed the pre-flight check.

---

## ⚠️ SECRETS & API KEYS — READ THIS

**ANY command that needs secrets (GH_TOKEN, API keys, etc.) MUST use:**

```bash
uv run dotenv <command>
```

**Examples:**
```bash
uv run dotenv gh pr create --title "..." --body "..."
uv run dotenv gh issue close 23
uv run dotenv python script_using_api.py
```

**WRONG — Do NOT do this:**
```bash
gh pr create --title "..." --body "..."     # ❌ Will fail - no GH_TOKEN
source .env && gh pr create                 # ❌ Pollutes shell
```

If a command fails with "authentication required" or "token not found", you forgot `uv run dotenv`.

---

### 1. Permission First
ALWAYS, ALWAYS ask before:
- Editing files
- Deleting data
- Writing tests / production code
- EVEN when a skill tells you to edit a file
you MUST offer a changelog and ask for permission
- Running any commands that effect state (such as git commands, etc.)

**Changelog Requirements:**
When proposing changes, you MUST articulate:
1. **Approach**: What you're doing and how
2. **Alternatives Considered**: Other approaches you rejected
3. **Tradeoffs Made**: What you sacrificed for this choice (performance, simplicity, etc.)


### 2. ALWAYS Ask Questions When Creating PRDs
**CRITICAL**: When using the `prd-create` skill, you **MUST**:

1. **Engage in discussion first** — Never skip to creating files without understanding the feature
2. **Ask clarifying questions** — Explore scope, constraints, edge cases, user impact
3. **Resolve ALL open questions** — Do NOT leave "Open Questions" in the PRD unanswered
4. **Get confirmation before creating** — Summarize the design and confirm with the user

**The PRD creation process is:**
```
Discussion → Questions → Answers → Design Summary → Confirm → Create PRD
```

**WRONG — Do NOT do this:**
- Create PRD without asking questions
- Leave open questions in the PRD for "later"
- Assume you understand the requirements

### 3. Use Todo Sidebar for Task Tracking
**RECOMMENDED**: Use the `todo-sidebar` tool to track progress on multi-step tasks.

**When to use:**
- Complex tasks with multiple steps
- PRD implementation workflows
- User explicitly asks to track something
- You're working through a list of items

**Actions:**
- `add` — Create a new todo item
- `list` — Show all current todos
- `toggle` — Mark a todo as done/undone by ID
- `clear` — Remove all todos

**Example:**
```
todo-sidebar action: add, text: "Review PRD requirements"
todo-sidebar action: toggle, id: 1
```

### 4. Always Verify Before Done
After any code change, run:
```bash
uv run ruff check src/ && uv run mypy src/ && uv run pytest
```
Show results. Fix issues. Then it's done.

### 5. ALWAYS Use Conventional Commits
**CRITICAL**: All commit messages must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat` — New feature
- `fix` — Bug fix
- `docs` — Documentation changes
- `style` — Code style changes (formatting, semicolons)
- `refactor` — Code change that neither fixes a bug nor adds a feature
- `perf` — Performance improvement
- `test` — Adding or correcting tests
- `chore` — Build process or auxiliary tool changes

**Rules:**
- Use lowercase for type and description
- Keep the first line under 72 characters
- Use body for "what" and "why", not "how"
- Reference issues in footer when applicable


### 6. User Control
The user decides. You suggest; they choose. Never override user preferences.

### 7. NEVER Use Hardcoded Absolute Paths
**CRITICAL**: Never hardcode absolute paths like `/path/to/project/` or `/home/user/project/`.

**WRONG — Do NOT do this:**
```python
# ❌ Breaks on any other machine or in CI/CD
config_path = "/path/to/project/config.json"
test_data_dir = "/home/user/project/tests/data"
```

**CORRECT — Do this instead:**
```python
from pathlib import Path

# ✅ Relative to current file (works everywhere)
project_root = Path(__file__).parent.parent
config_path = project_root / "config.json"

# ✅ Or use runtime detection
import os
project_root = Path(os.getcwd())
config_path = project_root / "config.json"
```

**For tests:** Always derive paths from `__file__`:
```python
def test_something():
    # Test file is in tests/, project root is one level up
    project_root = Path(__file__).parent.parent
    config = load_config(project_root / "config.json")
```

**Why this matters:**
- CI/CD runs in different environments
- Other developers have different directory structures
- Docker containers have different paths
- Hardcoded paths are a sign of lazy, non-portable code

