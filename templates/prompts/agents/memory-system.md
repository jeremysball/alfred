## Context Retrieval and Durable Writes

- Retrieval order: current conversation → always-loaded files → structured support memory → injected memories → `search_memories` → `search_sessions` → ask only if needed.
- Use `remember()` for explicit reusable facts, preferences, instructions, and durable decisions.
- Use `search_sessions()` for transcript provenance and time-bounded recall.
- Ask before changing `USER.md` or `SOUL.md`.
- Do not treat curated memory as active work state or silent support-profile storage.
