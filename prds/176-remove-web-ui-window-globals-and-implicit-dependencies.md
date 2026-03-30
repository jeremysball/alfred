# PRD: Remove Web UI Window Globals and Implicit Dependencies

**GitHub Issue**: [#176](https://github.com/jeremysball/alfred/issues/176)  
**Status**: Draft  
**Priority**: High  
**Created**: 2026-03-30  
**Author**: Agent

---

## 1. Problem Statement

The Web UI still relies too heavily on `window` globals and implicit dependencies.

A quick repository pass shows hundreds of `window.*` references across the frontend tree, including runtime ownership of:
- app-level singletons
- feature registries
- debug hooks
- third-party libraries
- component integration points
- cross-module convenience APIs

That creates six problems:

1. **Load order still matters too much**
   - When one module expects another to have populated `window`, startup stays brittle.

2. **Module boundaries are weaker than they look**
   - Even ESM modules can still act like globally-coupled scripts if their real contract is `window` state.

3. **Cross-feature reach-through is easy**
   - Any module can grab a global and depend on behavior it does not own.
   - That makes dependency graphs hard to inspect and refactor safely.

4. **Third-party dependencies leak into component logic**
   - Globals like markdown or highlight libraries shape component behavior directly instead of through explicit adapters.

5. **Testing and debugging get blurrier**
   - Globals can make behavior feel available everywhere even when the real dependency chain is hidden.

6. **Later cleanup stays blocked**
   - Bootstrap, state, transport, controller, and component cleanup are all harder while the real contracts are still implicit.

The result is a Web UI module graph that is nominally ESM but still partially behaves like a global script bundle.

---

## 2. Goals

1. Replace implicit global coupling with **explicit imports, adapters, and app-owned integration points**.
2. Keep browser-required globals only at the **true edge**.
3. Limit `window` usage to intentional debug or browser integration surfaces.
4. Make third-party library usage explicit and swappable.
5. Strengthen module boundaries across the Web UI.
6. Delete compatibility globals once new explicit contracts exist.

---

## 3. Non-Goals

- Removing every legitimate browser API usage on `window`.
- Replacing third-party libraries solely for style reasons.
- Turning the frontend into a build-tool-heavy dependency injection framework.
- Redesigning UI behavior as part of dependency cleanup.
- Preserving old global compatibility forever.

---

## 4. Proposed Solution

### 4.1 Classify all current globals

The frontend should distinguish between four categories:

1. **Browser globals that are legitimate**
   - `window.location`
   - `window.matchMedia`
   - event listeners
   - browser APIs

2. **App integration globals that should move behind explicit app context**
   - runtime services
   - feature instances
   - app-owned helpers

3. **Third-party library globals that should move behind adapters**
   - markdown/highlighting or similar formatting libraries

4. **Debug-only globals that may remain intentionally exposed**
   - only when explicitly documented and non-essential to runtime behavior

### 4.2 Replace runtime globals with explicit contracts

Cross-module app dependencies should move to one of:
- direct imports
- app context/services
- controller registration
- explicit feature registry hooks

Modules should stop assuming that another file has already populated `window` with the thing they need.

### 4.3 Add adapters for third-party dependencies

If the runtime depends on browser globals for third-party libraries, wrap them behind explicit adapters.

Example categories:
- markdown rendering
- syntax highlighting
- notification wrappers
- optional audio helpers where appropriate

That keeps components and controllers from depending directly on raw global libraries.

### 4.4 Preserve intentional debug surfaces only where justified

A small number of globals may remain for:
- manual debugging
- browser-console inspection
- explicit public integration hooks

If they remain, they should be:
- documented
- non-essential for core runtime behavior
- derived from app-owned services rather than being the service contract itself

### 4.5 Delete compatibility shims after migration

This PRD should not leave a permanent double system.

Migration pattern:
1. define explicit dependency contract
2. move consumers to the explicit contract
3. remove the old `window` dependency
4. keep only documented debug globals if still justified

---

## 5. Success Criteria

- [ ] Core runtime behavior no longer depends on undocumented app-owned `window` globals.
- [ ] Cross-module dependencies are explicit through imports, adapters, or app context.
- [ ] Third-party runtime globals are wrapped behind explicit adapters where they affect app logic.
- [ ] Remaining globals are intentional, documented, and non-essential to core behavior.
- [ ] Legacy compatibility globals are deleted once migration is complete.
- [ ] The implementation passes the relevant JS and browser validation workflow.

---

## 6. Milestones

### Milestone 1: Audit and classify current global usage
Map current `window` usage into browser APIs, app-owned runtime globals, third-party globals, and debug-only exposures.

Validation: the audit clearly separates legitimate browser API use from app-owned coupling.

### Milestone 2: Replace core runtime globals with explicit contracts
Migrate app-owned runtime dependencies to imports, app context, transport/state services, or controller registration.

Validation: core runtime modules no longer rely on implicit `window` population for normal behavior.

### Milestone 3: Introduce third-party adapters
Wrap third-party global dependencies behind explicit adapters and move component/controller usage to those adapters.

Validation: targeted tests prove formatting and other library-backed behavior still work through the adapter path.

### Milestone 4: Delete compatibility globals and narrow debug exposure
Remove migrated compatibility globals and document any intentionally retained debug-only surfaces.

Validation: remaining globals are minimal, intentional, and non-essential to core runtime correctness.

### Milestone 5: Regression coverage and documentation
Add or update tests and docs for dependency boundaries, adapter usage, and remaining intentional globals.

Validation: `npm run js:check` passes and targeted browser tests pass for the touched surfaces.

---

## 7. Likely File Changes

```text
src/alfred/interfaces/webui/static/js/main.js
src/alfred/interfaces/webui/static/js/websocket-client.js
src/alfred/interfaces/webui/static/js/features/keyboard/index.js
src/alfred/interfaces/webui/static/js/features/notifications/index.js
src/alfred/interfaces/webui/static/js/features/search/index.js
src/alfred/interfaces/webui/static/js/features/theme-palette.js
src/alfred/interfaces/webui/static/js/audio-manager.js
src/alfred/interfaces/webui/static/js/components/chat-message.js
src/alfred/interfaces/webui/static/js/app/context.js                # possible new
src/alfred/interfaces/webui/static/js/adapters/markdown.js         # possible new
src/alfred/interfaces/webui/static/js/adapters/highlight.js        # possible new
src/alfred/interfaces/webui/static/js/adapters/notifications.js    # possible new

tests/webui/test_frontend.py
tests/webui/test_websocket_client_protocol.py
tests/webui/test_tool_calls.py
tests/webui/test_theme_palette.py
prds/176-remove-web-ui-window-globals-and-implicit-dependencies.md
```

---

## 8. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Dependency cleanup breaks runtime integration order | High | stage the migration behind explicit bootstrap/app-context seams and validate each domain incrementally |
| Useful debug surfaces are removed too aggressively | Medium | keep intentional debug-only globals where they genuinely help and are clearly documented |
| Third-party adapter work adds unnecessary abstraction | Medium | wrap only where the adapter improves ownership and reduces direct global coupling |
| Compatibility shims linger indefinitely | Medium | delete the old global path immediately after consumers move to the explicit contract |

---

## 9. Validation Strategy

This PRD is primarily JavaScript with browser-visible verification.

Required validation depends on touched files:

```bash
npm run js:check
uv run pytest tests/webui/test_frontend.py tests/webui/test_websocket_client_protocol.py tests/webui/test_tool_calls.py tests/webui/test_theme_palette.py -v
```

Add targeted browser verification for any surface whose global contract changes visibly.

---

## 10. Related PRDs

- PRD #164: Repo-wide ESM Migration for JavaScript
- PRD #170: Web UI Bootstrap and Script Loading Cleanup
- PRD #172: Web UI State and Event-Flow Extraction
- PRD #173: Web UI WebSocket and Connection Status Service Cleanup
- PRD #174: main.js Decomposition into Domain Controllers
- PRD #175: Chat Message Component Decomposition

Series note: PRD #176 should land after the core bootstrap/state/controller seams exist so global removal can replace real contracts instead of papering over missing architecture.

---

## 11. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-30 | Treat app-owned `window` globals as a refactor target, not a stable API | Hidden global coupling is one of the main frontend maintenance problems |
| 2026-03-30 | Keep legitimate browser API usage but remove implicit app coupling | The goal is stronger module boundaries, not pretending the browser does not exist |
| 2026-03-30 | Wrap third-party runtime globals behind adapters where they affect app logic | Components and controllers should depend on explicit contracts, not raw globals |
| 2026-03-30 | Retain only intentional debug globals after migration | Debugging hooks can be useful, but they should not be required for core runtime behavior |
