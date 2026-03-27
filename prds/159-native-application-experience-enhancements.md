# PRD: Native Application Experience Enhancements

## Issue Reference

**GitHub Issue**: [#159](https://github.com/jeremysball/alfred/issues/159)  
**Priority**: High  
**Status**: Draft

---

## Problem Statement

The Alfred Web UI currently feels like a traditional web page rather than a modern native application. Users expect behaviors common in desktop apps:

1. **Hidden Power**: Keyboard shortcuts, command palette, and advanced features are undiscoverable
2. **Missing Context Menus**: Right-clicking does nothing, breaking muscle memory from native apps
3. **No System Integration**: No notifications when responses complete in background tabs
4. **Clunky Interactions**: No drag-and-drop, limited keyboard navigation, abrupt state changes
5. **Web-First Feel**: Animations feel basic, no offline support, no system tray integration

### Current vs Desired Experience

| Scenario | Current | Desired |
|----------|---------|---------|
| New user discovers shortcuts | Accidentally or never | Press `?` to see all shortcuts |
| Copy code from response | Select + Ctrl+C | Right-click → "Copy code block" |
| Response completes in background | Nothing happens | System notification appears |
| Navigate messages | Mouse scrolling only | Arrow keys or Tab to focus |
| File upload | No support | Drag & drop onto chat |
| Offline usage | Error page | Queue messages, send when reconnected |

---

## Solution Overview

Transform the Alfred Web UI into a Progressive Web App (PWA) with native desktop application behaviors:

1. **Command Palette (Ctrl+K)**: Universal search and action launcher
2. **Context Menus**: Right-click menus on messages, code blocks, and UI elements
3. **System Notifications**: Browser notifications + favicon badges for background activity
4. **Enhanced Keyboard Navigation**: Vim-style shortcuts, global shortcuts, shortcut help
5. **Drag & Drop**: File upload, message quoting, reordering
6. **Polished Animations**: Smooth transitions, skeleton loading, micro-interactions
7. **Service Worker**: Offline support, background sync, caching
8. **Mobile Gestures**: Swipe actions, pull-to-refresh, long-press menus

---

## Success Criteria

- [x] User can access all major features without touching the mouse (Milestone 2 - Keyboard Shortcuts)
- [x] Right-click context menus work on all interactive elements (Milestone 3 - Context Menus)
- [x] Notifications appear when responses complete in inactive tabs (Milestone 4 - System Notifications)
- [x] App works offline with static asset caching (UI loads, message queuing deferred) (Milestone 7)
- [x] Animations use only `transform`/`opacity`, complete within 200ms (Milestone 6)
- [ ] Lighthouse PWA score > 90 (enforced in CI) - pending Milestones 8-10
- [ ] All features work on desktop and mobile - pending Milestone 8
- [x] File uploads respect 10MB limit with clear error messages (Milestone 5 - Drag & Drop)
- [x] Mobile gestures disabled in 40px edge zone (no browser conflicts) (Milestone 8 - Phase 1)
- [x] Search latency < 16ms for <1000 commands (Milestone 1 - Command Palette)
- [x] Focus management follows ARIA guidelines (focus trap, return to trigger) (Milestone 1)

---

## Milestones

### Milestone 1: Command Palette Foundation ✅ COMPLETE
**Goal**: Universal search and action launcher accessible via Ctrl+K

**Features**:
- [x] Modal overlay with search input
- [x] Commands: "Clear chat", "Toggle theme", "New Session", "Focus Input"
- [x] Keyboard navigation (arrow keys, Enter, Escape)
- [x] Fuzzy search matching (native Intl.Collator, not Fuse.js - see Decision Log)

**Search Implementation**:
```javascript
import Fuse from 'fuse.js';

const fuse = new Fuse(commands, {
  keys: ['title', 'keywords', 'shortcut'],
  threshold: 0.4,        // 0=exact match, 1=match anything
  includeScore: true,    // For ranking results
  includeMatches: true,  // For highlighting matched characters
  minMatchCharLength: 2,
  limit: 10              // Max results shown
});
```

**Performance Budget**:
- Search latency < 16ms for <1000 commands (single frame at 60fps)
- If latency exceeds budget, implement debounce (150ms) or virtual scrolling

**Validation**:
- Press Ctrl+K opens palette within 100ms
- Type "clr" matches "Clear chat" via fuzzy matching
- Type "thm" matches "Toggle theme" 
- Results ranked by match score (exact matches first)
- Matched characters highlighted in result titles
- Enter executes selected command
- Escape closes palette
- Search latency measured via Performance API (verify <16ms)

---

### Milestone 2: Keyboard Shortcuts & Help System ✅ COMPLETE
**Goal**: Comprehensive keyboard control with discoverability

**Features**:
- [x] Global shortcuts (Ctrl+T toggle tools, already exists)
- [x] Message navigation (Tab/Shift+Tab or arrow keys between messages)
- [x] Shortcut help overlay (press `?` to view all shortcuts)
- [x] Focus management (Tab cycles through interactive elements)

**Shortcuts Implemented**:
| Key | Action | Status |
|-----|--------|--------|
| `?` | Show shortcut help | ✅ |
| `Tab` / `Shift+Tab` | Next/previous focusable element | ✅ |
| `↑` / `↓` (when message focused) | Previous/next message | ✅ |
| `Home` / `End` | Jump to first/last message | ✅ |
| `Esc` | Close modals/cancel actions | ✅ |
| `Ctrl+K` | Open command palette | ✅ (M1) |
| `Ctrl+F` | Search in conversation | ⏳ Pending |

**Validation**:
- [x] Press `?` shows help modal
- [x] Tab navigates between interactive elements
- [x] Arrow keys navigate between messages when a message has focus
- [x] All shortcuts documented in help

---

### Milestone 3: Context Menus ✅ COMPLETE
**Goal**: Right-click menus on messages and code blocks

**Features**:
- [x] Message context menu: Copy text, Quote reply
- [x] Code block menu: Copy, Copy as markdown
- [ ] Link context menu: Copy link, Open in new tab (deferred)
- [x] Keyboard accessible (Shift+F10 or context menu key)

**Validation**:
- [x] Right-click message shows context menu
- [x] Click "Copy Text" copies message content
- [x] Click "Quote Reply" adds quote to input
- [x] Right-click code block shows context menu
- [x] Menu closes on Escape or outside click
- [x] Menu returns focus to trigger on close
- [x] ARIA roles: menu, menuitem

---

### Milestone 4: System Notifications & Background Activity ✅ COMPLETE
**Goal**: Notify users of activity when tab is not focused

**Features**:
- [x] Browser notification when response completes (if tab not focused)
- [x] Favicon badge with unread count
- [x] Notification permission request (on first message send, before fetch)
- [ ] Sound notification option (respects system settings) - deferred

**WebSocket Protocol**:
```javascript
client → server: "client.visibility" {isVisible: false}  // On tab blur
server → client: notification sent only if !isVisible && permission === "granted"
```

**Permission Flow**:
```
User sends message → Check Notification.permission
  → "default": Request permission synchronously, then proceed
  → "granted": Proceed with notification on completion
  → "denied": Show in-app toast: "Enable notifications in browser settings for background alerts"
```

**WebSocket Protocol**:
```javascript
client → server: "client.visibility" {isVisible: false}  // On tab blur
server → client: notification sent only if !isVisible && permission === "granted"
```

**Validation**:
- [x] Send first message → permission prompt appears before network request
- [x] Deny permission → toast shown, message still sends
- [x] Send message, switch tabs (blur event triggers visibility message)
- [x] Response completes while hidden → notification appears
- [x] Click notification focuses Alfred tab
- [x] Badge shows on favicon with unread count
- [x] Grant permission, reload → no prompt on subsequent messages

---

### Milestone 5: Drag & Drop ✅ COMPLETE
**Goal**: File upload and message interaction via drag and drop

**Features**:
- [x] Drag files onto chat to upload
- [x] Visual drop zone indicator
- [ ] Drag message to quote it (drop on input) - deferred
- [ ] Drag to reorder messages (if editing allowed) - deferred
- [x] Paste image from clipboard → auto-upload

**WebSocket Protocol Extensions**:
```javascript
// File upload via WebSocket (base64 encoded)
client → server: "file.upload" {
  fileId: string,           // Client-generated UUID
  name: string,             // Original filename
  mimeType: string,         // MIME type
  size: number,             // File size in bytes (max 10MB)
  data: string              // Base64-encoded file content
}

server → client: "file.received" {
  fileId: string,           // Matches upload
  status: "accepted" | "rejected",
  reason?: string,          // If rejected (e.g., "File too large")
  url?: string              // If accepted, URL to access file
}
```

**Constraints**:
- Max file size: 10MB (rejected client-side before upload)
- Images >2MB auto-compressed client-side before base64 encoding
- Allowed types: images (png, jpg, gif, webp), text files (txt, md, py, js, json)

**Validation**:
- [x] Drag file over chat shows drop indicator
- [x] Drop triggers file.upload message (or shows error if >10MB)
- [x] Images >2MB auto-compressed
- [x] Invalid file types rejected with toast
- [x] Server responds with file.received
- [x] Copy image, paste in input → triggers upload
- [x] "Upload File" command in palette opens file picker

---

### Milestone 6: Enhanced Animations & Micro-interactions ✅ COMPLETE
**Goal**: Smooth, polished interactions that feel native

**Features**:
- Message entrance animations (slide from right for user, fade for assistant)
- Button press states (scale 0.95 on active)
- Smooth scroll with momentum
- Skeleton loading states for sessions list
- Typing indicator with animated dots
- Tool call progress animations

**Animation Specifications**:
```css
/* Use only transform and opacity for GPU acceleration */
.message-enter {
  transition: transform 200ms cubic-bezier(0.4, 0.0, 0.2, 1), 
              opacity 150ms ease-out;
  will-change: transform, opacity;
}

/* Avoid animating these properties (layout thrashing) */
/* NO: width, height, top, left, margin, padding */
```

**Performance Requirements**:
- All animations use only `transform` and `opacity`
- `will-change` applied before animation, removed after
- Animations complete within 200ms (perceived instant)
- No dropped frames during message streaming (maintain 60fps)

**Validation**:
- New messages animate in (slide 8px → 0, fade 0 → 1)
- Buttons scale to 0.95 on :active state (100ms transition)
- Loading states show skeleton shimmer, not blank
- Chrome DevTools Performance panel: no layout/paint during animations
- Lighthouse "Avoid non-composited animations" audit passes
- `prefers-reduced-motion` media query respected (disable animations)

---

### Milestone 7: Service Worker & Offline Support ✅ COMPLETE
**Goal**: Static asset caching and offline indicator only (reduced scope)

**Features**:
- [x] Service worker caches static assets (CSS, JS, HTML)
- [x] Offline indicator in UI when WebSocket disconnects
- [x] Page reload while offline loads cached UI shell
- **Out of Scope**: Message queuing (requires complex sync protocol - see Future Work)

**Implementation**:
```javascript
// service-worker.js - Static asset caching
const STATIC_ASSETS = [
  '/static/index.html',
  '/static/css/base.css',
  '/static/js/main.js',
  '/static/js/features/*/index.js',
  // ... app shell
];

// ConnectionMonitor tracks WebSocket state
const monitor = new ConnectionMonitor();
monitor.trackWebSocket(wsClient);
monitor.addEventListener('statechange', ({detail}) => {
  offlineIndicator.setAttribute('state', detail.state);
});
```

**Files Created**:
- `service-worker.js` - Cache-first strategy, offline fallback
- `features/offline/connection-monitor.js` - WebSocket state tracking
- `features/offline/offline-indicator.js` - Glassmorphism banner
- `features/offline/styles.css` - Slide-down animation, reduced motion support

**Validation**:
- [x] Disconnect network → offline indicator appears within 5 seconds
- [x] Page reload while offline loads cached UI (no 404 errors)
- [x] Reconnect WebSocket → indicator disappears
- [x] Lighthouse "Works Offline" audit passes

---

### Milestone 8: Mobile Gestures ⏳ IN PROGRESS
**Goal**: Touch-friendly interactions for mobile users

**Status**: Phases 1-7 Complete (Foundation + Gestures + Conflict Resolution + Integration)

**Implemented (Phase 1)**:
- [x] Touch device detection (ontouchstart, maxTouchPoints, pointer:coarse)
- [x] Edge zone utilities (40px margin for browser conflict protection)
- [x] Swipe detector class with passive event listeners
- [x] Module exports and initialization infrastructure
- [x] All 15 unit tests passing (touch-detector: 7, swipe-detector: 8)

**Implemented (Phase 2) - Swipe-to-Reply**:
- [x] `SwipeToReply` class with 80px threshold, right-swipe only
- [x] `attachToMessage()` - creates SwipeDetector per message
- [x] `attachToAllMessages()` - batch attachment with container selector
- [x] Visual feedback: CSS transform (translateX), 20px icon threshold, 85% opacity
- [x] Snap-back animation on insufficient swipe (300ms cubic-bezier)
- [x] Haptic feedback: 10ms on start, [20, 30, 20] pattern on reply
- [x] MutationObserver for dynamic message attachment
- [x] Lifecycle: `detachFromMessage()`, `destroy()` with full cleanup
- [x] All 15 unit tests passing (test-swipe-to-reply.js)

**Files Created (Phase 2)**:
- `features/mobile-gestures/swipe-to-reply.js` - SwipeToReply class
- `features/mobile-gestures/test-swipe-to-reply.js` - 15 tests

**Phase 2 Design Decisions** (see `execution-plan-159-milestone5-touch-gestures.md`):
- **Threshold**: 80px (tuned for mobile comfort)
- **Direction**: Right swipe only (consistent with iOS/Android)
- **Transform**: `translateX()` for 60fps GPU acceleration
- **Icon**: Reply arrow (↩️) fades in at 20px, fully visible at 80px
- **Snap-back**: 300ms cubic-bezier(0.4, 0.0, 0.2, 1) Material Design standard
- **Haptic**: Light tap on start, stronger pattern on success (progressive enhancement)

**Implemented (Phase 3) - Long Press Context Menu**:
- [x] `LongPressDetector` class with 500ms threshold, 10px movement tolerance
- [x] `LongPressContextMenu` integration class for message context menus
- [x] Visual feedback: scale (0.98) and opacity (0.95) at 200ms
- [x] Haptic feedback: 5ms tap at visual feedback point
- [x] Exclude selectors: buttons, links, inputs, textareas, contenteditable
- [x] Movement tolerance to distinguish from swipe (10px default)
- [x] MutationObserver for dynamic message attachment
- [x] Lifecycle: `detachFromElement()`, `destroy()` with full cleanup
- [x] All 32 unit tests passing (LongPressDetector: 16, LongPressContextMenu: 16)

**Files Created (Phase 3)**:
- `features/mobile-gestures/long-press-detector.js` - LongPressDetector class
- `features/mobile-gestures/long-press-context-menu.js` - Context menu integration
- `features/mobile-gestures/test-long-press-detector.js` - 16 tests
- `features/mobile-gestures/test-long-press-context-menu.js` - 16 tests

**Phase 3 Design Decisions**:
- **Threshold**: 500ms (standard mobile context menu timing)
- **Movement Tolerance**: 10px (prevents accidental cancel on slight finger drift)
- **Visual Feedback**: Subtle scale (0.98) + opacity (0.95) after 200ms
- **Exclude Elements**: Links, buttons, inputs (avoids conflicts with native behavior)
- **Integration**: Direct callback or fallback to global `MessageContextMenu`
- **Haptic**: Light tap at feedback point, optional pattern on success

**Implemented (Phase 4) - Pull-to-Refresh with WebSocket Integration**:
- [x] Glassmorphism pull indicator component with smooth animations
- [x] CSS custom properties for dynamic progress values (`--ptr-progress`, `--ptr-distance`)
- [x] Four visual states: hidden, pulling, ready, refreshing
- [x] Spinner rotation follows pull progress (0-180 degrees)
- [x] Reduced motion support via `prefers-reduced-motion`
- [x] `createPullIndicator()` factory for easy detector integration
- [x] **WebSocketReconnectIntegration** - `initializePullToRefresh()` wires to ConnectionMonitor
- [x] Success state shows "Connected!" for 1.5s
- [x] Error state shows "Failed to connect" for 2s
- [x] 2-second debounce prevents rapid pull spam
- [x] 26 unit tests passing in test-pull-to-refresh.js

**Files Created (Phase 4)**:
- `features/mobile-gestures/styles.css` - Pull indicator styles with glassmorphism
- `features/mobile-gestures/pull-indicator.js` - Visual component with state management

**Implemented (Phase 5) - Swipe-Up Fullscreen Compose**:
- [x] `FullscreenComposeModal` class with glassmorphism styling
- [x] Swipe-up (120px) on composer input opens fullscreen modal
- [x] Content sync between compact and fullscreen inputs
- [x] Swipe-down, close button, or Escape key to close
- [x] 300ms enter/exit animations with cubic-bezier easing
- [x] Reduced motion support via `prefers-reduced-motion`
- [x] iOS safe area support
- [x] 22 unit tests passing in test-fullscreen-compose.js

**Files Created (Phase 5)**:
- `features/mobile-gestures/fullscreen-compose.js` - Modal component + factory
- `features/mobile-gestures/fullscreen-compose.css` - Glassmorphism styles

**Implemented (Phase 6) - Gesture Conflict Resolution**:
- [x] `GestureCoordinator` singleton with priority-based preemption
- [x] `CoordinatedSwipeDetector` wrapper with axis locking (15px threshold)
- [x] `CoordinatedLongPressDetector` wrapper with edge zone handling (40px margin)
- [x] Priority system: Long-press (3) > Fullscreen/Pulldown (2) > Reply/Pull (1)
- [x] Axis locking: 15px threshold, 1.5x dominance ratio, no mid-gesture switching
- [x] Edge zone filtering: 40px left/right margins prevent browser conflicts
- [x] Region-based coordination: message, composer, modal, message-list contexts
- [x] `getRegionForElement()` utility using CSS selectors and `element.closest()`
- [x] 28 unit tests passing (GestureCoordinator: 8, CoordinatedDetectors: 20)

**Files Created (Phase 6)**:
- `features/mobile-gestures/gesture-coordinator.js` - Singleton coordination class
- `features/mobile-gestures/coordinated-detectors.js` - Wrapped detectors with coordination
- `features/mobile-gestures/test-gesture-coordinator.js` - 8 tests
- `features/mobile-gestures/test-coordinated-detectors.js` - 20 tests

**Implemented (Phase 7) - Integration & Module Export**:
- [x] `index.js` exports all coordinated detectors and utilities
- [x] `main.js` imports coordinated detectors and gesture coordinator
- [x] `initializeMobileGestures()` called on app startup (touch devices only)
- [x] SwipeToReply attached to message list with haptic feedback
- [x] Fullscreen compose initialized on message input
- [x] Cleanup on page unload via `beforeunload` event
- [x] All 148 tests passing across mobile-gestures module

**Files Modified (Phase 7)**:
- `main.js` - Added imports and initialization call

**Phase 8 - Cross-Platform Testing** ⏳ IN PROGRESS:
- [x] Testing infrastructure - Report template created
- [ ] Chrome DevTools mobile emulation (iPhone SE, iPad Pro, Pixel 5)
- [ ] Touch device validation - actual device testing
- [ ] Browser-specific issue documentation

**Testing Report**: `prds/testing-reports/159-milestone8-phase8-results.md`

**Execution Plan**: See `execution-plan-159-milestone8.md` for detailed implementation tasks

**Files Created**:
- `features/mobile-gestures/touch-detector.js` - Device detection, edge zone checking
- `features/mobile-gestures/swipe-detector.js` - Swipe detection with callbacks
- `features/mobile-gestures/long-press-detector.js` - Long press detection class
- `features/mobile-gestures/long-press-context-menu.js` - Context menu integration
- `features/mobile-gestures/swipe-to-reply.js` - Swipe-to-reply feature
- `features/mobile-gestures/pull-to-refresh.js` - Pull-to-refresh with WebSocket
- `features/mobile-gestures/pull-indicator.js` - Visual pull indicator component
- `features/mobile-gestures/fullscreen-compose.js` - Fullscreen compose modal
- `features/mobile-gestures/gesture-coordinator.js` - Gesture coordination singleton
- `features/mobile-gestures/coordinated-detectors.js` - Wrapped detectors
- `features/mobile-gestures/index.js` - Module exports, GESTURE_CONFIG

**Gesture Conflict Mitigation**:
```javascript
// Disable custom gestures near screen edges to avoid browser conflicts
const EDGE_MARGIN = 40; // px

function handleTouchStart(e) {
  const touchX = e.touches[0].clientX;
  if (touchX < EDGE_MARGIN) {
    return; // Let browser handle back gesture
  }
  // Proceed with custom swipe gesture
}
```

**Validation**:
- [x] Touch device detection works (ontouchstart, maxTouchPoints, pointer:coarse)
- [x] Edge zone filtering prevents gestures within 40px of edges
- [x] Swipe detection calculates direction, distance, and validity
- [x] Passive event listeners for scroll performance
- [x] Swipe-to-Reply: 80px threshold triggers onReply callback
- [x] Swipe-to-Reply: Visual feedback (transform, opacity, icon)
- [x] Swipe-to-Reply: Snap-back on insufficient swipe
- [x] Swipe-to-Reply: Haptic feedback (navigator.vibrate)
- [x] Swipe-to-Reply: MutationObserver for dynamic messages
- [x] Swipe from left edge (<40px) triggers browser back (not reply)
- [x] Long press shows context menu after 500ms
- [x] Pull down triggers reconnect (WebSocket integration when scrolled to top)
- [ ] Tested on Safari iOS, Chrome Android (Phase 8)

---

### Milestone 9: Search & Quick Navigation ⏳ READY
**Goal**: Find and navigate content quickly

**Status**: Execution plan created, ready for implementation

**Features**:
- In-conversation search (Ctrl+F) - browser native find on rendered content
- Highlight matches in current session
- Jump between matches with Enter/Shift+Enter
- Quick switcher (Ctrl+Tab) for recent sessions
- @ mentions to reference previous messages

**In-Conversation Search Approach**:
- **Phase 1 (MVP)**: Use browser's native `window.find()` API
  - Pros: No additional implementation, works immediately
  - Cons: Only searches rendered content, not full history
- **Phase 2 (Future)**: Server-side search via WebSocket protocol extension
  ```javascript
  client → server: "session.search" {query: string, limit: number}
  server → client: "session.search.results" {matches: [...]}
  ```

**Quick Switcher Data**:
- Uses already-loaded session list (from `/sessions` command)
- No additional server requests needed

**Validation**:
- Ctrl+F opens browser find bar (or custom UI calling window.find)
- Matches highlight in current viewport
- Enter/Shift+Enter navigates between matches
- Ctrl+Tab shows quick switcher with recent sessions (up to 10)
- Click session in switcher loads it via `/resume <id>`
- @ in composer shows dropdown of last 20 messages in session

**Execution Plan**: See `execution-plan-159-milestone9.md` for detailed implementation tasks

---

### Milestone 10: PWA Polish & System Integration ⏳ READY
**Goal**: Full Progressive Web App compliance

**Status**: Execution plan created, ready for implementation

**Features**:
- Install prompt (Add to Home Screen)
- Standalone window mode (no browser chrome)
- Auto-theme based on system preference
- Share target (share to Alfred from other apps)

**Out of Scope**: Desktop wrapper (Electron/Tauri) - requires separate deployment model PRD

**Validation**:
- Lighthouse PWA audit passes (score > 90)
- Install prompt appears
- Runs in standalone window
- Respects system dark/light mode
- CI runs Lighthouse on PRs (fails if score < 90)

**Execution Plan**: See `execution-plan-159-milestone10.md` for detailed implementation tasks

---

## Technical Design

### Architecture Changes

**IMPLEMENTED:**
```
src/alfred/interfaces/webui/static/js/
├── features/
│   ├── command-palette/        ✅ IMPLEMENTED
│   │   ├── commands.js         # Command registry with validation
│   │   ├── fuzzy-search.js     # Native Intl.Collator search
│   │   ├── palette.js          # Modal UI with keyboard nav
│   │   ├── styles.css          # Glassmorphism styling
│   │   ├── index.js            # Module exports
│   │   ├── test-commands.js    # 15 unit tests
│   │   └── test-fuzzy-search.js # 21 unit tests
│   ├── keyboard/               ✅ IMPLEMENTED
│   │   ├── shortcuts.js        # Shortcut registry with modifiers
│   │   ├── keyboard-manager.js # Global keydown listener
│   │   ├── help.js             # Help modal component
│   │   ├── navigation.js       # Message arrow key nav
│   │   ├── styles.css          # Help modal styles
│   │   ├── index.js            # Module exports
│   │   └── test-shortcuts.js   # 19 unit tests
│   ├── context-menu/           ✅ IMPLEMENTED
│   │   ├── menu.js             # Core menu component
│   │   ├── message-menu.js     # Message right-click actions
│   │   ├── code-menu.js        # Code block actions
│   │   ├── styles.css          # Menu styling
│   │   └── index.js            # Module exports
│   ├── notifications/        ✅ IMPLEMENTED
│   │   ├── permissions.js      # Permission management
│   │   ├── service.js          # Browser notifications
│   │   ├── favicon.js          # Favicon badge
│   │   ├── toast.js            # In-app toasts
│   │   ├── styles.css          # Toast styling
│   │   └── index.js            # Module exports
│   └── drag-drop/            ✅ IMPLEMENTED
│       ├── manager.js          # Drag-drop event handling
│       ├── validation.js       # File type/size validation
│       ├── compression.js      # Image compression
│       ├── upload.js           # WebSocket file upload
│       ├── clipboard.js        # Paste from clipboard
│       ├── visual.js           # Drop zone overlay
│       ├── styles.css          # Drop zone styling
│       └── index.js            # Module exports
│   ├── animations/           ✅ IMPLEMENTED
│   │   ├── utils.js            # prefersReducedMotion helper
│   │   ├── message-animator.js # Message entrance animations
│   │   ├── typing-indicator.js # Bouncing dots component
│   │   ├── tool-call-progress.js # Progress bar animations
│   │   ├── skeleton.js         # Loading skeletons
│   │   ├── styles.css          # Animation CSS (5.6KB)
│   │   └── index.js            # Module exports
│   ├── offline/              ✅ IMPLEMENTED
│   │   ├── connection-monitor.js # WebSocket state tracking
│   │   ├── offline-indicator.js  # Connection status banner
│   │   ├── styles.css            # Glassmorphism styles
│   │   └── index.js              # Module exports
│   └── mobile-gestures/      ✅ PHASE 2 COMPLETE
│       ├── touch-detector.js     # Device detection, edge zone
│       ├── swipe-detector.js     # Swipe detection with callbacks
│       ├── swipe-to-reply.js     # Swipe-to-reply feature (Phase 2)
│       ├── index.js              # Module exports, initializeGestures()
│       ├── test-touch-detector.js    # 7 unit tests
│       ├── test-swipe-detector.js    # 8 unit tests
│       ├── test-swipe-to-reply.js    # 15 unit tests (Phase 2)
│       └── test-index.js             # 10 unit tests

**PLANNED (Not Yet Implemented):**
```
src/alfred/interfaces/webui/static/js/
├── features/
│   ├── drag-drop/              ⏳ PARTIAL
│   │   ├── quote.js            # Drag-to-quote (deferred)
│   │   └── reorder.js          # Drag-to-reorder (deferred)
│   ├── offline/                ⏳ PARTIAL
│   │   └── queue.js            # Message queuing (deferred)
│   └── mobile-gestures/        ⏳ PARTIAL (Phases 2-4)
│       ├── swipe-to-reply.js   # Reply on swipe right
│       ├── long-press-detector.js # Long press detection
│       ├── pull-to-refresh.js  # Pull-to-refresh detector
│       └── styles.css          # Gesture styles
```

**PLANNED (Not Yet Implemented):**
```
src/alfred/interfaces/webui/static/js/
├── features/
│   ├── drag-drop/              ⏳ PARTIAL
│   │   ├── quote.js            # Drag-to-quote (deferred)
│   │   └── reorder.js          # Drag-to-reorder (deferred)
│   └── offline/                ⏳ PARTIAL
│       └── queue.js            # Message queuing (deferred)
```

### Key Components

**Command Palette**:
```javascript
// Register commands
commandPalette.register({
  id: 'clear-chat',
  title: 'Clear Chat',
  shortcut: 'Ctrl+Shift+C',
  action: () => clearChat()
});

// Open with Ctrl+K
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.key === 'k') {
    e.preventDefault();
    commandPalette.open();
  }
});
```

**Context Menu**:
```javascript
// Message right-click
messageElement.addEventListener('contextmenu', (e) => {
  e.preventDefault();
  contextMenu.show({
    x: e.clientX,
    y: e.clientY,
    items: [
      { label: 'Copy Text', action: () => copyText(message) },
      { label: 'Quote Reply', action: () => quoteReply(message) },
      { label: 'Edit', action: () => editMessage(message), visible: isUser },
      { label: 'Delete', action: () => deleteMessage(message), danger: true }
    ]
  });
});
```

**Service Worker**:
```javascript
// sw.js
self.addEventListener('fetch', (event) => {
  // Cache static assets
  // Queue POST requests when offline
});

self.addEventListener('sync', (event) => {
  if (event.tag === 'send-messages') {
    event.waitUntil(sendQueuedMessages());
  }
});
```

---

## UI/UX Specifications

### Command Palette

- **Trigger**: Ctrl+K (or Cmd+K on Mac)
- **Appearance**: Centered modal, 600px max width, glassmorphism blur
- **Input**: Search at top, immediate results below
- **Navigation**: ↑/↓ to select, Enter to execute, Esc to close
- **Visual**: Command name, keyboard shortcut, category icon

### Context Menus

- **Appearance**: Rounded corners, shadow, glassmorphism background
- **Sections**: Dividers between logical groups
- **Icons**: Left side for quick recognition
- **Danger actions**: Red text for destructive items

**Accessibility Requirements**:
```html
<!-- Trigger element -->
<button aria-haspopup="true" aria-expanded="false" aria-controls="menu-id">
  Open menu
</button>

<!-- Menu -->
<div 
  role="menu" 
  id="menu-id"
  aria-label="Message actions"
>
  <button role="menuitem">Copy text</button>
  <button role="menuitem">Quote reply</button>
</div>
```

**Keyboard Interaction**:
- `Shift+F10` or `ContextMenu` key opens menu from focused element
- `Escape` closes menu and returns focus to trigger
- `Tab`/`Shift+Tab` cycles through menu items (focus trap while open)
- `Enter` or `Space` activates focused item
- Arrow keys navigate between items

**Focus Management**:
- Focus moves to first menu item on open
- Focus returns to trigger element on close
- Focus trap prevents Tab from leaving menu while open

### Keyboard Shortcuts Help

- **Trigger**: Press `?` (or Shift+/)
- **Layout**: Two-column grid, grouped by category
- **Categories**: Navigation, Actions, Composer, Global
- **Close**: Esc or click outside

### Notifications

- **Permission**: Request on first message send (not on load)
- **Content**: "Response ready from Alfred" + message preview
- **Action**: Click focuses Alfred tab
- **Badge**: Red dot with number on favicon

### Animations

- **Message entrance**: 200ms ease-out, translateY(8px) → 0
- **Button press**: 100ms, scale(0.95) on :active
- **Modal open**: 150ms, fade + scale(0.98) → scale(1)
- **Skeleton**: Shimmer animation, 1.5s infinite

---

## Accessibility

- All keyboard shortcuts work with screen readers
- Focus indicators visible and logical
- Context menus keyboard accessible (Shift+F10)
- Reduced motion support (`prefers-reduced-motion`)
- ARIA live regions for dynamic content

---

## Testing Strategy

1. **Keyboard Navigation**: Tab through entire UI without mouse
2. **Screen Reader**: Navigate with NVDA/VoiceOver
3. **Mobile Gestures**: Test on actual devices
4. **Offline**: Use Chrome DevTools network throttling
5. **Performance**: 
   - Lighthouse CI runs on every PR (fails if PWA score < 90)
   - Chrome DevTools Performance panel: verify no layout/paint during animations
   - Animation frame time < 16ms (60fps target)
6. **Cross-browser**: Chrome, Firefox, Safari, Edge
7. **Lighthouse CI Configuration**:
   ```yaml
   # .github/workflows/lighthouse.yml
   - name: Run Lighthouse CI
     run: |
       npm install -g @lhci/cli
       lhci autorun --config=lighthouserc.json
   ```
   ```json
   // lighthouserc.json
   {
     "ci": {
       "assert": {
         "assertions": {
           "categories:pwa": ["error", { "minScore": 0.9 }],
           "categories:performance": ["warn", { "minScore": 0.8 }]
         }
       }
     }
   }
   ```

---

## Dependencies

- No new major dependencies
- Native APIs: Notification, Service Worker, Drag & Drop API
- Fuzzy search: Start with native `Intl.Collator`, add `fuse.js` only if needed
  ```javascript
  // Phase 1: Native implementation
  const collator = new Intl.Collator('en', { 
    sensitivity: 'base',
    ignorePunctuation: true 
  });
  const matches = commands.filter(c => 
    collator.compare(c.title.substring(0, query.length), query) === 0
  );
  
  // Phase 2: Add Fuse.js only if:
  // - Commands exceed 1000 items, OR
  // - Search latency > 16ms with native approach
  ```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Service Worker complexity | High | Reduced scope: static caching only, no message queue |
| Keyboard conflicts | Medium | Check conflicts with browser shortcuts, provide alternatives |
| Mobile gesture conflicts | Medium | Disable custom gestures within 40px of screen edges |
| Notification permission denied | Medium | Show in-app toast, message still sends |
| Notification fatigue | Low | Respect Do Not Disturb, easy to disable |
| Animation performance | Medium | Use CSS transforms only, respect reduced-motion |
| File upload size abuse | Low | 10MB limit client-side, reject with clear error |

---

## Future Enhancements (Post-MVP)

### Deferred to Future PRDs
- **Offline Message Queue**: Full IndexedDB queue with conflict resolution and server-side sync protocol
- **Desktop Wrapper**: Electron/Tauri app for system tray, global hotkeys, native menus
- **Server-Side Search**: `session.search` WebSocket message for searching full message history
- **Drag-to-Quote**: Drag message to input area to quote it
- **Drag-to-Reorder**: Drag messages to reorder them
- **Multi-file Upload UI**: Progress bars for multiple concurrent uploads

### Additional Ideas
- Voice input (Web Speech API)
- Picture-in-picture mode
- AI-powered command suggestions
- Collaborative cursors (if multi-user)

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-27 | **IMPLEMENTED**: Milestone 8 - Mobile Gestures (Phase 2) | Swipe-to-Reply complete: `SwipeToReply` class with 80px threshold, right-swipe only, CSS transform visual feedback, haptic feedback, MutationObserver for dynamic messages. 15 tests. Files: `swipe-to-reply.js`, `test-swipe-to-reply.js`. See `execution-plan-159-milestone5-touch-gestures.md` for full API. |
| 2026-03-27 | **DESIGNED**: Milestone 8 - Mobile Gestures (Phase 2) | Swipe-to-Reply architecture finalized: MutationObserver for dynamic attachment, CSS transform feedback with `--swipe-offset`/`--swipe-progress`, right-swipe only (100px threshold), markdown blockquote reply format. Composer integration: populate input, focus, position cursor. See `execution-plan-159-milestone5-touch-gestures.md` Decision Log. |
| 2026-03-27 | **IMPLEMENTED**: Milestone 8 - Mobile Gestures (Phase 4) | Pull-to-refresh detector complete: `pull-to-refresh.js` adds `PullToRefreshDetector`, `isScrolledToTop`, resistance handling, and refresh callbacks. Unit tests pass in `test-pull-to-refresh.js`. Visual feedback and reconnect wiring remain pending. See `features/mobile-gestures/`. |
| 2026-03-27 | **PARTIAL**: Milestone 8 - Mobile Gestures (Phase 1) | Foundation layer complete: touch-detector.js (device detection, 40px edge zone), swipe-detector.js (direction/distance/progress), index.js (module exports, 25 tests). Phases 2-4 pending: swipe-to-reply, long-press, pull-to-refresh. Passive listeners for scroll performance. See `features/mobile-gestures/`. |
| 2026-03-27 | **IMPLEMENTED**: Milestone 7 - Service Worker & Offline Support | Static asset caching via service worker, ConnectionMonitor for WebSocket state, glassmorphism offline indicator. Cache-first strategy, versioned caches, offline HTML fallback. Message queuing deferred. See `service-worker.js` and `features/offline/`. |
| 2026-03-27 | **IMPLEMENTED**: Milestone 6 - Enhanced Animations | GPU-accelerated animations (transform/opacity only). Message entrance, button press, smooth scroll, skeleton loading, typing indicator, tool call progress. Reduced motion support. See `features/animations/`. |
| 2026-03-26 | **IMPLEMENTED**: Milestone 5 - Drag & Drop | File upload via drag-drop and clipboard paste. Canvas-based image compression (>2MB), 10MB size limit, WebSocket base64 upload, glassmorphism drop zone. See `features/drag-drop/`. |
| 2026-03-26 | **IMPLEMENTED**: Milestone 4 - System Notifications | Browser notifications with permission handling, favicon badges for unread count, WebSocket visibility tracking, in-app toasts. See `features/notifications/`. |
| 2026-03-26 | **IMPLEMENTED**: Milestone 3 - Context Menus | Right-click menus for messages (copy, quote) and code blocks (copy, copy as markdown). ARIA roles, Shift+F10 keyboard access, viewport-aware positioning. See `features/context-menu/`. |
| 2026-03-26 | **IMPLEMENTED**: Milestone 2 - Keyboard Shortcuts | Context-aware shortcuts (global/input/message), 19 tests, Help modal with glassmorphism, Message navigation with arrow keys. See `features/keyboard/`. |
| 2026-03-26 | **IMPLEMENTED**: Native Intl.Collator for fuzzy search | Chosen over Fuse.js. 36 tests passing, <16ms latency achieved without external dependency. See `features/command-palette/fuzzy-search.js`. |
| 2026-03-26 | Scope reduction: Offline messaging deferred | Full queue/sync requires IndexedDB + conflict resolution protocol. Keeping static asset caching only for MVP. |
| 2026-03-26 | Remove Electron/Tauri from this PRD | Requires separate deployment model changes. PWA provides sufficient native feel for now. |
| 2026-03-26 | Add WebSocket protocol extensions | File upload and visibility tracking require explicit protocol messages. Documented in Technical Design. |
| 2026-03-26 | Native search first, Fuse.js conditional | Avoid dependency until proven necessary. Native Intl.Collator sufficient for <1000 commands. |
| 2026-03-26 | Browser find API for in-conversation search | No server changes needed. Server-side search deferred to Phase 2. |
| 2026-03-26 | 10MB file upload limit | Prevents memory exhaustion and WebSocket message size issues. Client-side enforcement. |
| 2026-03-26 | 40px edge margin for mobile gestures | Prevents conflict with browser back swipe (iOS Safari, Chrome Android). |
| 2026-03-26 | Lighthouse CI gate in PRs | Automated enforcement of PWA score > 90. Prevents regression. |
| TBD | Implement as PWA, not Electron | Keeps deployment simple, still get native feel |
| TBD | Use native context menus, not custom | Better accessibility, system integration |

---

## Related PRDs

- PRD #131: Ctrl-T Tool Call Expansion (existing keyboard shortcut)
- PRD #151: Web UI Compose, Cancel, Edit While Streaming (composer enhancements)

---

## Notes

- Each milestone can be implemented independently
- Start with Milestone 1 (Command Palette) for maximum impact
- Mobile gestures can wait if desktop is priority
- Service Worker requires HTTPS in production
