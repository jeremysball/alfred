# Execution Plan: PRD #136 - Milestone 6: Status and Notifications

## Overview
Implement the status bar with real-time token usage, model display, queue counter, and toast notification system for cron events.

---

## Milestone 6: Status and Notifications

### 6.1 Status Bar Component

- [ ] **Test**: `test_status_bar_renders_all_elements()` - Verify status bar shows model, tokens, queue
  - Create test that checks status bar contains expected elements
  - Verify all text elements are present
  - Run: `uv run pytest tests/webui/test_status_bar.py::test_status_bar_renders -v`

- [ ] **Implement**: Create status-bar.js Web Component
  - Create file at `src/alfred/interfaces/webui/static/js/components/status-bar.js`
  - Define custom element with attributes: model, tokens, queue, streaming
  - Render fixed position bar at bottom of header
  - Commit: `feat(webui): create status-bar web component`

- [ ] **Test**: Verify status bar displays correct data from WebSocket
  - Mock status.update messages and verify display updates
  - Run: `uv run pytest tests/webui/test_status_bar.py -v`

- [ ] **Implement**: Add status bar to index.html
  - Import status-bar.js component
  - Add `<status-bar>` element to app header
  - Style with CSS custom properties
  - Commit: `feat(webui): integrate status bar into main UI`

---

### 6.2 Token Usage Display

- [ ] **Test**: `test_token_usage_display_updates()` - Verify token counts update in real-time
  - Test that status bar updates when token values change
  - Run: Manual verification

- [ ] **Implement**: Wire up token usage from server to status bar
  - Update server.py to send token counts in status.update messages
  - Parse usage from chat.complete messages
  - Display format: "Input: X | Output: Y | Cached: Z"
  - Commit: `feat(webui): display real-time token usage in status bar`

---

### 6.3 Model Name Display

- [ ] **Test**: `test_model_name_shows_in_status()` - Verify current model is displayed
  - Check that model name attribute is rendered
  - Run: Manual verification

- [ ] **Implement**: Display current model name in status bar
  - Read model from Alfred config
  - Update status.update payload to include model
  - Show model badge with name
  - Commit: `feat(webui): show current model name in status bar`

---

### 6.4 Queue Counter

- [ ] **Test**: `test_queue_counter_updates()` - Verify queue badge shows correct count
  - Test that queue length updates when messages are queued
  - Run: `uv run pytest tests/webui/test_queue.py::test_counter -v`

- [ ] **Implement**: Enhance queue counter in status bar
  - Move queue badge into status bar component
  - Show count with visual indicator
  - Animate when new items added
  - Commit: `feat(webui): integrate queue counter into status bar`

---

### 6.5 Streaming Throbber

- [ ] **Test**: `test_throbber_animates_during_streaming()` - Verify throbber shows during LLM response
  - Check throbber appears on chat.started
  - Verify it stops on chat.complete
  - Run: Manual verification

- [ ] **Implement**: Add streaming indicator to status bar
  - Show animated throbber (⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏) when streaming
  - Display "Thinking..." or model name + throbber
  - Hide when streaming completes
  - Commit: `feat(webui): add streaming throbber to status bar`

---

### 6.6 Toast Notification System

- [ ] **Test**: `test_toast_shows_notification()` - Verify toast appears and auto-dismisses
  - Create test for toast container and individual toasts
  - Check auto-dismiss after timeout
  - Run: `uv run pytest tests/webui/test_toast.py::test_toast -v`

- [ ] **Implement**: Create toast-container.js Web Component
  - Create file at `src/alfred/interfaces/webui/static/js/components/toast-container.js`
  - Support different levels: info, success, warning, error
  - Auto-dismiss after 5 seconds
  - Stack multiple toasts
  - Commit: `feat(webui): create toast notification system`

- [ ] **Test**: `test_cron_toast_received()` - Verify cron events show as toasts
  - Mock server toast message and verify display
  - Run: Manual verification

- [ ] **Implement**: Wire up cron events to toast notifications
  - Update server.py to send toast messages for cron events
  - Handle toast message type in main.js
  - Show toast for job started/completed/failed
  - Commit: `feat(webui): display cron events as toast notifications`

---

### 6.7 WebSocket Protocol Updates

- [ ] **Test**: `test_status_update_message()` - Verify status.update message format
  - Test message contains all required fields
  - Run: `uv run pytest tests/webui/test_protocol.py::test_status -v`

- [ ] **Implement**: Update WebSocket protocol for status messages
  - Define status.update message structure
  - Include: model, contextTokens, inputTokens, outputTokens, cacheReadTokens, reasoningTokens, queueLength, isStreaming
  - Send periodic updates during streaming
  - Commit: `feat(webui): add status.update WebSocket protocol message`

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/alfred/interfaces/webui/static/js/components/status-bar.js` | **NEW** - Status bar component |
| `src/alfred/interfaces/webui/static/js/components/toast-container.js` | **NEW** - Toast notifications |
| `src/alfred/interfaces/webui/static/index.html` | Add status bar import |
| `src/alfred/interfaces/webui/static/css/base.css` | Style status bar and toasts |
| `src/alfred/interfaces/webui/server.py` | Send status.update messages |
| `src/alfred/interfaces/webui/static/js/main.js` | Handle status updates and toasts |

---

## Status Message Protocol

```typescript
// Server → Client status update
{
  type: "status.update",
  payload: {
    model: string,           // e.g., "kimi-latest"
    contextTokens: number,   // Total context window usage
    inputTokens: number,     // Input tokens for current message
    outputTokens: number,    // Output tokens generated
    cacheReadTokens: number, // Cache hits
    reasoningTokens: number, // Reasoning/thinking tokens
    queueLength: number,     // Messages in queue
    isStreaming: boolean     // Whether LLM is generating
  }
}

// Server → Client toast notification
{
  type: "toast",
  payload: {
    message: string,
    level: "info" | "success" | "warning" | "error",
    duration?: number  // ms, default 5000
  }
}
```

---

## Verification Commands

```bash
# Start webui server
uv run alfred webui --port 8080 &

# Test status bar
curl -s http://localhost:8080/static/js/components/status-bar.js | head -10

# Run tests
uv run pytest tests/webui/test_status_bar.py -v
uv run pytest tests/webui/test_toast.py -v
```

---

## Commit Strategy

1. `feat(webui): create status-bar web component`
2. `feat(webui): integrate status bar into main UI`
3. `feat(webui): display real-time token usage in status bar`
4. `feat(webui): show current model name in status bar`
5. `feat(webui): integrate queue counter into status bar`
6. `feat(webui): add streaming throbber to status bar`
7. `feat(webui): create toast notification system`
8. `feat(webui): display cron events as toast notifications`
9. `feat(webui): add status.update WebSocket protocol message`

---

## Success Criteria

- [ ] Status bar shows model name, token usage, queue count
- [ ] Throbber animates during streaming
- [ ] Toasts appear for cron events
- [ ] All updates are real-time via WebSocket
- [ ] No console errors

---

## Next Milestone

After M6 complete: **Milestone 7 - Markdown Rendering**
- Add marked.js for markdown parsing
- Syntax highlighting for code blocks
- Copy button on code blocks

**Run `/prd-update-progress` after completing these tasks.**
