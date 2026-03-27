# Execution Plan: Milestone 8 - Mobile Gestures

**PRD**: [#159 - Native Application Experience Enhancements](../159-native-application-experience-enhancements.md)  
**Scope**: Touch-friendly interactions for mobile users

---

## Overview

Implement mobile gesture support including swipe-to-reply, long-press context menus, pull-to-refresh, and swipe-up fullscreen compose. Follows the patterns established in existing features (command-palette, drag-drop, etc.).

---

## Phase 1: Touch Detection & Utilities

### TouchCapabilities

- [ ] Test: `test_detects_touch_device()` - verify touch detection works
- [ ] Test: `test_detects_mouse_device()` - verify mouse detection works
- [ ] Implement: Create `touch-detector.js` with `isTouchDevice()` helper
- [ ] Run: `node src/alfred/interfaces/webui/static/js/features/mobile-gestures/test-touch-detector.js`

### EdgeZoneDetection

- [ ] Test: `test_edge_zone_40px_left()` - verify touch at x=39px is in edge zone
- [ ] Test: `test_edge_zone_40px_right()` - verify touch at width-39px is in edge zone
- [ ] Test: `test_not_edge_zone_at_50px()` - verify touch at x=50px is NOT in edge zone
- [ ] Implement: `isInEdgeZone(touchX, screenWidth, edgeMargin = 40)` function
- [ ] Run: Verify tests pass

---

## Phase 2: Swipe-to-Reply Gesture

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

- [ ] Test: `test_swipe_detector_initializes()` - verify class instantiation
- [ ] Test: `test_swipe_threshold_100px()` - verify 100px minimum swipe distance
- [ ] Test: `test_horizontal_swipe_detected()` - verify horizontal swipe recognized
- [ ] Test: `test_vertical_swipe_ignored()` - verify vertical swipes don't trigger horizontal handler
- [ ] Implement: Create `swipe-detector.js` with SwipeDetector class
- [ ] Run: `node src/alfred/interfaces/webui/static/js/features/mobile-gestures/test-swipe-detector.js`

### SwipeToReply Module

- [ ] Test: `test_swipe_to_reply_module_exports()` - verify SwipeToReply class exported
- [ ] Test: `test_attach_to_message_creates_detector()` - verify attachment creates SwipeDetector instance
- [ ] Test: `test_detach_removes_detector()` - verify cleanup removes listeners
- [ ] Implement: Create `swipe-to-reply.js` with SwipeToReply class
- [ ] Implement: Dynamic attachment via MutationObserver on message-list
- [ ] Run: `node src/alfred/interfaces/webui/static/js/features/mobile-gestures/test-swipe-to-reply.js`

### SwipeRightOnMessage

- [ ] Test: `test_swipe_right_triggers_reply()` - verify right swipe on message calls reply callback
- [ ] Test: `test_swipe_left_does_nothing()` - verify left swipe is ignored
- [ ] Test: `test_swipe_in_edge_zone_ignored()` - verify swipe from left edge (<40px) doesn't trigger
- [ ] Test: `test_reply_callback_receives_message_element()` - verify callback gets correct element
- [ ] Implement: `onReply` callback extracts message content and populates composer input
- [ ] Implement: Callback uses `messageElement.getContent()` API from chat-message component
- [ ] Run: Manual test in browser DevTools mobile view

### SwipeVisualFeedback

- [ ] Test: `test_swipe_under_threshold_snaps_back()` - verify <100px swipe snaps back (300ms ease-out)
- [ ] Test: `test_swipe_over_threshold_completes()` - verify ≥100px swipe triggers reply action
- [ ] Test: `test_reply_hint_opacity_progress()` - verify hint opacity follows swipe progress (0% at 0px, 100% at 100px)
- [ ] Implement: CSS `--swipe-offset` custom property bound to touch position
- [ ] Implement: Reply hint SVG icon with `opacity: var(--swipe-progress, 0)`
- [ ] Implement: Snap-back animation uses `cubic-bezier(0.4, 0.0, 0.2, 1)` (Material Design standard)
- [ ] Run: Visual verification in browser, verify 60fps in Chrome DevTools Performance panel

### Composer Input Integration

- [ ] Test: `test_reply_populates_input()` - verify input value set to `> content\n\n`
- [ ] Test: `test_reply_focuses_input()` - verify composer textarea receives focus
- [ ] Test: `test_reply_caret_position()` - verify cursor at end of quoted text
- [ ] Implement: Reply callback queries `#message-input` and sets value
- [ ] Implement: Call `textarea.focus()` and `setSelectionRange()` to position cursor
- [ ] Run: End-to-end test - swipe message → input populated → ready to type response

---

## Phase 3: Long-Press Context Menu

### LongPressDetector

- [ ] Test: `test_long_press_500ms_threshold()` - verify 500ms press triggers
- [ ] Test: `test_short_press_ignored()` - verify <500ms press is ignored
- [ ] Test: `test_touch_move_cancels_long_press()` - verify movement cancels long press
- [ ] Test: `test_long_press_on_message()` - verify correct target element captured
- [ ] Implement: Create `long-press-detector.js` with LongPressDetector class
- [ ] Run: `node src/alfred/interfaces/webui/static/js/features/mobile-gestures/test-long-press.js`

### LongPressContextMenuIntegration

- [ ] Test: `test_long_press_opens_context_menu()` - verify long press opens existing menu
- [ ] Test: `test_context_menu_shows_at_touch_position()` - verify correct positioning
- [ ] Test: `test_touch_end_closes_menu()` - verify touch elsewhere closes menu
- [ ] Implement: Integrate with existing `features/context-menu/` system
- [ ] Implement: Position menu at touch coordinates (not mouse coordinates)
- [ ] Run: Manual test on message elements

### LongPressVisualFeedback

- [ ] Test: `test_long_press_shows_ripple()` - verify visual feedback during press
- [ ] Test: `test_ripple_centers_on_touch()` - verify ripple position matches touch
- [ ] Implement: CSS ripple effect (scale animation)
- [ ] Implement: Prevent default touch actions during long press detection
- [ ] Run: Visual verification in browser

---

## Phase 4: Pull-to-Refresh

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

- [ ] Test: `test_pull_triggers_websocket_reconnect()` - verify ConnectionMonitor.reconnect() called
- [ ] Test: `test_reconnect_success_hides_indicator()` - verify indicator hidden on success
- [ ] Test: `test_reconnect_failure_shows_error()` - verify error toast on failure
- [ ] Implement: Wire PullToRefresh to existing ConnectionMonitor
- [ ] Run: Integration test with offline/online toggle

---

## Phase 5: Swipe-Up Fullscreen Compose

### SwipeUpDetector

- [ ] Test: `test_swipe_up_threshold_120px()` - verify 120px upward swipe threshold
- [ ] Test: `test_swipe_up_on_input_area()` - verify detection on composer input
- [ ] Test: `test_horizontal_swipe_ignored_for_fullscreen()` - verify horizontal doesn't trigger
- [ ] Implement: Extend SwipeDetector with vertical swipe support
- [ ] Run: Verify tests pass

### FullscreenComposeModal

- [ ] Test: `test_swipe_up_opens_fullscreen()` - verify fullscreen modal opens
- [ ] Test: `test_fullscreen_contains_composer()` - verify textarea is focused
- [ ] Test: `test_swipe_down_closes_fullscreen()` - verify reverse gesture closes
- [ ] Implement: Create `fullscreen-compose.js` modal component
- [ ] Implement: Transfer input content between compact and fullscreen views
- [ ] Run: Manual test on mobile viewport

### FullscreenVisualDesign

- [ ] Test: `test_fullscreen_animation_300ms()` - verify smooth transition
- [ ] Test: `test_fullscreen_respects_reduced_motion()` - verify prefers-reduced-motion support
- [ ] Implement: CSS animations for modal enter/exit
- [ ] Implement: Glassmorphism background consistent with other modals
- [ ] Run: Visual verification, check animation performance in DevTools

---

## Phase 6: Gesture Conflict Resolution

### EdgeZoneHandling

- [ ] Test: `test_left_edge_swipe_passes_through()` - verify browser back gesture works
- [ ] Test: `test_right_edge_swipe_passes_through()` - verify browser forward gesture works
- [ ] Implement: Ensure all gesture detectors check edge zone before handling
- [ ] Run: Manual test on Safari iOS (if available) or Chrome DevTools mobile emulation

### MultiGestureCoordination

- [ ] Test: `test_swipe_and_long_press_dont_conflict()` - verify both work independently
- [ ] Test: `test_pull_and_swipe_up_dont_conflict()` - verify different regions work separately
- [ ] Implement: Gesture priority system (long-press takes precedence over swipe)
- [ ] Run: Verify all gestures work together without conflicts

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
├── gesture-coordinator.js        # Manages multiple gesture handlers
├── styles.css                    # All gesture-related styles
├── test-touch-detector.js        # Unit tests
├── test-swipe-detector.js        # Unit tests
├── test-long-press.js            # Unit tests
├── test-pull-to-refresh.js       # Unit tests
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
- `feat(mobile-gestures): add edge zone conflict resolution`
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

**Last Updated**: 2025-03-27
**Updated By**: Design review session (Phase 2 detailed planning)
