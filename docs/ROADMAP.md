# Alfred Roadmap

Alfred is a local-first relational support system with memory, tools, and continuity.

He is being built as **one general-purpose support architecture** that can help across:
- planning
- execution
- decisions
- review
- identity reflection
- direction reflection

The goal is not an ADHD-specific product or a pile of unrelated features. The goal is one coherent system that can stay present, remember what matters, and help across many kinds of real life and real work.

---

## Product Direction

Alfred should feel like a **persistent companion with operational intelligence**:
- **friend / peer first** by default
- able to lean into **mentor**, **coach**, or **analyst** when the moment calls for it
- grounded in real memory, real tools, and real runtime state
- honest about what is implemented today versus what is still planned

The current foundation already supports:
- always-loaded markdown context (`SYSTEM.md`, `AGENTS.md`, `SOUL.md`, `USER.md`)
- curated memories plus searchable session history
- typed support episodes, evidence refs, life domains, operational arcs, and fresh support situations
- SQLite-backed storage
- TUI, Web UI, Telegram, and cron surfaces
- tool use, self-model inspection, and local-first runtime control

The next architectural layer is the relational support model formalized in PRD #179.
Its support-memory foundation shipped in PRD #167, adaptive support runtime and bounded adaptation shipped in PRD #168, and bounded reflection, inspection, review, and correction surfaces shipped in PRD #169.

---

## Design Principles

1. **One system, many life challenges**  
   Build general support primitives instead of diagnosis-specific modes.

2. **Local-first continuity**  
   Alfred should keep context, state, and user control close to the user.

3. **Operational usefulness over abstraction**  
   Help the user act, decide, resume, and reflect — not just talk elegantly.

4. **Model judgment with inspectable boundaries**  
   Let the model reason, but keep memory, retrieval, and learned state legible.

5. **Relational without fabrication**  
   Alfred should feel present and real without inventing concrete facts or experiences.

6. **Stay truthful about the runtime**  
   Use the planned model as steering, but do not pretend unimplemented systems already exist.

---

## Current Foundation

### Runtime
- Python 3.12+ with `uv`
- CLI/TUI, Web UI, Telegram, and cron daemon entrypoints
- AlfredCore-style shared services and context assembly

### Storage and Retrieval
- SQLite-backed sessions, memories, and cron data
- curated memory search plus searchable session archive
- always-loaded markdown files for durable operating rules and explicit truths
- local and cloud embedding support depending on configuration

### Interaction Layer
- tool calling
- streaming responses
- runtime self-model and `/context` inspection
- Web UI and TUI improvements in active development

### Reference Docs
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/MEMORY.md`
- `docs/how-alfred-helps.md`
- `docs/relational-support-model.md`

---

## Roadmap

### Completed ✅

| Milestone | Description |
|-----------|-------------|
| M1 | Project Setup - Repository structure, tooling, CI/CD |
| M2 | Core Infrastructure - Configuration, context loading, prompt assembly |
| M3 | Memory Foundation - JSONL storage with embeddings |
| M4 | Vector Search - Semantic memory retrieval |
| M5 | Telegram Bot - Multi-user chat interface with CLI |
| M6 | Kimi Provider - Integration with Moonshot AI's Kimi API |
| M7 | Personality & Context - SOUL.md, USER.md, context assembly |
| M8 | Tool System - Built-in tools with Pydantic schemas |
| M9 | Agent Loop - Streaming with tool execution |
| M10 | Memory System V2 - Full CRUD operations |
| M11 | PyPI Trusted Publishing - Automated package distribution |
| M12 | Rich Markdown Output - Streaming markdown rendering with Rich Live for CLI |
| M13 | Code Health & Simplification - Removed 1,421 lines of dead code, duplication, over-engineering (PRD #82) |
| M14 | PyPiTUI CLI - Native scrollback, differential rendering, streaming responses, status line, input queue, command completion with fuzzy filtering (PRDs #94, #95, #97) |
| M15 | Config & Storage - XDG directories, TOML config, lock-free CAS JSONL store, context budget clarification (PRD #100) |
| M16 | Unified Memory System - Files + Memories (90-day TTL) + Session archive, placeholder system, TOOLS.md phase-out (PRD #102) |
| M17 | Session Summarization - Cron-based auto-summarization with two-stage search (PRD #76) |
| M18 | Tool Call Persistence - Persist tool calls in session, include in context, `/context` command (PRDs #101, #103) |
| M19 | Great Consolidation - Systematic cleanup: remove dead code, unify storage to SQLite, consolidate search logic (PRD #109) |
| M20 | Unified SQLite Storage - All storage (sessions, memories, cron) in single SQLite database with ACID transactions (PRD #117) |
| 14 | ✅ Cron Error Handling & UX | Friendly errors, local timezone, CLI responsiveness (PRD #75) |
| 15 | ✅ README Landing Page Refresh | Reframe the README around relational support, local-first continuity, and current/planned architecture |
| 25 | ✅ Code Quality | Auto-fix Ruff violations, manual lint fixes (PRD #125) |
| 83 | ✅ Interactive Terminal Tool | E2E testing capability for AI agents to run CLIs interactively with visual capture (PRD #83) |
| 105 | ✅ Local Embeddings + FAISS | BGE-base local embeddings and FAISS vector store for 5,400x faster search (PRD #105) |
| 119 | ✅ AlfredCore + Standalone Cron | Extract shared services into AlfredCore class, enable standalone cron daemon for reliable background summarization (PRD #119) |
| 120 | ✅ Cron Job Linter + Socket API | AST-based linting to detect blocking calls, decouple Alfred from cron via socket API (PRD #120) |
| 143 | Cosine Similarity Migration for Memory and Session Search | Migrate vector search semantics to cosine similarity across memory and session retrieval, with safe rebuild support (PRD #143) |
| 145 | Spacejam and Kidcore Theme Overhaul | Rework theme message surfaces, backgrounds, and subtle thinking blocks for the kidcore and spacejam themes (PRD #145) |
| 159 | ✅ Native Application Experience | Command palette, context menus, notifications, keyboard shortcuts, drag-drop, offline support (PRD #159) |
| 167 | ✅ Support Memory Foundation | Typed support episodes, evidence refs, life domains, operational arcs, fresh situations, and operational-first retrieval (PRD #167) |
| 168 | ✅ Adaptive Support Profile and Intervention Learning | Fixed support/relational registries, runtime support contracts, learning situations, bounded adaptation, and pattern-aware runtime policy (PRD #168) |
| 169 | ✅ Reflection Reviews and Support Controls | Bounded inline reflection, `/support` inspection, typed correction flows, and `/review` weekly/on-demand review surfaces (PRD #169) |

### In Progress / Next Up 🔨

| # | Milestone | Description |
|---|-----------|-------------|
| 88 | Programmatic Tool Calling | LLM writes Python code to orchestrate multiple tool calls in sandbox, reducing token consumption 30-50% |
| 90 | Multi-Provider LLM Support | z.ai, OpenRouter, Ollama with modal model selector |

### Short-term 📋

| # | Milestone | Description |
|---|-----------|-------------|
| 179 | Relational Support Operating Model | Formalize Alfred as one relational support system and align child PRDs, docs, and markdown ownership under shared primitives (PRD #179) |
| 164 | Repo-wide ESM Migration for JavaScript | Convert all JavaScript from CommonJS to ES Modules, fixing Web UI initialization failure (PRD #164) |
| 162 | Web UI WebSocket-first Status and Debug Instrumentation | Make live Web UI state and message delivery WebSocket-first, keep /health for readiness only, and add explicit server/client debug logs (PRD #162) |
| 160 | Dictation Support and Voice Mode | Bidirectional voice support for Web UI — speech-to-text input and text-to-speech responses with local and cloud options (PRD #160) |
| 155 | Interleaved Tool Calls and Thinking Blocks | Display tool calls and thinking blocks inline at their trigger point in conversation (PRD #155) |
| 156 | Playwright Browser Control | Agent can control browser programmatically with real-time preview (PRD #156) |
| 89 | Unified Notification System | Consistent notification formatting and prompt preservation (PRD #89) |
| 91 | Inline Streaming Renderer | Manual ANSI-based streaming markdown above prompt_toolkit prompt (PRD #91) |
| 131 | Ctrl-T Tool Call Expansion | Toggle all tool call boxes to show full output (PRD #131) |
| 132 | Dynamic Embedding Dimension Support | Auto-detect and re-embed when switching models (BGE↔OpenAI) (PRD #132) |
| 135 | Persistent Memory Context | Keep memories loaded across turns with LRU eviction when limits reached (PRD #135) |
| 140 | PyPiTUI v2 Adoption + Alfred Runtime Rewrite | Make PyPiTUI usable as a real runtime dependency and rewrite Alfred to consume it directly end-to-end (PRD #140) |
| 151 | Web UI Compose, Cancel, and Edit While Streaming | Add cancel/edit streaming UX in the Web UI (PRD #151) |
| 157 | Migrate to Pygments+Mistune | Replace Rich with Pygments+Mistune for 2-5x faster TUI markdown rendering (PRD #157) |
| 161 | Documentation Refresh | Continue aligning architecture/docs with SQLite storage, current interfaces, AlfredCore, and the relational support model (PRD #161) |
| 165 | Selective Tool Outcomes and Context Viewer Fixes | Replace raw tool-call context with derived outcomes, make `/context` truthful, and fix the Web UI context component (PRD #165) |
| 170 | Web UI Bootstrap and Script Loading Cleanup | Move Web UI startup to one deterministic app entrypoint and reduce `index.html` to a document shell (PRD #170) |
| 171 | Web UI Browser Test Harness and Fixture Stabilization | Stabilize browser-facing fixtures, readiness seams, and targeted regressions for safe frontend refactors (PRD #171) |
| 172 | Web UI State and Event-Flow Extraction | Introduce a lightweight app state/event layer for session, composer, queue, and connection behavior (PRD #172) |
| 173 | Web UI WebSocket and Connection Status Service Cleanup | Separate transport lifecycle and connection-status UI behind a cleaner app-facing service boundary (PRD #173) |
| 174 | main.js Decomposition into Domain Controllers | Split the monolithic Web UI runtime into focused controllers with a thin top-level shell (PRD #174) |
| 175 | Chat Message Component Decomposition | Break `chat-message` into smaller state, renderer, action, and adapter modules (PRD #175) |
| 176 | Remove Web UI Window Globals and Implicit Dependencies | Replace implicit `window` coupling with explicit imports, adapters, and app context boundaries (PRD #176) |

### Medium-term 📅

| # | Milestone | Description |
|---|-----------|-------------|
| 22 | Advanced Session Features | LLM context control, substring search, on-demand summaries |
| 24 | Configurable Context Budget | User-defined context percentages: 50% conversation, 10% tools, etc. |
| 25 | Local Embedding Models | Support for MiniLM, Nomic, MPNet running locally (no API calls) |
| 26 | HTTP API + Cron | Local API for scheduled actions |
| 139 | Web UI Test Fixture Realism | Replace bare MagicMock fixtures with explicit fakes and remove mock-aware Web UI shims (PRD #139) |
| 177 | Web UI CSS Theme and Asset Ownership Cleanup | Define clear ownership for base, component, feature, theme, and asset layers in the Web UI (PRD #177) |
| 178 | Web UI Auxiliary Subsystems Cleanup | Isolate kidcore, scrapbook, notifications, offline/PWA, drag-drop, and mobile gestures behind explicit subsystem boundaries (PRD #178) |

### Long-term 🔮

| # | Milestone | Description |
|---|-----------|-------------|
| 30 | Vector Database Evaluation | SQLite-vec or Chroma if search needs outgrow the current SQLite/vector approach |
| 31 | Multi-user Support | Proper user isolation and authentication |
| 32 | Plugin System | Extensible tool and skill architecture |
| 33 | Advanced Tool Orchestration | Multi-step tool workflows with conditional logic and error recovery |

---

## Success Criteria

- Alfred can resume active work without forcing the user to repeat core context
- Alfred retrieves durable context, memories, and prior session evidence before asking for recap
- Alfred supports planning, execution, decisions, and review reliably today
- Alfred's adaptive support runtime, reflection controls, inspection surfaces, typed correction flows, and bounded review surfaces are all shipped atop the support-memory foundation
- runtime descriptions, docs, and templates stay aligned enough that contributors can trust them
