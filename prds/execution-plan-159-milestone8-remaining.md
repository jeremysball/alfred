# Execution Plan: PRD #159 - Milestone 8 Remaining Phases (Mobile Gestures)

## Overview
Complete the Mobile Gestures milestone by implementing gesture conflict resolution, main.js integration, and cross-platform testing.

---

## Phase 6: Gesture Conflict Resolution

### GestureConflictResolver

- [ ] Test: `test_gesture_conflict_resolver_prioritizes_long_press_over_swipe()` - long press wins when both triggered
- [ ] Test: `test_gesture_conflict_resolver_cancels_on_vertical_scroll()` - scrolling cancels horizontal gestures
- [ ] Test: `test_gesture_conflict_resolver_prevents_simultaneous_pull_and_swipe()` - only one gesture active at a time
- [ ] Implement: `GestureConflictResolver` class with priority queue and active gesture tracking
- [ ] Implement: Conflict resolution logic (long-press > swipe > pull-to-refresh priority)
- [ ] Run: `uv run pytest tests/webui/test_gesture_conflict_resolver.py -v`

### TouchAction CSS

- [ ] Test: `test_touch_action_prevents_unwanted_scrolling_during_swipe()` - CSS touch-action applied correctly
- [ ] Implement: Dynamic `touch-action` CSS property management during active gestures
- [ ] Run: Browser verification - swipe gestures don't trigger page scroll

---

## Phase 7: Integration & Module Export

### main.js Wiring

- [ ] Test: `test_main_js_imports_gesture_modules()` - all gesture modules loaded
- [ ] Test: `test_initialize_gestures_called_on_dom_ready()` - gestures initialize after DOM ready
- [ ] Test: `test_gestures_cleanup_on_page_unload()` - proper cleanup prevents memory leaks
- [ ] Implement: Import gesture modules in main.js
  ```javascript
  import { initializeGestures, GESTURE_CONFIG } from './features/mobile-gestures/index.js';
  ```
- [ ] Implement: Call `initializeGestures()` after DOM ready, pass WebSocket client
- [ ] Implement: Cleanup on `beforeunload` event
- [ ] Run: Manual test - open Web UI, verify no console errors, gestures work

### Composer Integration (Swipe-to-Reply)

- [ ] Test: `test_swipe_to_reply_populates_composer_input()` - swipe sets input value
- [ ] Test: `test_swipe_to_reply_focuses_composer()` - input receives focus after swipe
- [ ] Implement: `onReply` callback that formats message as markdown quote
- [ ] Implement: Focus and cursor positioning in composer input
- [ ] Run: Browser test - swipe message, verify quote appears in input

---

## Phase 8: Cross-Platform Testing

### Device Testing Matrix

- [ ] Test: Safari iOS 17+ - swipe-to-reply, long-press, pull-to-refresh
- [ ] Test: Chrome Android 120+ - all gestures function correctly
- [ ] Test: Mobile Firefox - gesture compatibility
- [ ] Test: Touch-enabled desktop (Windows tablet mode) - gestures disabled or graceful degradation
- [ ] Document: Test results and any platform-specific issues

### Performance Validation

- [ ] Test: `test_gesture_handlers_use_passive_listeners()` - passive: true for touch events
- [ ] Test: `test_no_forced_synchronous_layout_during_gestures()` - no layout thrashing
- [ ] Implement: Performance.mark/measure for gesture latency tracking (optional)
- [ ] Run: Chrome DevTools Performance panel - verify 60fps during gestures

---

## Files to Modify

1. `src/alfred/interfaces/webui/static/js/main.js` - Import and initialize gesture modules
2. `src/alfred/interfaces/webui/static/js/features/mobile-gestures/gesture-conflict-resolver.js` - NEW
3. `src/alfred/interfaces/webui/static/js/features/mobile-gestures/index.js` - Export conflict resolver
4. `src/alfred/interfaces/webui/static/js/features/mobile-gestures/test-gesture-conflict-resolver.js` - NEW
5. `tests/webui/test_mobile_gestures_integration.py` - Integration tests

## Commit Strategy

Each checkbox = one atomic commit:
- `feat(mobile-gestures): add GestureConflictResolver for gesture prioritization`
- `feat(mobile-gestures): wire gesture modules to main.js`
- `feat(mobile-gestures): integrate swipe-to-reply with composer`
- `test(mobile-gestures): add cross-platform gesture validation`
