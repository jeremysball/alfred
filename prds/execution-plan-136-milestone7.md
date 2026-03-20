# Execution Plan: PRD #136 - Milestone 7: Markdown Rendering

## Overview
Implement rich markdown rendering with syntax highlighting for code blocks, copy buttons, and proper link/table handling.

---

## Phase 7: Markdown Rendering

### 7.1 marked.js Integration ✅

- [x] **Test**: `test_marked_js_loaded()` - Verify marked library is available
  - Check that `window.marked` is defined after loading
  - Run: `grep "marked" src/alfred/interfaces/webui/static/index.html`

- [x] **Implement**: Add marked.js to index.html
  - Add `<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>` before main.js
  - Or download and serve locally for offline support
  - Commit: `feat(webui): add marked.js for markdown parsing`

- [x] **Test**: `test_chat_message_renders_markdown()` - Verify markdown is parsed
  - Create test checking that chat-message component uses marked.parse()
  - Run: Manual verification via browser console

- [x] **Implement**: Update chat-message.js to render markdown
  - Import/use marked to parse message content
  - Replace `_escapeHtml()` with `marked.parse()` for assistant messages
  - Sanitize output to prevent XSS
  - Commit: `feat(webui): render markdown in chat messages`

---

### 7.2 Code Block Syntax Highlighting ✅

- [x] **Test**: `test_highlight_js_loaded()` - Verify highlight.js is available
  - Check that `hljs` is defined after loading
  - Run: `grep "highlight" src/alfred/interfaces/webui/static/index.html`

- [x] **Implement**: Add highlight.js to index.html
  - Add highlight.js CSS theme (github-dark or similar)
  - Add highlight.js library
  - Commit: `feat(webui): add highlight.js for syntax highlighting`

- [x] **Test**: `test_code_blocks_highlighted()` - Verify code blocks have highlighting
  - Check that `<pre><code class="language-*">` blocks are processed
  - Run: Manual verification with sample message containing code

- [x] **Implement**: Apply syntax highlighting to code blocks
  - After rendering markdown, find all `<pre><code>` elements
  - Call `hljs.highlightElement()` on each
  - Auto-detect language if not specified
  - Commit: `feat(webui): apply syntax highlighting to code blocks`

---

### 7.3 Copy Button on Code Blocks

- [ ] **Test**: `test_copy_button_exists()` - Verify copy buttons are added
  - Check that code blocks have associated copy buttons
  - Run: `uv run pytest tests/webui/test_markdown.py::test_copy_button -v`

- [ ] **Implement**: Add copy button to code blocks
  - Create `addCopyButtons()` function in main.js
  - Wrap code blocks in container with copy button
  - Style button with CSS (position top-right of code block)
  - Commit: `feat(webui): add copy buttons to code blocks`

- [ ] **Test**: `test_copy_button_copies_text()` - Verify copy functionality works
  - Test that clicking copy button copies code to clipboard
  - Run: Manual verification

- [ ] **Implement**: Implement copy functionality
  - Use Clipboard API (`navigator.clipboard.writeText()`)
  - Show visual feedback on click (checkmark icon, "Copied!" tooltip)
  - Revert to original icon after 2 seconds
  - Commit: `feat(webui): implement code block copy functionality`

---

### 7.4 Inline Code Styling

- [ ] **Test**: `test_inline_code_styled()` - Verify inline code has proper styling
  - Check that `<code>` elements without `<pre>` parent are styled
  - Run: Visual inspection

- [ ] **Implement**: Style inline code elements
  - Add CSS for `code:not(pre code)` selector
  - Use monospace font, subtle background, padding
  - Ensure contrast with message background
  - Commit: `style(webui): style inline code elements`

---

### 7.5 Link Handling

- [ ] **Test**: `test_links_open_in_new_tab()` - Verify links have target="_blank"
  - Check that `<a>` tags have `target="_blank"` and `rel="noopener"`
  - Run: Manual verification

- [ ] **Implement**: Configure marked to open links in new tab
  - Use marked renderer to customize link output
  - Add `target="_blank"` and `rel="noopener noreferrer"` to all links
  - Commit: `feat(webui): open markdown links in new tab`

---

### 7.6 Table Rendering

- [ ] **Test**: `test_tables_render()` - Verify markdown tables display correctly
  - Check that table syntax produces proper HTML table elements
  - Run: Manual verification with sample table

- [ ] **Implement**: Add table styling
  - Add CSS for `<table>`, `<th>`, `<td>` elements
  - Ensure tables are responsive (horizontal scroll on mobile)
  - Add zebra striping or borders for readability
  - Commit: `style(webui): style markdown tables`

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/alfred/interfaces/webui/static/index.html` | Add marked.js and highlight.js imports |
| `src/alfred/interfaces/webui/static/js/components/chat-message.js` | Use marked.parse() for content rendering |
| `src/alfred/interfaces/webui/static/js/main.js` | Add copy button functionality, highlight.js init |
| `src/alfred/interfaces/webui/static/css/base.css` | Style inline code, tables, copy buttons |

---

## CDN Resources

```html
<!-- marked.js -->
<script src="https://cdn.jsdelivr.net/npm/marked@9.1.6/marked.min.js"></script>

<!-- highlight.js -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
```

---

## Verification Commands

```bash
# Check files are modified
git diff --name-only

# Start server for manual testing
uv run alfred webui --port 8080 &

# Test markdown rendering
curl -s http://localhost:8080/static/index.html | grep -E "(marked|highlight)"
```

---

## Success Criteria

- [ ] Markdown renders correctly (bold, italic, lists, links)
- [ ] Code blocks have syntax highlighting
- [ ] Copy button works on all code blocks
- [ ] Tables render cleanly
- [ ] Links open in new tab
- [ ] No console errors

---

## Commit Strategy

1. `feat(webui): add marked.js for markdown parsing`
2. `feat(webui): render markdown in chat messages`
3. `feat(webui): add highlight.js for syntax highlighting`
4. `feat(webui): apply syntax highlighting to code blocks`
5. `feat(webui): add copy buttons to code blocks`
6. `feat(webui): implement code block copy functionality`
7. `style(webui): style inline code elements`
8. `feat(webui): open markdown links in new tab`
9. `style(webui): style markdown tables`

---

## Next Milestone

After M7 complete: **Milestone 8 - Testing and Documentation**
- Unit tests for WebSocket protocol
- Component tests for Web Components
- Update README with `alfred webui` usage

**Run `/prd-update-progress` after completing these tasks.**
