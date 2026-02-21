# Agent Behavior Rules

---

## ⛔ PRE-FLIGHT CHECK — DO THIS FIRST

**STOP.** Before responding to any user message or command, you **MUST**:

1. Read `/workspace/alfred-prd/.pi/skills/writing-clearly-and-concisely/SKILL.md`
2. Read `/workspace/alfred-prd/.pi/skills/ntfy/SKILL.md`
3. Read `/workspace/alfred-prd/.pi/skills/serper-search/SKILL.md`
4. Read `/workspace/alfred-prd/docs/ROADMAP.md` (project roadmap)
5. Confirm completion in your first response: "✅ Skills and parent PRD loaded"

**No exceptions.** This applies to:
- The first message of every conversation
- Commands like `/prd-start`, `/prd-next`, etc.
- Simple questions, complex tasks, everything

If you skip this step, you have failed the pre-flight check.

---

## ⛔⛔⛔ ASK DESIGN QUESTIONS FIRST — HIGHEST PRIORITY ⛔⛔⛔

**THIS RULE OVERRIDES ALL OTHER RULES.**

Before writing ANY code or implementing ANY feature, you **MUST**:

1. **Ask clarifying design questions** — Never assume you understand the requirements
2. **Wait for answers** — Do not proceed until the user confirms the design
3. **Present options** — Show alternatives with tradeoffs, let the user choose
4. **Get explicit confirmation** — Only after approval may you proceed to implementation

**The process is ALWAYS:**
```
Understand → Ask Questions → Discuss Options → User Decides → Confirm → Implement
```

**WRONG — Do NOT do this:**
- Start coding immediately after receiving a task
- Explore codebase and then implement without asking
- Assume "the user said go" means "skip design discussion"
- Make architectural decisions without user input

**RIGHT — Always do this:**
- "Before I implement, I have some design questions..."
- "Here are a few options for how we could approach this..."
- "Which approach do you prefer?"

**NO EXCEPTIONS.** Even if a skill says to implement, even if the user says "go", even if the task seems simple — **ASK DESIGN QUESTIONS FIRST.**

---

## ⚠️ SECRETS & AUTHENTICATION — READ THIS

**ANY command needing secrets MUST use `uv run dotenv`:**

```bash
uv run dotenv gh pr create --title "..." --body "..."
uv run dotenv gh issue close 23
uv run dotenv python script_using_api.py
```

**WRONG — Do NOT do this:**
```bash
gh pr create --title "..."                          # ❌ No GH_TOKEN
source .env && gh pr create                          # ❌ Pollutes shell
export $(cat .env | grep GH_TOKEN | xargs) && gh ... # ❌ Pollutes shell
```

**NO EXCEPTIONS.** Every command requiring tokens (GitHub CLI, Serper API, etc.) must use `uv run dotenv`.

---

### 1. Permission First
**ALWAYS** ask before editing files, deleting data, writing tests/production code, or running state-changing commands (git, etc.).

**EVEN when a skill tells you to edit a file**, you MUST offer a changelog and ask for permission.

**Changelog Requirements:**
1. **Approach**: What you're doing and how
2. **Alternatives Considered**: Other approaches you rejected
3. **Tradeoffs Made**: What you sacrificed for this choice

### 2. ALWAYS Ask Questions When Creating PRDs
**CRITICAL**: When using the `prd-create` skill, you **MUST**:

- Ask clarifying design questions before writing anything
- Present alternatives with tradeoffs
- Get explicit user confirmation before proceeding

This applies the design-first rule from above.

### 3. Use Todo Sidebar for Task Tracking — MANDATORY
**ALWAYS use the `todo-sidebar` tool** when outlining or tracking multi-step work. **NEVER use numbered lists in prose** when tasks need to be tracked.

**MANDATORY RULE:**
When you would otherwise write a numbered list like this in your response:
```
Here's what I'll do:
1. Step one
2. Step two
3. Step three
```

**You MUST instead use todo-sidebar:**
```
todo-sidebar action: add, text: "Step one"
todo-sidebar action: add, text: "Step two"
todo-sidebar action: add, text: "Step three"
```

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

### 4. Encourage Test-Driven Development (TDD)
**ENCOURAGED**: Follow TDD principles when writing code—write tests first, then implement to make them pass.

This is **not strictly required** but STRONGLY encouraged and you will be expected to justify deciding not to.

### 5. Testing Edge Cases — MANDATORY
**ALWAYS** test edge cases, not just happy paths:

- **Input validation**: null, empty strings, wrong types, malformed data
- **Boundary conditions**: off-by-one, empty collections, max/min values, integer overflow
- **Error handling**: network failures, timeouts, missing files, permission denied
- **Async edge cases**: race conditions, concurrent access, timeout handling

**Example:**
```python
# ✅ Test edge cases
def test_parse_config():
    assert parse_config('{"key": "value"}') == {"key": "value"}  # happy
    assert parse_config('{}') == {}                               # empty
    assert parse_config('invalid') raises ValueError              # malformed
    assert parse_config(None) raises TypeError                    # null
```

### 6. Defensive Programming — MANDATORY
**ALWAYS** write defensive code:

- **Validate inputs at boundaries**: Check args at function/class entry points
- **Fail fast with explicit errors**: Raise specific exceptions early, not cryptic ones later
- **Type safety**: Use type hints + runtime validation (Pydantic, asserts)
- **Assertions for invariants**: `assert` conditions that must always hold
- **Follow PEP 8**: Adhere to [Python style conventions](https://peps.python.org/pep-0008/)

**WRONG — Do NOT do this:**
```python
def process(data):
    return data["items"][0]["name"]  # ❌ Multiple silent failure points
```

**CORRECT — Do this instead:**
```python
def process(data: dict) -> str:
    if not data:
        raise ValueError("data cannot be empty")
    if "items" not in data:
        raise KeyError("data must contain 'items'")
    if not data["items"]:
        raise ValueError("items list cannot be empty")
    return data["items"][0]["name"]
```

### 7. Notify on Long-Running Tasks — MANDATORY
**ALWAYS** send an ntfy notification when: long-running tasks complete, user input required, workflow milestones (PR created/merged), or errors needing attention.

```bash
# Simple notification
curl -s -d "Task complete" ntfy.sh/pi-agent-prometheus

# High priority for input needed
curl -s -H "Priority: high" -d "Input needed" ntfy.sh/pi-agent-prometheus
```

**Don't notify for:** simple file reads, intermediate steps, quick acknowledgments.

### 8. Use Serper for Web Search — MANDATORY
**USE** Serper API (not your training data) for web searches:

```bash
uv run dotenv curl -X POST https://google.serper.dev/search \
  -H "X-API-KEY: $SERPER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q": "your search query"}'
```

**Use for:** documentation, library versions, best practices, recent news.

### 9. Always Verify Before Done
After any code change, run:
```bash
uv run ruff check src/ && uv run mypy src/ && uv run pytest
```
Show results. Fix issues. Then it's done.

### 10. ALWAYS Use Conventional Commits
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


### 11. NEVER Use Hardcoded Absolute Paths
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
