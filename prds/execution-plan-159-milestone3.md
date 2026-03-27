# Execution Plan: PRD #159 - Milestone 3: Context Menus

## Overview
Implement right-click context menus for messages and code blocks. Users can copy text, quote replies, and access code actions via right-click or Shift+F10.

---

## Phase 1: Core Context Menu Component

### ContextMenu Class

- [ ] **Test**: `test_menu_opens_at_coordinates()` - Menu appears at specified x,y position
- [ ] **Implement**: Create `features/context-menu/menu.js` with `show()` method
- [ ] **Run**: Manual test in browser - right-click shows menu at cursor

- [ ] **Test**: `test_menu_renders_items()` - Menu displays item labels and icons
- [ ] **Implement**: Render menu items with label, icon, and click handler
- [ ] **Run**: Visual verification - items visible in menu

- [ ] **Test**: `test_menu_closes_on_escape()` - Escape key closes menu
- [ ] **Implement**: Add Escape key listener
- [ ] **Run**: Press Escape, menu closes

- [ ] **Test**: `test_menu_closes_on_outside_click()` - Click outside closes menu
- [ ] **Implement**: Add click-outside detection
- [ ] **Run**: Click outside menu, it closes

- [ ] **Test**: `test_menu_returns_focus_on_close()` - Focus returns to trigger element
- [ ] **Implement**: Store trigger element, restore focus on close
- [ ] **Run**: Tab navigation after close

---

## Phase 2: Styling

### Context Menu Styles

- [ ] **Test**: `test_menu_has_glassmorphism()` - Menu has blur backdrop
- [ ] **Implement**: Create `features/context-menu/styles.css` with glassmorphism
- [ ] **Run**: Visual verification

- [ ] **Test**: `test_menu_items_have_hover_state()` - Items highlight on hover
- [ ] **Implement**: Add hover styles for menu items
- [ ] **Run**: Hover over items

- [ ] **Test**: `test_menu_positioned_near_cursor()` - Menu appears near click, not off-screen
- [ ] **Implement**: Position calculation with viewport boundary detection
- [ ] **Run**: Click near screen edges

- [ ] **Test**: `test_menu_has_separator_lines()` - Dividers between item groups
- [ ] **Implement**: Add separator element between sections
- [ ] **Run**: Visual verification

---

## Phase 3: Message Context Menu

### Message Menu Items

- [ ] **Test**: `test_message_menu_has_copy_text()` - "Copy Text" item exists
- [ ] **Implement**: Add "Copy Text" action that copies message content
- [ ] **Run**: Click copy, verify clipboard

- [ ] **Test**: `test_message_menu_has_quote_reply()` - "Quote Reply" item exists
- [ ] **Implement**: Add "Quote Reply" that inserts quote in input
- [ ] **Run**: Click quote, input shows quote

- [ ] **Test**: `test_message_menu_shows_on_right_click()` - Right-click message shows menu
- [ ] **Implement**: Attach contextmenu listener to messages in main.js
- [ ] **Run**: Right-click a message

- [ ] **Test**: `test_message_menu_shows_on_shift_f10()` - Shift+F10 opens menu
- [ ] **Implement**: Add Shift+F10 keyboard shortcut
- [ ] **Run**: Press Shift+F10 on focused message

---

## Phase 4: Code Block Context Menu

### Code Menu Items

- [ ] **Test**: `test_code_menu_has_copy()` - "Copy" item exists for code blocks
- [ ] **Implement**: Add "Copy" that copies code content
- [ ] **Run**: Click copy on code block, verify clipboard

- [ ] **Test**: `test_code_menu_has_copy_as_markdown()` - "Copy as Markdown" item exists
- [ ] **Implement**: Add "Copy as Markdown" that wraps code in markdown
- [ ] **Run**: Click copy as markdown, verify format

- [ ] **Test**: `test_code_menu_shows_on_right_click()` - Right-click code block shows menu
- [ ] **Implement**: Attach contextmenu listener to code blocks
- [ ] **Run**: Right-click a code block

---

## Phase 5: ARIA Accessibility

### Accessibility Attributes

- [ ] **Test**: `test_menu_has_menu_role()` - Menu has `role="menu"`
- [ ] **Implement**: Add ARIA role attributes
- [ ] **Run**: Inspect element in DevTools

- [ ] **Test**: `test_menu_items_have_menuitem_role()` - Items have `role="menuitem"`
- [ ] **Implement**: Add menuitem role to each item
- [ ] **Run**: Inspect element

- [ ] **Test**: `test_menu_has_aria_label()` - Menu has aria-label
- [ ] **Implement**: Add aria-label describing the menu
- [ ] **Run**: Screen reader test

- [ ] **Test**: `test_menu_item_accepts_keyboard_activation()` - Enter/Space activates item
- [ ] **Implement**: Add Enter/Space key handlers
- [ ] **Run**: Focus item, press Enter

---

## Phase 6: Integration

### Wire Up in Main.js

- [ ] **Test**: `test_messages_get_context_menu()` - All messages have right-click menu
- [ ] **Implement**: Attach listeners when messages are rendered
- [ ] **Run**: Right-click various messages

- [ ] **Test**: `test_code_blocks_get_context_menu()` - All code blocks have right-click menu
- [ ] **Implement**: Attach listeners when highlighting code
- [ ] **Run**: Right-click code blocks

- [ ] **Test**: `test_new_messages_get_menu()` - Dynamically added messages have menu
- [ ] **Implement**: Use MutationObserver to attach to new messages
- [ ] **Run**: Send message, right-click it

---

## Files to Create

### New Files
1. `features/context-menu/menu.js` - Core menu component
2. `features/context-menu/message-menu.js` - Message-specific items
3. `features/context-menu/code-menu.js` - Code block items
4. `features/context-menu/styles.css` - Menu styling
5. `features/context-menu/index.js` - Module exports
6. `features/context-menu/test-menu.js` - Unit tests

### Modified Files
7. `main.js` - Attach context menu listeners
8. `index.html` - Add context menu scripts and styles

---

## Commit Strategy

```bash
# Phase 1
git commit -m "feat(context-menu): add core ContextMenu component"

# Phase 2
git commit -m "feat(context-menu): add glassmorphism styling and positioning"

# Phase 3
git commit -m "feat(context-menu): add message menu with copy and quote"

# Phase 4
git commit -m "feat(context-menu): add code block menu with copy options"

# Phase 5
git commit -m "a11y(context-menu): add ARIA roles and keyboard support"

# Phase 6
git commit -m "feat(context-menu): wire up to messages and code blocks in main.js"
```

---

## Success Criteria

- [ ] Right-click message shows context menu
- [ ] Menu items: Copy text, Quote reply
- [ ] Right-click code block shows: Copy, Copy as markdown
- [ ] Menu closes on Escape or outside click
- [ ] Menu returns focus to trigger on close
- [ ] Shift+F10 opens menu (keyboard accessible)
- [ ] ARIA roles: menu, menuitem
- [ ] Menu positioned near cursor, not off-screen
- [ ] Works on dynamically added messages

---

**Next Step**: Start with Phase 1 - Core Context Menu Component