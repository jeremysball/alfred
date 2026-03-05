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

### 11. Create Granular Execution Plans

When implementing a feature or PRD phase, create an extremely granular checklist first.

**Principles:**
- Each item = single atomic action
- Each item = independently verifiable
- Items ordered by dependency
- Include test items after implementation items
- Include manual verification items

**Granularity:**

| Too Coarse | Good | Excellent |
|------------|------|-----------|
| "Add throbber" | "Create Throbber class" | "Create file `src/interfaces/pypitui/throbber.py`" |
| "Wire into TUI" | "Add throbber to status line" | "Add `self._throbber = Throbber()` in `__init__`" |
| "Test it works" | "Test throbber animation" | "Test: `test_throbber_tick_advances()`" |

**Template:**
```
- [ ] Create/modify <file>
- [ ] Add <specific code change>
- [ ] Test: `test_<what>()`—verify <behavior>
- [ ] Run: `uv run pytest <file>`—fix failures
```

**Store in:** `prds/execution-plan-<feature>.md`
