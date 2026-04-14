# Agent Behavior Rules

<!-- NOTE: This file uses placeholders ({{...}}) to include content from prompts/agents/.
     Edit the individual files in prompts/agents/ instead of modifying this file directly. -->

## Core Behavior

- Tools are capabilities, not permissions.
- Read before changing files. Prefer the smallest safe tool.
- Search context before asking the user to repeat themselves.
- Remember selectively. Save reusable facts, preferences, decisions, and recurring constraints.
- Ask before external, irreversible, or identity-file changes.
- `SYSTEM.md` owns the operating model. `AGENTS.md` owns execution rules.

{{prompts/agents/memory-system.md}}

{{prompts/agents/beta-notice.md}}

{{prompts/agents/pre-flight.md}}

{{prompts/agents/design-questions.md}}

{{prompts/agents/tdd.md}}

{{prompts/agents/secrets.md}}

{{prompts/agents/running-project.md}}

{{prompts/agents/tui-colors.md}}

{{prompts/agents/rules-index.md}}
