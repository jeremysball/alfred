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
- [x] Lighthouse PWA score > 90 (enforced in CI) - Milestone 10 complete
- [x] All features work on desktop and mobile - Milestone 8 complete
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

### Milestone 8: Mobile Gestures ✅ COMPLETE
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

**Phase 8 - Cross-Platform Testing** ✅ COMPLETE:
- [x] Testing infrastructure - Report template created
- [x] Chrome DevTools mobile emulation (iPhone SE, iPad Pro, Pixel 5)
- [x] Touch device validation - Playwright automated testing
- [x] Browser-specific issue documentation - No issues found

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
- [x] Tested on multiple device profiles via Playwright (Phase 8)

---

### Milestone 9: Search & Quick Navigation ✅ COMPLETE
**Goal**: Find and navigate content quickly

**Status**: All 3 phases complete (Ctrl+F, Ctrl+Tab, @ Mentions)

**Features**:
- In-conversation search (Ctrl+F) - browser native find on rendered content
- Highlight matches in current session
- Jump between matches with Enter/Shift+Enter
- Quick switcher (Ctrl+Tab) for recent sessions
- @ mentions to reference previous messages

**Phase 1: In-Conversation Search (Ctrl+F)** ✅ COMPLETE
- [x] Design: `SearchOverlay` component with singleton pattern
- [x] Design: `window.find()` API for MVP (visible messages only)
- [x] Design: Case-insensitive search, "N of M" match counter
- [x] Design: Glassmorphism UI (consistent with Command Palette)
- [x] Implement: Search overlay component (`search-overlay.js`)
- [x] Implement: Module exports and initialization (`index.js`)
- [x] Implement: Match navigation (Enter/Shift+Enter)
- [x] Implement: Match counter display ("N of M" format)
- [x] Implement: Glassmorphism styles (`styles.css`)
- [x] Test: 10 unit tests (all passing in `test-search-overlay.js`)
- [x] Integrate: CSS import added to `index.html`
- [x] Integrate: `initSearch()` added to `main.js` initialization

**Files Created**:
- `features/search/search-overlay.js` - SearchOverlay class (263 lines)
- `features/search/test-search-overlay.js` - 10 unit tests
- `features/search/styles.css` - Glassmorphism styling
- `features/search/index.js` - Module exports

**Files Modified**:
- `index.html` - Added search styles.css link
- `main.js` - Added initSearch() function and initialization call

**Usage**: Press `Ctrl+F` to open search overlay in Alfred

**Design Decisions**:
- **API Strategy**: `window.find()` for MVP, server-side search deferred to Phase 2
- **Search Scope**: Visible/rendered messages only (DOM-based)
- **Case Sensitivity**: Case-insensitive for better UX
- **Architecture**: Component-based with event-driven pattern
- **Styling**: Glassmorphism design matching Command Palette

**Phase 2: Quick Session Switcher (Ctrl+Tab)** ✅ COMPLETE
- [x] Design: `QuickSwitcher` component with singleton pattern
- [x] Design: localStorage-based session tracking (capture on `/new`, `/resume`)
- [x] Design: Max 10 recent sessions, display name + relative time
- [x] Design: Simple character-matching fuzzy search MVP
- [x] Design: Ctrl+Tab shortcut (avoiding Ctrl+Shift+Tab browser conflict)
- [x] Implement: Quick switcher component (`quick-switcher.js`)
- [x] Implement: Session tracking in localStorage
- [x] Implement: Fuzzy filtering logic
- [x] Implement: Keyboard navigation (arrows, Enter, Escape)
- [x] Implement: `/resume <id>` command integration
- [x] Test: 15 unit tests for QuickSwitcher class
- [x] Integrate: Added to `main.js` initialization

**Files Created**:
- `features/search/quick-switcher.js` - QuickSwitcher class (350 lines)
- `features/search/test-quick-switcher.js` - 15 unit tests

**Files Modified**:
- `features/search/index.js` - Export QuickSwitcher
- `features/search/styles.css` - Quick switcher glassmorphism styles
- `main.js` - Add initQuickSwitcher() call

**Usage**: Press `Ctrl+Tab` to open session switcher, type to filter, arrows to navigate, Enter to select

**Design Decisions**:
- **Session Tracking**: localStorage on every `/new` and `/resume` (self-contained, no backend changes)
- **Max Sessions**: 10 recent (configurable, sufficient for most users)
- **Display Format**: Session name + relative time (e.g., "Project Planning - 2h ago")
- **Fuzzy Search**: Simple character-matching MVP (can upgrade to scoring later)
- **Shortcut**: Ctrl+Tab (Ctrl+Shift+Tab reserved for browser backward navigation)

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

**Phase 1 Validation**:
- Ctrl+F opens search overlay (not browser find)
- Matches highlight in current viewport
- Enter/Shift+Enter navigates between matches
- Match counter shows "3 of 12" format
- Escape closes search overlay

**Phase 3: @ Mentions** ✅ COMPLETE
- [x] Design: `MentionDropdown` component with singleton pattern
- [x] Design: DOM-based message extraction (scans .message elements)
- [x] Design: Fuzzy search filtering for message text
- [x] Design: Max 20 messages, format: `@author: "excerpt..."`
- [x] Implement: Mention dropdown component (`mention-dropdown.js`)
- [x] Implement: Message extraction from DOM
- [x] Implement: Fuzzy filtering with query after @
- [x] Implement: Keyboard navigation (↑↓, Enter, Escape, Tab)
- [x] Implement: Mention insertion at cursor position
- [x] Test: 11 unit tests for MentionDropdown class
- [x] Integrate: Added to `main.js` initialization

**Files Created**:
- `features/search/mention-dropdown.js` - MentionDropdown class (380 lines)
- `features/search/test-mention-dropdown.js` - 11 unit tests

**Files Modified**:
- `features/search/index.js` - Export MentionDropdown
- `features/search/styles.css` - Mention dropdown glassmorphism styles
- `main.js` - Add initMentions() call

**Usage**: Type `@` in composer to open mention dropdown, type to filter, arrows to navigate, Enter to insert

**Design Decisions**:
- **Message Source**: DOM scan of `.message` elements (no backend changes)
- **Max Messages**: 20 recent messages (sufficient for context)
- **Mention Format**: `@author: "excerpt..."` (clear and compact)
- **Trigger**: `@` character in composer (standard convention)
- **Position**: Below composer input (follows cursor)

**Phase 1 Validation**:
- Ctrl+F opens search overlay (not browser find)
- Matches highlight in current viewport
- Enter/Shift+Enter navigates between matches
- Match counter shows "3 of 12" format
- Escape closes search overlay

**Phase 2 Validation**:
- Ctrl+Tab opens quick switcher modal
- Shows up to 10 recent sessions
- Session name + relative time displayed
- Type to filter sessions (fuzzy search)
- Arrow keys navigate up/down
- Enter selects and loads session via `/resume <id>`
- Escape closes without action

**Phase 3 Validation**:
- Type `@` in composer opens mention dropdown
- Shows up to 20 recent messages
- Displays author name + message excerpt
- Type to filter messages (fuzzy search)
- Arrow keys (↑↓) navigate mentions
- Enter inserts `@author: "excerpt..."` at cursor
- Escape closes dropdown without inserting
- Click on mention item to select

**Execution Plan**: See `execution-plan-159-milestone9.md` for detailed implementation tasks

---

### Milestone 10: PWA Polish & System Integration ✅ COMPLETE
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
- **Leader Mode and Which-Key Refinement**: Keep `Ctrl+S` as the leader prefix, mirror the shortcut registry exactly, and skin the overlay with theme-specific surface tokens. This is an integrity follow-up, not a rollback to legacy direct shortcuts. The prefix binding should live in the registry as `composer.leader`, and leader metadata should be declared on real shortcut entries as path-array node specs.

### Additional Ideas
- Voice input (Web Speech API)
- Picture-in-picture mode
- AI-powered command suggestions
- Collaborative cursors (if multi-user)

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-27 | **DESIGNED**: Leader mode and which-key refinement | Keep `Ctrl+S` as the leader prefix, derive which-key paths from the shortcut registry, enforce a strict mirror, and add theme-specific overlay tokens. The overlay should present registry-derived chord paths with no alternate leader system. |
| 2026-03-27 | **PLANNED**: Leader mode follow-up implementation | Add leader metadata fields to the existing shortcut registry, replace the hardcoded tree in `main.js` with registry-derived bindings, keep `WhichKey` as a pure renderer, and add parity and theme coverage tests. The derived tree should be the single runtime source for both overlay rendering and leader-action execution, with a shared lookup helper instead of ad hoc path matching in `main.js`. Phase 1 is registry-only; runtime consumers move in later phases after the schema and validation are proven. |
| 2026-03-27 | **DECIDED**: WhichKey Phase 2 starts with a derived-tree renderer fixture | Add a unit test that renders `WhichKey` from a local derived-tree fixture before refactoring the component. Keeping the test self-contained and registry-free locks the renderer contract first and prevents `which-key.js` from reclaiming shortcut logic during the follow-up. |
| 2026-03-27 | **DECIDED**: WhichKey follow-up stays test-first and file-local | Add only the new `test-which-key.js` unit test first and leave `which-key.js` untouched until that fixture is in place. This keeps the first Phase 2 slice narrow, makes the expected renderer contract explicit, and preserves the current overlay implementation until the test proves the desired tree shape. |
| 2026-03-27 | **IMPLEMENTED**: WhichKey derived-tree renderer fixture | Added `src/alfred/interfaces/webui/static/js/features/keyboard/test-which-key.js` to prove `WhichKey` renders a plain derived-tree fixture with nested submenu data and no registry imports. The new test locks the Phase 2 renderer contract before any component refactor. |
| 2026-03-27 | **DECIDED**: Preserve leader-mode keybind UX as the canonical keyboard path | Do not revert to legacy direct shortcuts. Keep the `Ctrl+S` leader prefix, but make sure the overlay, help sheet, and runtime handlers stay aligned with the same shortcut registry so displayed bindings always match actual behavior. |
| 2026-03-27 | **DECIDED**: Leader metadata belongs in the existing shortcut registry | Use the current shortcut registry as the single source of truth for leader paths, labels, and grouping metadata instead of introducing a separate leader-map module. This minimizes drift, keeps WhichKey purely presentational, and makes parity tests straightforward. Leader-visible actions must always be registry-backed rather than defined only in `main.js`, and the registry should remain the only place that can declare leader-visible actions. |
| 2026-03-27 | **DECIDED**: Runtime leader navigation consumes the derived tree | `main.js` should use the shared derived tree and lookup helper for leader traversal and leaf execution instead of re-implementing path matching logic. This keeps runtime behavior aligned with the overlay data and reduces drift risk. The helper should own path resolution; `main.js` should only handle mode transitions and action dispatch. |
| 2026-03-27 | **DECIDED**: Registry-derived leader tree | Build the which-key tree and leader runtime resolution from the same registry-backed data so the overlay, help text, and executed actions cannot drift apart. The helper may live alongside the registry, but it must derive from registry data only. |
| 2026-03-27 | **DECIDED**: Derived leader tree refreshes with keymap changes | Recompute the derived leader tree whenever the persisted keymap changes so rebinding stays synchronized across the overlay, help sheet, and runtime traversal. This prevents stale leader state after shortcut edits and keeps the pure tree helper free of lifecycle concerns. |
| 2026-03-27 | **DECIDED**: Leader prefix binding is `Ctrl+S` | Store the leader prefix in the registry as `composer.leader` with `Ctrl+S` so the displayed prefix, runtime handler, and help text all refer to the same binding. Help and overlay formatting should display the same chord path, not alternate aliases. |
| 2026-03-27 | **DECIDED**: Declarative leader metadata schema | Represent leader navigation as declarative metadata on registry entries so the tree can be derived and duplicate paths can be validated before render time. Validation should fail fast on duplicate or conflicting paths before the overlay renders. This schema is the contract for both runtime navigation and which-key rendering. |
| 2026-03-27 | **DECIDED**: Leader metadata uses path-array node specs | Store leader structure as ordered path-array node specs attached to existing shortcut entries rather than introducing separate group/leaf pseudo-entries. This keeps the registry as the only source of truth, makes nested path validation deterministic, and avoids duplicating menu structure outside the shortcuts themselves. |
| 2026-03-27 | **DECIDED**: Phase 1 is registry-only | Start the leader-keybind integrity work by proving the schema and tree validation in `keymap.js` before wiring `main.js`, `WhichKey`, or help-sheet consumers. This isolates the new contract, keeps the first test surface small, and defers runtime changes until the derived data is validated. |
| 2026-03-27 | **IMPLEMENTED**: Leader prefix binding contract | Updated `composer.leader` to `Ctrl+S` and added a focused registry test that verifies the formatter output. This establishes the prefix contract for the leader-mode follow-up; tree derivation and runtime consumers remain pending. |
| 2026-03-27 | **IMPLEMENTED**: Leader tree derivation helper and canonical fixture | Added `buildLeaderTree()` and `getLeaderNodeForPath()` in `keymap.js` with deterministic ordering, internal filtering of non-leader entries, and fail-fast validation, plus canonical fixture coverage in `test-keymap.js`. This proves the derived leader-tree contract in Phase 1; runtime consumers remain pending. |
| 2026-03-27 | **IMPLEMENTED**: Registry-backed leader metadata and canonical help path | Added declarative `leader.path` metadata to the real shortcut registry in `keymap.js`, removed the legacy duplicate help alias, and covered the canonical registry tree in `test-keymap.js`. This makes the leader tree derive from production data instead of fixtures only. |
| 2026-03-27 | **IMPLEMENTED**: Leader helper exports through the keyboard barrel | Re-exported `buildLeaderTree()` and `getLeaderNodeForPath()` from `features/keyboard/index.js` and added them to `window.KeymapManager` so browser consumers share the same public API as the registry module. |
| 2026-03-27 | **DECIDED**: Leader tree builder uses canonical path-array fixtures | Phase 1 tests should use small registry fixtures with canonical `leader.path` arrays to prove tree derivation and conflict detection before any runtime consumer wiring. This keeps the builder contract explicit and lets `buildLeaderTree()` stay pure and deterministic. |
| 2026-03-27 | **DECIDED**: Leader tree builder returns a root-node array | `buildLeaderTree()` should return an ordered array of root nodes, with each node carrying nested `children` and leaf `actionId` metadata. The helper must remain pure data-only in Phase 1, leaving runtime callbacks and consumer wiring for later phases. |
| 2026-03-27 | **DECIDED**: Leader tree validation rejects prefix collisions | The derived tree must fail fast on duplicate full paths, conflicting shared-prefix metadata, and leaf-vs-prefix collisions. This ensures the registry cannot express ambiguous leader paths and keeps the derived model deterministic before render time. |
| 2026-03-27 | **DECIDED**: Leader tree tests use tiny canonical fixtures | Phase 1 tests should use a minimal registry fixture with a few representative `leader.path` arrays so the tree builder contract stays easy to reason about and verify. This keeps the test surface small while still proving nested groups, leaves, and conflict handling. |
| 2026-03-27 | **DECIDED**: Leader tree output is deterministically ordered | `buildLeaderTree()` should sort sibling nodes deterministically, using chord key first and label as a tiebreaker. Stable ordering keeps the derived tree predictable for tests, overlay rendering, and help-sheet parity. |
| 2026-03-27 | **DECIDED**: Leader tree helpers stay pure and explicit | Expose the derived model through `buildLeaderTree(keymap)` and `getLeaderNodeForPath(tree, path)` as pure helpers in `keymap.js`. Keeping the signatures explicit and side-effect free makes the builder easy to test in isolation and preserves a single traversal contract for later consumers. |
| 2026-03-27 | **DECIDED**: Leader tree builder accepts the full keymap object | `buildLeaderTree()` should accept the full keymap registry object and filter leader-visible entries internally instead of requiring prefiltered input. This keeps the public contract simple, lets the helper own its own filtering rules, and avoids splitting the registry contract across multiple call sites. |
| 2026-03-27 | **DECIDED**: Leader tree builder filters leader-visible entries internally | `buildLeaderTree()` should ignore registry entries without `leader.path` and derive the tree only from leader-enabled shortcuts. This keeps the helper responsible for the exact selection logic while preserving a single public input contract. |
| 2026-03-27 | **DECIDED**: Leader tree builder treats `leader.path` as authoritative | The tree builder should derive structure exclusively from `leader.path` arrays and not infer hierarchy from action ids, labels, or categories. This keeps the contract declarative and ensures the registry is the single source of menu truth. |
| 2026-03-27 | **DECIDED**: Leader tree builder uses map-backed insertion | Build the derived tree with a lightweight root map and nested children arrays rather than a dedicated tree class or secondary index. This keeps collision checks local to insertion, avoids extra abstraction, and preserves the pure data-only contract. |
| 2026-03-27 | **DECIDED**: Leader tree lookup remains direct traversal | `getLeaderNodeForPath()` should walk the derived tree directly instead of maintaining a separate lookup cache. The tree is small, so direct traversal keeps the contract simple and avoids duplicate state. |
| 2026-03-27 | **DECIDED**: Leader tree lookup returns null for missing paths | `getLeaderNodeForPath()` should return `null` when any chord in the requested path is missing rather than throwing or synthesizing a partial match. This keeps invalid leader input easy to handle and makes the traversal contract predictable for runtime consumers and tests. |
| 2026-03-27 | **DECIDED**: Leader path segments must be fully specified | Each `leader.path` segment must include non-empty `key`, `label`, and `description` strings so the builder can validate node metadata before insertion. This keeps malformed registry entries and fixtures from producing ambiguous overlay output. |
| 2026-03-27 | **DECIDED**: Phase 1 tests use local registry fixtures | Test the tree builder against a small ad hoc registry fixture instead of `DEFAULT_KEYMAP` so the initial assertions stay deterministic and focused on the derived-tree contract. This keeps Phase 1 tests isolated from unrelated shortcut defaults and makes failures easier to interpret. |
| 2026-03-27 | **DECIDED**: Leader tree tests cover both happy path and conflict cases | Phase 1 should include one canonical derivation test plus dedicated failure tests for duplicate full paths, leaf-vs-prefix collisions, and conflicting prefix metadata. This gives the builder an explicit contract for both valid and invalid registry states before any runtime consumer wiring. |
| 2026-03-27 | **DECIDED**: Leader tree tests should assert traversal lookup | Phase 1 should include a focused `getLeaderNodeForPath()` test alongside the tree derivation test so the shared lookup helper is proven before runtime consumers depend on it. This keeps the traversal contract explicit and avoids introducing a separate behavior surface later. |
| 2026-03-27 | **DECIDED**: Leader tree tests follow a strict test-first order | Implement the leader-tree tests in a deterministic sequence: happy-path derivation first, lookup second, then conflict cases. This keeps the initial failure surface small, makes the builder contract easier to establish incrementally, and preserves a clean test-driven flow. |
| 2026-03-27 | **DECIDED**: Leader tree tests use explicit expected node shapes | The Phase 1 tests should assert the full nested node objects, including labels, descriptions, children, and leaf `actionId` fields. This makes the contract concrete and ensures the builder output stays stable and inspectable. |
| 2026-03-27 | **DECIDED**: Leader tree tests prefer canonical chord fixtures | The fixture should use a small set of representative chord paths with obvious root ordering so the expected tree reads naturally and the sort contract stays visible in the assertions. This keeps the happy-path test easy to scan while still proving nested structure. |
| 2026-03-27 | **DECIDED**: Leader tree tests validate root ordering explicitly | The happy-path test should assert the returned root nodes in their canonical sorted order so deterministic sibling sorting is part of the contract, not an implied implementation detail. This makes regressions in ordering immediately visible. |
| 2026-03-27 | **DECIDED**: Leader tree tests prefer a stable alphabetical root order | The canonical fixture should produce roots in a predictable alphabetical order by chord key so the expected tree is easy to read and the sort contract remains obvious in the assertion. This keeps the happy-path test deterministic and human-scannable. |
| 2026-03-27 | **DECIDED**: Phase 1 stays registry-only and defers runtime consumers | Prove the leader-tree contract in `keymap.js` with local fixture tests before touching `main.js`, `WhichKey`, `help.js`, or broader default keymap migration. This keeps the first patch small, avoids coupling schema validation to runtime behavior, and leaves consumer wiring for later phases after the derived model is trusted. |
| 2026-03-27 | **DECIDED**: Phase 1 uses local fixtures only and defers default registry migration | Keep the initial tree-builder tests anchored to a small ad hoc registry fixture instead of migrating `DEFAULT_KEYMAP` leader entries during the same patch. This keeps the first implementation step easy to verify, limits the blast radius of failures, and lets the leader-tree contract stabilize before default bindings are converted to the new declarative schema. |
| 2026-03-27 | **DECIDED**: Phase 1 keeps a pure data-only tree with explicit traversal lookup | `buildLeaderTree()` should return plain nested node data with `actionId` only on terminal nodes, and `getLeaderNodeForPath()` should traverse the tree directly without a lookup cache. This keeps the initial contract simple, testable, and free of consumer lifecycle concerns. |
| 2026-03-27 | **DECIDED**: Phase 1 validates a deterministic sort contract on the derived tree | The builder should return roots and descendants in a stable order, using chord key first and label as a tiebreaker, so the fixture-based tests can assert exact node shapes without relying on incidental object order. This makes the tree predictable for later rendering and parity checks. |
| 2026-03-27 | **DECIDED**: Phase 1 keeps helper exports local until consumers need them | Expose `buildLeaderTree()` and `getLeaderNodeForPath()` from `keymap.js` for the Phase 1 tests, but defer any additional re-export wiring through `features/keyboard/index.js` until a later consumer actually depends on it. This keeps the first patch minimal and avoids widening the API surface prematurely. |
| 2026-03-27 | **DECIDED**: Phase 1 fixture tests define the acceptance bar | The first implementation patch should be judged by the local fixture-based tree test, traversal lookup, and conflict failures in `test-keymap.js`, not by any runtime consumer behavior. This keeps the acceptance criteria aligned with the deliberately narrow Phase 1 scope. |
| 2026-03-27 | **DECIDED**: Phase 1 validates the `Ctrl+S` leader prefix without migrating runtime consumers | Keep the leader-prefix formatter contract visible in the keymap test suite, but do not couple that check to the new tree helpers or any `main.js` / overlay changes in the same patch. This preserves the prefix contract while keeping the first implementation slice isolated. |
| 2026-03-27 | **DECIDED**: Phase 1 implementation stays confined to `keymap.js` and its direct tests | Implement the leader tree helpers and fixture tests only inside the keyboard keymap module during Phase 1. This keeps the patch tightly scoped, avoids premature consumer wiring, and makes the first acceptance gate easy to validate. |
| 2026-03-27 | **DECIDED**: Phase 1 tree builder uses plain data nodes with recursive sorting | Model the derived leader tree as plain nested objects rather than a custom tree class, and sort each sibling list recursively by chord key with label as a tiebreaker. This keeps the helper easy to inspect, deterministic for tests, and lightweight for future consumers. |
| 2026-03-27 | **IMPLEMENTED**: Milestone 9 Phase 3 - @ Mentions | MentionDropdown implementation complete: singleton pattern, DOM-based message extraction (scans `.message` elements), fuzzy search filtering, max 20 messages. Keyboard navigation (↑↓ arrows, Enter, Escape, Tab). Inserts mention in format `@author: "excerpt..."` at cursor position. 11 unit tests. Glassmorphism dropdown positioned below composer. Files: `mention-dropdown.js`, `test-mention-dropdown.js`. |
| 2026-03-27 | **IMPLEMENTED**: Milestone 9 Phase 2 - Quick Session Switcher (Ctrl+Tab) | QuickSwitcher implementation complete: singleton pattern, localStorage session tracking (captures on `/new` and `/resume`), max 10 sessions, simple fuzzy character matching. Keyboard navigation (arrows, Enter, Escape, Tab). Sends `/resume <id>` via WebSocket on selection. 15 unit tests. Glassmorphism modal UI centered on screen. Files: `quick-switcher.js`, `test-quick-switcher.js`. |
| 2026-03-27 | **DESIGNED**: Milestone 9 Phase 2 - Quick Session Switcher (Ctrl+Tab) | Session switching architecture: `QuickSwitcher` class with singleton pattern, localStorage-based session tracking (capture on every `/new` and `/resume`), max 10 recent sessions, simple character-matching fuzzy search MVP. Glassmorphism UI reuses Phase 1 styles. Display: session name + relative time. Selection sends `/resume <id>` via WebSocket. Ctrl+Tab shortcut (avoiding Ctrl+Shift+Tab browser conflict). |
| 2026-03-27 | **IMPLEMENTED**: Milestone 9 Phase 1 - In-Conversation Search (Ctrl+F) | SearchOverlay implementation complete: singleton pattern, `window.find()` API for DOM-based search, case-insensitive matching, "N of M" counter, Enter/Shift+Enter navigation. 10 unit tests. Glassmorphism top-right overlay. Integrated in `main.js`. Files: `search-overlay.js`, `test-search-overlay.js`, `styles.css`. |
| 2026-03-27 | **DESIGNED**: Milestone 9 - Search & Quick Navigation (Phase 1) | In-conversation search architecture: `SearchOverlay` class with singleton pattern, `window.find()` API for MVP (visible messages only), case-insensitive search, "3 of 12" match counter. Glassmorphism UI consistent with Command Palette. Ctrl+F shortcut overrides browser native find. Server-side search deferred to Phase 2. See `execution-plan-159-milestone9.md`. |
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
| 2026-03-27 | **DECIDED**: Phase 1 happy-path fixture should include an unrelated non-leader shortcut | Include at least one non-leader registry entry in the canonical tree test fixture so `buildLeaderTree()` proves it filters leader-enabled entries internally instead of relying on prefiltered input. This keeps the happy-path test aligned with the helper contract and guards against accidental coupling to fixture shape. |
| 2026-03-27 | **DECIDED**: Phase 1 canonical test should combine prefix formatting and tree derivation | Keep the first fixture test in `test-keymap.js` focused on one happy-path assertion that checks `formatBinding(DEFAULT_KEYMAP["composer.leader"]) === "Ctrl+S"` and the derived tree shape in the same test. This keeps the initial acceptance bar small, makes the contract explicit, and avoids splitting the first Phase 1 proof across multiple test cases before the builder exists. |

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
