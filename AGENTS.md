# Agent Behavior Rules

---

## Beta Product Notice

**Alfred is a beta product in active development.**

- **Do not get attached to code** — We refactor aggressively. Code written today may be rewritten or removed tomorrow.
- **Do not worry about backwards compatibility** — Breaking changes are expected and encouraged when they improve the architecture.
- **Prefer clean deletion over preservation** — When removing features, delete code completely rather than deprecating or commenting out.
- **Optimize for maintainability** — Favor small, readable changes and one clear source of truth over cleverness or convenience.
- **Simple is better** — Favor straightforward solutions over complex abstractions. If it feels heavy, it probably is.

---

## Pre-Flight Check

Do this once per conversation/session:

1. Read `/home/node/.pi/skills/skill-index/SKILL.md`.
2. Read `/workspace/alfred-prd/docs/ROADMAP.md`.
3. Confirm once: `✅ Skills and parent PRD loaded`

Do not automatically read `/home/node/.pi/skills/writing-clearly-and-concisely/SKILL.md`. Use normal judgment for prose unless the user explicitly asks for writing help or the change clearly needs that extra guidance.

Do not repeat these reads or the confirmation unless the session context has been reset.

---

## Operating Priorities

When rules compete, use this order:

1. **User intent and explicit confirmation**
2. **Maintainability and correctness**
3. **Tests and verifiable behavior**
4. **Clear, dense technical communication**
5. **Speed and convenience**

---

## Communication Standard

When reporting technical changes, default to this order:

- **changed** — file paths and the behavior or rule that changed
- **why** — the reason for the change
- **validation** — tests or checks that ran
- **risks** — follow-ups, caveats, or known gaps

Avoid filler. Prefer exact deltas over narrative.

---

## Core Rules

### Ask Design Questions First

This rule applies to **code changes and behavior changes**.

Before changing code:

1. Ask clarifying questions.
2. Present options and tradeoffs when multiple approaches are valid.
3. Get explicit confirmation before implementation.

For prose edits or clearly mechanical changes, state intent briefly and proceed.

### Use the Right Planning Tool

- **PRD work** — use the PRD workflow and `prd-exec` for execution planning.
- **Ad-hoc bug fixes or small follow-ups** — use the `todo` tool.
- Create one todo per distinct ad-hoc change and mark it complete when finished.

### Execution Plan Quality

For PRD execution plans:
- start from the public seam: define the observable behavior or success signal that proves the milestone works
- define the intra-PRD phase contract before changing code: observable behavior, current repo constraints, validation workflow, and the docs or prompts that must stay aligned
- name the current repo constraints and risks explicitly so the plan is grounded in today's globals, side effects, legacy hooks, and ordering assumptions
- split refactors by boundary so each task covers one seam such as HTML shell, bootstrap path, app runtime, storage boundary, API contract, or optional feature layer
- prefer observable behavior tests over internal implementation-shape checks unless the internal shape is itself the contract
- include at least one task that proves each claimed milestone outcome or PRD success criterion the plan says it will satisfy
- choose the validation workflow explicitly: Python, JavaScript, or both; do not leave mixed-surface work with only one side validated
- use the smallest meaningful validation for each task; broaden only when the change crosses boundaries or the failure mode is unclear
- when the abstract rules feel ambiguous, follow `docs/execution-plans/contract-first-examples.md`

### Execution Plan Review Gate

Before approving or executing a PRD execution plan, check:
1. the phases map cleanly to the PRD milestones or to an explicit sub-slice of one milestone
2. no catch-all smoke test combines unrelated surfaces when smaller boundary tests would isolate failures better
3. no test only asserts exports, import order, file counts, or filenames unless those are the actual contract
4. the listed validation matches the touched files under the dual workflow rule
5. docs and managed prompts are included when runtime behavior, user-visible behavior, or explanation changes

If a plan fails this review, revise the plan before implementation.

### Planning Guidance Sync

`AGENTS.md` contains repo-specific execution-plan rules. `prd-exec` contains the reusable planning workflow. `docs/execution-plans/contract-first-examples.md` contains the tracked examples for this repo.

When changing execution-plan guidance:
- update all three when the change affects how plans should be written and reviewed
- keep them aligned so one does not require behavior the others omit
- keep generic planning guidance in `prd-exec`, Alfred-specific enforcement in `AGENTS.md`, and concrete examples in the repo doc

### Prefer Deletion and Consolidation

When improving a system:
- delete duplication instead of preserving parallel versions
- keep one source of truth for each policy or behavior
- shorten instructions when the same rule is repeated
- move long examples into skills or docs when the main rule can stand on its own

### Update Docs and Managed Prompts With Feature Work

This rule applies to all feature and behavior changes.

- update the relevant documentation as part of the same work
- update managed prompts/templates when runtime behavior, memory behavior, or user-visible explanation changes
- do not treat docs or prompts as optional follow-up cleanup
- do not consider a feature complete until code, docs, and managed prompts agree

---

## Code Quality and Maintainability

### Default Standard

Favor code that is:
- easy to read
- easy to change
- easy to test
- hard to misuse

When implementing changes, prefer the **smallest code change** that produces the correct behavior the user intends. Do not over-engineer or expand scope beyond what is requested.

### Defensive Programming

- Validate inputs at boundaries.
- Fail fast with explicit errors.
- Use concrete types where possible.
- Do not use `Any` as a lazy escape hatch. If you must use it, justify it.
- Prefer simple data flow over clever indirection.

### Paths and File Access

Never hardcode machine-specific absolute paths in project code or tests.

Use `Path(__file__)`-relative paths or project-relative paths instead.

---

## Testing and Verification

### Test-First for Code Changes

For code changes:

1. Create or update the relevant test first.
2. Run the test and observe the failure when appropriate.
3. Implement the minimum change to pass.
4. Refactor while tests protect behavior.

Do not use `python -c` as a substitute for real tests. It is fine for exploration or debugging, not for verification.

### Test Behavior, Not Just Logic

For TUI, CLI, async lifecycle, and similar bug-prone surfaces, test through the public interface and full lifecycle.

If the bug is about hanging, freezing, cleanup, input handling, or event-loop behavior, the test must exercise real behavior rather than only internal state.

### TUI and CLI Testing Defaults

- Use `MockTerminal` for most TUI tests.
- Use real terminal or tmux-based testing only when you need ANSI, resize, layout, or visual verification.
- Use the tmux or tmux-tape skills when interactive automation is required.

### Prefer Explicit Fakes

For contract-shaped collaborators like Alfred, session managers, token trackers, and context loaders:

1. fake or stub
2. spy
3. `MagicMock` or `AsyncMock` at narrow edges
4. monkeypatch only when necessary

Do not use a bare root-level `MagicMock` where an explicit fake would better represent the real object graph.

### Cover Edge Cases

Always consider:
- input validation
- empty and boundary cases
- error handling
- async timing, concurrency, and timeout behavior

### Slow-Test Rule

Mark a test `@pytest.mark.slow` when it consistently lands at **3s+** in:

```bash
uv run pytest --durations=0 --durations-min=3
```

Keep the default `uv run pytest -m "not slow"` run fast.

### Verify Before Done

After code changes, run the smallest tests that cover the surfaces you touched.

- Prefer targeted unit, integration, browser, CLI, or TUI tests that exercise the changed path directly.
- Be liberal in adding adjacent surface tests when they improve confidence.
- Do **not** default to the full `uv run pytest -m "not slow"` sweep or the entire test suite.
- Broaden only when the change crosses boundaries, the failure mode is unclear, or you need release-style coverage.

When code changes require static checks, run the relevant one for the touched language:

- Python: `uv run ruff check src/ && uv run mypy --strict src/`
- JavaScript: `npm run js:check`

If Ruff can fix issues automatically, run:

```bash
uv run ruff check src/ tests/ --fix
```

Then re-run the relevant checks and the targeted tests for the touched surface.

Run the full `uv run pytest` sweep only when you need slow coverage or final release-style verification.

For Web UI changes:
- use Playwright for browser-level verification
- do not stop at unit tests if browser behavior could regress

For TUI or CLI changes:
- actually launch the application before claiming it is done

Docs-only changes do not need code validation unless behavior changed.

### Dual Workflow Rule

The repository has two independent quality workflows. **Choose one per commit** based on what you changed:

| Workflow | Files | Validation Command |
|----------|-------|-------------------|
| **Python** | `src/**/*.py`, `tests/**/*.py` | `uv run ruff check src/ && uv run mypy --strict src/ && uv run pytest <targeted tests for touched surfaces>` |
| **JavaScript** | `src/alfred/interfaces/webui/static/js/**/*.js` | `npm run js:check` |

**Note:** For pytest, prefer targeted tests that cover the touched surface. Use the full suite only when the change is broad or you need release-style verification.

**Rules:**
1. Python-only changes → Run Python workflow only
2. JavaScript-only changes → Run JavaScript workflow only  
3. Both changed → Run both workflows
4. Never run both workflows "just to be safe"

**JavaScript setup (first time):**
```bash
npm install
npm run js:check      # Validate lint + format
npm run js:check:fix  # Auto-fix issues
```

**Knip (dead code detection):**
```bash
npm run js:deadcode   # Informational only — does not block CI
```

---

## Tooling Rules

### Use ESM for All JavaScript

All JavaScript code must use ES Modules (ESM) syntax exclusively:
- Use `import` / `export` instead of `require` / `module.exports`
- Browser-facing code in `src/alfred/interfaces/webui/static/js/` must be native ESM
- Node.js JavaScript utilities should use `.mjs` extension or `"type": "module"` in package.json
- Never mix CommonJS and ESM in the same module graph

See PRD #164 for the full migration rationale and implementation details.

### Use `uv`, Never `pip`

Use `uv` for package management and command execution.

- `uv add ...`
- `uv sync`
- `uv run ...`

Do not use `pip install`, `python -m pip`, or bare `pytest` / `python` commands when `uv` should be used.

### Use tmux for Interactive Work

Use tmux whenever something needs interactive control, manual TUI inspection, or long-running session management.

### Use ast-grep for Structured Code Transformations

Use `ast-grep` for code search and replacement when structure matters.

Do not use `sed`, regex replacement, or plain grep-based rewriting for code modifications.

`grep` and `sed` are still fine for logs, config files, and non-code text.

### Use Playwright for Web UI Work

Use Playwright for development, debugging, and verification of browser behavior.

### Viewing User Screenshots from Image Hosting Services

Users often share screenshots via indirect links (gallery pages) rather than direct image URLs. To view these images:

**postimg.cc links:**
1. The user-provided URL (e.g., `https://postimg.cc/qNkrWMV3`) is an HTML page, not the image
2. Fetch the HTML page and extract the direct image URL:
   ```bash
   curl -s "https://postimg.cc/qNkrWMV3" | grep -oE 'https://i\.postimg\.cc/[^"]+\.png'
   ```
3. Download and view the extracted direct URL:
   ```bash
   curl -L -o /tmp/screenshot.png "https://i.postimg.cc/bwnvDsm3/untitled.png"
   ```

**imgur links:**
1. Gallery URLs (e.g., `https://imgur.com/abc123`) need to be converted to direct links
2. The direct URL format is: `https://i.imgur.com/abc123.png` (or `.jpg`)
3. For Imgur, append the extension or use the `i.imgur.com` subdomain with original extension

**General pattern:**
- Always try to extract the direct image URL from the HTML page source
- Look for `meta` tags with `og:image` or similar properties
- When in doubt, fetch the page HTML and parse for image URLs

Then use the `read` tool on the downloaded file to view the image.

---

## PRD Workflow

Use the PRD workflow for feature work:

- `prd-create` for new feature specs
- `prd-start` to begin implementation
- `prd-next` for the next task
- `prd-update-progress` after completed work
- `prd-done` when the PRD is fully implemented

We use PRDs as the feature-level spec, and we execute each PRD phase contract-first.

- define the phase contract before implementation: observable behavior, repo constraints, validation workflow, and the docs or prompts that must stay aligned
- keep the PRD, execution plan, supporting docs, managed prompts, and shipped behavior aligned as the work evolves
- treat drift between the contract, docs, prompts, and code as a real bug, not cleanup for later

This keeps decisions consistent and reduces drift during aggressive refactors.

When using `prd-create`, ask design questions before writing anything.

Do not use the `todo` tool as a substitute for PRD execution planning.

---

## Commit Rules

You may commit when the work reaches a clear atomic checkpoint and either:
- it follows the commit skill directly
- it is the natural checkpoint of an approved workflow such as the PRD cycle

Do not commit if the user explicitly asked you not to.

Pushes still require explicit user direction.

When committing:
- read the commit skill first
- prefer atomic commits
- use conventional commits
- make sure the relevant validation has run

Conventional commit types include:
- `feat`
- `fix`
- `docs`
- `style`
- `refactor`
- `perf`
- `test`
- `chore`

Do not batch unrelated changes into one commit.

---

## Bottom Line

Optimize for maintainability, verify behavior, communicate densely, and do not act without user consent when a change affects code, behavior, or architecture. For commits, follow the commit and workflow rules above and keep checkpoints small and atomic. For pushes, wait for explicit user direction.
