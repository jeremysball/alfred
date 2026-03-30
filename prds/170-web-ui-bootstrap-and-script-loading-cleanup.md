# PRD: Web UI Bootstrap and Script Loading Cleanup

**GitHub Issue**: [#170](https://github.com/jeremysball/alfred/issues/170)  
**Status**: Draft  
**Priority**: High  
**Created**: 2026-03-30  
**Author**: Agent

---

## 1. Problem Statement

The Web UI startup path is still too implicit.

Today, initialization is split across:
- `src/alfred/interfaces/webui/static/index.html`
- direct `<script>` tags with mixed classic and module loading
- global side effects during module evaluation
- feature-specific boot code that assumes other modules already ran

That creates five problems:

1. **Startup order is brittle**
   - Behavior depends on script order and side effects rather than one explicit boot sequence.
   - A small HTML or import-order change can break initialization in ways that are hard to see.

2. **`index.html` owns too much runtime wiring**
   - The document is acting as a bootloader instead of a document shell.
   - Runtime registration, feature ordering, and app lifecycle are spread between HTML and JavaScript.

3. **Feature boundaries are harder to enforce**
   - When startup is implicit, features reach across boundaries more easily.
   - It becomes unclear which module owns config loading, component registration, and app readiness.

4. **Testing startup is harder than it should be**
   - Browser tests need to reason about many startup paths at once.
   - It is harder to create one deterministic “app is ready” seam for regression tests.

5. **Future refactors stay blocked behind boot complexity**
   - State extraction, WebSocket cleanup, and `main.js` decomposition are all harder while the startup contract is fuzzy.

The result is a frontend that works largely by accumulated boot conventions instead of one explicit, inspectable startup path.

---

## 2. Goals

1. Create **one deterministic app entrypoint** for the Web UI.
2. Make the Web UI boot sequence **explicit, ordered, and testable**.
3. Reduce `index.html` to a document shell rather than a runtime orchestrator.
4. Preserve the current **vanilla ESM + Web Components** approach.
5. Keep behavior stable while moving startup ownership into JavaScript.
6. Create a clean foundation for PRDs #171-#176.

---

## 3. Non-Goals

- Migrating the frontend to React, Vue, Svelte, or another framework.
- Redesigning chat UX, themes, or feature behavior.
- Replacing the WebSocket protocol or backend message contracts.
- Decomposing `main.js` fully inside this PRD.
- Removing all globals by itself; that belongs to PRD #176.

---

## 4. Proposed Solution

### 4.1 Establish one app bootstrap module

Create one explicit bootstrap entrypoint for the Web UI runtime.

Responsibilities:
- wait for document readiness
- load app config
- register required custom elements and feature modules
- initialize core services in a fixed order
- initialize optional feature modules through explicit registration
- expose one clear “app ready” boundary for tests

### 4.2 Make `index.html` a document shell

`index.html` should primarily own:
- document structure
- static containers
- CSS links
- one app entry script
- browser-required static tags such as manifest and icons

It should stop owning:
- long chains of runtime script ordering
- scattered feature boot assumptions
- implicit startup sequencing

### 4.3 Define a startup contract

The frontend should boot through a stable sequence such as:
1. DOM ready
2. config available
3. component registry loaded
4. core services initialized
5. app controllers initialized
6. optional features initialized
7. app ready signal emitted

The order must be documented and tested.

### 4.4 Separate core and optional startup

Boot should distinguish between:
- **core runtime**: chat, composer, sessions, WebSocket transport, status surfaces
- **optional/auxiliary features**: notifications, PWA/offline, drag-drop, kidcore, scrapbook, mobile gestures

That does not remove optional features. It makes their boot path explicit and lower-risk.

### 4.5 Preserve ESM and explicit imports

This PRD builds on PRD #164.

Requirements:
- native ESM remains the only JavaScript module format
- new bootstrap code uses explicit imports, not `window` reach-through
- any required browser global should be intentionally wrapped and documented

### 4.6 Add failure visibility during boot

Startup failures should fail loudly and locally.

Requirements:
- boot steps can report which phase failed
- tests can detect boot completion or boot failure deterministically
- optional features should not silently corrupt core startup

---

## 5. Success Criteria

- [ ] `index.html` loads one primary app entry module for runtime startup.
- [ ] Web UI boot order is explicit and documented.
- [ ] Core services and optional features initialize through defined registration points.
- [ ] Browser tests can wait on one deterministic app-ready seam.
- [ ] The change preserves current product behavior while simplifying startup ownership.
- [ ] The implementation passes the relevant JS and browser validation workflow.

---

## 6. Milestones

### Milestone 1: Define the bootstrap contract
Document the app startup phases, the distinction between core and optional features, and the ownership boundary between HTML and JavaScript.

Validation: architecture notes and startup tests agree on the boot sequence and readiness contract.

### Milestone 2: Introduce a single app entrypoint
Add the explicit bootstrap module and move top-level startup orchestration into JavaScript while preserving current behavior.

Validation: the browser boots successfully through the new entrypoint and exposes one testable ready seam.

### Milestone 3: Migrate runtime registration into the bootstrap path
Move component registration, service startup, and feature initialization out of HTML-driven ordering and into explicit bootstrap registration.

Validation: targeted browser tests prove the same runtime features still initialize correctly.

### Milestone 4: Delete redundant script-order wiring
Remove no-longer-needed direct script orchestration and duplicate startup code paths once the bootstrap path is authoritative.

Validation: `index.html` is materially simpler and runtime startup still works through the new path only.

### Milestone 5: Regression coverage and documentation
Add or update tests and docs for boot sequencing, readiness, and startup ownership.

Validation: `npm run js:check` passes and targeted Web UI startup/browser tests pass for the touched surfaces.

---

## 7. Likely File Changes

```text
src/alfred/interfaces/webui/static/index.html
src/alfred/interfaces/webui/static/js/main.js
src/alfred/interfaces/webui/static/js/app/bootstrap.js        # new
src/alfred/interfaces/webui/static/js/app/registry.js         # possible new
src/alfred/interfaces/webui/static/js/app/ready.js            # possible new
src/alfred/interfaces/webui/static/service-worker.js          # only if startup registration moves

tests/webui/test_bootstrap.py
tests/webui/test_frontend.py
tests/webui/test_webui_cli.py
prds/170-web-ui-bootstrap-and-script-loading-cleanup.md
```

---

## 8. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Startup refactor breaks load order in subtle ways | High | keep behavior unchanged, add explicit boot phases, and verify with targeted browser tests |
| Optional features accidentally become hard dependencies | Medium | separate core and optional registration paths explicitly |
| `index.html` cleanup gets mixed with unrelated feature work | Medium | limit this PRD to startup ownership and sequencing only |
| Boot failures become harder to debug during transition | Medium | add phase-level failure visibility and deterministic readiness checks |

---

## 9. Validation Strategy

This PRD is primarily JavaScript with browser-facing verification.

Required validation depends on touched files:

```bash
npm run js:check
uv run pytest tests/webui/test_bootstrap.py tests/webui/test_frontend.py -v
```

If Python-backed startup surfaces change, also run the relevant Python workflow for the touched files.

---

## 10. Related PRDs

- PRD #164: Repo-wide ESM Migration for JavaScript
- PRD #171: Web UI Browser Test Harness and Fixture Stabilization
- PRD #172: Web UI State and Event-Flow Extraction
- PRD #173: Web UI WebSocket and Connection Status Service Cleanup
- PRD #174: main.js Decomposition into Domain Controllers
- PRD #176: Remove Web UI Window Globals and Implicit Dependencies

Series note: PRD #170 is the intended starting point for the frontend refactor series.

---

## 11. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-30 | Keep vanilla ESM and Web Components | The current stack is sufficient; the problem is startup architecture, not missing framework machinery |
| 2026-03-30 | Move runtime orchestration out of `index.html` | HTML should be a document shell, not the runtime bootloader |
| 2026-03-30 | Separate core startup from optional feature startup | The chat runtime should stay simple even when auxiliary browser features exist |
| 2026-03-30 | Make app readiness explicit and testable | Later refactors need one deterministic boot seam |
