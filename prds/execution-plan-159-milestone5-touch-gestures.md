# Execution Plan: PRD #159 Milestone 5 - Touch Gesture Support (Phase 2)

## Overview
Implement Swipe-to-Reply feature for mobile touch interactions in Alfred Web UI.

## Phase 1: Foundation ✅ COMPLETE
**Goal**: Core touch detection infrastructure

### Task 1.1: Touch Detector Utility ✅
- [x] Test: `isTouchDevice()` detects touch capability
- [x] Implement: Check touch APIs, maxTouchPoints, coarse pointer
- [x] Test: `isInEdgeZone()` protects browser edge gestures
- [x] Implement: Left/right edge detection (40px margin)
- [x] Test: `shouldHandleTouch()` filters excluded elements
- [x] Implement: Input, textarea, contenteditable exclusion
- [x] Run: Verify detection on mobile vs desktop

### Task 1.2: Swipe Detector ✅
- [x] Test: SwipeDetector initializes with defaults
- [x] Implement: Constructor with options (threshold, direction, edgeMargin)
- [x] Test: Horizontal swipe detected
- [x] Implement: touchstart/touchmove/touchend handlers
- [x] Test: Threshold filtering (100px default)
- [x] Implement: Distance calculation and validity check
- [x] Test: Edge zone filtering
- [x] Implement: 40px edge margin protection
- [x] Run: Browser testing with touch device

**Files created**:
- `touch-detector.js` - Touch capability detection utilities
- `swipe-detector.js` - Swipe gesture detection class
- `test-touch-detector.js` - 6 tests
- `test-swipe-detector.js` - 8 tests

---

## Phase 2: Swipe-to-Reply ✅ COMPLETE
**Goal**: Message swipe triggers reply composer

### Task 2.1: SwipeToReply Module ✅
- [x] Test: SwipeToReply class exports correctly
- [x] Implement: Class with configurable options
- [x] Test: Initialize with default options (threshold: 80px, direction: right)
- [x] Implement: Constructor with sensible defaults
- [x] Test: Accept custom threshold, direction, callbacks
- [x] Implement: Options merging
- [x] Test: `attachToMessage()` creates SwipeDetector instance
- [x] Implement: Create detector with callbacks
- [x] Test: Returns false for invalid element
- [x] Implement: Element validation
- [x] Run: Test attachment to DOM elements

**Design Decisions**:
- **Threshold**: 80px (tuned for mobile comfort - less than default 100px)
- **Direction**: Right swipe only (consistent with iOS/Android conventions)
- **Edge Margin**: 0px on messages (edge protection at SwipeDetector level)

### Task 2.2: Visual Feedback ✅
- [x] Test: `applyVisualFeedback()` sets transform styles
- [x] Implement: translateX() for GPU-accelerated movement
- [x] Test: Swipe progress calculation (0-1 ratio)
- [x] Implement: Progress based on threshold
- [x] Test: Reply icon appears at 20px threshold
- [x] Implement: Dynamic icon creation and fade-in
- [x] Test: Opacity fades to 85% during swipe
- [x] Implement: Subtle opacity transition
- [x] Run: Visual test on mobile device

**Design Decisions**:
- **Transform**: Use `translateX()` instead of `left` for 60fps performance
- **Icon Threshold**: 20px (early feedback before full threshold)
- **Max Movement**: Capped at 120px (prevents excessive sliding)
- **Opacity**: Subtle fade (15%) keeps context visible

### Task 2.3: Reply Activation & Snap-Back ✅
- [x] Test: Swipe above 80px triggers reply
- [x] Implement: Threshold check in onSwipeEnd
- [x] Test: `onReply(messageId)` callback fires
- [x] Implement: Invoke callback with message ID
- [x] Test: Swipe below threshold snaps back
- [x] Implement: CSS transition for smooth return
- [x] Test: Visual state resets after snap
- [x] Implement: Reset transform, opacity, remove icon
- [x] Run: Full swipe-to-reply flow test

**Design Decisions**:
- **Threshold**: 80px (sweet spot for intentional vs accidental)
- **Snap Animation**: 300ms cubic-bezier(0.4, 0.0, 0.2, 1) (Material Design standard)
- **Cleanup**: Remove DOM elements after animation completes

### Task 2.4: Haptic Feedback ✅
- [x] Test: Haptic triggers when enabled
- [x] Implement: navigator.vibrate(10ms) on swipe start
- [x] Test: Haptic skipped when disabled
- [x] Implement: enableHaptic option check
- [x] Test: Reply success has stronger haptic pattern
- [x] Implement: [20, 30, 20] pattern for confirmation
- [x] Run: Device testing (Android with vibration API)

**Design Decisions**:
- **Default**: Enabled (progressive enhancement)
- **Start Feedback**: Light 10ms tap (acknowledges touch)
- **Success Feedback**: Pattern [20, 30, 20] (intentional feel)
- **Fallback**: Silent if navigator.vibrate unavailable

### Task 2.5: MutationObserver for Dynamic Messages ✅
- [x] Test: `attachToAllMessages()` counts attachments
- [x] Implement: Query and attach to all [data-message-id] elements
- [x] Test: MutationObserver created on init
- [x] Implement: observer.observe() with childList, subtree
- [x] Test: New messages auto-attach
- [x] Implement: Handle addedNodes in mutations
- [x] Test: Nested message elements detected
- [x] Implement: Recursively check added subtrees
- [x] Run: Test with real-time chat simulation

**Design Decisions**:
- **Observer Config**: childList + subtree (catches all insertions)
- **Selector**: `[data-message-id]` (project convention)
- **Auto-cleanup**: Old detectors destroyed on re-attachment

### Task 2.6: Cleanup & Lifecycle ✅
- [x] Test: `detachFromMessage()` removes detector
- [x] Implement: Destroy detector and remove from Map
- [x] Test: `destroy()` cleans up all detectors
- [x] Implement: Iterate and destroy all
- [x] Test: MutationObserver disconnected on destroy
- [x] Implement: observer.disconnect()
- [x] Test: Visual state reset on cleanup
- [x] Implement: Reset styles, remove icons
- [x] Run: Memory leak check

**Design Decisions**:
- **Storage**: Map with messageId keys (O(1) lookup)
- **Cleanup Order**: Disconnect observer before destroying detectors
- **Memory**: Remove all references to allow GC

---

## Files Created

### Implementation
- `swipe-to-reply.js` - SwipeToReply class with full feature set

### Tests
- `test-swipe-to-reply.js` - 15 comprehensive tests

---

## API Documentation

### SwipeToReply Constructor Options
```javascript
{
  threshold: 80,           // px to trigger reply
  direction: 'right',      // 'right' (only direction supported)
  onReply: (messageId) => {},  // Callback when swipe triggers
  enableHaptic: true,      // Enable vibration feedback
  enableVisualFeedback: true  // Enable visual movement
}
```

### Methods
```javascript
attachToMessage(element, messageId) → boolean
attachToAllMessages(container, selector='[data-message-id]') → number
detachFromMessage(messageId)
destroy()
```

### Usage Example
```javascript
const swipeReply = new SwipeToReply({
  threshold: 80,
  onReply: (messageId) => {
    composer.quoteMessage(messageId);
  }
});

// Attach to existing messages
swipeReply.attachToAllMessages(document.querySelector('.message-container'));
```

---

## Validation Checklist ✅
- [x] Swipe right on message → visual feedback starts
- [x] Swipe past 20px → reply icon fades in
- [x] Swipe past 80px → haptic feedback + reply triggered
- [x] Swipe under 80px → smooth snap-back animation
- [x] New messages auto-attach via MutationObserver
- [x] Haptic feedback on supported devices
- [x] No visual feedback on excluded elements (inputs)
- [x] All animations use transform/opacity only
- [x] Memory cleanup works correctly

---

## Next Phase
**Phase 3**: Visual Polish - Reply icon styling, animation refinement, dark mode support
