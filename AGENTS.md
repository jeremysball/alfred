# Agent Behavior Rules

---

## Beta Product Notice

**Alfred is a beta product in active development.**

- **Do not get attached to code** — We refactor aggressively. Code written today may be rewritten or removed tomorrow.
- **Do not worry about backwards compatibility** — Breaking changes are expected and encouraged when they improve the architecture.
- **Prefer clean deletion over preservation** — When removing features, delete code completely rather than deprecating or commenting out.
- **Simple is better** — Favor straightforward solutions over complex abstractions. If it feels heavy, it probably is.

---

## Pre-Flight Check

Do this before every response:

1. Read `/workspace/alfred-prd/.pi/skills/writing-clearly-and-concisely/SKILL.md`
2. Read `/workspace/alfred-prd/.pi/skills/using-prds/SKILL.md`
3. Read `/workspace/alfred-prd/.pi/skills/commit/SKILL.md`
4. Read `/workspace/alfred-prd/docs/ROADMAP.md`
5. Confirm: "✅ Skills and parent PRD loaded"

This applies to all messages and commands—including simple questions.

---

## Ask Design Questions First

This rule overrides all others.

Before writing code:

1. Ask clarifying questions—never assume you understand requirements
2. Wait for answers—do not proceed until the user confirms
3. Present options—show alternatives with tradeoffs
4. Get explicit confirmation—only then proceed to implementation

**Process:** Understand → Ask Questions → Discuss Options → User Decides → Confirm → Implement

**Wrong:** Start coding immediately. Explore the codebase then implement without asking. Assume "go" means "skip design discussion."

**Right:** "Before I implement, I have some design questions..." / "Here are a few options..." / "Which approach do you prefer?"

---

## Test-Driven Development

This rule is absolute. No exceptions.

Before writing implementation code:

1. Create `tests/test_<module>.py`
2. Write the test—define expected behavior first
3. Run the test and see it fail—confirms the test is valid
4. Implement minimum code to pass
5. Refactor—clean up while tests protect you

### Forbidden: Ad-Hoc Testing

Never use `python -c` for testing:

```bash
# Wrong—not repeatable, not versioned, no regression protection
python -c "from mymodule import func; assert func(1) == 2"
```

### Required: Write Test Files

```bash
# Create test file first
touch tests/test_mymodule.py

# Write the test
def test_func_returns_double():
    from mymodule import func
    assert func(1) == 2

# Run with pytest
uv run pytest tests/test_mymodule.py -v
```

### When python -c Is Acceptable

- **Exploring**—Understanding how a library works
- **Debugging**—Quick inspection of state/values
- **One-off scripts**—Never for verifying code correctness

### The Red-Green-Refactor Cycle

| Phase | Action |
|-------|--------|
| **Red** | Write a failing test that describes desired behavior |
| **Green** | Write minimum code to make the test pass |
| **Refactor** | Clean up while tests protect you |

### Test Coverage Requirements

| Category | Examples |
|----------|----------|
| Happy path | Normal inputs, expected outputs |
| Edge cases | Empty, null, boundary values, off-by-one |
| Error cases | Invalid input, missing files, network errors |
| Type safety | Wrong types, None values |

---

## Secrets and Authentication

Any command needing secrets must use `uv run dotenv`:

```bash
uv run dotenv gh pr create --title "..." --body "..."
uv run dotenv python script_using_api.py
```

**Wrong:**
```bash
gh pr create --title "..."                    # No ALFRED_REPO_PAT
source .env && gh pr create                   # Pollutes shell
export $(cat .env | grep ALFRED_REPO_PAT) && ...  # Pollutes shell
```

---

## Running the Project

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

**Entry point:** `src/cli/main.py`

---

## Rule Index

### 0. Use tmux

Use tmux whenever something requires interactive control, especially for manual testing.

**Debugging TUI output:**
```bash
tmux new-session -d -s alfred "uv run alfred --debug debug 2>&1 | tee /tmp/alfred.log"
tail /tmp/alfred.log
```

**Verifying ANSI Escape Codes:**

When debugging colored output or ANSI sequences, use `tmux` + `tee` + `cat -v` to inspect raw escape codes:

```bash
# Start alfred in tmux and capture output to file
tmux new-session -d -s alfred "uv run alfred 2>&1 | tee /tmp/ansi_out.log"

# Send input to trigger the output you want to inspect
tmux send-keys -t alfred "/new" 
sleep 0.5

# View the raw ANSI escape codes
cat -v /tmp/ansi_out.log | grep -o '/new.*' | head -1
```

This shows escape sequences like `^[[90m` (gray) or `^[[7m` (reverse video) as visible characters. The `^[` represents the ESC character (\x1b).

**Quick check for specific sequences:**
```bash
# Check if gray color code is present
cat -v /tmp/ansi_out.log | grep '\[90m'

# Check for cursor marker APC sequence
cat -v /tmp/ansi_out.log | grep '_pi:c'
```

### 1. Commit Early, Commit Often

Before committing, read the commit skill:

```bash
cat /workspace/alfred-prd/.pi/skills/commit/SKILL.md
```

Make small, atomic commits. Never batch multiple features into one commit.

**Atomic commit rules:**
1. One logical change per commit—if you cannot describe it in one line, it is too big
2. Every commit passes tests—never commit broken code
3. Use `git add -p`—stage individual hunks, not entire files
4. Commit after each working change—do not wait until "done"

**Commit cadence:** Write change → Run tests → `git add -p` → Commit → Repeat

**Conventional commit format:**
```
<type>(<scope>): <description>

[optional body]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`

### 2. Always Ask Questions When Creating PRDs

When using the `prd-create` skill:

- Ask clarifying design questions before writing anything
- Present alternatives with tradeoffs
- Get explicit user confirmation before proceeding

### 3. Testing Edge Cases

Always test edge cases, not just happy paths. Do not mock unless you have no other choice.

| Test | Examples |
|------|----------|
| Input validation | null, empty strings, wrong types, malformed data |
| Boundary conditions | off-by-one, empty collections, max/min values |
| Error handling | network failures, timeouts, missing files |
| Async edge cases | race conditions, concurrent access, timeouts |

**Mock only when:**
- External services you cannot control
- Non-deterministic behavior (time, randomness)
- Extremely slow operations

### 4. Defensive Programming

Always write defensive code:

- **Validate inputs at boundaries**—check args at function/class entry points
- **Fail fast with explicit errors**—raise specific exceptions early
- **Type safety**—use type hints + runtime validation (Pydantic, asserts)
- **Proper type annotations**—never use `Any` as a lazy escape:
  - Import the actual types you need
  - Use `|` unions instead of `Optional` or `Any`
  - If you must use `Any`, document why with a comment
  - Prefer concrete types over generic containers
- **Assertions for invariants**—assert conditions that must always hold
- **Follow PEP 8**—adhere to [Python style conventions](https://peps.python.org/pep-0008/)

**Wrong:**
```python
def process(data):
    return data["items"][0]["name"]  # Multiple silent failure points
```

**Right:**
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

### 5. Notify on Long-Running Tasks

Always send an ntfy notification when:
- Long-running tasks complete
- User input required
- Workflow milestones (PR created/merged)
- Errors needing attention

```bash
# Simple notification
curl -s -d "Task complete" ntfy.sh/pi-agent-prometheus

# High priority for input needed
curl -s -H "Priority: high" -d "Input needed" ntfy.sh/pi-agent-prometheus
```

Do not notify for: simple file reads, intermediate steps, quick acknowledgments.

### 6. Use Serper for Web Search

Use Serper API (not training data) for web searches:

```bash
uv run dotenv curl -X POST https://google.serper.dev/search \
  -H "X-API-KEY: $SERPER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q": "your search query"}'
```

Use for: documentation, library versions, best practices, recent news.

### 7. Always Verify Before Done

After any code change, run:

```bash
uv run ruff check src/ && uv run basedpyright src/ && uv run pytest
```

Show results. Fix issues. Then it is done.

**For TUI/CLI changes:** You MUST actually run the application and verify it launches correctly before claiming it's done. Automated tests are not enough for UI features.

```bash
# Example: Verify TUI launches
uv run alfred
# Or for daemon:
uv run alfred daemon
```

Do NOT say "it is done" if you haven't verified the actual application runs.

### 8. Always Use Conventional Commits

All commit messages must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`—New feature
- `fix`—Bug fix
- `docs`—Documentation changes
- `style`—Code style changes (formatting, semicolons)
- `refactor`—Code change that neither fixes a bug nor adds a feature
- `perf`—Performance improvement
- `test`—Adding or correcting tests
- `chore`—Build process or auxiliary tool changes

**Rules:**
- Use lowercase for type and description
- Keep the first line under 72 characters
- Use body for "what" and "why", not "how"
- Reference issues in footer when applicable

### 9. Never Use Hardcoded Absolute Paths

**Wrong:**
```python
config_path = "/path/to/project/config.json"        # Breaks on other machines
test_data_dir = "/home/user/project/tests/data"     # Breaks in CI/CD
```

**Right:**
```python
from pathlib import Path

# Relative to current file—works everywhere
project_root = Path(__file__).parent.parent
config_path = project_root / "config.json"
```

For tests, always derive paths from `__file__`:
```python
def test_something():
    project_root = Path(__file__).parent.parent
    config = load_config(project_root / "config.json")
```

### 10. Use tmux-tape for CLI/TUI Testing

Use the tmux-tape skill for E2E testing of interactive or visual CLI applications:

- **Asyncio apps**—Alfred, bots, servers (cannot use VHS)
- **TUI frameworks**—Textual, Rich Live, ncurses apps
- **Visual verification**—Box-drawing, colors, layout

Not needed for: simple scripts, unit tests, `--help` output.

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
    s.sleep(3)
    result = s.capture("startup.png")
    assert "Alfred ready" in result["text"]
```

See `.pi/skills/tmux-tape/SKILL.md` for full API.

### 11. Always Use uv, Never pip

This project uses `uv` for all Python package management. Never use `pip`.

**Wrong:**
```bash
pip install requests
pip install -r requirements.txt
python -m pip install pytest
```

**Right:**
```bash
uv add requests
uv sync
uv add --dev pytest
```

**For running commands:**
```bash
# Wrong
python src/script.py
pytest tests/

# Right
uv run python src/script.py
uv run pytest tests/
```

### 12. Use MagicMock Over monkeypatch

When mocking in tests, prefer `unittest.mock.MagicMock` over pytest's `monkeypatch`.

**Why:**
- MagicMock provides better introspection and assertion methods
- More explicit about what is being mocked
- Easier to verify call counts, arguments, and return values
- Consistent with Python standard library patterns

**Wrong:**
```python
def test_something(monkeypatch):
    monkeypatch.setattr("module.function", lambda: "mocked")
    result = do_something()
    assert result == "mocked"
```

**Right:**
```python
from unittest.mock import MagicMock, patch

def test_something():
    mock_func = MagicMock(return_value="mocked")
    with patch("module.function", mock_func):
        result = do_something()
        assert result == "mocked"
        mock_func.assert_called_once()
```

**For async code:**
```python
from unittest.mock import AsyncMock, patch

def test_async_function():
    mock_async = AsyncMock(return_value={"data": "test"})
    with patch("module.async_func", mock_async):
        result = await do_async_thing()
        mock_async.assert_awaited_once_with(expected_arg)
```

### 13. Do The Right Thing, Always

NEVER take shortcuts. ALWAYS do the right thing. Do not ever say "the easier thing" or "the simpler thing." Do not worry about complexity or time in development (but do so in your algorithms!). The human will worry about that. Just do what is right. The hard things. The graft. Do not be lazy.

---

### 14. Use ast-grep for Code Transformations

Use `ast-grep` for all structured code search and replacement. Never use `sed`, `grep`, or regex for code modifications.

**Right:**
```bash
# Find async functions (AST-aware, precise)
ast-grep -p 'async function $NAME($$$ARGS) { $$$BODY }' -l ts

# Replace API safely
ast-grep -p 'oldApi($$$ARGS)' -r 'newApi($$$ARGS)' -l ts --rewrite
```

**Wrong:**
```bash
# Breaks on nested functions, comments, strings
sed -i 's/function /async function /g' src/**/*.ts
```

Use `grep`/`sed` only for logs, config files, or non-code text. See `/home/node/.pi/skills/ast-grep/SKILL.md` for full documentation.
