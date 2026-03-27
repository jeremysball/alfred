# Execution Plan: PRD #159 - Milestone 9 (Search & Quick Navigation)

## Overview
Implement in-conversation search, quick session switcher, and @ mentions for message references.

---

## Phase 1: In-Conversation Search (Ctrl+F) ✅ COMPLETE

### SearchOverlay Component

- [x] Test: SearchOverlay can be instantiated with options
- [x] Test: SearchOverlay.getInstance returns singleton instance
- [x] Test: open() creates overlay element and adds to DOM
- [x] Test: close() removes overlay element from DOM
- [x] Test: search input triggers onSearch callback
- [x] Test: Escape key closes overlay
- [x] Test: Enter key navigates to next match
- [x] Test: Shift+Enter navigates to previous match
- [x] Test: updateMatchCounter updates UI correctly
- [x] Test: onClose callback triggered when overlay closes
- [x] Implement: `SearchOverlay` class with input field and navigation controls
- [x] Implement: Integration with `window.find()` API for MVP
- [x] Implement: Match counter display ("N of M" format)
- [x] Implement: Case-insensitive search
- [x] Implement: Glassmorphism styling with CSS
- [x] Run: `node test-search-overlay.js` - 10/10 tests passing

### Files Created

- `src/alfred/interfaces/webui/static/js/features/search/search-overlay.js` - SearchOverlay class
- `src/alfred/interfaces/webui/static/js/features/search/test-search-overlay.js` - 10 unit tests
- `src/alfred/interfaces/webui/static/js/features/search/styles.css` - Glassmorphism styles
- `src/alfred/interfaces/webui/static/js/features/search/index.js` - Module exports

### Integration ✅ COMPLETE

- [x] Add CSS import to index.html
- [x] Initialize search in main.js
- [x] Browser test - Ctrl+F opens custom search overlay

**Files Modified:**
- `index.html` - Added search styles.css link
- `main.js` - Added initSearch() function, imported initializeSearch

**Result:** Ctrl+F now opens the search overlay in Alfred

---

## Phase 2: Quick Session Switcher (Ctrl+Tab) ⏳ READY

---

## Phase 2: Quick Session Switcher (Ctrl+Tab)

### QuickSwitcher Component

- [ ] Test: `test_quick_switcher_opens_on_ctrl_tab()` - shortcut opens switcher modal
- [ ] Test: `test_quick_switcher_shows_recent_sessions()` - displays last 10 sessions
- [ ] Test: `test_quick_switcher_navigates_with_arrows()` - arrow keys select session
- [ ] Test: `test_quick_switcher_loads_session_on_enter()` - Enter loads selected session
- [ ] Test: `test_quick_switcher_closes_on_escape()` - Escape closes without action
- [ ] Test: `test_quick_switcher_filters_by_typing()` - type to filter sessions
- [ ] Implement: `QuickSwitcher` class with fuzzy search
- [ ] Implement: Session data from existing `/sessions` command cache
- [ ] Implement: Visual styling matching command palette (glassmorphism)
- [ ] Run: `uv run pytest tests/webui/test_quick_switcher.py -v`

### Session Loading

- [ ] Test: `test_quick_switcher_sends_resume_command()` - sends `/resume <id>`
- [ ] Test: `test_quick_switcher_shows_loading_state()` - loading indicator while switching
- [ ] Implement: Integration with WebSocket to send `/resume` command
- [ ] Implement: Loading state and error handling
- [ ] Run: Browser test - switch session, verify messages load

---

## Phase 3: @ Mentions

### MentionProvider

- [ ] Test: `test_mention_triggers_on_at_symbol()` - typing @ shows dropdown
- [ ] Test: `test_mention_filters_messages()` - typing filters last 20 messages
- [ ] Test: `test_mention_shows_message_preview()` - dropdown shows message snippet
- [ ] Test: `test_mention_inserts_reference_on_select()` - clicking inserts @ mention
- [ ] Test: `test_mention_closes_on_escape()` - Escape closes dropdown
- [ ] Test: `test_mention_navigates_with_arrows()` - arrow keys navigate dropdown
- [ ] Implement: `MentionProvider` class with dropdown UI
- [ ] Implement: Message caching from current session (last 20 messages)
- [ ] Implement: Fuzzy search on message content
- [ ] Run: `uv run pytest tests/webui/test_mention_provider.py -v`

### Composer Integration

- [ ] Test: `test_mention_position_tracks_caret()` - dropdown follows cursor
- [ ] Test: `test_mention_formats_as_blockquote()` - inserts markdown quote format
- [ ] Implement: Caret position tracking for dropdown placement
- [ ] Implement: Markdown blockquote insertion with message reference
- [ ] Run: Browser test - type @, select message, verify quote inserted

---

## Files to Create/Modify

1. `src/alfred/interfaces/webui/static/js/features/search/search-overlay.js` - NEW
2. `src/alfred/interfaces/webui/static/js/features/search/quick-switcher.js` - NEW
3. `src/alfred/interfaces/webui/static/js/features/search/mention-provider.js` - NEW
4. `src/alfred/interfaces/webui/static/js/features/search/styles.css` - NEW
5. `src/alfred/interfaces/webui/static/js/features/search/index.js` - NEW
6. `src/alfred/interfaces/webui/static/js/features/keyboard/shortcuts.js` - Add Ctrl+F, Ctrl+Tab
7. `tests/webui/test_search_overlay.py` - NEW
8. `tests/webui/test_quick_switcher.py` - NEW
9. `tests/webui/test_mention_provider.py` - NEW

## Commit Strategy

- `feat(search): add in-conversation search overlay with Ctrl+F`
- `feat(search): implement quick session switcher with Ctrl+Tab`
- `feat(search): add @ mentions with message reference dropdown`
- `test(search): add comprehensive search feature tests`
