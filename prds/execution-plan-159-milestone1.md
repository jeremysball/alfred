# Execution Plan: PRD #159 - Command Palette Foundation

## Overview
Implement Milestone 1 of the Native Application Experience enhancements: the Command Palette. This provides universal search and action launching via Ctrl+K, establishing patterns for keyboard navigation, modals, and fuzzy search that will be reused across all other milestones.

---

## Phase 1: Core Infrastructure

### Command Registry

- [ ] Test: `test_register_command_adds_to_registry()` - Verify commands can be registered with id, title, keywords, action
- [ ] Implement: Create `features/command-palette/commands.js` with `register()` and `getAll()` functions
- [ ] Run: `cd /workspace/alfred-prd/src/alfred/interfaces/webui/static/js && node -e "const {register, getAll} = require('./features/command-palette/commands.js'); register({id: 'test', title: 'Test'}); console.log(getAll().length === 1 ? 'PASS' : 'FAIL')"`

- [ ] Test: `test_command_has_required_fields()` - Verify id, title, action are required
- [ ] Implement: Add validation that throws if required fields missing
- [ ] Run: `node -e "const {register} = require('./features/command-palette/commands.js'); try { register({}); } catch(e) { console.log('PASS'); }"`

### Fuzzy Search Engine

- [ ] Test: `test_fuzzy_search_matches_title()` - "clr" matches "Clear chat"
- [ ] Implement: Create `features/command-palette/fuzzy-search.js` using Intl.Collator
- [ ] Run: Open browser console and test: `search('clr', [{title: 'Clear chat'}])`

- [ ] Test: `test_fuzzy_search_matches_keywords()` - "thm" matches "Toggle theme" via keywords
- [ ] Implement: Search against both title and keywords fields
- [ ] Run: Browser console test

- [ ] Test: `test_fuzzy_search_ranks_exact_matches_first()` - Exact matches score higher
- [ ] Implement: Add scoring algorithm (exact=3, prefix=2, fuzzy=1)
- [ ] Run: Browser console test verifying order

- [ ] Test: `test_search_latency_under_16ms_for_1000_commands()` - Performance budget
- [ ] Implement: Benchmark test measuring search time
- [ ] Run: `node -e "const start = performance.now(); for(let i=0;i<1000;i++) search('test', commands); console.log(performance.now()-start < 16 ? 'PASS' : 'FAIL')"`

---

## Phase 2: UI Components

### Modal Component

- [ ] Test: `test_palette_opens_on_ctrl_k()` - Ctrl+K keydown opens modal
- [ ] Implement: Add global keydown listener in `features/command-palette/palette.js`
- [ ] Run: Manual test - press Ctrl+K in browser

- [ ] Test: `test_palette_closes_on_escape()` - Escape key closes modal
- [ ] Implement: Add Escape key handler when modal is open
- [ ] Run: Manual test - open palette, press Escape

- [ ] Test: `test_palette_shows_search_input()` - Modal contains input field
- [ ] Implement: Create DOM structure with input, results container
- [ ] Run: Visual verification - input visible when open

- [ ] Test: `test_palette_has_glassmorphism_styling()` - Backdrop blur effect
- [ ] Implement: CSS with `backdrop-filter: blur()` and semi-transparent background
- [ ] Run: Visual verification in browser

### Results List

- [ ] Test: `test_results_show_command_title()` - Commands display with titles
- [ ] Implement: Render results as list items with command titles
- [ ] Run: Visual verification - type "clear", see "Clear Chat"

- [ ] Test: `test_results_highlight_matched_characters()` - Matched chars styled differently
- [ ] Implement: Wrap matched characters in `<mark>` or styled span
- [ ] Run: Visual verification - "clr" search highlights "C", "l", "r" in results

- [ ] Test: `test_results_show_keyboard_shortcut()` - Shortcuts displayed next to title
- [ ] Implement: Render shortcut in result item (if defined)
- [ ] Run: Visual verification - "Clear Chat Ctrl+Shift+C"

---

## Phase 3: Keyboard Navigation

### Navigation Controls

- [ ] Test: `test_arrow_keys_navigate_results()` - Down/Up arrows move selection
- [ ] Implement: Track selected index, update visual state on keydown
- [ ] Run: Manual test - open palette, press Down/Up, see highlight move

- [ ] Test: `test_enter_executes_selected_command()` - Enter runs command action
- [ ] Implement: Call selected command's action function on Enter
- [ ] Run: Manual test - select "Clear Chat", press Enter, chat clears

- [ ] Test: `test_selection_wraps_at_bounds()` - Down from last goes to first, Up from first goes to last
- [ ] Implement: Modulo arithmetic for index wrapping
- [ ] Run: Manual test - press Down past last item

---

## Phase 4: Commands Integration

### Default Commands

- [ ] Test: `test_clear_chat_command_exists()` - Command registered at startup
- [ ] Implement: Register default commands in `main.js` init
- [ ] Run: Open palette, type "clear", see result

- [ ] Test: `test_toggle_theme_command_exists()` - Theme toggle registered
- [ ] Implement: Register with existing theme toggle function
- [ ] Run: Open palette, type "theme", see result

- [ ] Test: `test_view_sessions_command_exists()` - Sessions command registered
- [ ] Implement: Register command that triggers sessions view
- [ ] Run: Open palette, type "session", see result

---

## Phase 5: Accessibility

### ARIA and Focus

- [ ] Test: `test_palette_has_dialog_role()` - Modal has `role="dialog"`
- [ ] Implement: Add ARIA attributes to modal container
- [ ] Run: Inspect element in DevTools

- [ ] Test: `test_input_has_aria_label()` - Search input labeled
- [ ] Implement: Add `aria-label="Search commands"`
- [ ] Run: Screen reader test or DevTools inspection

- [ ] Test: `test_results_have_listbox_role()` - Results container has proper role
- [ ] Implement: `role="listbox"` on results, `role="option"` on items
- [ ] Run: Screen reader test or DevTools inspection

- [ ] Test: `test_focus_trapped_in_modal()` - Tab cycles within modal when open
- [ ] Implement: Tab key handler that cycles focus between input and results
- [ ] Run: Manual test - open palette, press Tab repeatedly

---

## Files to Modify

### New Files
1. `src/alfred/interfaces/webui/static/js/features/command-palette/commands.js` - Command registry
2. `src/alfred/interfaces/webui/static/js/features/command-palette/fuzzy-search.js` - Search engine
3. `src/alfred/interfaces/webui/static/js/features/command-palette/palette.js` - Modal UI and logic
4. `src/alfred/interfaces/webui/static/js/features/command-palette/index.js` - Public API exports

### Modified Files
5. `src/alfred/interfaces/webui/static/js/main.js` - Import and initialize command palette
6. `src/alfred/interfaces/webui/static/index.html` - Add palette container element (if needed)

### Test Files
7. `tests/webui/test_command_palette.js` - Jest/browser-based tests

---

## Commit Strategy

Each checkbox = one atomic commit following conventional commits:

```bash
# Examples:
git commit -m "feat(command-palette): add command registry with register/getAll"
git commit -m "test(command-palette): verify required fields validation"
git commit -m "feat(command-palette): implement Intl.Collator fuzzy search"
git commit -m "perf(command-palette): verify <16ms search latency for 1000 commands"
git commit -m "feat(command-palette): add Ctrl+K keyboard shortcut to open"
git commit -m "feat(command-palette): render search results with highlighted matches"
git commit -m "feat(command-palette): add arrow key navigation"
git commit -m "feat(command-palette): register default commands (clear, theme, sessions)"
git commit -m "a11y(command-palette): add ARIA roles and labels"
```

---

## Verification Commands

### Unit Tests (Node.js compatible)
```bash
cd /workspace/alfred-prd/src/alfred/interfaces/webui/static/js
node features/command-palette/test-commands.js
node features/command-palette/test-fuzzy-search.js
```

### Integration Tests (Browser)
```bash
# Start dev server
cd /workspace/alfred-prd
uv run alfred --webui

# Then in browser console:
CommandPalette.open()
CommandPalette.search('clear')
CommandPalette.select(0)
```

### Performance Test
```javascript
// In browser console
const commands = Array.from({length: 1000}, (_, i) => ({
  id: `cmd-${i}`,
  title: `Command ${i}`,
  keywords: [`keyword-${i}`]
}));

const start = performance.now();
for (let i = 0; i < 100; i++) {
  fuzzySearch('test', commands);
}
console.log(`Avg: ${(performance.now() - start) / 100}ms`);
```

---

## Success Criteria

- [ ] Press Ctrl+K opens palette within 100ms
- [ ] Type "clr" matches "Clear chat" via fuzzy matching
- [ ] Results ranked by match score (exact matches first)
- [ ] Matched characters highlighted in result titles
- [ ] Enter executes selected command
- [ ] Escape closes palette
- [ ] Search latency < 16ms for <1000 commands
- [ ] All commands have ARIA labels and roles
- [ ] Keyboard navigation works without mouse

---

**Next Step**: Run `/prd-start 159` to begin implementation on a feature branch.