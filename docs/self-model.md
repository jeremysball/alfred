# Alfred Self-Model

## Overview

Alfred maintains an internal **self-model**: a runtime snapshot of his own identity, capabilities, environment, and current context pressure.

The point of the self-model is not self-mythology. The point is grounding.

It helps Alfred reason from what is actually true right now:
- which interface he is using
- which tools are available
- whether memory/search are enabled
- how much context is already loaded
- what environment he is operating inside

This keeps Alfred more honest, more inspectable, and less likely to bluff about his own runtime state.

The self-model is **internal-first**. It informs prompt assembly and runtime reasoning. Users mainly encounter it through the `/context` inspection surface.

---

## What Alfred Knows Today

### Identity
- **Name**: Alfred
- **Role label**: current runtime role string from the self-model
- **Version**: package version when available

### Runtime State
- **Interface**: CLI or Web UI
- **Session ID**: current session identifier
- **Mode**: interactive vs daemon/background

### Capabilities
- **Tools available**: which tools Alfred can call in the current runtime
- **Memory enabled**: whether durable memory storage is available
- **Search enabled**: whether retrieval/search is available

### Context Pressure
- **Message count**: current session message volume
- **Memory count**: currently loaded/retrieved memories
- **Approximate tokens**: rough current token pressure when available

### Environment
- **Working directory**
- **Python version**
- **Platform**

---

## What the Self-Model Is Not

The self-model is **not** the user model.

It does not hold the user's identity, values, or life-direction truths. Those belong in the user-facing durable context and memory systems.

It is also **not** a replacement for the broader relational support model. Today, the self-model is intentionally conservative: it is mostly about runtime grounding, not learned support-state introspection.

As Alfred's relational support architecture grows, the self-model may eventually expose richer support-state facts. Until then, it should stay factual and compact.

---

## Inspecting the Self-Model

Use the `/context` command in the TUI to inspect Alfred's current runtime state:

```text
/context
```

The output includes an **ALFRED SELF-MODEL** section with a compact summary of:
- identity
- interface and mode
- available capabilities
- current context pressure
- runtime environment

Use it when you want to:
- verify which interface Alfred thinks he is in
- confirm whether memory/search are enabled
- see which tools are currently registered
- understand how much context is already loaded
- debug mismatches between the runtime and the prompt behavior

---

## Relationship to the Relational Support Model

The self-model helps Alfred stay truthful about himself.

The relational support model helps Alfred decide **how to help the user**.

Those are related, but different:
- the **self-model** is about Alfred's current runtime facts
- the **support model** is about support context, stance, memory, learning, and reflection

That separation matters. Alfred should feel present and relational, but he should not invent capabilities or pretend unimplemented support systems already exist.

---

## Privacy & Boundaries

- **Internal-first**: the full self-model is for prompt assembly and runtime reasoning
- **Compact inspection**: users see only a terse, practical view via `/context`
- **No invented facts**: if a runtime fact is missing, Alfred should omit it or mark it unknown
- **No user dossier**: the self-model is about Alfred's own state, not a hidden profile of the user

---

## For Developers

The self-model is implemented in `src/alfred/self_model.py`.

Key pieces:
- `RuntimeSelfModel` — structured model of identity, runtime, environment, capabilities, and context pressure
- `build_runtime_self_model()` — builds the snapshot from the live Alfred instance
- `to_prompt_section()` — serializes the model into prompt-ready markdown

The self-model is injected during context assembly so the model can reason from live runtime facts instead of vague assumptions.
