# PRD: Web UI Auxiliary Subsystems Cleanup

**GitHub Issue**: [#178](https://github.com/jeremysball/alfred/issues/178)  
**Status**: Draft  
**Priority**: Medium  
**Created**: 2026-03-30  
**Author**: Agent

---

## 1. Problem Statement

The Web UI includes several auxiliary browser-facing subsystems that add real value but currently increase coupling in the core runtime.

These include surfaces such as:
- kidcore and scrapbook/homeboard behavior
- notifications
- offline/PWA handling
- drag-drop and clipboard upload flow
- mobile gestures and fullscreen compose
- other optional browser-native enhancements

Current problems:

1. **Auxiliary features still leak into core runtime ownership**
   - Optional features often initialize from the same top-level runtime path as core chat behavior.
   - That makes it harder to tell what is essential versus additive.

2. **Feature boundaries are inconsistent**
   - Some auxiliary features are relatively self-contained.
   - Others still depend on globals, top-level page state, or direct DOM reach-through.

3. **Core runtime cleanup is harder while optional features stay tangled**
   - Bootstrap, state, controller, and dependency cleanup are all easier once auxiliary subsystems have explicit ownership boundaries.

4. **Maintenance cost rises as features accumulate**
   - Each optional behavior is useful on its own, but together they can make the runtime harder to reason about.

5. **Testing optional features remains more expensive than necessary**
   - Without explicit boundaries, auxiliary behavior is harder to smoke-test and easier to regress indirectly.

The result is a frontend where optional browser enhancements make the core app harder to change than they should.

---

## 2. Goals

1. Isolate auxiliary browser features behind **explicit subsystem boundaries**.
2. Keep the **core chat runtime simple** even when optional features are enabled.
3. Make auxiliary subsystem init/destroy rules explicit.
4. Reduce reliance on globals and top-level reach-through for optional features.
5. Preserve valuable optional features rather than deleting them by default.
6. Make targeted smoke testing of auxiliary features cheaper and clearer.

---

## 3. Non-Goals

- Removing expressive or playful UI features purely because they are optional.
- Redesigning every auxiliary feature.
- Folding optional features into the core runtime model if they do not need it.
- Solving the whole frontend architecture inside this PRD.
- Treating all auxiliary features as identical when their boundaries differ.

---

## 4. Proposed Solution

### 4.1 Define core vs auxiliary boundaries

The frontend should explicitly distinguish:
- **core runtime**: chat, composer, sessions, transport, top-level status
- **auxiliary subsystems**: optional browser features and expressive surfaces layered on top

Auxiliary subsystems should integrate through explicit hooks, not top-level runtime gravity.

### 4.2 Give each subsystem a clear lifecycle

Each auxiliary subsystem should have explicit ownership for:
- initialization
- dependency requirements
- event subscriptions
- teardown or cleanup where relevant
- public integration points with the core runtime

### 4.3 Reduce cross-subsystem coupling

Auxiliary subsystems should not depend on random global page knowledge if they can instead depend on:
- explicit app context
- controller/service interfaces
- feature registration hooks
- adapter modules

### 4.4 Keep optional feature initialization modular

Examples of target cleanup areas:
- kidcore and scrapbook/homeboard initialization
- notifications and favicon badge behavior
- offline/PWA and service-worker feature hooks
- drag-drop/upload flow
- mobile gesture registration and fullscreen compose

The point is not to flatten them into one system. The point is to isolate them cleanly from the core runtime.

### 4.5 Add targeted smoke coverage

Each auxiliary subsystem should have at least one focused regression or smoke test for:
- boot/attachment
- primary interaction path
- isolation from unrelated core behavior where relevant

---

## 5. Success Criteria

- [ ] Auxiliary browser features have explicit subsystem boundaries.
- [ ] Optional features no longer inflate core runtime ownership unnecessarily.
- [ ] Auxiliary subsystems initialize through explicit integration hooks.
- [ ] Cross-subsystem global coupling is reduced.
- [ ] Targeted smoke coverage exists for the major auxiliary features that remain user-visible.
- [ ] The implementation passes the relevant JS and browser validation workflow for touched surfaces.

---

## 6. Milestones

### Milestone 1: Define auxiliary subsystem boundaries
Map the current optional browser features and define the intended lifecycle and dependency boundary for each major subsystem.

Validation: the subsystem map distinguishes core runtime responsibilities from optional browser features cleanly.

### Milestone 2: Extract subsystem init and integration hooks
Move auxiliary subsystem startup behind explicit registration and lifecycle hooks rather than scattered top-level initialization.

Validation: targeted tests prove touched subsystems still boot and attach correctly.

### Milestone 3: Reduce cross-subsystem coupling
Replace top-level or global reach-through with explicit subsystem dependencies and app integration points where needed.

Validation: touched auxiliary features no longer require unrelated top-level runtime knowledge for normal operation.

### Milestone 4: Delete redundant auxiliary boot and glue paths
Remove superseded top-level or compatibility wiring once subsystem ownership is explicit.

Validation: auxiliary features still function through their explicit subsystem path only.

### Milestone 5: Smoke coverage and documentation
Add or update smoke tests and docs for subsystem lifecycle, ownership, and integration boundaries.

Validation: `npm run js:check` passes and targeted browser verification passes for the touched auxiliary features.

---

## 7. Likely File Changes

```text
src/alfred/interfaces/webui/static/js/kidcore-homeboard.js
src/alfred/interfaces/webui/static/js/scrapbook.js
src/alfred/interfaces/webui/static/js/audio-manager.js
src/alfred/interfaces/webui/static/js/features/notifications/*
src/alfred/interfaces/webui/static/js/features/offline/*
src/alfred/interfaces/webui/static/js/features/pwa/*
src/alfred/interfaces/webui/static/js/features/drag-drop/*
src/alfred/interfaces/webui/static/js/features/mobile-gestures/*
src/alfred/interfaces/webui/static/js/main.js
src/alfred/interfaces/webui/static/service-worker.js

tests/webui/test_kidcore_browser.py
tests/webui/test_kidcore_audio.py
tests/webui/test_mobile_gestures.py
tests/webui/test_reconnect.py
tests/webui/test_frontend.py
prds/178-web-ui-auxiliary-subsystems-cleanup.md
```

---

## 8. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Auxiliary cleanup accidentally breaks beloved browser features | High | preserve feature behavior, add focused smoke coverage, and keep the refactor structural |
| Optional feature extraction bleeds back into core runtime cleanup | Medium | enforce explicit core vs auxiliary boundaries and lifecycle ownership |
| One PRD becomes too broad because the subsystems are diverse | Medium | group them by shared architectural goal only, not by forcing identical internals |
| Cleanup work turns into feature deletion by convenience | Medium | treat deletion as optional and only when a feature is truly redundant or superseded |

---

## 9. Validation Strategy

This PRD is primarily JavaScript with browser-visible verification.

Required validation depends on touched files:

```bash
npm run js:check
uv run pytest tests/webui/test_kidcore_browser.py tests/webui/test_kidcore_audio.py tests/webui/test_mobile_gestures.py tests/webui/test_frontend.py -v
```

Add targeted browser verification for any auxiliary subsystem whose primary interaction path changes.

---

## 10. Related PRDs

- PRD #145: Spacejam and Kidcore Theme Overhaul
- PRD #159: Native Application Experience
- PRD #170: Web UI Bootstrap and Script Loading Cleanup
- PRD #171: Web UI Browser Test Harness and Fixture Stabilization
- PRD #176: Remove Web UI Window Globals and Implicit Dependencies
- PRD #177: Web UI CSS Theme and Asset Ownership Cleanup

Series note: PRD #178 should land after the core runtime and dependency cleanup PRDs so optional browser features can be isolated cleanly instead of stabilizing around moving core seams.

---

## 11. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-30 | Treat auxiliary features as maintainable subsystems, not clutter by default | Many of these features are valuable and should be isolated rather than casually removed |
| 2026-03-30 | Separate core runtime ownership from optional feature ownership | The chat runtime should stay simple even when browser enhancements are rich |
| 2026-03-30 | Give each subsystem explicit lifecycle boundaries | Initialization and teardown are where a lot of hidden coupling accumulates |
| 2026-03-30 | Add focused smoke coverage for touched auxiliary features | Optional features still need public-behavior protection during cleanup |
