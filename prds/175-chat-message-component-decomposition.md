# PRD: Chat Message Component Decomposition

**GitHub Issue**: [#175](https://github.com/jeremysball/alfred/issues/175)  
**Status**: Draft  
**Priority**: High  
**Created**: 2026-03-30  
**Author**: Agent

---

## 1. Problem Statement

`src/alfred/interfaces/webui/static/js/components/chat-message.js` is too large and owns too many concerns.

The component currently mixes:
- message state
- content block management
- assistant streaming behavior
- markdown rendering
- syntax highlighting
- inline editing
- reasoning-block rendering
- tool-call rendering
- copy/share actions
- performance instrumentation

That creates five problems:

1. **One component owns too many behaviors**
   - Rendering, state, user actions, third-party formatting, and debug hooks all live together.
   - A change in one surface can destabilize another.

2. **Message behavior is hard to isolate**
   - Streaming text, reasoning blocks, inline editing, and tool-call blocks all interact.
   - That makes the component risky to modify.

3. **Third-party formatting concerns are tangled with component logic**
   - Markdown and syntax highlighting are implementation details, but they currently shape component structure.

4. **Large component size hides real sub-boundaries**
   - The component already contains separable domains such as block modeling, renderers, editing actions, and adapters.

5. **Further frontend cleanup is blocked by component gravity**
   - Even if app and controller architecture improves, a giant message component still keeps message behavior hard to maintain.

The result is a key UI component that is functionally rich but structurally too monolithic.

---

## 2. Goals

1. Keep the existing custom element approach while splitting the component into smaller modules.
2. Separate **message state**, **rendering**, **actions**, and **formatting adapters**.
3. Keep one clear source of truth for message content and message state.
4. Reduce the risk of changing markdown, editing, reasoning, or tool-call behavior.
5. Preserve current UI behavior while making the component easier to evolve.
6. Support later dependency cleanup from PRD #176.

---

## 3. Non-Goals

- Replacing the custom element with a framework component.
- Redesigning the message UI.
- Changing the interleaved reasoning/tool-call product behavior defined elsewhere.
- Solving all third-party global cleanup in this PRD alone.
- Refactoring unrelated components just because they are nearby.

---

## 4. Proposed Solution

### 4.1 Keep one message owner, split internal responsibilities

The custom element can remain the public component surface.

Internally, split responsibilities into smaller modules such as:
- message model/state helpers
- block sequencing and normalization
- text/markdown renderer
- reasoning-block renderer
- tool-call renderer
- inline editing/actions controller
- formatting/highlight adapters

Exact names can vary, but ownership should be explicit.

### 4.2 Preserve one source of truth for message content

The component should keep one canonical representation for:
- text blocks
- reasoning blocks
- tool-call blocks
- message state such as idle/streaming/editing
- editability and metadata

Rendering helpers should derive from that truth instead of creating parallel interpretations.

### 4.3 Isolate formatting adapters

Markdown and syntax highlighting should be wrapped so the component is not structured around raw third-party globals.

This PRD should move toward:
- explicit renderer/adapters
- cleaner fallback behavior
- reduced formatting logic inside the main component body

### 4.4 Separate interaction behavior from rendering behavior

User actions such as:
- copy
- retry
- inline edit save/cancel
- reasoning expansion

should not be interleaved everywhere with render construction if a smaller action/controller module would make ownership clearer.

### 4.5 Preserve streaming and reasoning correctness

This component is central to the user-visible conversation experience.

Refactor work must preserve:
- streaming append behavior
- reasoning block progression
- tool-call ordering
- inline edit affordances
- code block copy behavior
- scroll preservation where relevant

### 4.6 Delete legacy internal paths after extraction

This should not become a permanent façade over the old file.

Each extracted internal responsibility should end with deletion of the superseded inline implementation.

---

## 5. Success Criteria

- [ ] `chat-message` remains the public custom element but no longer owns all message behavior inline.
- [ ] Message state, rendering, interactions, and formatting concerns are split into clearer internal modules.
- [ ] The component keeps one clear source of truth for message content and UI state.
- [ ] Streaming, reasoning, tool-call, and inline-edit behavior remain correct.
- [ ] Formatting logic becomes easier to swap or update without destabilizing unrelated behavior.
- [ ] The implementation passes the relevant JS and browser validation workflow.

---

## 6. Milestones

### Milestone 1: Define the component sub-boundaries
Map the internal responsibilities of `chat-message` and define the extraction targets for state, renderers, actions, and adapters.

Validation: the decomposition plan covers message state, rendering, interactions, and formatting without overlap.

### Milestone 2: Extract message-state and block-model helpers
Move the core message/block representation into explicit helpers so renderers and actions consume the same source of truth.

Validation: targeted tests prove text, reasoning, and tool-call block ordering still derives from one canonical model.

### Milestone 3: Extract rendering and formatting adapters
Split markdown/highlighting and per-block rendering into clearer modules while preserving output behavior.

Validation: targeted browser/component tests prove rendered message output still behaves correctly.

### Milestone 4: Extract interaction behavior and delete legacy inline paths
Move editing, copy/retry, and related interaction logic behind clearer internal ownership and remove superseded inline code.

Validation: targeted browser tests prove inline edit, copy, retry, and reasoning controls still work.

### Milestone 5: Regression coverage and documentation
Add or update tests and docs for component boundaries, formatting adapters, and message-state ownership.

Validation: `npm run js:check` passes and targeted browser/component tests pass for the touched message surfaces.

---

## 7. Likely File Changes

```text
src/alfred/interfaces/webui/static/js/components/chat-message.js
src/alfred/interfaces/webui/static/js/components/chat-message/
├── message-model.js                     # possible new
├── block-renderer.js                    # possible new
├── reasoning-renderer.js                # possible new
├── tool-call-renderer.js                # possible new
├── edit-actions.js                      # possible new
└── markdown-adapter.js                  # possible new

src/alfred/interfaces/webui/static/js/components/tool-call.js     # if ownership changes

tests/webui/test_frontend.py
tests/webui/test_tool_calls.py
tests/webui/test_streaming_edit.py
tests/webui/test_reasoning_scroll.py
tests/webui/test_markdown_lists.py
tests/webui/test_markdown_tables.py
prds/175-chat-message-component-decomposition.md
```

---

## 8. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Streaming or reasoning behavior regresses during extraction | High | protect the key message flows with targeted browser regressions before and during extraction |
| Decomposition leaves the same hidden coupling in more files | Medium | split by responsibility and keep one canonical message model |
| Formatting adapters diverge from rendered behavior | Medium | test the public rendered output, not just helper internals |
| Old and new code coexist too long | Medium | delete each superseded inline path immediately after the extracted path is validated |

---

## 9. Validation Strategy

This PRD is primarily JavaScript with browser-facing verification.

Required validation depends on touched files:

```bash
npm run js:check
uv run pytest tests/webui/test_tool_calls.py tests/webui/test_streaming_edit.py tests/webui/test_reasoning_scroll.py tests/webui/test_markdown_lists.py tests/webui/test_markdown_tables.py -v
```

Add targeted browser verification for any message behavior that changes visibly during the extraction.

---

## 10. Related PRDs

- PRD #145: Spacejam and Kidcore Theme Overhaul
- PRD #155: Interleaved Tool Calls and Thinking Blocks
- PRD #165: Selective Tool Outcomes and Context Viewer Fixes
- PRD #171: Web UI Browser Test Harness and Fixture Stabilization
- PRD #174: main.js Decomposition into Domain Controllers
- PRD #176: Remove Web UI Window Globals and Implicit Dependencies

Series note: PRD #175 should follow the app/controller cleanup enough that message behavior is no longer being stabilized through top-level monolith changes at the same time.

---

## 11. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-30 | Keep `chat-message` as the public custom element | The problem is internal monolith structure, not the existence of a custom element |
| 2026-03-30 | Split by message model, renderers, interactions, and adapters | Those are the real sub-boundaries already present in the file |
| 2026-03-30 | Preserve one canonical message/block model | Rendering and actions must not invent parallel truths |
| 2026-03-30 | Test visible message behavior during every extraction step | The message surface is too user-visible to refactor by internal confidence alone |
