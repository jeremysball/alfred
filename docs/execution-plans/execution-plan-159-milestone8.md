# Execution Plan: PRD #159 - Milestone 8: Mobile Gestures

## Overview

Touch-friendly interactions for mobile users. This milestone adds swipe gestures, long-press menus, and pull-to-refresh to make the Alfred Web UI feel like a native mobile application.

**Scope**: Touch detection utilities, swipe-to-reply, long-press context menus, pull-to-refresh, and edge zone protection.

---

## Phase 1: Touch Detection & Utilities

### TouchDetector ✅ COMPLETE

- [x] Test: `test_detects_touch_device()` - verify `isTouchDevice()` returns true for touch-capable devices
- [x] Test: `test_detects_mouse_device()` - verify `isMouseDevice()` returns true for mouse-capable devices
- [x] Test: `test_detects_hybrid_device()` - verify correct detection when both touch and mouse present
- [x] Implement: Create `features/mobile-gestures/touch-detector.js` with `isTouchDevice()`, `isInEdgeZone()`, `shouldHandleTouch()`
- [x] Run: `node test-touch-detector.js` (7 tests passing)

### EdgeZoneUtils ✅ COMPLETE (part of touch-detector.js)

- [x] Test: `test_edge_zone_40px_left()` - verify `isInEdgeZone(touchX, screenWidth, edgeMargin=40)` returns true for x < 40
- [x] Test: `test_edge_zone_40px_right()` - verify `isInEdgeZone()` returns true for x > screenWidth - 40
- [x] Test: `test_center_zone_not_edge()` - verify `isInEdgeZone()` returns false for x in middle of screen
- [x] Test: `test_custom_edge_margin()` - verify custom edge margins work correctly
- [x] Implement: `isInEdgeZone()` function in `touch-detector.js`
- [x] Run: `node test-touch-detector.js` (included in touch detector tests)

### GestureConfig

- [ ] Test: `test_default_gesture_config()` - verify default thresholds and constants
- [ ] Implement: Create `features/gestures/config.js` with constants:
  - `SWIPE_THRESHOLD: 50` (px to trigger swipe)
  - `EDGE_MARGIN: 40` (px to disable gestures)
  - `LONG_PRESS_DELAY: 500` (ms)
  - `PULL_THRESHOLD: 80` (px to trigger refresh)
- [ ] Run: `uv run pytest tests/webui/test_gesture_config.py -v`

---

## Phase 2: Swipe Gestures - Swipe to Reply

### SwipeDetector ✅ COMPLETE

- [x] Test: `test_detects_horizontal_swipe()` - verify swipe direction detection
- [x] Test: `test_calculates_swipe_velocity()` - verify velocity calculation (via duration)
- [x] Test: `test_detects_swipe_distance()` - verify minimum threshold check
- [x] Test: `test_respects_edge_zone()` - verify no swipe detection in 40px edge zone
- [x] Test: `test_prevents_default_on_valid_swipe()` - verify passive listeners used
- [x] Implement: Create `features/mobile-gestures/swipe-detector.js` with:
  - `attachToElement(element)` - attach swipe detection to element
  - `detach()` - remove listeners
  - `onSwipe` callback - swipe event handler
  - Touch event support with edge zone protection
  - Progress tracking for visual feedback
- [x] Run: `node test-swipe-detector.js` (8 tests passing)

### SwipeToReply Component

- [ ] Test: `test_shows_reply_preview_on_swipe()` - verify reply UI appears during swipe
- [ ] Test: `test_triggers_reply_on_swipe_complete()` - verify message is quoted on successful swipe
- [ ] Test: `test_cancels_on_insufficient_swipe()` - verify no action if swipe too short
- [ ] Test: `test_cancels_in_edge_zone()` - verify swipe from edge does nothing
- [ ] Test: `test_animates_preview_smoothly()` - verify CSS transform animation
- [ ] Implement: Create `features/gestures/swipe-to-reply.js`:
  - Integrate with SwipeDetector
  - Show reply preview overlay (slide from right)
  - On threshold met: trigger `contextMenu.quoteReply(messageId)`
  - CSS animation: `transform: translateX(0) → translateX(100px)`
- [ ] Run: `uv run pytest tests/webui/test_swipe_to_reply.py -v`

### Wire into Message Component

- [ ] Test: `test_swipe_attached_to_messages()` - verify swipe detector attached to message elements
- [ ] Implement: Modify `MessageList` or message rendering to:
  - Attach swipe-to-reply on mobile/touch devices only
  - Skip attachment if `isTouchDevice()` returns false
  - Pass message ID to swipe handler
- [ ] Run: `uv run pytest tests/webui/test_message_list.py -v`

---

## Phase 3: Long Press Gestures

### LongPressDetector

- [ ] Test: `test_detects_long_press()` - verify press held for 500ms triggers callback
- [ ] Test: `test_cancels_on_move()` - verify moving finger cancels long press
- [ ] Test: `test_cancels_on_release()` - verify releasing before threshold cancels
- [ ] Test: `test_prevents_context_menu_on_success()` - verify native context menu suppressed
- [ ] Implement: Create `features/gestures/long-press-detector.js`:
  - `attach(element, callback, options)` - attach long press detection
  - `detach(element)` - remove listeners
  - Timer-based detection (500ms default)
  - Touch and Pointer event support
- [ ] Run: `uv run pytest tests/webui/test_long_press_detector.py -v`

### LongPressMenu Integration

- [ ] Test: `test_shows_context_menu_on_long_press()` - verify existing context menu opens
- [ ] Test: `test_positions_menu_at_touch_point()` - verify menu appears at touch location
- [ ] Test: `test_menu_closes_on_tap_outside()` - verify dismiss behavior works
- [ ] Implement: Modify `context-menu/menu.js`:
  - Add `showAt(x, y)` method for touch positioning
  - Integrate with LongPressDetector on message elements
  - Reuse existing menu items (copy, quote, etc.)
- [ ] Run: `uv run pytest tests/webui/test_context_menu.py -v`

---

## Phase 4: Pull-to-Refresh

### PullDetector

- [ ] Test: `test_detects_pull_from_top()` - verify pull detection when scrolled to top
- [ ] Test: `test_ignores_pull_when_scrolled()` - verify no detection when not at top
- [ ] Test: `test_calculates_pull_distance()` - verify distance tracking
- [ ] Test: `test_triggers_on_threshold()` - verify callback when 80px threshold reached
- [ ] Test: `test_respects_elastic_resistance()` - verify rubber-band feel
- [ ] Implement: Create `features/gestures/pull-detector.js`:
  - `attach(element, callback)` - attach to scrollable container
  - Check `element.scrollTop === 0` before activating
  - Calculate pull distance with resistance formula
  - Trigger callback at threshold
- [ ] Run: `uv run pytest tests/webui/test_pull_detector.py -v`

### PullToRefresh Component

- [ ] Test: `test_shows_refresh_indicator_on_pull()` - verify indicator appears
- [ ] Test: `test_animates_indicator_with_pull()` - verify indicator moves with finger
- [ ] Test: `test_triggers_reconnect_on_release()` - verify ConnectionMonitor.refresh() called
- [ ] Test: `test_shows_success_state()` - verify checkmark on successful reconnect
- [ ] Test: `test_shows_error_state()` - verify error message on failed reconnect
- [ ] Implement: Create `features/gestures/pull-to-refresh.js`:
  - Integrate with PullDetector on chat container
  - Visual indicator: spinner that rotates with pull distance
  - On release + threshold: call `ConnectionMonitor.refresh()`
  - Success/error states with brief message
- [ ] Run: `uv run pytest tests/webui/test_pull_to_refresh.py -v`

---

## Phase 5: Gesture Styles & Accessibility

### CSS Styles

- [ ] Implement: Create `features/gestures/styles.css`:
  - Swipe preview overlay styles (glassmorphism)
  - Pull-to-refresh indicator styles
  - Smooth transitions for all gesture animations
  - Reduced motion support (`prefers-reduced-motion`)
- [ ] Run: Visual verification + Lighthouse "prefers-reduced-motion" check

### Module Exports

- [ ] Implement: Create `features/gestures/index.js`:
  - Export `TouchDetector`, `EdgeZoneUtils`, `SwipeDetector`
  - Export `LongPressDetector`, `PullDetector`
  - Export `SwipeToReply`, `PullToRefresh`
  - Initialize all gesture features on DOM ready

### Accessibility

- [ ] Test: `test_respects_prefers_reduced_motion()` - verify gestures disabled when reduced motion preferred
- [ ] Test: `test_fallback_for_no_touch()` - verify mouse users unaffected
- [ ] Implement: Add ARIA labels to gesture-sensitive elements
- [ ] Run: `uv run pytest tests/webui/test_gesture_a11y.py -v`

---

## Files to Create/Modify

### Existing Files ✅
1. `src/alfred/interfaces/webui/static/js/features/mobile-gestures/touch-detector.js` ✅
2. `src/alfred/interfaces/webui/static/js/features/mobile-gestures/test-touch-detector.js` ✅
3. `src/alfred/interfaces/webui/static/js/features/mobile-gestures/swipe-detector.js` ✅
4. `src/alfred/interfaces/webui/static/js/features/mobile-gestures/test-swipe-detector.js` ✅

### New Files (Remaining)
5. `src/alfred/interfaces/webui/static/js/features/mobile-gestures/index.js` - Module exports
6. `src/alfred/interfaces/webui/static/js/features/mobile-gestures/swipe-to-reply.js` - Swipe right to reply
7. `src/alfred/interfaces/webui/static/js/features/mobile-gestures/long-press-detector.js` - Long press detection
8. `src/alfred/interfaces/webui/static/js/features/mobile-gestures/pull-detector.js` - Pull to refresh detector
9. `src/alfred/interfaces/webui/static/js/features/mobile-gestures/pull-to-refresh.js` - Pull to refresh UI
10. `src/alfred/interfaces/webui/static/js/features/mobile-gestures/styles.css` - Gesture styles

### Modified Files
11. `src/alfred/interfaces/webui/static/js/features/context-menu/menu.js` - Add `showAt(x, y)` method
12. `src/alfred/interfaces/webui/static/js/components/MessageList.js` - Attach swipe-to-reply
13. `src/alfred/interfaces/webui/static/js/app.js` - Import and initialize gestures module

---

## Commit Strategy

Each checkbox = one atomic commit following conventional commits:

```
feat(gestures): add touch detection utilities
feat(gestures): add edge zone detection for conflict prevention
feat(gestures): add swipe detector with velocity tracking
feat(gestures): implement swipe-to-reply on messages
feat(gestures): add long press detector (500ms threshold)
feat(gestures): wire long press to context menu
feat(gestures): add pull-to-refresh detector
feat(gestures): implement pull-to-refresh reconnect UI
feat(gestures): add gesture styles with reduced motion support
test(gestures): add comprehensive test suite for all gesture components
```

---

## Validation Checklist

After all phases complete:

- [ ] Swipe right on message shows "Reply" action
- [ ] Swipe from left edge (<40px) triggers browser back (not reply)
- [ ] Long press shows context menu after 500ms
- [ ] Pull down triggers reconnect (only when scrolled to top)
- [ ] All gestures work on Safari iOS, Chrome Android
- [ ] `prefers-reduced-motion` disables animations
- [ ] All new tests pass
- [ ] Lighthouse PWA audit still passes
- [ ] Existing keyboard/mouse interactions unaffected

---

## Dependencies

- **ConnectionMonitor** (from Milestone 7) - For pull-to-refresh reconnect
- **ContextMenu** (from Milestone 3) - For long-press menu integration
- **Offline indicator** - Existing visual patterns to follow
