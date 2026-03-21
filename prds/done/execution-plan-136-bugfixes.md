# Execution Plan: PRD #136 - Post-M5 Bug Fixes

## Overview
Address UX issues discovered after Milestone 5 completion. These are polish items that improve the Web UI experience before moving to M6 (Status/Notifications) and M7 (Markdown).

---

## Bug Fixes

### Fix 1: Commands Displayed as User Messages

- [x] Test: `test_command_shows_as_system_message()` - Verify /commands render as system messages
- [x] Implement: Move user message creation after command check in `sendMessageContent()`
- [x] Run: Manual verification - type `/new` and confirm it shows as "Command: /new" in gray, not blue bubble
- [x] Commit: `fix(webui): show commands as system messages instead of user bubbles`

**Status**: ✅ Complete

---

### Fix 2: Missing Streaming Throbber

- [x] Test: `test_streaming_indicator_visible_during_generation()` - Verify throbber appears during chat
- [x] Implement: Add `streaming-indicator` element to header with CSS animation
- [x] Implement: Add `showStreaming()`/`hideStreaming()` functions in main.js
- [x] Implement: Wire up to `chat.started`, `chat.complete`, `chat.error` events
- [x] Run: Manual verification - send message and confirm `⠋ ⠙ ⠹` animation appears in header
- [x] Commit: `feat(webui): add streaming throbber indicator`

**Status**: ✅ Complete

---

### Fix 3: Thinking Block Looks Like Code Block

- [x] Test: Visual verification - reasoning block should look distinct from code
- [x] Implement: Remove box styling (background, border) from `.reasoning-section`
- [x] Implement: Add left border accent instead of full border
- [x] Implement: Apply italic styling and muted colors
- [x] Run: Manual verification - compare reasoning block vs code block appearance
- [x] Commit: `style(webui): distinguish reasoning blocks from code blocks`

**Status**: ✅ Complete

---

### Fix 4: Settings Menu z-index Issue

- [x] Test: Manual - open settings menu on mobile, verify it appears above chat
- [x] Implement: Add `z-index: 1000` to `.settings-dropdown`
- [x] Implement: Add `position: relative` to `.settings-menu` wrapper
- [x] Run: Manual verification on mobile viewport
- [x] Commit: `fix(webui): fix settings menu z-index on mobile`

**Status**: ✅ Complete

---

## Verification Checklist

Before marking this execution plan complete:

- [ ] All changes committed with conventional commit format
- [ ] PRD #136 updated with bug fix documentation
- [ ] AGENTS.md skill paths fixed (already done)
- [ ] Tests pass: `uv run pytest tests/webui/ -v`
- [ ] Manual verification complete on both desktop and mobile

---

## Files Modified

| File | Changes |
|------|---------|
| `src/alfred/interfaces/webui/static/js/main.js` | Command handling, streaming indicator logic |
| `src/alfred/interfaces/webui/static/css/base.css` | Throbber animation, reasoning styles, z-index fixes |
| `src/alfred/interfaces/webui/static/index.html` | Added streaming indicator element |
| `prds/done/136-web-ui.md` | Documented bug fixes section |
| `AGENTS.md` | Fixed skill paths (separate concern) |

---

## Next Steps

After these bug fixes are committed:

1. **Milestone 6** (Status and Notifications):
   - Token count display in status bar
   - Toast notification system
   - Queue counter improvements

2. **Milestone 7** (Markdown Rendering):
   - marked.js integration
   - Syntax highlighting
   - Copy buttons on code blocks

3. **Milestone 8** (Testing and Documentation):
   - Component tests for Web Components
   - README updates
   - WebSocket protocol documentation

---

## Progress Summary

| Fix | Status | Commit Ready |
|-----|--------|--------------|
| Command display | ✅ Done | ✅ Yes |
| Streaming throbber | ✅ Done | ✅ Yes |
| Thinking block styling | ✅ Done | ✅ Yes |
| Settings z-index | ✅ Done | ✅ Yes |

**Total**: 4/4 fixes complete
