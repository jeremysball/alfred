# Execution Plan: PRD #159 Milestone 6 - Enhanced Animations & Micro-interactions

## Overview
Add smooth, polished animations and micro-interactions to the Alfred Web UI to create a native app feel. All animations must use GPU-accelerated properties (transform, opacity) and respect `prefers-reduced-motion`.

---

## Phase 1: Message Entrance Animations

### AnimationCSS

- [x] Test: Verify `message-enter` CSS class exists with transform/opacity transitions
- [x] Implement: Add CSS `.message-enter` with `transform: translateY(8px) → 0`, `opacity: 0 → 1`
- [x] Run: `grep -E 'message-enter|translateY.*8px' src/alfred/interfaces/webui/static/js/features/animations/styles.css`

### AnimationJavaScript

- [x] Test: `test_message_enters_with_animation()` - verify animation class is applied to new messages
- [x] Implement: Add animation.js with `MessageAnimator.animateEntrance(element, type)` method
- [x] Run: Open browser console, run `new MessageAnimator().animateEntrance(el, 'user')` and check for animation class

### UserVsAssistant

- [x] Test: Verify user messages slide from right, assistant messages fade in
- [x] Implement: Add `.message-enter--user` (translateX) and `.message-enter--assistant` (opacity only) variants
- [x] Run: Send test messages, verify user slides from right (8px), assistant fades in

### WillChangeManagement

- [x] Test: Verify `will-change` is applied before animation and removed after
- [x] Implement: Add `will-change: transform, opacity` on animation start, remove on `transitionend`
- [x] Run: Chrome DevTools → Elements → Styles, verify will-change appears then disappears after animation

---

## Phase 2: Button Press Micro-interactions

### ButtonActiveState

- [x] Test: Verify button scales to 0.95 on :active state
- [x] Implement: Add CSS `button:active { transform: scale(0.95); transition: transform 100ms ease }`
- [x] Run: Hold click on send button, verify scale via Chrome DevTools computed styles

### AllInteractiveElements

- [x] Test: Verify all buttons, icon buttons, and links have press feedback
- [x] Implement: Apply `.btn-press` class or global selector to all interactive elements
- [x] Run: Click all buttons in UI (send, stop, settings, theme switcher), verify visual feedback

---

## Phase 3: Smooth Scroll with Momentum

### ScrollBehavior

- [x] Test: Verify message list uses `scroll-behavior: smooth`
- [x] Implement: Add CSS `scroll-behavior: smooth` to message list container
- [x] Run: Send message, observe smooth auto-scroll (not instant jump)

### MomentumScroll

- [x] Test: Verify `-webkit-overflow-scrolling: touch` on mobile
- [x] Implement: Add iOS momentum scroll CSS for touch devices
- [x] Run: Test on iOS Safari, verify momentum scrolling feel

---

## Phase 4: Skeleton Loading States

### SkeletonComponent

- [x] Test: `test_skeleton_shows_during_loading()` - verify skeleton element appears during async operations
- [x] Implement: Create Skeleton component with shimmer animation
- [x] Run: Add `Skeleton.show(container)` call, verify shimmer animation in browser

### ShimmerAnimation

- [x] Test: Verify shimmer uses transform (translateX) not background-position
- [x] Implement: CSS shimmer with `transform: translateX(-100%) → translateX(100%)` keyframes
- [x] Run: Chrome DevTools → Performance, record during skeleton display, verify no layout/paint spikes

### SessionListSkeleton

- [x] Test: Verify sessions list shows skeleton while loading
- [x] Implement: Add skeleton state to sessions list initialization
- [x] Run: Hard reload page, verify skeleton appears before sessions load

---

## Phase 5: Typing Indicator

### TypingIndicatorComponent

- [x] Test: `test_typing_indicator_shows_animated_dots()` - verify 3 bouncing dots animation
- [x] Implement: Create TypingIndicator with 3 dots and staggered bounce animation
- [x] Run: Call `TypingIndicator.show()`, verify dots animate in browser

### BounceAnimation

- [x] Test: Verify dots use transform: translateY (not margin/padding)
- [x] Implement: CSS `@keyframes bounce { 0%, 100% { transform: translateY(0) } 50% { transform: translateY(-4px) } }`
- [x] Run: Chrome DevTools → Performance, verify animation uses only compositor thread

### WebSocketIntegration

- [x] Test: Verify typing indicator appears when server sends `typing.start` message
- [x] Implement: Handle `typing.start` and `typing.stop` WebSocket messages
- [x] Run: Trigger typing event from server, verify indicator appears with animation

---

## Phase 6: Tool Call Progress Animations

### ToolCallProgressComponent

- [x] Test: `test_tool_call_shows_progress_animation()` - verify progress bar animates
- [x] Implement: Create ToolCallProgress with animated progress bar
- [x] Run: Trigger tool call, verify progress bar animation

### ProgressBarAnimation

- [x] Test: Verify progress bar uses transform: scaleX (not width)
- [x] Implement: CSS `transform: scaleX(0) → scaleX(1)` for progress, `transform-origin: left`
- [x] Run: Chrome DevTools → Performance, verify no layout thrashing during progress animation

### PulseAnimation

- [x] Test: Verify executing tool call has subtle pulse animation
- [x] Implement: CSS `@keyframes pulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.7 } }`
- [x] Run: Trigger tool call, verify pulsing effect on executing state

---

## Phase 7: Reduced Motion Support

### MediaQuery

- [x] Test: Verify `@media (prefers-reduced-motion: reduce)` disables animations
- [x] Implement: Add CSS media query that sets `transition: none !important` and `animation: none !important`
- [x] Run: macOS Settings → Accessibility → Display → Reduce Motion → ON, reload page, verify no animations

### JavaScriptCheck

- [x] Test: `test_reduced_motion_disables_js_animations()` - verify JS animations respect user preference
- [x] Implement: Add `prefersReducedMotion()` utility, check before running JS animations
- [x] Run: Unit test with `window.matchMedia('(prefers-reduced-motion: reduce)').matches = true`

---

## Phase 8: Performance Validation

### NoLayoutThrashing

- [x] Test: Verify no `width`, `height`, `top`, `left`, `margin`, `padding` animations in CSS
- [x] Implement: Review all animation CSS, replace any layout-triggering properties
- [x] Run: `grep -E 'transition.*(width|height|top|left|margin|padding)' src/alfred/interfaces/webui/static/js/features/animations/styles.css` (returns nothing - only static sizing)

### SixtyFPS

- [x] Test: Verify 60fps during message streaming with Chrome DevTools Performance panel
- [x] Implement: All animations use transform/opacity only (GPU-accelerated)
- [x] Run: Chrome DevTools → Performance → Record, verify frame rate stays at 60fps

### LighthouseAudit

- [x] Test: Run Lighthouse "Avoid non-composited animations" audit, verify passes
- [x] Implement: All animations use compositor-only properties (transform, opacity)
- [x] Run: Chrome DevTools → Lighthouse → Performance → Generate report, check "Avoid non-composited animations"

---

## Files to Modify

1. **New files:**
   - `src/alfred/interfaces/webui/static/js/features/animations/` (new directory)
   - `src/alfred/interfaces/webui/static/js/features/animations/index.js` - Module exports
   - `src/alfred/interfaces/webui/static/js/features/animations/message-animator.js` - Message entrance animations
   - `src/alfred/interfaces/webui/static/js/features/animations/typing-indicator.js` - Typing dots animation
   - `src/alfred/interfaces/webui/static/js/features/animations/tool-call-progress.js` - Tool call progress
   - `src/alfred/interfaces/webui/static/js/features/animations/skeleton.js` - Loading skeletons
   - `src/alfred/interfaces/webui/static/js/features/animations/styles.css` - All animation CSS
   - `src/alfred/interfaces/webui/static/js/features/animations/utils.js` - prefersReducedMotion helper

2. **Modified files:**
   - `src/alfred/interfaces/webui/static/css/base.css` - Add scroll-behavior, button active states
   - `src/alfred/interfaces/webui/static/js/main.js` - Initialize animations, hook into message rendering
   - `src/alfred/interfaces/webui/static/index.html` - Add animation scripts/styles

---

## Commit Strategy

Each checkbox = one atomic commit following conventional commits:

```
feat(animations): add message entrance animations
feat(animations): add button press micro-interactions
feat(animations): implement smooth scroll with momentum
feat(animations): add skeleton loading states with shimmer
feat(animations): add typing indicator with bouncing dots
feat(animations): add tool call progress animations
feat(animations): implement prefers-reduced-motion support
feat(animations): optimize for 60fps performance
```

---

## Validation Checklist

- [x] New messages animate in (slide 8px → 0, fade 0 → 1)
- [x] User messages slide from right, assistant messages fade in
- [x] Buttons scale to 0.95 on :active state (100ms transition)
- [x] Scroll behavior is smooth (not instant jump)
- [x] Skeleton shimmer shows during loading (transform-based)
- [x] Typing indicator shows 3 bouncing dots
- [x] Tool call progress bar animates smoothly
- [x] All animations use only transform and opacity
- [x] `will-change` applied before, removed after animations
- [x] `prefers-reduced-motion` disables all animations
- [x] Chrome DevTools shows 60fps during streaming
- [x] Lighthouse "Avoid non-composited animations" audit passes
