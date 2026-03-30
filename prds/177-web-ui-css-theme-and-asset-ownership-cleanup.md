# PRD: Web UI CSS Theme and Asset Ownership Cleanup

**GitHub Issue**: [#177](https://github.com/jeremysball/alfred/issues/177)  
**Status**: Draft  
**Priority**: Medium  
**Created**: 2026-03-30  
**Author**: Agent

---

## 1. Problem Statement

The Web UI styling layer has grown feature by feature, but ownership boundaries are still too fuzzy.

Today, styles and assets are spread across:
- `base.css`
- component-level CSS
- feature-level CSS
- many theme files
- asset references across HTML, CSS, and service worker caches

That creates five problems:

1. **CSS ownership is unclear**
   - It is not always obvious whether a rule belongs to base layout, a component, a feature, or a theme override.

2. **Theme and feature overrides can accumulate unpredictably**
   - Features and themes may both override the same surface without one clear layering model.

3. **Asset ownership and cache references are harder to reason about**
   - Icons, audio, theme assets, and service worker references can drift.

4. **Visual cleanup work becomes riskier than it should be**
   - Small surface tweaks can trigger regressions because the real style source of truth is unclear.

5. **Later feature cleanup stays blocked behind style ambiguity**
   - Auxiliary UI cleanup and component cleanup are easier once styling and asset boundaries are explicit.

The result is a visual layer that is flexible but too dependent on convention and accumulated overrides.

---

## 2. Goals

1. Define clear ownership for **base layout**, **components**, **features**, **themes**, and **assets**.
2. Reduce duplicated or conflicting CSS rules.
3. Make theme overrides explicit and easier to audit.
4. Clarify asset ownership and runtime references.
5. Keep current aesthetics unless a cleanup is required to establish ownership.
6. Build on the existing theme work instead of redoing it.

---

## 3. Non-Goals

- Redesigning all Web UI themes.
- Removing kidcore or other expressive visual surfaces purely for taste reasons.
- Replacing CSS with a CSS-in-JS system or build pipeline.
- Reworking component runtime behavior beyond what styling ownership requires.
- Changing theme direction from PRD #145.

---

## 4. Proposed Solution

### 4.1 Define the style layering model

Create an explicit ownership model such as:
- **base/layout**: app shell, layout primitives, shared tokens
- **components**: component-owned visuals and local states
- **features**: feature-specific surfaces that are not global theme rules
- **themes**: theme token overrides and theme-specific art direction
- **assets**: icons, audio, manifest/service-worker references, and other static media

### 4.2 Reduce cross-layer overrides

Requirements:
- base rules should not quietly behave like theme rules
- feature CSS should not carry unrelated global resets
- theme files should override through clear variables/tokens/surfaces rather than random selector duplication where possible

### 4.3 Clarify asset ownership and references

Static asset references should have one clear owner.

Examples:
- icons and manifest assets
- theme-specific audio/media
- cache lists and service worker asset references
- component-specific static media

### 4.4 Keep expressive themes, reduce structural ambiguity

This PRD should not flatten the visual identity of the app.

Instead, it should make it easier to answer:
- where does this surface get its base style?
- where does a theme override it?
- where is the asset that powers this effect owned?

### 4.5 Delete dead or redundant style paths

When a base/component/feature/theme rule is superseded, delete it instead of preserving parallel visual paths.

---

## 5. Success Criteria

- [ ] The Web UI has a documented style and asset ownership model.
- [ ] Base, component, feature, and theme rules have clearer boundaries.
- [ ] Redundant or conflicting style rules are reduced.
- [ ] Theme/asset references are easier to audit and maintain.
- [ ] Current visual identity is preserved unless a structural cleanup requires change.
- [ ] The implementation passes the relevant JS and browser validation workflow for touched surfaces.

---

## 6. Milestones

### Milestone 1: Define CSS and asset ownership boundaries
Document the layering model for base, components, features, themes, and assets.

Validation: the documented ownership model maps cleanly onto current frontend files.

### Milestone 2: Consolidate style ownership in high-churn surfaces
Move the most confusing or duplicated style rules into the right ownership layers and remove obviously redundant paths.

Validation: targeted browser checks prove the touched surfaces still render correctly.

### Milestone 3: Normalize theme override boundaries
Clarify how themes override shared surfaces and reduce selector duplication where possible without changing the visual direction.

Validation: theme surfaces still behave correctly and ownership is clearer in the touched files.

### Milestone 4: Clarify asset ownership and cache references
Align asset references across HTML, CSS, and service-worker/runtime ownership and remove drift where found.

Validation: targeted checks prove the touched assets still load correctly and cache manifests remain consistent.

### Milestone 5: Regression coverage and documentation
Add or update docs and targeted verification for the style layering model and touched visual surfaces.

Validation: `npm run js:check` passes for touched JS references and targeted browser verification passes for the touched visual areas.

---

## 7. Likely File Changes

```text
src/alfred/interfaces/webui/static/css/base.css
src/alfred/interfaces/webui/static/css/themes.css
src/alfred/interfaces/webui/static/css/themes/*.css
src/alfred/interfaces/webui/static/css/components/*.css
src/alfred/interfaces/webui/static/js/features/*/*.css
src/alfred/interfaces/webui/static/index.html
src/alfred/interfaces/webui/static/service-worker.js
src/alfred/interfaces/webui/static/icons/*
src/alfred/interfaces/webui/static/audio/*

tests/webui/test_theme_persistence.py
tests/webui/test_theme_palette.py
tests/webui/test_kidcore_theme.py
tests/webui/test_spacejam_theme.py
prds/177-web-ui-css-theme-and-asset-ownership-cleanup.md
```

---

## 8. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Visual regressions slip in under the banner of “cleanup” | High | keep the scope structural, use targeted browser verification, and avoid aesthetic churn |
| Theme cleanup accidentally fights PRD #145 direction | Medium | treat PRD #145 as the source of truth for current theme intent |
| CSS ownership work expands into a redesign | Medium | keep the goal on layering, duplication, and maintainability |
| Asset reference cleanup breaks offline/cache behavior | Medium | validate touched service-worker and runtime asset references directly |

---

## 9. Validation Strategy

This PRD is mostly CSS and browser-visible behavior, with possible JS/service-worker touches.

Required validation depends on touched files:

```bash
npm run js:check
uv run pytest tests/webui/test_theme_persistence.py tests/webui/test_theme_palette.py tests/webui/test_kidcore_theme.py tests/webui/test_spacejam_theme.py -v
```

Add targeted browser verification for any touched theme or asset-loading surface.

---

## 10. Related PRDs

- PRD #145: Spacejam and Kidcore Theme Overhaul
- PRD #170: Web UI Bootstrap and Script Loading Cleanup
- PRD #174: main.js Decomposition into Domain Controllers
- PRD #178: Web UI Auxiliary Subsystems Cleanup

Series note: PRD #177 should follow the core runtime cleanup so visual ownership can be simplified without core architecture still moving underneath it.

---

## 11. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-30 | Treat CSS cleanup as an ownership problem first | The main issue is structural ambiguity, not lack of visual variety |
| 2026-03-30 | Preserve existing theme direction where possible | This PRD should improve maintainability without forcing a redesign |
| 2026-03-30 | Include asset ownership and cache references in the cleanup | Visual maintenance depends on assets and runtime references, not CSS alone |
| 2026-03-30 | Delete redundant style paths instead of preserving parallel overrides | One source of truth per layer is easier to maintain |
