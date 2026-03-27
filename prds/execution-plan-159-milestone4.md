# Execution Plan: PRD #159 - Milestone 4: System Notifications & Background Activity

## Overview
Implement browser notifications and favicon badges to alert users when responses complete while the tab is not focused. Includes permission handling and WebSocket visibility tracking.

---

## Phase 1: Permission Manager

### NotificationPermission Module

- [ ] **Test**: `test_permission_manager_requests_on_first_send()` - Permission prompt appears on first message
- [ ] **Implement**: Create `features/notifications/permissions.js` with request flow
- [ ] **Run**: Manual test - send first message, see permission prompt

- [ ] **Test**: `test_permission_manager_handles_denied()` - Shows toast when permission denied
- [ ] **Implement**: Handle "denied" state with user-friendly message
- [ ] **Run**: Deny permission, see toast

- [ ] **Test**: `test_permission_manager_remembers_granted()` - No prompt after granted
- [ ] **Implement**: Check permission before requesting
- [ ] **Run**: Grant permission, send another message - no prompt

- [ ] **Test**: `test_permission_manager_stores_in_localstorage()` - Persist permission choice
- [ ] **Implement**: Save permission state to localStorage
- [ ] **Run**: Reload page, permission state preserved

---

## Phase 2: Notification Service

### NotificationService Module

- [ ] **Test**: `test_notification_shows_when_tab_hidden()` - Notification appears when tab not focused
- [ ] **Implement**: Create `features/notifications/service.js` with showNotification()
- [ ] **Run**: Send message, switch tabs, response completes → notification

- [ ] **Test**: `test_notification_has_title_and_body()` - Shows "Response ready from Alfred" + preview
- [ ] **Implement**: Format notification with title and message preview
- [ ] **Run**: Verify notification content

- [ ] **Test**: `test_notification_click_focuses_tab()` - Click notification brings Alfred to front
- [ ] **Implement**: Add click handler to focus window
- [ ] **Run**: Click notification, Alfred tab focuses

- [ ] **Test**: `test_notification_respects_dnd()` - No notification when Do Not Disturb enabled
- [ ] **Implement**: Check Notification.permission and visibility
- [ ] **Run**: Enable DND, no notification

---

## Phase 3: Favicon Badge

### FaviconBadge Module

- [ ] **Test**: `test_badge_shows_unread_count()` - Favicon shows number of unread messages
- [ ] **Implement**: Create `features/notifications/favicon.js` with setBadge(count)
- [ ] **Run**: Receive messages while hidden, see badge

- [ ] **Test**: `test_badge_clears_on_focus()` - Badge clears when tab becomes active
- [ ] **Implement**: Clear badge on visibilitychange to visible
- [ ] **Run**: Focus tab, badge disappears

- [ ] **Test**: `test_badge_updates_canvas()` - Draw badge on favicon canvas
- [ ] **Implement**: Create canvas-based badge overlay
- [ ] **Run**: Visual verification - red dot with number

- [ ] **Test**: `test_badge_limit_99()` - Shows "99+" for 100+ unread
- [ ] **Implement**: Cap display at 99
- [ ] **Run**: 100 messages → shows "99+"

---

## Phase 4: Visibility Tracking

### WebSocket Visibility Protocol

- [ ] **Test**: `test_visibility_sent_on_blur()` - Client sends visibility:false on tab blur
- [ ] **Implement**: Add visibilitychange listener in websocket-client.js
- [ ] **Run**: Check WebSocket messages in DevTools

- [ ] **Test**: `test_visibility_sent_on_focus()` - Client sends visibility:true on tab focus
- [ ] **Implement**: Send visibility state on focus
- [ ] **Run**: Check WebSocket messages

- [ ] **Test**: `test_server_tracks_visibility()` - Server stores visibility state per session
- [ ] **Implement**: Track visibility in server-side session state
- [ ] **Run**: Server logs show visibility changes

---

## Phase 5: Toast Notifications

### Toast Notification System

- [ ] **Test**: `test_toast_shows_in_app()` - In-app toast when notification permission denied
- [ ] **Implement**: Create toast component for in-app alerts
- [ ] **Run**: Deny permission, see toast instead of browser notification

- [ ] **Test**: `test_toast_auto_dismisses()` - Toast disappears after 5 seconds
- [ ] **Implement**: Auto-dismiss with timeout
- [ ] **Run**: Wait 5 seconds, toast gone

- [ ] **Test**: `test_toast_clickable()` - Click toast to dismiss early
- [ ] **Implement**: Click to dismiss
- [ ] **Run**: Click toast, it disappears

---

## Phase 6: Integration

### Wire Up in Main.js

- [ ] **Test**: `test_notification_flow_end_to_end()` - Complete flow works
- [ ] **Implement**: Integrate all modules in initNotifications()
- [ ] **Run**: Full test - send message, hide tab, get notification

- [ ] **Test**: `test_notification_only_when_hidden()` - No notification when tab visible
- [ ] **Implement**: Check visibility before showing notification
- [ ] **Run**: Tab visible → no notification

- [ ] **Test**: `test_badge_only_when_hidden()` - No badge when tab visible
- [ ] **Implement**: Only update badge when document.hidden
- [ ] **Run**: Tab visible → no badge

---

## Files to Create

### New Files
1. `features/notifications/permissions.js` - Permission management
2. `features/notifications/service.js` - Browser notifications
3. `features/notifications/favicon.js` - Favicon badge
4. `features/notifications/toast.js` - In-app toasts
5. `features/notifications/styles.css` - Toast styling
6. `features/notifications/index.js` - Module exports

### Modified Files
7. `websocket-client.js` - Send visibility messages
8. `main.js` - Initialize notification system
9. `index.html` - Add notification scripts

---

## WebSocket Protocol

```javascript
// Client → Server: Visibility change
{
  type: "client.visibility",
  payload: {
    isVisible: false,
    timestamp: 1234567890
  }
}

// Server uses this to decide whether to send browser notification
// when response completes
```

---

## Commit Strategy

```bash
# Phase 1
git commit -m "feat(notifications): add permission manager with localStorage"

# Phase 2
git commit -m "feat(notifications): add browser notification service"

# Phase 3
git commit -m "feat(notifications): add favicon badge for unread count"

# Phase 4
git commit -m "feat(notifications): add visibility tracking via WebSocket"

# Phase 5
git commit -m "feat(notifications): add in-app toast notifications"

# Phase 6
git commit -m "feat(notifications): integrate all components in main.js"
```

---

## Success Criteria

- [ ] Send first message → permission prompt appears
- [ ] Deny permission → in-app toast shows
- [ ] Grant permission, hide tab → browser notification on completion
- [ ] Click notification → Alfred tab focuses
- [ ] Favicon shows unread count when tab hidden
- [ ] Badge clears when tab becomes active
- [ ] Visibility messages sent over WebSocket
- [ ] No notification when tab is visible
- [ ] Respects Do Not Disturb mode

---

**Next Step**: Start with Phase 1 - Permission Manager