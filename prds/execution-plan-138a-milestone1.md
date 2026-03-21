# Execution Plan: Sub-PRD 138A - Milestone 1

## Milestone
Theme Registration & Base Surfaces

## Status
Completed

## Overview
Added `kidcore-playground` as a selectable theme, loaded its stylesheet from the Web UI, and implemented the first-pass kidcore surfaces with validation tests plus real browser verification.

---

## 1. Theme Registration

### 1.1 Add failing selector coverage
- [x] **Test**: `test_theme_selector_lists_kidcore_playground_theme()`
  - Created `tests/webui/test_kidcore_theme.py`
  - Asserted `theme-selector.js` contains `kidcore-playground`
  - Asserted the theme label references Kidcore / Playground styling
  - Run: `uv run pytest tests/webui/test_kidcore_theme.py::test_theme_selector_lists_kidcore_playground_theme -v`

### 1.2 Register the theme
- [x] **Implement**: Update `src/alfred/interfaces/webui/static/js/components/theme-selector.js`
  - Added one theme entry for `kidcore-playground`
  - Kept the current generic `data-theme` activation model

### 1.3 Verify registration
- [x] **Run**: `uv run pytest tests/webui/test_kidcore_theme.py::test_theme_selector_lists_kidcore_playground_theme -v`

---

## 2. Static Theme Loading

### 2.1 Add failing HTML coverage
- [x] **Test**: `test_index_loads_kidcore_playground_stylesheet()`
  - Asserted `index.html` includes `/static/css/themes/kidcore-playground.css`
  - Run: `uv run pytest tests/webui/test_kidcore_theme.py::test_index_loads_kidcore_playground_stylesheet -v`

### 2.2 Load the stylesheet
- [x] **Implement**: Update `src/alfred/interfaces/webui/static/index.html`
  - Added the new theme stylesheet link
  - Kept script and stylesheet order consistent with the current app

### 2.3 Verify static loading
- [x] **Run**: `uv run pytest tests/webui/test_kidcore_theme.py::test_index_loads_kidcore_playground_stylesheet -v`

---

## 3. Theme File Foundation

### 3.1 Add failing theme-file coverage
- [x] **Test**: `test_kidcore_theme_file_defines_core_surface_tokens()`
  - Asserted `kidcore-playground.css` exists
  - Asserted it contains `[data-theme="kidcore-playground"]`
  - Asserted it defines core tokens used by the app, including:
    - `--bg-primary`
    - `--bg-secondary`
    - `--text-primary`
    - `--accent-primary`
    - `--composer-bg`
    - `--status-bg`
    - `--send-button-bg`
  - Run: `uv run pytest tests/webui/test_kidcore_theme.py::test_kidcore_theme_file_defines_core_surface_tokens -v`

### 3.2 Create the theme CSS
- [x] **Implement**: Create `src/alfred/interfaces/webui/static/css/themes/kidcore-playground.css`
  - Defined the base loud palette
  - Restyled app shell, header, message cards, composer, buttons, status bar, settings, sessions, and toasts
  - Kept the theme readable enough for chat

### 3.3 Verify theme CSS
- [x] **Run**: `uv run pytest tests/webui/test_kidcore_theme.py::test_kidcore_theme_file_defines_core_surface_tokens -v`

---

## 4. Persistence & Regression Safety

### 4.1 Add failing compatibility coverage
- [x] **Test**: `test_theme_selector_keeps_generic_activation_and_existing_themes()`
  - Asserted selector still uses generic `data-theme` activation
  - Asserted existing theme ids remain present after adding kidcore
  - Run: `uv run pytest tests/webui/test_kidcore_theme.py::test_theme_selector_keeps_generic_activation_and_existing_themes -v`

### 4.2 Preserve existing theme behavior
- [x] **Implement**: Adjust selector data only as needed to keep existing themes intact

### 4.3 Verify compatibility
- [x] **Run**: `uv run pytest tests/webui/test_kidcore_theme.py::test_theme_selector_keeps_generic_activation_and_existing_themes -v`

---

## Files Modified

1. `tests/webui/test_kidcore_theme.py`
2. `tests/webui/test_kidcore_browser.py`
3. `src/alfred/interfaces/webui/static/js/components/theme-selector.js`
4. `src/alfred/interfaces/webui/static/index.html`
5. `src/alfred/interfaces/webui/static/css/themes/kidcore-playground.css`

---

## Verification Commands

```bash
uv run pytest tests/webui/test_kidcore_theme.py -v
uv run pytest tests/webui/test_kidcore_browser.py -v
uv run pytest tests/webui/ -v -k kidcore
uv run alfred webui --port 8080
```

### Browser Check
Completed with Playwright in `tests/webui/test_kidcore_browser.py`:
- select Kidcore Playground in settings
- refresh and confirm it persists
- verify header, messages, composer, and buttons change visibly
- confirm the real app launches and the theme is active in-browser

---

## Commit Strategy

- `test(webui): cover kidcore theme registration`
- `feat(webui): register kidcore playground theme`
- `test(webui): cover kidcore theme stylesheet loading`
- `feat(webui): create kidcore playground base theme`
- `test(webui): verify kidcore playground theme in browser`

---

## Next Milestone

- Milestone 2: Full Chaos Visual Layer
- Focus: decorative layers, marquee energy, animations, and extra flourish
