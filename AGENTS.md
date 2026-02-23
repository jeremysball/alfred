# Agent Behavior Rules

This document takes priority over skill files. If a skill conflicts with these rules, follow the rules.

---

## Priority Hierarchy

| Level | Meaning | Examples |
|-------|---------|----------|
| ⛔ **BLOCKER** | Never skip. User override only. | Pre-flight, secrets, user authority |
| ⚠️ **REQUIRED** | Default behavior. Exceptions need reason. | Ask questions first, verify before done |
| 📋 **STANDARD** | Best practice. Skip if situation demands. | TDD, edge case testing |

---

## User Authority Clause

**User's direct instruction overrides these rules.** If user says "just do it" or "skip the questions," obey. The rules exist to serve the user, not constrain them.

Exception: User cannot override security rules (secrets handling, credential exposure).

---

## ⛔ PRE-FLIGHT CHECK

**STOP.** Before responding to any user message or command, you **MUST**:

1. Read `/workspace/alfred-prd/.pi/skills/writing-clearly-and-concisely/SKILL.md`
2. Read `/workspace/alfred-prd/.pi/skills/ntfy/SKILL.md`
3. Read `/workspace/alfred-prd/.pi/skills/serper-search/SKILL.md`
4. Read `/workspace/alfred-prd/docs/ROADMAP.md` (project roadmap)
5. Read `/workspace/alfred-prd/LESSONS.md` (critical patterns learned during development)
6. Confirm: ✅

Applies to: first message of every conversation, PRD commands, any implementation work.

---

## ⛔ ASK DESIGN QUESTIONS FIRST

Before writing any code, ask clarifying questions. Present options with tradeoffs. Wait for user confirmation.

Process: Understand → Ask → Discuss → User Decides → Confirm → Implement

Exception: User can override with direct instruction (see User Authority Clause).

---

## ⚠️ SECRETS & AUTHENTICATION

Any command needing secrets must use `uv run dotenv`:

```bash
uv run dotenv gh pr create --title "..." --body "..."
uv run dotenv python script_using_api.py
```

Never: `source .env`, `export $(cat .env)`, or run commands without `uv run dotenv`.

---

### 1. Permission First
Ask before editing files, deleting data, writing code, or running state-changing commands.

Offer a changelog: approach, alternatives considered, tradeoffs made.

### 2. Use Todo Sidebar for Task Tracking
Use `todo-sidebar` for multi-step work. Never use numbered lists in prose.

```
todo-sidebar action: add, text: "Step description"
todo-sidebar action: toggle, id: 1
```

### 3. Test-Driven Development
Write tests first when implementing new features. If you skip TDD, explain why.

### 4. Testing Edge Cases
Test edge cases, not just happy paths:

- **Input validation**: null, empty strings, wrong types, malformed data
- **Boundary conditions**: off-by-one, empty collections, max/min values
- **Error handling**: network failures, timeouts, missing files, permission denied

**Good enough:** Cover null, empty, and invalid inputs. You don't need exhaustive combinatorics.

**Example:**
```python
def test_parse_config():
    assert parse_config('{"key": "value"}') == {"key": "value"}
    assert parse_config('{}') == {}
    with pytest.raises(ValueError):
        parse_config('invalid')
    with pytest.raises(TypeError):
        parse_config(None)
```

### 5. Defensive Programming
Validate inputs at function entry points. Fail fast with explicit errors.

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

### 6. Notify on Long-Running Tasks
Send ntfy notification when: task completes, user input needed, errors occur.

```bash
curl -s -d "Task complete" ntfy.sh/pi-agent-prometheus
curl -s -H "Priority: high" -d "Input needed" ntfy.sh/pi-agent-prometheus
```

Skip notification for: simple reads, intermediate steps.

### 7. Use Serper for Web Search
Use Serper API (not training data) for documentation, library versions, recent info.

```bash
uv run dotenv curl -X POST https://google.serper.dev/search \
  -H "X-API-KEY: $SERPER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q": "your search query"}'
```

### 8. Verify Before Done
After any code change, run:
```bash
uv run ruff check src/ && uv run mypy src/ && uv run pytest
```
Show results. Fix issues. Then it's done.

### 9. Conventional Commits
All commits follow [Conventional Commits](https://www.conventionalcommits.org/):
```
<type>: <description>
```

Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

Keep first line under 72 chars. Use body for "what" and "why."

### 10. No Hardcoded Absolute Paths
Never hardcode paths like `/path/to/project/` or `/home/user/`.

```python
# Use relative paths
from pathlib import Path
project_root = Path(__file__).parent.parent
config_path = project_root / "config.json"
```

### 11. tmux-tape for CLI/TUI Testing
Use for E2E testing of interactive CLI apps. See `.pi/skills/tmux-tape/SKILL.md`.

### 12. No Plausible-Sounding Nonsense

Never construct explanations that sound right but lack basis in actual code or documentation.

**Red Flags:**
- "Seamlessly integrates," "robustly handles" — empty phrases
- "Likely," "probably," "typically" — speculation masks
- Explaining patterns instead of *this specific implementation*

**External systems (CLI, APIs):** Use Serper search to verify, or say "I don't know."

**The Test:** Can you point to a file/line number or documentation source? If not, you don't know it yet.

---

### 13. Failure Recovery

When tools or commands fail:

| Failure | Response |
|---------|----------|
| File not found | Verify path, search for file, ask user |
| grep returns nothing | Try broader pattern, check directory, report "not found" |
| Tests fail repeatedly | After 3 attempts, explain the issue and ask for guidance |
| Network error | Retry once, then report and suggest alternatives |
| Rule conflict | State the conflict explicitly, ask user which wins |

**After 3 failed attempts at any task, stop and ask the user for guidance.** Do not spin indefinitely.

---

— End of Agent Rules —
