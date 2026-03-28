# Execution Plan: PRD #159 - Leader Mode and Which-Key Refinement

## Status: COMPLETE

## Overview
Make the leader-mode keyboard path trustworthy by deriving the which-key tree, runtime traversal, and help text from the same registry-backed keymap. Preserve `Ctrl+S` as the leader prefix, keep `WhichKey` render-only, and let theme surface tokens control the overlay skin.

This is a post-milestone follow-up to the completed PRD 159 core work.

Checkpoint complete: `composer.leader` now formats as `Ctrl+S`, the canonical leader-tree fixture test passes, duplicate/conflict leader-path validation is covered, the derived leader tree now drives the renderer and runtime dispatcher, help-sheet parity now shares the same breadcrumb formatter, and WhichKey now skins through shared panel surface tokens.

---

## Phase 1: Registry-Backed Leader Schema

### KeymapManager Leader Metadata

- [x] Test: `test_keymap_manager_formats_composer_leader_as_ctrl_s()` - `window.KeymapManager.getBinding("composer.leader")` formats as `Ctrl+S`, not `Ctrl+A`
- [x] Test: `test_keymap_manager_builds_nested_leader_tree_from_registry()` - a derived tree exposes the expected root groups, submenu leaves, and labels
- [x] Test: `test_keymap_manager_rejects_duplicate_or_conflicting_leader_paths()` - duplicate chord paths or conflicting labels fail fast before render time
- [x] Implement: update `composer.leader` to `Ctrl+S` and add focused formatter coverage
- [x] Implement: add declarative leader metadata to registry entries in `keymap.js`, including prefix binding, group labels, leaf labels, and chord paths
- [x] Implement: add pure helpers in `keymap.js` for `buildLeaderTree()` and `getLeaderNodeForPath()` with deterministic ordering and validation
- [x] Implement: export the new helpers through `features/keyboard/index.js` and `window.KeymapManager`
- [x] Run: `node src/alfred/interfaces/webui/static/js/features/keyboard/test-keymap.js && npm run js:check`

---

## Phase 2: WhichKey Renderer and Runtime Leader Dispatch

### WhichKey

- [x] Test: `test_which_key_renders_the_derived_tree_without_registry_logic()` - opening leader mode shows the nested tree from derived data, not a hardcoded binding array
- [x] Test: `test_which_key_header_shows_the_current_leader_path()` - the overlay header and breadcrumb path match the same chord vocabulary used by runtime actions
- [x] Implement: refactor `which-key.js` to accept derived tree data and active path state only; remove tree construction and shortcut interpretation from the component
- [x] Implement: keep `WhichKey` as a pure renderer with DOM, layout, and visibility responsibilities only
- [x] Run: `uv run pytest tests/webui/test_frontend.py::test_leader_popup_shows_legend_and_nested_submenu -v`

### main.js Leader Dispatcher

- [x] Test: `test_ctrl_s_enters_leader_mode_and_executes_registry_backed_actions()` - `Ctrl+S` opens leader mode and representative paths such as `S -> M` still trigger the expected UI action
- [x] Test: `test_invalid_leader_key_exits_mode_without_dispatching()` - an unknown chord closes leader mode instead of falling through to stale bindings
- [x] Implement: remove the hardcoded `leaderBindings` tree from `main.js`
- [x] Implement: derive leader data from the keymap, build the tree once, and use the shared lookup helper for traversal and leaf dispatch
- [x] Implement: keep `main.js` responsible for mode transitions and action dispatch only; do not re-implement path matching there
- [x] Run: `uv run pytest tests/webui/test_leader_keybinds.py -v`

---

## Phase 3: Help Sheet Parity

### Keyboard Help

- [x] Test: `test_help_sheet_lists_the_same_chord_paths_as_which_key()` - help output and the leader overlay show the same path text for the same binding
- [x] Test: `test_help_sheet_never_shows_the_legacy_leader_alias()` - no `Ctrl+A` leader text appears in help or overlay output
- [x] Implement: update `help.js` formatting so help text uses the same chord-path vocabulary as the derived leader tree
- [x] Implement: keep help rendering subscribed to keymap changes so rebinding refreshes the sheet when open
- [x] Run: `uv run pytest tests/webui/test_frontend.py tests/webui/test_leader_keybinds.py -v`

---

## Phase 4: Theme Surface Tokens for the Overlay

### WhichKey Theme Skinning

- [x] Test: `test_which_key_uses_theme_surface_tokens_for_background_and_border()` - switching themes changes the overlay surface tokens instead of falling back to a single hardcoded look
- [x] Test: `test_theme_files_define_surface_panel_tokens_where_needed()` - theme CSS contains the overlay surface tokens expected by `features/keyboard/styles.css`
- [x] Implement: extend `themes.css` token docs/defaults for the which-key surface-panel tokens
- [x] Implement: update `base.css` and `features/keyboard/styles.css` to consume the surface tokens consistently
- [x] Implement: update the targeted theme files that should skin the overlay distinctly, including the existing dark/light/custom themes that already carry theme-specific surface values
- [x] Run: `uv run pytest tests/webui/test_theme_palette.py tests/webui/test_theme_persistence.py -v`

---

## Files to Modify

1. `src/alfred/interfaces/webui/static/js/features/keyboard/keymap.js` - add leader metadata, tree derivation, lookup, and validation
2. `src/alfred/interfaces/webui/static/js/features/keyboard/index.js` - re-export new keymap helpers through `KeymapManager`
3. `src/alfred/interfaces/webui/static/js/features/keyboard/which-key.js` - consume derived tree data only
4. `src/alfred/interfaces/webui/static/js/main.js` - remove the hardcoded leader tree and dispatch through shared lookup helpers
5. `src/alfred/interfaces/webui/static/js/features/keyboard/help.js` - align help-sheet chord formatting with the derived tree vocabulary
6. `src/alfred/interfaces/webui/static/js/features/keyboard/styles.css` - update which-key surface styling to use theme tokens
7. `src/alfred/interfaces/webui/static/css/base.css` - ensure the overlay surface tokens have usable defaults
8. `src/alfred/interfaces/webui/static/css/themes.css` - document the overlay surface tokens and default values
9. `src/alfred/interfaces/webui/static/css/themes/*.css` - update targeted themes to skin the leader overlay consistently
10. `tests/webui/test_frontend.py` - update existing leader-overlay assertions and path text expectations
11. `tests/webui/test_leader_keybinds.py` - expand browser coverage for leader parity and invalid-path behavior
12. `tests/webui/test_theme_palette.py`, `tests/webui/test_theme_persistence.py` - add or adjust theme-token assertions as needed

---

## Commit Strategy

Each checkbox should map to one atomic commit following conventional commits:
- `test(keymap): verify registry-derived leader prefix and tree validation`
- `feat(keymap): derive leader tree from shortcut registry`
- `feat(keyboard): route leader mode through shared tree lookup`
- `feat(help): align help sheet with registry-derived chord paths`
- `feat(theme): add which-key surface tokens for overlay skinning`
- `test(webui): cover leader parity and invalid chord handling`
