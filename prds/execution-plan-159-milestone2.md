# Execution Plan: PRD #159 - Milestone 2: Keyboard Shortcuts & Help System

## Overview
Implement keyboard shortcut discoverability and navigation. Users press `?` to see all shortcuts, and can navigate messages with arrow keys when focused.

---

## Phase 1: Shortcut Registry

### ShortcutRegistry Module

- [ ] **Test**: `test_register_shortcut_adds_to_registry()` - Verify shortcuts can be registered with key, action, description
- [ ] **Implement**: Create `features/keyboard/shortcuts.js` with `register()` and `getAll()` functions
- [ ] **Run**: `node features/keyboard/test-shortcuts.js`

- [ ] **Test**: `test_register_requires_key_and_action()` - Verify validation throws for missing fields
- [ ] **Implement**: Add validation that key and action are required
- [ ] **Run**: `node features/keyboard/test-shortcuts.js`

- [ ] **Test**: `test_getAll_groups_by_category()` - Shortcuts grouped by category (Global, Navigation, etc.)
- [ ] **Implement**: Group shortcuts when retrieving
- [ ] **Run**: `node features/keyboard/test-shortcuts.js`

- [ ] **Test**: `test_shortcut_with_modifier_keys()` - Handle Ctrl+K, Shift+?, etc.
- [ ] **Implement**: Parse modifier keys (ctrl, shift, alt, meta)
- [ ] **Run**: `node features/keyboard/test-shortcuts.js`

---

## Phase 2: Global Keyboard Listener

### Keyboard Manager

- [ ] **Test**: `test_global_listener_captures_registered_shortcuts()` - Pressing registered key triggers action
- [ ] **Implement**: Add global keydown listener that checks registered shortcuts
- [ ] **Run**: Manual test in browser console

- [ ] **Test**: `test_context_aware_shortcuts()` - Shortcuts only work in specific contexts (e.g., message-focused)
- [ ] **Implement**: Add context checking (global, input-focused, message-focused)
- [ ] **Run**: Manual test - shortcut works only when context matches

- [ ] **Test**: `test_shortcut_prevent_default()` - Shortcuts prevent browser default behavior
- [ ] **Implement**: Call e.preventDefault() for matched shortcuts
- [ ] **Run**: Manual test - Ctrl+K doesn't open browser search

---

## Phase 3: Help Modal

### Help Modal Component

- [ ] **Test**: `test_help_modal_opens_on_question_mark()` - Press `?` opens help modal
- [ ] **Implement**: Create `features/keyboard/help.js` with show/hide methods
- [ ] **Run**: Manual test - press `?` in browser

- [ ] **Test**: `test_help_modal_closes_on_escape()` - Escape closes help modal
- [ ] **Implement**: Add Escape key handler
- [ ] **Run**: Manual test

- [ ] **Test**: `test_help_displays_shortcuts_by_category()` - Shortcuts grouped in UI
- [ ] **Implement**: Render shortcuts in categorized sections
- [ ] **Run**: Visual verification - see categories in modal

- [ ] **Test**: `test_help_shows_key_and_description()` - Each shortcut displays key combo and what it does
- [ ] **Implement**: Render key combination and description for each shortcut
- [ ] **Run**: Visual verification

---

## Phase 4: Message Navigation

### Message Focus Navigation

- [ ] **Test**: `test_messages_have_tabindex()` - Message elements are focusable
- [ ] **Implement**: Add tabindex="0" to message elements in main.js
- [ ] **Run**: Inspect element in DevTools

- [ ] **Test**: `test_arrow_up_navigates_to_previous_message()` - ArrowUp moves focus up
- [ ] **Implement**: Add ArrowUp handler to move focus to previous message
- [ ] **Run**: Manual test - focus message, press ArrowUp

- [ ] **Test**: `test_arrow_down_navigates_to_next_message()` - ArrowDown moves focus down
- [ ] **Implement**: Add ArrowDown handler to move focus to next message
- [ ] **Run**: Manual test

- [ ] **Test**: `test_focus_wraps_at_boundaries()` - Up from first goes to last, vice versa
- [ ] **Implement**: Wrap focus at message list boundaries
- [ ] **Run**: Manual test

---

## Phase 5: Register Default Shortcuts

### Default Shortcuts Registration

- [ ] **Test**: `test_question_mark_registered()` - `?` shortcut is registered at init
- [ ] **Implement**: Register `?` → show help modal in initKeyboard()
- [ ] **Run**: Manual test - press `?`

- [ ] **Test**: `test_tab_navigation_registered()` - Tab/Shift+Tab shortcuts registered
- [ ] **Implement**: Register tab navigation shortcuts
- [ ] **Run**: Manual test - Tab cycles through elements

- [ ] **Test**: `test_message_arrow_keys_registered()` - Arrow keys registered for message navigation
- [ ] **Implement**: Register ↑/↓ for message navigation when message-focused
- [ ] **Run**: Manual test - focus message, use arrow keys

- [ ] **Test**: `test_home_end_registered()` - Home/End keys registered
- [ ] **Implement**: Register Home → first message, End → last message
- [ ] **Run**: Manual test

---

## Phase 6: Styling

### Help Modal Styles

- [ ] **Test**: `test_help_uses_glassmorphism()` - Help modal has blur backdrop
- [ ] **Implement**: Create `features/keyboard/styles.css` with glassmorphism
- [ ] **Run**: Visual verification

- [ ] **Test**: `test_shortcut_keys_styled_as_kbd()` - Keys shown in `<kbd>` elements
- [ ] **Implement**: Style kbd elements to look like keys
- [ ] **Run**: Visual verification - keys look like keyboard buttons

- [ ] **Test**: `test_categories_visually_distinct()` - Category headers stand out
- [ ] **Implement**: Style category headers
- [ ] **Run**: Visual verification

---

## Files to Create

### New Files
1. `features/keyboard/shortcuts.js` - Shortcut registry
2. `features/keyboard/help.js` - Help modal component
3. `features/keyboard/navigation.js` - Message navigation
4. `features/keyboard/styles.css` - Help modal styles
5. `features/keyboard/index.js` - Module exports
6. `features/keyboard/test-shortcuts.js` - Unit tests

### Modified Files
7. `main.js` - Initialize keyboard system, register shortcuts
8. `index.html` - Add keyboard scripts and styles

---

## Commit Strategy

```bash
# Phase 1
git commit -m "feat(keyboard): add ShortcutRegistry with validation"

# Phase 2
git commit -m "feat(keyboard): add global keyboard listener with context awareness"

# Phase 3
git commit -m "feat(keyboard): add Help modal component"

# Phase 4
git commit -m "feat(keyboard): add message navigation with arrow keys"

# Phase 5
git commit -m "feat(keyboard): register default shortcuts (? help, arrows, home/end)"

# Phase 6
git commit -m "feat(keyboard): add help modal styling with kbd elements"
```

---

## Success Criteria

- [ ] Press `?` opens help modal showing all shortcuts
- [ ] Shortcuts organized by category (Global, Navigation, Actions, Composer)
- [ ] `Tab`/`Shift+Tab` navigates between interactive elements
- [ ] `↑`/`↓` navigates between messages when message has focus
- [ ] `Home` jumps to first message, `End` jumps to last
- [ ] Help modal styled with glassmorphism
- [ ] Shortcut keys displayed as `<kbd>` elements
- [ ] 15+ unit tests passing

---

**Next Step**: Start with Phase 1 - Shortcut Registry