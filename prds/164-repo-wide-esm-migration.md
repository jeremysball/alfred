# PRD: Repo-wide ESM Migration for JavaScript

**GitHub Issue**: #164  
**Status**: In Progress  
**Priority**: High  
**Created**: 2026-03-27  
**Author**: Agent

---

## Problem Statement

The project currently uses a mix of CommonJS (`require`/`module.exports`) and ES Modules (`import`/`export`) for JavaScript. This inconsistency causes a **fatal runtime error** in the Web UI frontend:

- `main.js` imports mobile-gestures and other features using ES module syntax (`import { ... } from '...'`)
- But those modules use CommonJS syntax (`const { ... } = require('...')` and `module.exports = ...`)
- When the browser loads `main.js` as a module, it attempts to resolve the entire import graph as ESM
- The `require` calls fail with `ReferenceError: require is not defined`
- This prevents `main.js` from executing, breaking:
  - WebSocket client initialization
  - Send button event handlers
  - Connection status tooltip handlers
  - `window.__alfredWebUI` global assignment

**Result**: UI renders but is completely non-functional.

---

## Solution Overview

Migrate **all JavaScript code throughout the repository** to use ES Modules (ESM) consistently:

1. **AGENTS.md Policy Update**: Document "Use ESM for all JavaScript" as a project standard
2. **Web UI Frontend**: Convert all CommonJS modules under `src/alfred/interfaces/webui/static/js/` to ESM
3. **Test Files**: Update any JavaScript test helpers/utilities to ESM
4. **Build/Tooling**: Ensure no tooling conflicts with ESM-only JavaScript

---

## Goals

- Eliminate all CommonJS syntax (`require`, `module.exports`) from JavaScript files
- Ensure Web UI loads and initializes correctly in the browser
- Maintain all existing functionality (mobile gestures, notifications, drag-drop, etc.)
- Establish clear policy in AGENTS.md for future code

---

## Non-Goals

- Converting Python code (obviously)
- Changing CSS file formats
- Modifying HTML structure beyond script type attributes if needed
- Adding bundlers or build tools (keep native ESM in browser)

---

## Milestones

### Milestone 1: AGENTS.md Policy Update ✅
- [x] Add "Use ESM for all JavaScript" rule to AGENTS.md
- [x] Reference this PRD in the rule
- [x] Commit the documentation change

### Milestone 2: Web UI Core Modules
- [x] Convert `features/mobile-gestures/index.js` from CommonJS to ESM
- [x] Convert `features/mobile-gestures/touch-detector.js`
- [x] Convert `features/mobile-gestures/swipe-detector.js`
- [x] Convert `features/mobile-gestures/long-press-detector.js`
- [x] Convert `features/mobile-gestures/long-press-context-menu.js`
- [x] Convert `features/mobile-gestures/swipe-to-reply.js`
- [x] Convert `features/mobile-gestures/pull-to-refresh.js`
- [x] Convert `features/mobile-gestures/pull-indicator.js`
- [x] Convert `features/mobile-gestures/fullscreen-compose.js`
- [x] Convert `features/mobile-gestures/gesture-coordinator.js`
- [x] Convert `features/mobile-gestures/coordinated-detectors.js`

### Milestone 3: Web UI Feature Modules
- [x] Convert `features/search/search-overlay.js`
- [x] Verify `features/search/index.js` ESM imports work correctly
- [x] Convert `features/notifications/index.js` (if CommonJS)
- [x] Convert `features/dragdrop/index.js` (if CommonJS)
- [x] Convert `features/context-menu/index.js` (if CommonJS)

### Milestone 4: Browser Testing
- [ ] Run browser tests: `tests/webui/test_streaming_composer.py`
- [ ] Run browser tests: `tests/webui/test_kidcore_browser.py`
- [x] Verify `window.__alfredWebUI` is defined
- [x] Verify send button works
- [ ] Verify connection status tooltip works

### Milestone 5: Remaining JS Files
- [x] Audit all `.js` files in repository for CommonJS syntax
- [ ] Convert any remaining files (test utilities, scripts, etc.)

### Milestone 6: Validation
- [ ] Full test suite passes: `uv run pytest`
- [ ] Ruff check passes: `uv run ruff check src/`
- [ ] MyPy check passes: `uv run mypy --strict src/`
- [ ] Manual browser verification: UI loads and all features work

Progress note:
- Runtime Web UI modules are now ESM.
- `src/alfred/interfaces/webui/static/index.html` still loads several feature bundles through classic `<script>` tags; Phase 2 of the execution plan covers the remaining entrypoint wiring.
- Browser-side `test-*.js` helpers still use CommonJS, so the repo-wide scan gate remains open.
- `tests/webui/test_bootstrap.py` now passes for page boot, `window.__alfredWebUI`, and `chat.send`.
- The broader `tests/webui/test_streaming_composer.py::test_streaming_composer_keyboard_contract` check still fails later on stale edit assertions.


---

## Files to Modify

### AGENTS.md
- Add ESM policy section under "Code Quality and Maintainability" or "Tooling Rules"

### Web UI JavaScript (CommonJS → ESM)
```
src/alfred/interfaces/webui/static/js/features/mobile-gestures/
├── index.js                    # require/module.exports
├── touch-detector.js           # module.exports
├── swipe-detector.js           # module.exports
├── long-press-detector.js      # module.exports
├── long-press-context-menu.js  # require/module.exports
├── swipe-to-reply.js           # require/module.exports
├── pull-to-refresh.js          # module.exports
├── pull-indicator.js           # module.exports
├── fullscreen-compose.js       # module.exports
├── gesture-coordinator.js      # module.exports
└── coordinated-detectors.js    # require/module.exports

src/alfred/interfaces/webui/static/js/features/search/
└── search-overlay.js           # module.exports
```

---

## Conversion Pattern

CommonJS → ESM transformations:

```javascript
// BEFORE (CommonJS)
const { foo } = require('./foo.js');
module.exports = { foo, bar };
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { FooClass };
}

// AFTER (ESM)
import { foo } from './foo.js';
export { foo, bar };
export { FooClass };
// Remove conditional module.exports - not needed for browser ESM
```

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing tests | Run full test suite after each milestone |
| Browser compatibility | Native ESM supported in all modern browsers |
| Missing exports after conversion | Use `export { ... }` for each previously exported symbol |
| Circular dependencies revealed | ESM is stricter; fix any circular imports found |
| Test files using CommonJS | Update test JS files to use dynamic import or convert to ESM |

---

## Success Criteria

- [x] AGENTS.md contains clear "Use ESM for all JavaScript" policy
- [ ] No `require()` or `module.exports` in any `.js` files (verified via grep)
- [ ] Web UI loads without console errors
- [x] `window.__alfredWebUI` is defined after page load
- [x] Send button sends messages
- [ ] Connection status tooltip shows on hover/click
- [ ] All browser tests pass
- [ ] Full pytest suite passes

---

## Related Issues

- Original bug report: Web UI renders but is non-functional
- Affects: message sending, connection status interactions

---

## Notes

- This is a **breaking change** for any external code depending on CommonJS exports
- Internal project code only - no public API exposed
- Mobile gesture features will be restored (not removed) through this fix
