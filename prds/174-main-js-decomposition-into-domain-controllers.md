# PRD: main.js Decomposition into Domain Controllers

**GitHub Issue**: [#174](https://github.com/jeremysball/alfred/issues/174)  
**Status**: Draft  
**Priority**: High  
**Created**: 2026-03-30  
**Author**: Agent

---

## 1. Problem Statement

`src/alfred/interfaces/webui/static/js/main.js` is still a monolith.

At roughly 3,800+ lines, it currently owns too many responsibilities at once, including:
- chat message flow
- composer behavior
- edit/cancel/retry behavior
- session reconciliation
- queue and history handling
- connection status interactions
- keyboard shortcuts and leader-mode glue
- scrolling/mobile chrome behavior
- feature initialization for notifications, drag-drop, search, and more

That creates six problems:

1. **One file owns too many domains**
   - Changes in one behavior area risk regressions in unrelated areas.
   - Review and reasoning costs stay high.

2. **Responsibility boundaries are unclear**
   - It is hard to answer which code owns chat flow, session hydration, keyboard glue, or scroll behavior.

3. **Refactor sequencing is blocked**
   - Even after bootstrap, state, and transport cleanup, there is still one giant orchestration file holding everything together.

4. **Testing extracted behavior is harder**
   - Browser tests can validate outcomes, but there are few stable internal seams for controller-level cleanup.

5. **Deletion is delayed because migration targets are fuzzy**
   - Without explicit controller boundaries, old and new code paths tend to overlap too long.

6. **The rest of the frontend keeps depending on `main.js` gravity**
   - Other modules grow around the monolith instead of around clean runtime contracts.

The result is a central file that does too much and keeps the frontend from having real runtime ownership boundaries.

---

## 2. Goals

1. Split `main.js` into a small set of **domain controllers**.
2. Leave one thin top-level wiring shell instead of one giant behavior file.
3. Give each controller a **clear domain boundary**.
4. Make migration incremental and deletion-oriented.
5. Preserve behavior while extracting structure.
6. Build on PRDs #170-#173 instead of bypassing them.

---

## 3. Non-Goals

- Rewriting the frontend in a framework.
- Changing backend contracts.
- Redesigning the UI or feature set.
- Solving all component decomposition in this PRD.
- Keeping long-lived parallel paths after controller extraction.

---

## 4. Proposed Solution

### 4.1 Define controller boundaries

Extract a small set of controllers with clear ownership, for example:
- **chat controller**
- **composer controller**
- **session controller**
- **connection/status controller**
- **keyboard controller**
- **scroll/mobile controller**
- **feature bootstrap controller** for optional feature registration where needed

Exact names can vary, but ownership should stay crisp.

### 4.2 Keep the top-level shell thin

After extraction, the top-level entry file should primarily:
- create app context
- initialize shared state and transport
- register controllers
- start the app

It should not keep owning the detailed behavior of every runtime flow.

### 4.3 Make controllers depend on explicit contracts

Controllers should consume:
- bootstrap/app context from PRD #170
- shared state/event surfaces from PRD #172
- transport service boundary from PRD #173

That prevents the decomposition from turning into a file move with the same hidden coupling.

### 4.4 Migrate one domain at a time

Recommended migration order:
1. connection/status
2. composer and queue/history
3. session reconciliation
4. chat streaming lifecycle
5. keyboard and scroll glue
6. optional feature initialization glue

The exact order can shift, but each move should end with deletion of the old path.

### 4.5 Keep feature integration explicit

Features like notifications, search, drag-drop, and mobile behavior should not be initialized through scattered top-level blocks forever.

This PRD should move them behind explicit controller- or registry-based ownership, even if their internal cleanup lands in later PRDs.

### 4.6 Make extraction measurable

A successful extraction should show:
- materially smaller top-level file size
- fewer top-level mutable variables
- reduced domain mixing
- clearer targeted tests for touched controllers

---

## 5. Success Criteria

- [ ] `main.js` is reduced to a thin wiring shell or equivalent app entry file.
- [ ] Core runtime behavior is split across a small set of domain controllers.
- [ ] Controllers depend on explicit app/state/transport contracts instead of ad hoc globals.
- [ ] Old controller logic is deleted once migrated.
- [ ] Targeted regression tests protect the extracted behavior.
- [ ] The implementation passes the relevant JS and browser validation workflow.

---

## 6. Milestones

### Milestone 1: Define controller boundaries and migration order
Document the controller domains, responsibilities, and migration order for the top-level runtime.

Validation: the planned controller boundaries map cleanly to current behavior in `main.js`.

### Milestone 2: Extract the first controller slices
Move the first runtime domains out of `main.js` using explicit app/state/transport dependencies.

Validation: targeted tests prove the extracted domains still behave correctly through the new controller seams.

### Milestone 3: Migrate the remaining core runtime domains
Continue extracting session, chat, keyboard, scroll, and feature-init behavior into their controller owners.

Validation: the remaining `main.js` file shrinks materially and no migrated domain still depends on parallel top-level logic.

### Milestone 4: Delete monolithic legacy orchestration paths
Remove duplicated top-level logic once the controller-based path is authoritative.

Validation: the app boots and runs through controller ownership without fallback to the monolithic path.

### Milestone 5: Regression coverage and documentation
Add or update tests and docs for controller boundaries, app wiring, and extracted runtime ownership.

Validation: `npm run js:check` passes and targeted browser tests pass for the touched domains.

---

## 7. Likely File Changes

```text
src/alfred/interfaces/webui/static/js/main.js
src/alfred/interfaces/webui/static/js/app/controllers/chat-controller.js         # new
src/alfred/interfaces/webui/static/js/app/controllers/composer-controller.js     # new
src/alfred/interfaces/webui/static/js/app/controllers/session-controller.js      # new
src/alfred/interfaces/webui/static/js/app/controllers/connection-controller.js   # new
src/alfred/interfaces/webui/static/js/app/controllers/keyboard-controller.js     # new
src/alfred/interfaces/webui/static/js/app/controllers/scroll-controller.js       # new
src/alfred/interfaces/webui/static/js/app/controllers/features-controller.js     # possible new

tests/webui/test_frontend.py
tests/webui/test_streaming_composer.py
tests/webui/test_streaming_edit.py
tests/webui/test_sessions.py
tests/webui/test_leader_keybinds.py
prds/174-main-js-decomposition-into-domain-controllers.md
```

---

## 8. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Extraction becomes a file shuffle without real decoupling | High | require controllers to depend on explicit app/state/transport contracts |
| Too many tiny controllers create new complexity | Medium | keep the number of controllers small and domain-focused |
| Old and new paths overlap too long | High | migrate one domain at a time and delete the old path immediately after validation |
| Browser-visible regressions slip through during extraction | Medium | protect each migrated domain with targeted browser regressions |

---

## 9. Validation Strategy

This PRD is primarily JavaScript with browser-facing verification.

Required validation depends on touched files:

```bash
npm run js:check
uv run pytest tests/webui/test_frontend.py tests/webui/test_streaming_composer.py tests/webui/test_streaming_edit.py tests/webui/test_sessions.py tests/webui/test_leader_keybinds.py -v
```

If Python-backed server/test surfaces change, also run the relevant Python workflow for those touched files.

---

## 10. Related PRDs

- PRD #170: Web UI Bootstrap and Script Loading Cleanup
- PRD #171: Web UI Browser Test Harness and Fixture Stabilization
- PRD #172: Web UI State and Event-Flow Extraction
- PRD #173: Web UI WebSocket and Connection Status Service Cleanup
- PRD #175: Chat Message Component Decomposition
- PRD #176: Remove Web UI Window Globals and Implicit Dependencies

Series note: PRD #174 should land after bootstrap/state/transport seams exist, because otherwise `main.js` decomposition risks preserving the same hidden coupling in smaller files.

---

## 11. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-30 | Decompose `main.js` by runtime domain, not by arbitrary file size | The goal is clearer ownership, not just shorter files |
| 2026-03-30 | Keep a thin top-level wiring shell | The app still needs one place to assemble controllers and startup services |
| 2026-03-30 | Extract controllers only after bootstrap/state/transport seams exist | Those seams make controller ownership real instead of cosmetic |
| 2026-03-30 | Delete migrated top-level logic immediately after validation | Long-lived overlap would make the refactor harder to trust |
