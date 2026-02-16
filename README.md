# OpenClaw Pi

Dispatcher-first agent framework with Telegram thread isolation and first-class sub-agents.

## Docs

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Core design, components, message flow
- **[QUICKSTART.md](QUICKSTART.md)** — Basic bash scripts (no dispatcher)

## Quick Start (Basic)

```bash
./setup.sh
export ANTHROPIC_API_KEY=sk-ant-...
./run.sh
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DISPATCHER (LLM)                         │
│  - Never hangs (enforced timeouts)                         │
│  - Routes to correct thread                                │
│  - Spawns sub-agents                                       │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                    SHARED AGENT                             │
│  workspace/ (AGENTS.md, SOUL.md, USER.md, MEMORY.md)       │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ Thread 1      │  │ Thread 2      │  │ Thread N      │
│ (Main chat)   │  │ (Side topic)  │  │ (Side topic)  │
│ history only  │  │ history only  │  │ history only  │
└───────────────┘  └───────────────┘  └───────────────┘

Same agent, different conversation contexts.
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for full design.

## Status

- [x] Basic bash scripts (build-prompt.sh, run.sh, ask.sh)
- [ ] Dispatcher with Telegram support
- [ ] Thread isolation
- [ ] First-class sub-agents
- [ ] Memory system
