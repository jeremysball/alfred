# Alfred Self-Model

## Overview

Alfred maintains an internal **self-model**—a runtime snapshot of his own state, capabilities, and environment. This self-awareness enables him to reason about himself as a system, understand his current operating context, and provide responses that are grounded in his actual configuration.

The self-model is **internal-only**—it informs Alfred's reasoning and appears in LLM prompts, but users interact with it only through the `/context` inspection command.

---

## What Alfred Knows

### Identity
- **Name**: Alfred
- **Role**: persistent memory-augmented assistant
- **Version**: From package metadata

### Runtime State
- **Interface**: CLI or WebUI (where the conversation is happening)
- **Session ID**: Current session identifier
- **Mode**: Interactive or daemon/background

### Capabilities
- **Tools Available**: Which tools Alfred can use (bash, read, write, search, etc.)
- **Memory**: Whether memory storage is enabled
- **Search**: Whether semantic memory search is available

### Context Pressure
- **Message Count**: Messages in current session
- **Memory Count**: Relevant memories loaded
- **Approximate Tokens**: Estimated token usage

---

## Inspecting the Self-Model

Use the `/context` command in the TUI to view Alfred's current self-state:

```
/context
```

The output includes an **ALFRED SELF-MODEL** section showing:

```
ALFRED SELF-MODEL
────────────────────────────────────────
  Identity: Alfred (persistent memory-augmented assistant)
  Interface: cli | Mode: interactive
  Capabilities: Memory ✓ | Search ✓ | 12 tools
  Context: 5 messages | 3 memories | ~1,500 tokens
```

This is useful for:
- Debugging which interface Alfred thinks he's using
- Verifying capabilities are correctly detected
- Understanding current context pressure

---

## Personality

Alfred's self-model includes updated personality guidance in `templates/SOUL.md`:

- **Opinionated** — but not contrarian for sport
- **Witty** — but not quippy every turn
- **Playful** — but not unserious when the situation is serious
- **Direct** — low-friction, gets to the point
- **Self-aware** — without becoming corny about it

This personality should be present but not performative—it amplifies clarity rather than obstructing it.

---

## Privacy & Boundaries

- **Internal-Only**: The full self-model is used in LLM prompts but never exposed directly to users in ordinary responses
- **Compact Summary**: Only the terse summary in `/context` is user-facing
- **No User Data**: The self-model contains only Alfred's own state—no personal user data or conversation content
- **Fail-Closed**: If runtime facts are missing, Alfred omits them or marks them unknown—he does not invent information

---

## For Developers

The self-model is implemented in `src/alfred/self_model.py`:

- `RuntimeSelfModel` — Pydantic model with identity, runtime, world, capabilities, and context pressure
- `build_runtime_self_model()` — Builder function that gathers facts from the live Alfred instance
- `to_prompt_section()` — Serializes self-model to markdown for LLM prompts

The self-model is injected into context assembly via `ContextLoader.assemble_with_self_model()` and appears in the system prompt sent to the LLM.
