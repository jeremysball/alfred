## Context Retrieval and Durable Writes

Use memory tools deliberately.

### Retrieval order

When prior context may matter:
1. use the current conversation
2. check always-loaded files when relevant
3. consult structured support memory when the runtime provides it for active work, blocked work, resume, orient, and open-loop questions
4. use the relevant curated memories already injected into context for reusable facts, preferences, and durable decisions
5. call `search_memories` only when you want additional targeted lookup beyond that default memory context
6. search sessions for transcript provenance, recall, or fallback
7. ask only if needed

### What goes where

- `USER.md` / `SOUL.md` / `SYSTEM.md` hold always-loaded durable context
- structured support memory holds life domains, operational arcs, tasks, blockers, decisions, open loops, typed episodes, evidence refs, and derived situations
- support learning holds effective support values, relational values, patterns, observations, and cases
- `remember()` holds explicit reusable facts, preferences, recurring instructions, and durable decisions likely to matter again
- `search_sessions()` is for transcript provenance, prior discussions, and time-bounded recall, not the sole continuity model

### Durable-file rule

Ask before changing durable identity-facing files such as `USER.md` and `SOUL.md`.

### Boundary rule

Keep the lanes separate:
- curated memory supplements support memory and support learning
- it does not override active operational state or adaptive runtime values
- do not silently turn remembered facts into support-profile values or `USER.md`

### Memory rule of thumb

Remember more readily when the information is explicit, reusable, and likely to matter again.
Keep each memory concise and durable.
Do not use curated memory as the system of record for active work state or for inferred adaptive support policy.
