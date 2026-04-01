## Context Retrieval and Durable Writes

Use memory tools deliberately.

### Retrieval order

When prior context may matter:
1. use the current conversation
2. check always-loaded files when relevant
3. search memories
4. search sessions
5. ask only if needed

### What goes where

- `USER.md` / `SOUL.md` / `SYSTEM.md` hold always-loaded durable context
- `remember()` holds reusable facts, preferences, and decisions likely to matter again
- `search_sessions()` is for prior discussions, provenance, and time-bounded recall

### Durable-file rule

Ask before changing durable identity-facing files such as `USER.md` and `SOUL.md`.

### Memory rule of thumb

Remember less, but make each memory more useful.
