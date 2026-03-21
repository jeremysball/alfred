# Execution Plan: Sub-PRD 138A - Milestone 2

## Milestone
Full Chaos Visual Layer

## Overview
Turn the base theme into the actual nightmare carnival version: stickers, badges, marquee energy, animated gradients, and over-the-top motion. Keep it loud, but still recognizable as a chat app.

---

## 1. Decorative UI Hooks

### 1.1 Add failing markup coverage
- [ ] **Test**: `test_index_includes_kidcore_decorative_hooks()`
  - Create `tests/webui/test_kidcore_chaos.py`
  - Assert `index.html` includes at least one explicit decorative hook for the theme, such as a marquee/banner or badge container
  - Run: `uv run pytest tests/webui/test_kidcore_chaos.py::test_index_includes_kidcore_decorative_hooks -v`

### 1.2 Add decorative markup
- [ ] **Implement**: Update `src/alfred/interfaces/webui/static/index.html`
  - Add a small banner / marquee / badge element that can be themed into full chaos mode
  - Keep it harmless to non-kidcore themes

### 1.3 Verify decorative hooks
- [ ] **Run**: `uv run pytest tests/webui/test_kidcore_chaos.py::test_index_includes_kidcore_decorative_hooks -v`

---

## 2. Animation Coverage

### 2.1 Add failing animation coverage
- [ ] **Test**: `test_kidcore_theme_defines_chaos_animations()`
  - Assert `kidcore-playground.css` defines keyframes/selectors for effects such as wiggle, shimmer, bounce, float, or marquee motion
  - Run: `uv run pytest tests/webui/test_kidcore_chaos.py::test_kidcore_theme_defines_chaos_animations -v`

### 2.2 Implement animations
- [ ] **Implement**: Extend `src/alfred/interfaces/webui/static/css/themes/kidcore-playground.css`
  - Add animated gradients
  - Add hover wiggles / button squish
  - Add floating sparkle / sticker motion
  - Add marquee-style movement where appropriate

### 2.3 Verify animations
- [ ] **Run**: `uv run pytest tests/webui/test_kidcore_chaos.py::test_kidcore_theme_defines_chaos_animations -v`

---

## 3. Component-Level Loud Styling

### 3.1 Add failing styling coverage
- [ ] **Test**: `test_kidcore_theme_styles_secondary_components()`
  - Assert the theme stylesheet includes selectors for status bar, toast, session list, and tool-call surfaces
  - Run: `uv run pytest tests/webui/test_kidcore_chaos.py::test_kidcore_theme_styles_secondary_components -v`

### 3.2 Push secondary components into the theme
- [ ] **Implement**: Update `kidcore-playground.css`
  - Restyle status bar
  - Restyle toast notifications
  - Restyle session list cards
  - Restyle tool-call cards if present

### 3.3 Verify secondary styling
- [ ] **Run**: `uv run pytest tests/webui/test_kidcore_chaos.py::test_kidcore_theme_styles_secondary_components -v`

---

## 4. Readability Guardrail

### 4.1 Add failing readability coverage
- [ ] **Test**: `test_kidcore_theme_keeps_message_and_composer_surfaces_readable()`
  - Assert the theme still gives explicit backgrounds/borders to message bubbles and composer surfaces
  - Run: `uv run pytest tests/webui/test_kidcore_chaos.py::test_kidcore_theme_keeps_message_and_composer_surfaces_readable -v`

### 4.2 Rein in the worst offenders
- [ ] **Implement**: Adjust theme CSS so content surfaces remain readable even when decorations are absurd

### 4.3 Verify readability guardrail
- [ ] **Run**: `uv run pytest tests/webui/test_kidcore_chaos.py::test_kidcore_theme_keeps_message_and_composer_surfaces_readable -v`

---

## Files to Modify

1. `tests/webui/test_kidcore_chaos.py`
2. `src/alfred/interfaces/webui/static/index.html`
3. `src/alfred/interfaces/webui/static/css/themes/kidcore-playground.css`

---

## Verification Commands

```bash
uv run pytest tests/webui/test_kidcore_chaos.py -v
uv run pytest tests/webui/ -v -k kidcore
uv run alfred webui --port 8080
```

### Browser Check
- verify the theme looks obviously louder than every other theme
- verify animations run
- verify the composer and messages are still readable
- verify the app still feels like Alfred, just cursed

---

## Commit Strategy

- `test(webui): cover kidcore chaos markup hooks`
- `feat(webui): add kidcore decorative hooks`
- `test(webui): cover kidcore animation styling`
- `style(webui): add kidcore chaos effects`
- `test(webui): cover kidcore readability guardrails`
- `style(webui): keep kidcore content surfaces readable`

---

## Next Task

- [ ] **Test**: `test_index_includes_kidcore_decorative_hooks()`
- [ ] **Implement**: Add a marquee or badge hook to `index.html`
- [ ] **Run**: `uv run pytest tests/webui/test_kidcore_chaos.py::test_index_includes_kidcore_decorative_hooks -v`
