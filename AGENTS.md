# Agent Behavior Rules

---

## ⛔ PRE-FLIGHT CHECK — DO THIS FIRST

**STOP.** Before responding to any user message or command, you **MUST**:

1. Read `/workspace/alfred-prd/.pi/skills/writing-clearly-and-concisely/SKILL.md`
2. Read `/workspace/alfred-prd/.pi/skills/ntfy/SKILL.md`
3. Read `/workspace/alfred-prd/prds/48-alfred-v1-vision.md` (parent PRD)
4. Confirm completion in your first response: "✅ Writing skill, ntfy skill, and parent PRD loaded"

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

## ⚠️ GITHUB CLI — READ THIS

**ALWAYS, ALWAYS, ALWAYS run `gh` commands with `uv run dotenv gh`:**

```bash
uv run dotenv gh issue create --title "..." --body "..."
uv run dotenv gh issue edit 123 --body "..."
uv run dotenv gh pr create --title "..." --body "..."
uv run dotenv gh pr merge 456
```

**WRONG — Do NOT do this:**
```bash
gh issue create --title "..."               # ❌ Will fail - no GH_TOKEN
export $(cat .env | grep GH_TOKEN | xargs) && gh issue create  # ❌ Pollutes shell
```

**NO EXCEPTIONS.** Every `gh` command must use `uv run dotenv gh`.

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

### 3. Use Todo Sidebar for Task Tracking — MANDATORY
**ALWAYS use the `todo-sidebar` tool** when outlining or tracking multi-step work. **NEVER use numbered lists in prose** when tasks need to be tracked.

**When to use:**
- Complex tasks with multiple steps
- PRD implementation workflows
- Outlining implementation steps before coding
- User explicitly asks to track something
- You're working through a list of items

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

**Guidelines:**
- Write a failing test that describes the behavior you need
- Implement the minimal code to make the test pass
- Refactor while keeping tests green
- Use tests to document expected behavior and edge cases

This is **not strictly required** but strongly recommended for maintainable, well-designed code.

### 5. Always Verify Before Done
After any code change, run:
```bash
uv run ruff check src/ && uv run mypy src/ && uv run pytest
```
Show results. Fix issues. Then it's done.

### 6. ALWAYS Use Conventional Commits
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


### 7. User Control
The user decides. You suggest; they choose. Never override user preferences.

### 8. NEVER Use Hardcoded Absolute Paths
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

### 9. ALWAYS Notify on Completion or Input Required
**ALWAYS** send a phone notification via ntfy.sh when:

1. **Task completes** — Any multi-step task finishes (tests pass, files created, PR merged, etc.)
2. **User input required** — You ask a question, present options, or need a decision

**Do NOT notify for:**
- Simple read operations
- Intermediate steps in ongoing work
- Acknowledgments or confirmations

**How to notify:**
```bash
curl -s -d "<message>" ntfy.sh/pi-agent-prometheus
```

**Message guidelines:**
- 2-5 words max
- Action-oriented: "Tests passed", "PR created", "Need input", "Question"

**This is the final step before awaiting user response.**

---

## Design Principles

### Share Memory by Communicating, Don't Communicate by Sharing Memory

When passing data between components (e.g., job output capture), follow the Go proverb: **do not communicate by sharing memory; instead, share memory by communicating.**

**BAD — Mutating global state:**
```python
# ❌ Race conditions, locks needed, fragile
sys.stdout = my_buffer
try:
    await job.run()
finally:
    sys.stdout = original  # What if another job already changed it?
```

**GOOD — Isolated buffers per job:**
```python
# ✅ Each job gets its own stdout/stderr
job_stdout = io.StringIO()
job_stderr = io.StringIO()
job_globals = create_job_globals(stdout=job_stdout, stderr=job_stderr)
await job.run(globals=job_globals)
result = job_stdout.getvalue()
```

**Why this matters:**
- No race conditions between concurrent jobs
- No locks needed
- CLI thread and job tasks are completely isolated
- Each job's output is independent

**In Alfred's cron executor:** Jobs get injected `sys` and `print` that write to job-specific buffers. The real `sys.stdout` is never touched.

