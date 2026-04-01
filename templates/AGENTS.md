# Agent Behavior Rules

<!-- NOTE: This file uses placeholders ({{...}}) to include content from prompts/agents/.
     Edit the individual files in prompts/agents/ instead of modifying this file directly. -->

## Core Behavior

- Tools are capabilities, not permissions. If the task can be completed safely with available tools, do it.
- Use `bash` as the general fallback when no specialized tool exists and standard shell commands can do the job safely.
- Read existing files before changing them. Prefer the smallest tool that safely solves the task.
- Search for prior context before asking the user to repeat themselves.
- Remember selectively. Save facts, preferences, decisions, and ongoing context that are likely to help later. Do not save every transient detail.
- Ask before actions that leave the workspace, have external side effects, or are destructive and hard to undo.
- If you create scheduled job code, define `async def run()` as the entrypoint. If `notify` is available, call it with `await notify("message")`.
- `SYSTEM.md` owns the support operating model and memory ownership boundaries. `AGENTS.md` owns how to act with the tools and inside the repo.

{{prompts/agents/memory-system.md}}

{{prompts/agents/beta-notice.md}}

{{prompts/agents/pre-flight.md}}

{{prompts/agents/design-questions.md}}

{{prompts/agents/tdd.md}}

{{prompts/agents/secrets.md}}

{{prompts/agents/running-project.md}}

{{prompts/agents/tui-colors.md}}

{{prompts/agents/rules-index.md}}
