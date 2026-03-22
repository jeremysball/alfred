# Execution Plan: PRD #138 - Milestone 1: Foundation & Theme System

## Overview
Create the new "Modern Dark" theme as the default, update CSS architecture with CSS custom properties, and ensure theme switching works correctly. This establishes the visual foundation for all subsequent UI improvements.

---

## Milestone 1: Foundation & Theme System

### 1.1 CSS Custom Properties Architecture

- [ ] **Test**: Verify CSS custom properties are defined and accessible
  - Create test page that reads `--bg-primary`, `--accent-primary` values
  - Verify values match expected Modern Dark palette
  - Run: Manual verification in browser DevTools

- [ ] **Implement**: Add CSS custom properties to `base.css`
  - Add `:root` section with all custom property definitions
  - Include color palette, spacing, typography tokens
  - Use Modern Dark as default values
  - Commit: `feat(css): add CSS custom properties for theming`

- [ ] **Test**: Verify theme switching via `data-theme` attribute
  - Test that `[data-theme="dark-academia"]` overrides properties
  - Test that `[data-theme="modern-dark"]` uses default values
  - Run: Manual theme switch test in browser

---

### 1.2 Modern Dark Theme File

- [ ] **Test**: Verify `modern-dark.css` loads and applies correctly
  - Create test that checks computed styles match expected values
  - Verify `--bg-primary: #0d1117` is applied to body
  - Run: `python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8080/static/css/themes/modern-dark.css').status)"`

- [ ] **Implement**: Create `modern-dark.css` theme file
  - Define complete color palette per PRD spec
  - Include all message, input, and UI component colors
  - Add theme as `[data-theme="modern-dark"]` variant
  - Commit: `feat(theme): create Modern Dark theme with GitHub-inspired palette`

- [ ] **Test**: Verify theme renders correctly in browser
  - Screenshot test: Compare rendered output to expected design
  - Check contrast ratios pass WCAG AA (4.5:1)
  - Run: Manual visual verification

---

### 1.3 Update themes.css

- [ ] **Test**: Verify theme switching works via JavaScript
  - Test `document.documentElement.setAttribute('data-theme', 'modern-dark')`
  - Verify computed styles update immediately
  - Run: Manual test in browser console

- [ ] **Implement**: Update `themes.css` with new theme architecture
  - Add theme transition animations
  - Ensure smooth switching between themes
  - Add fallback for unsupported browsers
  - Commit: `refactor(css): update themes.css for CSS custom property architecture`

---

### 1.4 Update index.html

- [ ] **Test**: Verify new theme loads by default
  - Check that `modern-dark.css` is loaded in `<head>`
  - Verify no flash of unstyled content
  - Run: `curl -s http://localhost:8080/static/index.html | grep modern-dark`

- [ ] **Implement**: Update `index.html` to load Modern Dark theme
  - Add `<link>` tag for `modern-dark.css`
  - Set `data-theme="modern-dark"` on `<html>` element
  - Ensure theme files load in correct order
  - Commit: `feat(html): set Modern Dark as default theme`

---

### 1.5 Legacy Theme Compatibility

- [ ] **Test**: Verify Dark Academia theme still works
  - Switch to `data-theme="dark-academia"`
  - Verify all components render correctly
  - Run: Manual theme switch test

- [ ] **Test**: Verify Swiss International and Neumorphism themes work
  - Test each theme renders without errors
  - Verify theme switching is smooth
  - Run: Manual verification

- [ ] **Implement**: Update legacy themes to use CSS custom properties
  - Refactor `dark-academia.css` to override custom properties
  - Refactor `swiss-international.css`
  - Refactor `neumorphism.css`
  - Commit: `refactor(themes): migrate legacy themes to CSS custom properties`

---

### 1.6 Base.css Foundation Updates

- [ ] **Test**: Verify improved spacing and layout
  - Check consistent padding/margins across components
  - Verify responsive breakpoints work
  - Run: Visual regression test with screenshots

- [ ] **Implement**: Update `base.css` with improved foundations
  - Add consistent spacing scale (4px, 8px, 12px, 16px, 24px, 32px)
  - Improve layout grid system
  - Add smooth transitions for theme changes
  - Update typography with better hierarchy
  - Commit: `style(css): improve base.css spacing and layout foundations`

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/alfred/interfaces/webui/static/css/base.css` | Add CSS custom properties, improve spacing |
| `src/alfred/interfaces/webui/static/css/themes/modern-dark.css` | **NEW** - Create Modern Dark theme |
| `src/alfred/interfaces/webui/static/css/themes.css` | Update for custom property architecture |
| `src/alfred/interfaces/webui/static/css/themes/dark-academia.css` | Migrate to custom properties |
| `src/alfred/interfaces/webui/static/css/themes/swiss-international.css` | Migrate to custom properties |
| `src/alfred/interfaces/webui/static/css/themes/neumorphism.css` | Migrate to custom properties |
| `src/alfred/interfaces/webui/static/index.html` | Load Modern Dark theme by default |

---

## Color Palette Reference

```css
/* Modern Dark - GitHub-inspired */
--bg-primary: #0d1117;
--bg-secondary: #161b22;
--bg-tertiary: #21262d;
--bg-hover: #30363d;

--accent-primary: #58a6ff;
--accent-success: #238636;
--accent-warning: #d29922;
--accent-danger: #da3633;

--text-primary: #f0f6fc;
--text-secondary: #8b949e;
--text-tertiary: #6e7681;

--message-user-bg: #1f6feb;
--message-user-text: #ffffff;
--message-assistant-bg: #21262d;
--message-assistant-border: #30363d;
```

---

## Verification Commands

```bash
# Start webui server
uv run alfred webui --port 8080 &

# Test theme loads
curl -s http://localhost:8080/static/css/themes/modern-dark.css | head -20

# Verify custom properties work
# Open browser DevTools and check:
# getComputedStyle(document.body).getPropertyValue('--bg-primary')
# Expected: #0d1117

# Run tests
uv run pytest tests/webui/ -v -k theme
```

---

## Commit Strategy

1. `feat(css): add CSS custom properties for theming`
2. `feat(theme): create Modern Dark theme with GitHub-inspired palette`
3. `refactor(css): update themes.css for CSS custom property architecture`
4. `feat(html): set Modern Dark as default theme`
5. `refactor(themes): migrate legacy themes to CSS custom properties`
6. `style(css): improve base.css spacing and layout foundations`

---

## Success Criteria

- [ ] Modern Dark theme loads by default
- [ ] CSS custom properties accessible in all components
- [ ] Theme switching works smoothly (no flash)
- [ ] All legacy themes still functional
- [ ] Contrast ratios pass WCAG AA (4.5:1)
- [ ] No console errors

---

## Next Milestone

After M1 complete: **Milestone 2 - Message Component Redesign**
- Add avatars to chat-message.js
- Implement proper message alignment
- Redesign message bubble styling

**Run `/prd-update-progress` after completing these tasks.**
