# Execution Plan: Milestone 8 - Mobile Gestures

**PRD**: [#159 - Native Application Experience Enhancements](../159-native-application-experience-enhancements.md)  
**Scope**: Touch-friendly interactions for mobile users

---

## Overview

Implement mobile gesture support including swipe-to-reply, long-press context menus, pull-to-refresh, and swipe-up fullscreen compose. Follows the patterns established in existing features (command-palette, drag-drop, etc.).

---

## Phase 1: Touch Detection & Utilities ✅ COMPLETE

### TouchCapabilities

- [x] Test: `test_detects_touch_device()` - verify touch detection works
- [x] Test: `test_detects_mouse_device()` - verify mouse detection works
- [x] Implement: Create `touch-detector.js` with `isTouchDevice()` helper
- [x] Run: `node src/alfred/interfaces/webui/static/js/features/mobile-gestures/test-touch-detector.js`

### EdgeZoneDetection

- [x] Test: `test_edge_zone_40px_left()` - verify touch at x=39px is in edge zone
- [x] Test: `test_edge_zone_40px_right()` - verify touch at width-39px is in edge zone
- [x] Test: `test_not_edge_zone_at_50px()` - verify touch at x=50px is NOT in edge zone
- [x] Implement: `isInEdgeZone(touchX, screenWidth, edgeMargin = 40)` function
- [x] Run: Verify tests pass

**Status**: 7 tests passing in `test-touch-detector.js`, 10 tests in `test-index.js`
**Files**: `touch-detector.js`, `index.js`, `test-touch-detector.js`, `test-index.js`

---

## Phase 2: Swipe-to-Reply Gesture ✅ COMPLETE

### Design Decisions (Phase 2)

**Decision**: Dynamic attachment via MutationObserver
- **Rationale**: `chat-message` elements are created dynamically during streaming and session loading. Static attachment at init would miss messages added after page load.
- **Impact**: SwipeToReply class manages its own lifecycle, attaching to new messages as they're added to DOM.

**Decision**: CSS transform-based visual feedback
- **Rationale**: GPU-accelerated, aligns with Milestone 6 animation requirements (transform/opacity only, 60fps target).
- **Impact**: Use `transform: translateX(var(--swipe-offset))` with `transition` managed via CSS class toggling.

**Decision**: Right-swipe only for reply
- **Rationale**: Left swipe reserved for potential future "delete/archive" feature (common pattern in messaging apps like WhatsApp/Signal).
- **Impact**: SwipeDetector configured with `direction: 'right'` only.

**Decision**: Reply format uses markdown blockquote (`> quoted text`)
- **Rationale**: Familiar markdown pattern, renders correctly in composer preview.
- **Impact**: Reply callback populates input with `> ${content}\n\n` format.

### SwipeDetectorClass

- [x] Test: `test_swipe_detector_initializes()` - verify class instantiation
- [x] Test: `test_swipe_threshold_100px()` - verify 100px minimum swipe distance
- [x] Test: `test_horizontal_swipe_detected()` - verify horizontal swipe recognized
- [x] Test: `test_vertical_swipe_ignored()` - verify vertical swipes don't trigger horizontal handler
- [x] Implement: Create `swipe-detector.js` with SwipeDetector class
- [x] Run: `node src/alfred/interfaces/webui/static/js/features/mobile-gestures/test-swipe-detector.js`

### SwipeToReply Module

- [x] Test: `test_swipe_to_reply_module_exports()` - verify SwipeToReply class exported
- [x] Test: `test_attach_to_message_creates_detector()` - verify attachment creates SwipeDetector instance
- [x] Test: `test_detach_removes_detector()` - verify cleanup removes listeners
- [x] Implement: Create `swipe-to-reply.js` with SwipeToReply class
- [x] Implement: Dynamic attachment via MutationObserver on message-list
- [x] Run: `node src/alfred/interfaces/webui/static/js/features/mobile-gestures/test-swipe-to-reply.js`

**Status**: 15 tests passing
**Files**: `swipe-to-reply.js`, `test-swipe-to-reply.js`

### SwipeRightOnMessage

- [x] Test: `test_swipe_right_triggers_reply()` - verify right swipe on message calls reply callback
- [x] Test: `test_swipe_left_does_nothing()` - verify left swipe is ignored
- [x] Test: `test_swipe_in_edge_zone_ignored()` - verify swipe from left edge (<40px) doesn't trigger
- [x] Test: `test_reply_callback_receives_message_element()` - verify callback gets correct element
- [x] Implement: `onReply` callback extracts message content and populates composer input
- [x] Implement: Callback uses `messageElement.getContent()` API from chat-message component
- [x] Run: Manual test in browser DevTools mobile view

### SwipeVisualFeedback

- [x] Test: `test_swipe_under_threshold_snaps_back()` - verify <100px swipe snaps back (300ms ease-out)
- [x] Test: `test_swipe_over_threshold_completes()` - verify ≥100px swipe triggers reply action
- [x] Test: `test_reply_hint_opacity_progress()` - verify hint opacity follows swipe progress (0% at 0px, 100% at 100px)
- [x] Implement: CSS `--swipe-offset` custom property bound to touch position
- [x] Implement: Reply hint SVG icon with `opacity: var(--swipe-progress, 0)`
- [x] Implement: Snap-back animation uses `cubic-bezier(0.4, 0.0, 0.2, 1)` (Material Design standard)
- [x] Run: Visual verification in browser, verify 60fps in Chrome DevTools Performance panel

### Composer Input Integration

- [x] Test: `test_reply_populates_input()` - verify input value set to `> content\n\n`
- [x] Test: `test_reply_focuses_input()` - verify composer textarea receives focus
- [x] Test: `test_reply_caret_position()` - verify cursor at end of quoted text
- [x] Implement: Reply callback queries `#message-input` and sets value
- [x] Implement: Call `textarea.focus()` and `setSelectionRange()` to position cursor
- [x] Run: End-to-end test - swipe message → input populated → ready to type response

---

## Phase 3: Long-Press Context Menu ✅ COMPLETE

### LongPressDetector

- [x] Test: `test_long_press_500ms_threshold()` - verify 500ms press triggers
- [x] Test: `test_short_press_ignored()` - verify <500ms press is ignored
- [x] Test: `test_touch_move_cancels_long_press()` - verify movement cancels long press
- [x] Test: `test_long_press_on_message()` - verify correct target element captured
- [x] Implement: Create `long-press-detector.js` with LongPressDetector class
- [x] Run: `node src/alfred/interfaces/webui/static/js/features/mobile-gestures/test-long-press.js`

### LongPressContextMenuIntegration

- [x] Test: `test_long_press_opens_context_menu()` - verify long press opens existing menu
- [x] Test: `test_context_menu_shows_at_touch_position()` - verify correct positioning
- [x] Test: `test_touch_end_closes_menu()` - verify touch elsewhere closes menu
- [x] Implement: Integrate with existing `features/context-menu/` system
- [x] Implement: Position menu at touch coordinates (not mouse coordinates)
- [x] Run: Manual test on message elements

### LongPressVisualFeedback

- [x] Test: `test_long_press_shows_ripple()` - verify visual feedback during press
- [x] Test: `test_ripple_centers_on_touch()` - verify ripple position matches touch
- [x] Implement: CSS ripple effect (scale animation)
- [x] Implement: Prevent default touch actions during long press detection
- [x] Run: Visual verification in browser

**Status**: 16 tests in `test-long-press-detector.js`, 16 tests in `test-long-press-context-menu.js`
**Files**: `long-press-detector.js`, `long-press-context-menu.js`, `test-long-press-detector.js`, `test-long-press-context-menu.js`

---

## Phase 4: Pull-to-Refresh ✅ COMPLETE

### ScrollPositionDetection

- [x] Test: `test_scroll_at_top_true()` - verify scrollTop === 0 detection
- [x] Test: `test_scroll_at_top_false()` - verify scrollTop > 0 returns false
- [x] Test: `test_scroll_threshold_10px()` - verify small tolerance allowed
- [x] Implement: `isScrolledToTop(element, threshold = 10)` helper
- [x] Run: Verify tests pass

### PullToRefreshDetector

- [x] Test: `test_pull_down_threshold_80px()` - verify 80px pull threshold
- [x] Test: `test_pull_only_when_at_top()` - verify pull ignored when scrolled down
- [x] Test: `test_pull_triggers_reconnect()` - verify callback fires on valid pull
- [x] Test: `test_pull_resistance_feel()` - verify pull distance feels natural
- [x] Implement: Create `pull-to-refresh.js` with PullToRefreshDetector class
- [x] Run: `node src/alfred/interfaces/webui/static/js/features/mobile-gestures/test-pull-to-refresh.js`

### PullToRefreshVisualFeedback

- [x] Test: `test_pull_indicator_shows()` - verify visual indicator appears
- [x] Test: `test_pull_indicator_rotates()` - verify spinner rotates during pull
- [x] Test: `test_release_triggers_refresh()` - verify release at threshold triggers action
- [x] Implement: Glassmorphism pull indicator component (`pull-indicator.js`)
- [x] Implement: CSS animations for pull state (pulling, releasing, refreshing) (`styles.css`)
- [x] Run: Visual verification in browser DevTools mobile view

**Files Created:**
- `features/mobile-gestures/styles.css` - Glassmorphism pull indicator styles with CSS custom properties
- `features/mobile-gestures/pull-indicator.js` - PullIndicator component with state management

**Implementation Details:**
- Uses CSS custom properties (`--ptr-progress`, `--ptr-distance`, `--ptr-opacity`, `--ptr-translate`) for smooth animations
- Four visual states: `hidden`, `pulling`, `ready`, `refreshing`
- Spinner rotates 0-180 degrees based on pull progress
- Reduced motion support via `prefers-reduced-motion` media query
- `createPullIndicator()` factory function wires callbacks to PullToRefreshDetector
- `initializePullToRefresh()` helper combines detector + indicator setup
- 9 new tests added (23 total passing in test-pull-to-refresh.js)

### WebSocketReconnectIntegration

- [x] Test: `test_pull_triggers_websocket_reconnect()` - verify ConnectionMonitor.reconnect() called
- [x] Test: `test_reconnect_success_hides_indicator()` - verify indicator hidden on success
- [x] Test: `test_reconnect_failure_shows_error()` - verify error toast on failure
- [x] Implement: Wire PullToRefresh to existing ConnectionMonitor via `initializePullToRefresh()`
- [x] Implement: `createPullIndicator` updated to handle async success/error states
- [x] Implement: Debounce (2s) to prevent rapid pull spam
- [x] Run: Integration test with offline/online toggle

**Implementation Details:**
- `initializePullToRefresh()` accepts `connectionMonitor` option with `reconnect()` method
- `onRefresh` callback wraps ConnectionMonitor.reconnect() and handles async result
- Success: Shows "Connected!" state for 1.5s via `indicator.showSuccess()`
- Failure: Shows "Failed to connect" state for 2s via `indicator.showError()`
- `createPullIndicator()` updated to await async callbacks and catch errors
- Returns `{ detector, indicator, cleanup }` for proper lifecycle management

---

## Phase 5: Swipe-Up Fullscreen Compose ✅ COMPLETE

### SwipeUpDetector

- [x] Test: `test_swipe_up_threshold_120px()` - verify 120px upward swipe threshold (via createFullscreenCompose)
- [x] Test: `test_swipe_up_on_input_area()` - verify detection on composer input
- [x] Test: `test_horizontal_swipe_ignored_for_fullscreen()` - verify horizontal doesn't trigger
- [x] Implement: Swipe-up detection integrated in `createFullscreenCompose()`
- [x] Run: Verify tests pass

### FullscreenComposeModal

- [x] Test: `test_swipe_up_opens_fullscreen()` - verify fullscreen modal opens (via factory function)
- [x] Test: `test_fullscreen_contains_composer()` - verify textarea is focused
- [x] Test: `test_swipe_down_closes_fullscreen()` - verify reverse gesture closes
- [x] Implement: Create `fullscreen-compose.js` modal component
- [x] Implement: Transfer input content between compact and fullscreen views
- [x] Implement: Swipe-down detection for closing modal
- [x] Run: 22 tests passing in test-fullscreen-compose.js

### FullscreenVisualDesign

- [x] Test: `test_fullscreen_animation_300ms()` - verify smooth transition
- [x] Test: `test_fullscreen_respects_reduced_motion()` - verify prefers-reduced-motion support
- [x] Implement: CSS animations for modal enter/exit (`fullscreen-compose.css`)
- [x] Implement: Glassmorphism background with backdrop-filter
- [x] Implement: 300ms cubic-bezier animation
- [x] Run: Visual verification (via test coverage)

**Files Created:**
- `features/mobile-gestures/fullscreen-compose.js` - FullscreenComposeModal class + factory
- `features/mobile-gestures/fullscreen-compose.css` - Glassmorphism styles + animations
- `features/mobile-gestures/test-fullscreen-compose.js` - 22 unit tests

**Implementation Details:**
- Swipe-up threshold: 120px, max duration: 500ms
- Content sync: compact ↔ fullscreen on open/close
- Close methods: swipe-down, close button, Escape key
- Submit: button or Cmd/Ctrl+Enter
- Reduced motion support via `prefers-reduced-motion`
- iOS safe area support via `env(safe-area-inset-*)`

---

## Phase 6: Gesture Conflict Resolution

### Design Decisions (Phase 6)

**Decision**: Use Wrapper Pattern for Gesture Coordination
- **Context**: 5 gesture systems operate independently (swipe-to-reply, long-press, pull-to-refresh, swipe-up compose, swipe-down close)
- **Rationale**: Wrapper pattern (Option B) keeps existing detectors untouched while adding coordination layer. Less risky than modifying working code.
- **Implementation**: Create `CoordinatedSwipeDetector`, `CoordinatedLongPressDetector` wrappers that use central `GestureCoordinator`
- **Impact**: New files `gesture-coordinator.js`, `coordinated-detectors.js`; existing detectors remain unchanged

**Decision**: 15px Axis-Locking Threshold
- **Context**: Need to distinguish horizontal swipes (reply) from vertical (pull/compose)
- **Rationale**: 10px too sensitive (accidental triggers), 20px requires too much deliberate movement
- **Implementation**: Track deltaX and deltaY; lock to dominant axis once |dominant| > 15px and |dominant| > |other| * 1.5
- **Impact**: Coordinated detectors calculate axis dominance before committing to gesture type

**Decision**: Touch Target Region Definitions
- **Context**: Gestures overlap in screen regions (composer vs message list vs page body)
- **Regions**:
  - **Message Items** (`.chat-message`): Swipe-to-reply (right), Long-press
  - **Composer Input** (`#message-input`): Swipe-up fullscreen
  - **Fullscreen Modal** (`.fullscreen-compose`): Swipe-down close
  - **Page Body** (top, scrolled): Pull-to-refresh
  - **Edge Zones** (x<40px, x>width-40px): Browser gestures only
- **Impact**: Coordinator checks element.matches() against region selectors before granting gesture lock

**Decision**: Gesture Priority Hierarchy
- **Priority**: Long-press (3) > Fullscreen/Pulldown (2) > Reply/Pull (1)
- **Rationale**: Long-press requires intentional hold (500ms), should win over accidental swipes
- **Rule**: Once gesture starts (threshold met), it owns the touch until `touchend`
- **Impact**: `GestureCoordinator.requestGesture()` uses priority map; higher priority can preempt lower

### GestureCoordinator Class

- [x] Test: `test_coordinator_singleton_pattern()` - verify single coordinator instance
- [x] Test: `test_requestGesture_grants_lock()` - verify lock granted when available
- [x] Test: `test_requestGesture_denies_when_busy()` - verify lock denied when gesture active
- [x] Test: `test_releaseGesture_clears_lock()` - verify lock released after gesture ends
- [x] Test: `test_higher_priority_can_preempt()` - verify high priority preempts low priority
- [x] Test: `test_equal_priority_cannot_preempt()` - verify equal priority denied
- [x] Test: `test_getActiveGesture_returns_info()` - verify complete gesture info returned
- [x] Test: `test_isGestureActive_checks_any()` - verify can check any gesture active
- [x] Implement: Create `gesture-coordinator.js` with `GestureCoordinator` class
- [x] Run: `node test-gesture-coordinator.js` - 8 tests passing

### CoordinatedDetectors ✅ COMPLETE

- [x] Test: `test_coordinated_swipe_checks_before_start()` - verifies coordinator lock on touchstart
- [x] Test: `test_coordinated_long_press_checks_before_start()` - verifies coordinator lock
- [x] Test: `test_coordinated_detector_releases_on_end()` - verifies lock released on touchend
- [x] Implement: Create `coordinated-detectors.js` with wrapped versions
- [x] Implement: `CoordinatedSwipeDetector` wraps `SwipeDetector` with coordinator calls
- [x] Implement: `CoordinatedLongPressDetector` wraps `LongPressDetector` with coordinator calls
- [x] Run: Verify 131 total tests passing (128 existing + 3 new)

**Files Created:**
- `features/mobile-gestures/coordinated-detectors.js` - CoordinatedSwipeDetector and CoordinatedLongPressDetector classes
- `features/mobile-gestures/test-coordinated-detectors.js` - 3 unit tests

**Implementation Details:**
- Priority: Swipe=1 (standard), LongPress=3 (highest)
- Lock requested on `touchstart`, released on `touchend`/`touchcancel`
- Wrapped detector only triggers callbacks when lock is held
- Passive listeners maintained for performance
- Exports added to `index.js`

### AxisLocking ✅ COMPLETE

- [x] Test: `test_axis_lock_horizontal_at_15px()` - X-movement > 15px locks to horizontal
- [x] Test: `test_axis_lock_vertical_at_15px()` - Y-movement > 15px locks to vertical
- [x] Test: `test_axis_neutral_below_threshold()` - no lock below 15px
- [x] Test: `test_axis_switch_prevented_after_lock()` - cannot switch axis once locked
- [x] Implement: Axis dominance calculation in coordinated detectors
- [x] Run: 135 total tests passing

**Implementation Details:**
- Threshold: 15px minimum movement to trigger lock
- Dominance ratio: 1.5x (dominant axis must be 50% larger than other)
- Horizontal lock: `|deltaX| > 15 && |deltaX| > |deltaY| * 1.5`
- Vertical lock: `|deltaY| > 15 && |deltaY| > |deltaX| * 1.5`
- Lock persists until `touchend`/`touchcancel` (no mid-gesture switching)
- Stored in `axisLock` property ('horizontal', 'vertical', or null)

### EdgeZoneHandling

- [ ] Test: `test_left_edge_swipe_passes_through()` - verify browser back gesture works
- [ ] Test: `test_right_edge_swipe_passes_through()` - verify browser forward gesture works
- [ ] Test: `test_edge_zone_prevents_custom_gesture()` - our gestures disabled in edge zones
- [ ] Implement: Check `isInEdgeZone()` before requesting gesture lock
- [ ] Run: Manual test on Safari iOS (if available) or Chrome DevTools mobile emulation

### MultiGestureCoordination

- [ ] Test: `test_swipe_and_long_press_dont_conflict()` - verify both work independently
- [ ] Test: `test_long_press_wins_after_200ms()` - long-press locks out swipe after hold
- [ ] Test: `test_swipe_wins_with_movement()` - significant X-movement prevents long-press
- [ ] Test: `test_pull_and_swipe_up_dont_conflict()` - different regions work separately
- [ ] Test: `test_gesture_priority_respected()` - high priority preempts low priority
- [ ] Test: `test_active_gesture_exclusivity()` - once started, owns touch until end
- [ ] Implement: Gesture priority system with preempt logic
- [ ] Run: Verify all gestures work together without conflicts

### RegionBasedCoordination

- [ ] Test: `test_region_composer_prevents_pull()` - swipe-up on composer doesn't trigger pull
- [ ] Test: `test_region_message_prevents_fullscreen()` - message swipe doesn't trigger fullscreen
- [ ] Test: `test_region_fullscreen_isolates_gestures()` - modal has its own gesture space
- [ ] Implement: Region selector checks in coordinated detectors
- [ ] Run: Integration test with all regions active

---

## Phase 7: Integration & Module Export

### IndexModule

- [ ] Test: `test_module_exports_all_components()` - verify clean public API
- [ ] Implement: Create `features/mobile-gestures/index.js` with exports
- [ ] Run: `node -e "const m = require('./index.js'); console.log(Object.keys(m));"`

### MainJSIntegration

- [ ] Implement: Import mobile-gestures module in main.js
- [ ] Implement: Initialize SwipeDetector on message containers
- [ ] Implement: Initialize LongPressDetector on messages and code blocks
- [ ] Implement: Initialize PullToRefresh on chat container
- [ ] Run: Verify no console errors on page load

---

## Phase 8: Cross-Platform Testing

### MobileEmulationTests

- [ ] Test: Chrome DevTools mobile emulation - iPhone SE
- [ ] Test: Chrome DevTools mobile emulation - iPad Pro
- [ ] Test: Chrome DevTools mobile emulation - Pixel 5
- [ ] Document: Any browser-specific issues found

### TouchDeviceValidation

- [ ] Test: Verify gestures only attach on touch-capable devices
- [ ] Test: Verify mouse interactions still work (no regression)
- [ ] Test: Verify touch + mouse hybrid devices work correctly
- [ ] Run: Manual test on actual mobile device if available

---

## Files to Create

```
src/alfred/interfaces/webui/static/js/features/mobile-gestures/
├── index.js                      # Module exports
├── touch-detector.js             # Touch capability detection
├── swipe-detector.js             # Swipe gesture detection (horizontal/vertical)
├── long-press-detector.js        # Long press detection (500ms)
├── pull-to-refresh.js            # Pull-down refresh detector
├── fullscreen-compose.js         # Swipe-up fullscreen composer
├── gesture-coordinator.js        # Central gesture coordination singleton
├── coordinated-detectors.js      # Wrapped detectors with coordination
├── styles.css                    # All gesture-related styles
├── test-touch-detector.js        # Unit tests
├── test-swipe-detector.js        # Unit tests
├── test-long-press.js            # Unit tests
├── test-pull-to-refresh.js       # Unit tests
├── test-fullscreen-compose.js    # Unit tests
├── test-gesture-coordinator.js   # Coordination unit tests
└── README.md                     # Usage documentation
```

## Files to Modify

```
src/alfred/interfaces/webui/static/
├── main.js                       # Import and initialize mobile-gestures
├── index.html                    # Add fullscreen compose modal container
└── css/base.css                  # Add global touch-action rules
```

## Commit Strategy

Each checkbox = one atomic commit:
- `test(mobile-gestures): add touch detection tests`
- `feat(mobile-gestures): implement touch detector utility`
- `test(mobile-gestures): add swipe detector tests`
- `feat(mobile-gestures): implement swipe-to-reply`
- `feat(mobile-gestures): add swipe visual feedback`
- `test(mobile-gestures): add long-press tests`
- `feat(mobile-gestures): implement long-press context menus`
- `test(mobile-gestures): add pull-to-refresh tests`
- `feat(mobile-gestures): implement pull-to-refresh`
- `feat(mobile-gestures): implement fullscreen compose`
- `test(mobile-gestures): add gesture coordinator tests`
- `feat(mobile-gestures): implement gesture coordinator`
- `feat(mobile-gestures): add coordinated detectors with axis locking`
- `feat(mobile-gestures): integrate with main.js`

## Validation Checklist

- [ ] Swipe right on message shows "Reply" action (≥100px threshold)
- [ ] Swipe from left edge (<40px) triggers browser back (not reply)
- [ ] Long press (500ms) shows context menu on messages
- [ ] Pull down triggers reconnect (only when scrolled to top, ≥80px)
- [ ] Swipe up on input opens fullscreen compose
- [ ] All gestures respect `prefers-reduced-motion`
- [ ] No console errors on touch or mouse devices
- [ ] Works in Chrome DevTools mobile emulation
- [ ] Touch and mouse interactions work without conflicts

## Dependencies

**Already Implemented:**
- `features/context-menu/` - Long-press opens these menus
- `features/offline/connection-monitor.js` - Pull-to-refresh triggers reconnect
- `features/animations/` - Animation utilities and reduced-motion support

**Out of Scope (Future):**
- Pinch-to-zoom (requires image lightbox first)
- Multi-touch gestures (complex, low priority)
- Custom haptic feedback (Vibration API inconsistent support)

## Notes

- Use `touch-action: pan-y` on message list to allow vertical scroll while enabling horizontal swipes
- All touch handlers must call `preventDefault()` only when gesture is confirmed (not on touchstart)
- Test with actual devices when possible - emulators don't perfectly simulate touch behavior
- Safari iOS has specific quirks with touch events and passive listeners

---

## Decision Log

### 2025-03-27: Swipe-to-Reply Architecture

**Decision**: Use dynamic attachment via MutationObserver for swipe detection on messages
- **Context**: `chat-message` elements are dynamically created during streaming and session restore
- **Rationale**: Static initialization at page load misses messages added after init. MutationObserver ensures all messages (present and future) get swipe detection.
- **Implementation**: `SwipeToReply` class manages detector lifecycle, attaching to new messages via `MutationObserver` on `message-list` container
- **Impact**: Requires `SwipeToReply.attachToMessage()` and `SwipeToReply.detachFromMessage()` public methods
- **Owner**: Implementation team

### 2025-03-27: Visual Feedback Strategy

**Decision**: CSS transform-based swipe feedback with CSS custom properties
- **Context**: Need smooth 60fps animation during swipe gesture
- **Rationale**: `transform: translateX()` is GPU-accelerated and aligns with Milestone 6 animation requirements (transform/opacity only)
- **Implementation**: 
  - `--swipe-offset`: pixels dragged (updated in real-time during touchmove)
  - `--swipe-progress`: 0-1 normalized progress (for hint opacity)
  - Transitions disabled during drag (`transition: none`), enabled for snap-back
- **Impact**: All visual state in CSS, JavaScript only updates custom property values
- **Owner**: Implementation team

### 2025-03-27: Swipe Direction Constraint

**Decision**: Right-swipe only for reply, left swipe reserved for future features
- **Context**: Need to decide which swipe directions to support for Phase 2
- **Rationale**: WhatsApp/Signal pattern - right swipe replies, left swipe deletes/archives. Starting with right-only allows adding left later without breaking UX.
- **Implementation**: `SwipeDetector` configured with `direction: 'right'` (or `['right']` for array support)
- **Impact**: Phase 2 scope constrained to right-swipe only
- **Owner**: Implementation team

### 2025-03-27: Reply Content Format

**Decision**: Use markdown blockquote (`> quoted text`) for reply formatting
- **Context**: Need consistent format when populating composer input via swipe-to-reply
- **Rationale**: Blockquote is universally understood markdown, renders correctly in preview, visually distinct from new content
- **Implementation**: Reply callback sets `input.value = > ${content}\n\n` and positions cursor after
- **Impact**: Affects `chat-message.getContent()` API usage and composer input handling
- **Owner**: Implementation team

### 2025-03-27: Composer Integration Pattern

**Decision**: Reply action populates input and focuses, does not auto-send
- **Context**: What happens after successful swipe-to-reply?
- **Rationale**: User should review quoted context and compose response. Auto-send would be surprising and potentially error-prone.
- **Implementation**: 
  1. Populate `textarea.value` with quoted content + newlines
  2. Call `textarea.focus()`
  3. Position cursor at end via `setSelectionRange()`
- **Impact**: Reply gesture is "compose mode" not "quick reply mode". User must explicitly send after reviewing context.
- **Owner**: Implementation team

### 2026-03-27: Gesture Coordination Architecture (Phase 6)

**Decision**: Use Wrapper Pattern for Gesture Coordination
- **Context**: 5 gesture systems (swipe-to-reply, long-press, pull-to-refresh, swipe-up compose, swipe-down close) operate independently and can conflict
- **Rationale**: Wrapper pattern (Option B) adds coordination layer without modifying existing working detectors. Lower risk than invasive changes.
- **Implementation**: Create `CoordinatedSwipeDetector`, `CoordinatedLongPressDetector` wrappers that use central `GestureCoordinator` singleton
- **Impact**: New files `gesture-coordinator.js`, `coordinated-detectors.js`, `test-gesture-coordinator.js`; existing 120 tests remain unchanged
- **Owner**: Implementation team

### 2026-03-27: Axis-Locking Threshold

**Decision**: 15px threshold for horizontal/vertical axis locking
- **Context**: Need to distinguish horizontal swipes (reply) from vertical (pull/compose)
- **Options Considered**: 10px (too sensitive), 20px (requires too much movement)
- **Rationale**: 15px balances responsiveness with accidental trigger prevention. Lock activates when dominant axis > 15px AND dominant > other * 1.5
- **Implementation**: Coordinated detectors calculate deltaX/deltaY; lock to dominant axis once threshold met
- **Impact**: Prevents diagonal gestures from triggering wrong action
- **Owner**: Implementation team

### 2026-03-27: Touch Target Region Definitions

**Decision**: Define clear gesture regions to prevent conflicts
- **Context**: Gestures overlap in screen space (composer vs message list vs page body)
- **Regions Defined**:
  - **Message Items** (`.chat-message`): Swipe-to-reply (right), Long-press
  - **Composer Input** (`#message-input`): Swipe-up fullscreen
  - **Fullscreen Modal** (`.fullscreen-compose`): Swipe-down close
  - **Page Body** (top, scrolled): Pull-to-refresh
  - **Edge Zones** (x<40px, x>width-40px): Browser gestures only
- **Rationale**: Explicit regions prevent ambiguity about which gesture should fire
- **Implementation**: Coordinator uses `element.matches()` to identify regions before granting gesture lock
- **Impact**: Composer swipe-up won't trigger page pull-to-refresh
- **Owner**: Implementation team

### 2026-03-27: Gesture Priority Hierarchy

**Decision**: Priority-based gesture resolution with active exclusivity
- **Context**: Multiple gestures could start simultaneously (e.g., long-press timer running during swipe movement)
- **Priority Map**: Long-press (3) > Fullscreen/Pulldown (2) > Reply/Pull (1)
- **Rationale**: Long-press requires intentional 500ms hold, should win over accidental swipes. Once gesture passes threshold, it owns the touch.
- **Rules**:
  1. Higher priority can preempt lower priority before threshold
  2. Once threshold met, gesture owns touch until `touchend`
  3. Axis lock prevents direction switches after commitment
- **Implementation**: `GestureCoordinator.requestGesture(type, priority)` checks current lock; `releaseGesture()` clears on `touchend`
- **Impact**: Predictable gesture behavior, no "fighting" between detectors
- **Owner**: Implementation team

### 2026-03-27: Coordinated Detector Wrapper Architecture (Phase 6, Step 2)

**Decision**: Request lock immediately on `touchstart` with low priority
- **Context**: When should coordinated detectors request gesture lock from coordinator?
- **Options Considered**:
  - A: On `touchstart` immediately
  - B: After minimal movement (10px) to confirm intent
- **Rationale**: Option A ensures fast response. Low priority (1 for swipe, 3 for long-press) means higher priority gestures can still preempt within first ~50ms if needed.
- **Implementation**: `CoordinatedSwipeDetector` and `CoordinatedLongPressDetector` call `coordinator.requestGesture()` in their `touchstart` handlers
- **Impact**: Gesture coordination begins at touch start, preventing race conditions
- **Owner**: Implementation team

**Decision**: Detector Priorities for Coordinated Wrappers
- **Context**: What priority should each coordinated detector use?
- **Priorities Defined**:
  - `CoordinatedLongPressDetector`: priority 3 (highest - intentional 500ms hold)
  - `CoordinatedSwipeDetector` (reply): priority 1 (standard)
  - Future coordinated pull-to-refresh: priority 1 (standard)
  - Future coordinated fullscreen compose: priority 2 (modal overlay)
- **Rationale**: Matches the priority hierarchy defined earlier. Long-press requires most intentional user action.
- **Implementation**: Each wrapper class hardcodes its priority constant, passed to `requestGesture(type, priority)`
- **Impact**: Consistent priority behavior across all coordinated detectors
- **Owner**: Implementation team

**Decision**: Wrapped Detector Lifecycle Management
- **Context**: How to manage the underlying detector's lifecycle within the wrapper?
- **Approach**:
  1. Create wrapped detector in constructor (but don't attach)
  2. On `touchstart` + lock granted, manually trigger wrapped detector's touch handling
  3. On `touchend`/`touchcancel`, release lock and let wrapped detector complete normally
  4. `destroy()` releases any active lock and destroys wrapped detector
- **Rationale**: Allows wrapper to intercept events for coordination while delegating actual gesture logic to tested detectors
- **Implementation**: Store wrapped detector instance, proxy events when lock granted, clean up on destroy
- **Impact**: Existing detectors remain unchanged; wrappers add coordination layer
- **Owner**: Implementation team

**Decision**: Passive Listener Compatibility
- **Context**: Wrapped detectors use `{ passive: true }` for scroll performance
- **Solution**: Coordination check happens in wrapper's non-passive handler first, then delegates to wrapped detector's passive handler if lock granted
- **Rationale**: Must maintain passive listeners for performance while still being able to prevent gesture if lock denied
- **Implementation**: Wrapper attaches non-passive listener for coordination, wrapped detector attaches its own passive listeners
- **Impact**: No performance regression; coordination works correctly
- **Owner**: Implementation team

### 2026-03-27: Axis Locking Architecture (Phase 6, Step 3)

**Decision**: Track touch origin in detector (not coordinator)
- **Context**: Where should the touch start position (startX, startY) be stored for delta calculations?
- **Options Considered**:
  - A: Store in detector instance (this.startX/Y)
  - B: Store in coordinator gesture info
- **Rationale**: Option A keeps each detector isolated and responsible for its own tracking. Coordinator should only manage locks, not gesture-specific state.
- **Implementation**: Each coordinated detector stores `this.startX` and `this.startY` in `touchstart`, calculates deltas in `touchmove`
- **Impact**: Cleaner separation of concerns; coordinator remains gesture-agnostic
- **Owner**: Implementation team

**Decision**: 15px Threshold with 1.5x Dominance Ratio
- **Context**: When should axis lock trigger to distinguish horizontal from vertical gestures?
- **Formula**:
  - Horizontal lock: `|deltaX| > 15 && |deltaX| > |deltaY| * 1.5`
  - Vertical lock: `|deltaY| > 15 && |deltaY| > |deltaX| * 1.5`
- **Rationale**: 15px minimum prevents accidental locks on tiny movements. 1.5x ratio ensures clear dominance (e.g., 20px X vs 10px Y = horizontal, but 20px X vs 15px Y = neutral).
- **Implementation**: `axisLock` property set to 'horizontal', 'vertical', or null in `touchmove` handler
- **Impact**: Predictable gesture recognition; diagonal swipes stay neutral until dominance is clear
- **Owner**: Implementation team

**Decision**: Lock Persistence Until touchend
- **Context**: Should axis lock be released if user reverses direction?
- **Rationale**: Once committed to a gesture direction, switching mid-gesture would be confusing. Lock persists until `touchend`/`touchcancel`.
- **Implementation**: `axisLock` cleared in `_releaseLock()` alongside gesture coordinator lock
- **Impact**: Consistent gesture behavior throughout touch lifecycle
- **Owner**: Implementation team

**Decision**: Modify coordinated-detectors.js only (no new files)
- **Context**: Where should axis locking logic live?
- **Rationale**: Axis locking is core to coordinated detector behavior. Adding to existing file keeps related logic together.
- **Implementation**: Add `axisLock`, `startX`, `startY` properties and axis check logic to both `CoordinatedSwipeDetector` and `CoordinatedLongPressDetector`
- **Impact**: Minimal file changes; tests added to existing `test-coordinated-detectors.js`
- **Owner**: Implementation team

### 2025-03-27: Open Questions (Phase 2)

**Question**: Should swipe be disabled when message actions are visible (`.active` class)?
- **Options**: 
  - A: Yes - swipe disabled when menu open to prevent conflict
  - B: No - swipe always active, menu click takes precedence
- **Recommendation**: Option A - check `messageElement.classList.contains('active')` before starting swipe
- **Status**: Pending implementation decision

**Question**: Multi-select swipe or single message only?
- **Options**:
  - A: Single only - swipe one message at a time
  - B: Multi-select - long-swipe enters multi-select mode
- **Recommendation**: Option A for Phase 2, defer multi-select to future enhancement
- **Status**: Scope decision needed

---

**Last Updated**: 2026-03-27
**Updated By**: Design review session (Phase 6 detailed planning)
