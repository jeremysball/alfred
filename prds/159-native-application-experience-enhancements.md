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

- [ ] User can access all major features without touching the mouse
- [ ] Right-click context menus work on all interactive elements
- [ ] Notifications appear when responses complete in inactive tabs
- [ ] App works offline with static asset caching (UI loads, message queuing deferred)
- [ ] Animations use only `transform`/`opacity`, complete within 200ms
- [ ] Lighthouse PWA score > 90 (enforced in CI)
- [ ] All features work on desktop and mobile
- [ ] File uploads respect 10MB limit with clear error messages
- [ ] Mobile gestures disabled in 40px edge zone (no browser conflicts)
- [ ] Search latency < 16ms for <1000 commands
- [ ] Focus management follows ARIA guidelines (focus trap, return to trigger)

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

### Milestone 4: System Notifications & Background Activity
**Goal**: Notify users of activity when tab is not focused

**Features**:
- Browser notification when response completes (if tab not focused)
- Favicon badge with unread count
- Notification permission request (on first message send, before fetch)
- Sound notification option (respects system settings)

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
- Send first message → permission prompt appears before network request
- Deny permission → toast shown, message still sends
- Send message, switch tabs (blur event triggers visibility message)
- Response completes while hidden → notification appears
- Click notification focuses Alfred tab
- Badge shows on favicon with unread count
- Grant permission, reload → no prompt on subsequent messages

---

### Milestone 5: Drag & Drop
**Goal**: File upload and message interaction via drag and drop

**Features**:
- Drag files onto chat to upload
- Visual drop zone indicator
- Drag message to quote it (drop on input)
- Drag to reorder messages (if editing allowed)
- Paste image from clipboard → auto-upload

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
- Drag file over chat shows drop indicator
- Drop triggers file.upload message (or shows error if >10MB)
- Server responds with file.received within 30 seconds
- Copy image, paste in input → shows preview, queues for upload

---

### Milestone 6: Enhanced Animations & Micro-interactions
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

### Milestone 7: Service Worker & Offline Support
**Goal**: Static asset caching and offline indicator only (reduced scope)

**Features**:
- Service worker caches static assets (CSS, JS, HTML)
- Offline indicator in UI when WebSocket disconnects
- Page reload while offline loads cached UI shell
- **Out of Scope**: Message queuing (requires complex sync protocol - see Future Work)

**Rationale**: Full offline messaging requires IndexedDB queue, conflict resolution, and server-side sync protocol. Deferred to post-MVP.

**WebSocket Protocol Extensions**:
```javascript
// Client tracks visibility for notification logic
client → server: "client.visibility" {isVisible: boolean, timestamp: number}

// Server uses this to decide whether to send browser notification
// when response completes while tab hidden
```

**Validation**:
- Disconnect network → offline indicator appears within 5 seconds
- Page reload while offline loads cached UI (no 404 errors)
- Reconnect WebSocket → indicator disappears
- Lighthouse "Works Offline" audit passes

---

### Milestone 8: Mobile Gestures
**Goal**: Touch-friendly interactions for mobile users

**Features**:
- Swipe right on message = reply (disabled in 40px edge zone)
- Long press = context menu (500ms threshold)
- Pull down to refresh/reconnect (only from top of scroll)
- Swipe up on input = fullscreen compose
- Pinch to zoom on images (when implemented)

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
- Swipe right on message shows "Reply" action
- Swipe from left edge (<40px) triggers browser back (not reply)
- Long press shows context menu after 500ms
- Pull down triggers reconnect (only when scrolled to top)
- Tested on Safari iOS, Chrome Android

---

### Milestone 9: Search & Quick Navigation
**Goal**: Find and navigate content quickly

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

---

### Milestone 10: PWA Polish & System Integration
**Goal**: Full Progressive Web App compliance

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
│   └── context-menu/           ✅ IMPLEMENTED
│       ├── menu.js             # Core menu component
│       ├── message-menu.js     # Message right-click actions
│       ├── code-menu.js        # Code block actions
│       ├── styles.css          # Menu styling
│       └── index.js            # Module exports
```

**PLANNED (Not Yet Implemented):**
```
src/alfred/interfaces/webui/static/js/
├── features/
│   ├── context-menu/           ⏳ PENDING
│   │   ├── menu.js
│   │   ├── message-menu.js
│   │   └── code-menu.js
│   ├── notifications/          ⏳ PENDING
│   │   ├── browser.js
│   │   ├── favicon.js
│   │   └── permissions.js
│   ├── drag-drop/              ⏳ PENDING
│   │   ├── upload.js
│   │   ├── quote.js
│   │   └── visual.js
│   └── offline/                ⏳ PENDING
│       ├── service-worker.js
│       ├── queue.js
│       └── sync.js
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
- **Advanced File Upload**: Drag-to-reorder, multi-file upload, progress bars

### Additional Ideas
- Voice input (Web Speech API)
- Picture-in-picture mode
- AI-powered command suggestions
- Collaborative cursors (if multi-user)

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
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
