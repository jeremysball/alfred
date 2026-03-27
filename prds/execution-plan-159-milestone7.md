# Execution Plan: Milestone 7 - Service Worker & Offline Support

**PRD**: [#159 - Native Application Experience Enhancements](../159-native-application-experience-enhancements.md)  
**Scope**: Static asset caching + offline indicator (message queuing deferred to post-MVP)

---

## Phase 1: Service Worker Registration ✅ COMPLETE

### Registration

- [x] Test: `test_service_worker_registers()` - verify SW registers on page load
- [x] Implement: Create `service-worker.js` in web root
- [x] Implement: Register SW in `main.js` on DOMContentLoaded
- [x] Run: Check DevTools → Application → Service Workers, verify registration

### Scope

- [x] Test: Verify SW scope covers `/` (entire app)
- [x] Implement: Set scope to root in registration options
- [x] Run: Navigate to various paths, verify SW controls all

### Lifecycle

- [x] Test: Verify SW installs, activates, and controls pages
- [x] Implement: Handle `install` and `activate` events
- [x] Run: DevTools → Console, verify lifecycle logs

---

## Phase 2: Static Asset Caching ✅ COMPLETE

### CacheOnInstall

- [x] Test: `test_assets_cached_on_install()` - verify CSS/JS/HTML cached
- [x] Implement: Cache shell assets in `install` event
- [x] Run: DevTools → Cache Storage, verify entries exist

**Cached Assets**:
```javascript
const STATIC_ASSETS = [
  '/',
  '/static/index.html',
  '/static/css/base.css',
  '/static/js/main.js',
  '/static/js/features/command-palette/index.js',
  '/static/js/features/command-palette/styles.css',
  '/static/js/features/keyboard/index.js',
  '/static/js/features/keyboard/styles.css',
  '/static/js/features/context-menu/index.js',
  '/static/js/features/context-menu/styles.css',
  '/static/js/features/notifications/index.js',
  '/static/js/features/notifications/styles.css',
  '/static/js/features/drag-drop/index.js',
  '/static/js/features/drag-drop/styles.css',
  '/static/js/features/animations/index.js',
  '/static/js/features/animations/styles.css',
];
```

### CacheStrategy

- [x] Test: Verify stale-while-revalidate strategy for JS/CSS
- [x] Implement: Return cached, fetch update in background
- [x] Run: Throttle to Slow 3G, verify instant load from cache

### HTMLFallback

- [x] Test: `test_offline_page_load()` - verify HTML served when offline
- [x] Implement: Network-first for HTML, fallback to cache
- [x] Run: DevTools → Network → Offline, reload page, verify UI loads

---

## Phase 3: Offline Indicator ✅ COMPLETE

### WebSocketState

- [x] Test: Verify `ws.state` tracked (connecting, open, closed)
- [x] Implement: Track WebSocket readyState changes via ConnectionMonitor
- [x] Run: Check `window.__alfredConnectionMonitor.getState()` in console

### OfflineIndicatorComponent

- [x] Test: `test_offline_indicator_shows_on_disconnect()`
- [x] Implement: Create `OfflineIndicator` custom element
- [x] Implement: Show banner when WebSocket disconnects
- [x] Run: Stop WebSocket server, verify banner appears

### ReconnectState

- [x] Test: `test_offline_indicator_hides_on_reconnect()`
- [x] Implement: Hide indicator when WebSocket reconnects
- [x] Implement: Add "Reconnecting..." state with spinner
- [x] Run: Restart WebSocket server, verify indicator disappears

### VisualDesign

- [x] Test: Verify indicator matches glassmorphism style
- [x] Implement: Position at top of viewport, slide down animation
- [x] Run: Check styling matches other UI components

---

## Phase 4: Cache Management ✅ COMPLETE

### CacheVersioning

- [x] Test: Verify old caches purged on new version
- [x] Implement: Version cache names (e.g., `alfred-v1`)
- [x] Implement: Delete old caches in `activate` event
- [x] Run: Deploy new version, verify old cache removed

### CacheLimits

- [x] Test: Verify cache size stays under 50MB
- [x] Implement: Monitor cache size via DevTools
- [x] Run: Check DevTools → Cache Storage → Size

### PrecacheUpdate

- [x] Test: Verify new assets cached on SW update
- [x] Implement: SkipWaiting + claim clients on update
- [x] Run: Update SW, verify clients claim immediately

---

## Phase 5: Integration & Validation ✅ COMPLETE

### LighthouseAudit

- [x] Test: Run Lighthouse "Works Offline" audit
- [x] Implement: All PWA requirements met
- [x] Run: Verify audit passes (required for PWA score > 90)

### DevToolsVerification

- [x] Test: Verify all checks in DevTools
- [x] Check: Application → Service Workers → Status: Activated
- [x] Check: Cache Storage → Entries present
- [x] Check: Network → Offline → Page reloads from cache
- [x] Run: Manual verification complete

### CrossBrowser

- [x] Test: Verify SW works in Chrome, Firefox, Safari, Edge
- [x] Check: Safari iOS (limited SW support - basic caching only)
- [x] Run: Manual test documentation in PRD

---

## Validation Checklist ✅ ALL COMPLETE

- [x] Service worker registers on page load
- [x] Static assets cached (CSS, JS, HTML)
- [x] Page reload while offline serves cached UI
- [x] Offline indicator appears when WebSocket disconnects
- [x] Offline indicator disappears on reconnect
- [x] Old caches purged on new version
- [x] Lighthouse "Works Offline" audit passes
- [x] No console errors during SW lifecycle
- [x] Works in Chrome, Firefox, Safari, Edge

---

## Files to Create

```
src/alfred/interfaces/webui/static/
├── service-worker.js           # Main SW file
├── js/features/offline/
│   ├── index.js               # Module exports
│   ├── offline-indicator.js   # Custom element
│   ├── connection-monitor.js  # WebSocket state tracking
│   └── styles.css             # Offline indicator styles
```

## Files to Modify

```
src/alfred/interfaces/webui/static/
├── index.html                 # Add offline-indicator element, register SW
├── main.js                    # Import offline module, track WS state
└── js/
    └── websocket-client.js    # Emit state change events
```

---

## Out of Scope (Deferred)

- **Message Queuing**: IndexedDB queue, conflict resolution, server sync
- **Background Sync**: Queue and retry failed requests
- **Push Notifications**: Server-initiated notifications
- **Precache Manifest**: Auto-generated from build (future enhancement)

---

## Notes

- Service Worker requires HTTPS in production (localhost OK for dev)
- Cache size limited to 50MB to avoid storage quota issues
- Use Cache API, not IndexedDB (simpler for static assets)
- Update flow: new SW waits in `waiting` state, skipWaiting on activate
