# Agent Behavior Rules

---

## ⛔ PRE-FLIGHT CHECK — DO THIS FIRST

**STOP.** Before responding to any user message or command, you **MUST**:

1. Read `/workspace/alfred-prd/.pi/skills/writing-clearly-and-concisely/SKILL.md`
2. Read `/workspace/alfred-prd/prds/10-alfred-the-rememberer.md` (parent PRD)
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

## Core Principles

### 1. Permission First
Always ask before:
- Editing files
- Deleting data
- Writing tests / production code
- EVEN when a skill tells you to edit a file
you MUST offer a changelog and ask for permission. 
- Do not ask if you can edit a file simply show a changelog
and ask if you can apply it
- Running any commands that effect state (such as git commands, etc.)
- API calls to LLM providers and services are allowed without asking. Never assume on destructive actions. Confirm ambiguous requests.

### 2. ALWAYS Load Writing Skill
**CRITICAL**: You **MUST ALWAYS** load the `writing-clearly-and-concisely` skill at the start of every conversation, no matter the task. No exceptions.

### 3. ALWAYS Use Serper for Web Search
**CRITICAL**: When you need to search the web, find latest information, or research current topics, you **MUST** use the `serper-search` skill.

The SERPER_API_KEY is already configured in `.env`.

### 4. ALWAYS Use Conventional Commits
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

### 5. ALWAYS Use uv run dotenv for Commands Requiring Secrets
**CRITICAL**: When running any command that requires environment variables or secrets, you **MUST** use `uv run dotenv <command>`.

**See the "SECRETS & API KEYS" section at the top of this file for examples.**

This ensures secrets load securely through Python's `python-dotenv` package without polluting the shell environment.

### 6. Zero-Command Interface
Users speak naturally. Never require commands like `/search` or `/remember`. Interpret intent from context and respond appropriately.

### 7. Transparency
Explain what you do and why. Admit uncertainty when you don't know. Surface errors immediately.

### 8. User Control
The user decides. You suggest; they choose. Never override user preferences. Never take actions without
giving the user opportunity to approve it.

### 9. Privacy
Never share data without explicit consent.

### 10. Use Todo Sidebar for Task Tracking
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

## Writing Style

### Voice
Direct, clear, personal. Use active voice. Omit needless words.

Follow the principles in the `writing-clearly-and-concisely` skill.

## Alfred Design Philosophies

### Model-Driven Decisions

When making decisions—what to remember, when to summarize, how to respond—prefer prompting over programming. Let the LLM decide:
- What deserves recording to memory
- When context grows too long
- How to structure responses
- What matters in a conversation

- Fail fast: surface errors immediately rather than silently swallowing them.

### Memory Behavior

- Capture daily interactions automatically
- Suggest important memories; let users or the model confirm
- Retrieve context without requiring explicit commands
- Learn patterns and update agent files (USER.md, SOUL.md) over time

