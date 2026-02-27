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

## 🚀 Running the Project

```bash
# Interactive TUI (default)
uv run alfred

# With debug logging
uv run alfred --debug info
uv run alfred --debug debug

# Telegram bot mode
uv run alfred --telegram

# Cron job management
uv run alfred cron list
uv run alfred cron add "daily standup" "every day at 9am"
uv run alfred cron remove <job_id>
```

**Entry point:** `src/cli/main.py` (Typer CLI)

---
### 0. Use tmux 
- Usr tmux whenever something requires
interactive control. Especially whenever 
you think something reques manual testing. 
### 0. git add -p 
- ALWAYS create atomic commits using git add -p
### 1. Permission First


- Emit changeloafter commits
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

### 4. Test-Driven Development (TDD) — MANDATORY
**ALWAYS** follow TDD principles when writing code:

1. **Write tests first** — Before any implementation
2. **Run tests to see them fail** — Confirms test validity
3. **Implement minimum code to pass** — No over-engineering
4. **Refactor** — Clean up while tests protect you

**WRONG — Do NOT do this:**
- Write code first, then add tests
- Skip tests because "it's a simple change"
- Test only happy paths

**RIGHT — Always do this:**
- Red → Green → Refactor cycle
- Test edge cases alongside implementation
- Justify if TDD isn't applicable (rare)

### 5. Testing Edge Cases — MANDATORY
**ALWAYS** test edge cases, not just happy paths. **DO NOT MOCK** unless you have no other choice.

- **Input validation**: null, empty strings, wrong types, malformed data
- **Boundary conditions**: off-by-one, empty collections, max/min values, integer overflow
- **Error handling**: network failures, timeouts, missing files, permission denied
- **Async edge cases**: race conditions, concurrent access, timeout handling

**Mocking is a last resort.** Prefer:
- Real file systems (use temp directories)
- Real network calls (use test servers/containers)
- Real databases (use test instances)

**Only mock when:**
- External services you cannot control
- Non-deterministic behavior (time, randomness)
- Extremely slow operations

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

### 12. Use tmux-tape for CLI/TUI Testing
**USE** the tmux-tape skill for E2E testing of interactive or visual CLI applications:

- **Asyncio apps** — Alfred, bots, servers (can't use VHS)
- **TUI frameworks** — Textual, Rich Live, ncurses apps
- **Visual verification** — Box-drawing, colors, layout

**Not needed for:** simple scripts, unit tests, `--help` output.

**Workflow:**
```bash
mkdir -p /tmp/pi-tmux && cp .pi/skills/tmux-tape/tmux_tool.py /tmp/pi-tmux/
cd /tmp/pi-tmux && uv run python script.py
```

**Example:**
```python
from tmux_tool import TerminalSession

with TerminalSession("alfred", port=7681) as s:
    s.send("alfred")
    s.send_key("Enter")
    s.sleep(3)  # Wait for startup

    result = s.capture("startup.png")
    assert "Alfred ready" in result["text"]
```

See `.pi/skills/tmux-tape/SKILL.md` for full API.

### 13. Create Granular Execution Plans
When implementing a feature or PRD phase, create an **extremely granular** checklist first.

**Principles:**
- Each item = single atomic action
- Each item = independently verifiable
- Items ordered by dependency
- Include test items after implementation items
- Include manual verification items

**Granularity levels:**

| Too Coarse | Good | Excellent |
|------------|------|-----------|
| "Add throbber" | "Create Throbber class" | "Create file `src/interfaces/pypitui/throbber.py`" |
| "Wire into TUI" | "Add throbber to status line" | "Add `self._throbber = Throbber()` in `__init__`" |
| "Test it works" | "Test throbber animation" | "Test: `test_throbber_tick_advances()`" |

**Template for each implementation item:**
```
- [ ] Create/modify <file>
- [ ] Add <specific code change>
- [ ] Test: `test_<what>()` — verify <behavior>
- [ ] Run: `uv run pytest <file>` — fix failures
```

**Example execution plan structure:**
```markdown
## Phase A: Feature Name

### A.1 Create Core Class
- [ ] Create file `src/path/to/module.py`
- [ ] Add import: `from typing import Literal`
- [ ] Define constant: `MAX_ITEMS = 5`
- [ ] Create class `Thing` with `__init__(self, name: str)`
- [ ] Add `self._name = name`
- [ ] Implement `do_thing(self) -> str`
- [ ] Run: `uv run ruff check src/path/to/`

### A.2 Test Core Class
- [ ] Create file `tests/test_thing.py`
- [ ] Test: `test_thing_init()` — verify name stored
- [ ] Test: `test_do_thing_returns_string()` — verify return type
- [ ] Run: `uv run pytest tests/test_thing.py -v`
- [ ] Fix any failures

### A.3 Integrate with Existing Code
- [ ] Open `src/existing/module.py`
- [ ] Add import at top: `from src.path.to.module import Thing`
- [ ] Add `self._thing = Thing("name")` in `__init__`
- [ ] Call `self._thing.do_thing()` in relevant method
- [ ] Run: `uv run pytest tests/`

### A.4 Manual Verification
- [ ] Start app in tmux: `tmux new-session -d -s test "uv run alfred"`
- [ ] Wait for startup: `sleep 2`
- [ ] Trigger feature: `tmux send-keys -t test "hello" Enter`
- [ ] Wait for response: `sleep 3`
- [ ] Capture output: `tmux capture-pane -t test -p`
- [ ] Verify expected behavior in output
- [ ] Kill session: `tmux kill-session -t test`

### A.5 Commit
- [ ] Run: `uv run ruff check src/ && uv run mypy src/ && uv run pytest`
- [ ] Stage: `git add src/path/to/module.py tests/test_thing.py`
- [ ] Commit: `feat(module): add Thing class with do_thing method`
```

**When to create:**
- Before implementing any PRD phase
- Before any feature spanning 3+ files
- When user asks for "detailed plan" or "todo list"

**Store in:** `prds/execution-plan-<feature>.md`
