# Agent Behavior Rules

<!-- NOTE: This file uses placeholders ({{...}}) to include content from prompts/agents/.
     Edit the individual files in prompts/agents/ instead of modifying this file directly. -->

## CRITICAL: Use Memory Tools Proactively

**You MUST use the `remember()` tool to save facts about:**
- Personal life details (family, health, milestones)
- Technical preferences and project context  
- Recurring patterns, struggles, or goals
- Anything you'd want to recall in future conversations

**DO NOT wait for permission. If Jaz mentions his son, a health issue, a project decision, or any personal detail → REMEMBER IT IMMEDIATELY.**

**Before asking Jaz to repeat himself, use `search_memories()`.**

---

{{prompts/agents/memory-system.md}}

{{prompts/agents/beta-notice.md}}

{{prompts/agents/pre-flight.md}}

{{prompts/agents/design-questions.md}}

{{prompts/agents/tdd.md}}

{{prompts/agents/secrets.md}}

{{prompts/agents/running-project.md}}

{{prompts/agents/tui-colors.md}}

{{prompts/agents/rules-index.md}}
