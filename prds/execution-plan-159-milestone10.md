# Execution Plan: PRD #159 - Milestone 10 (PWA Polish & System Integration)

## Overview
Complete PWA compliance with install prompt, standalone mode, auto-theme, share target, and Lighthouse CI integration.

---

## Phase 1: PWA Manifest

### manifest.json

- [ ] Test: `test_manifest_served_at_root()` - `/manifest.json` returns valid JSON
- [ ] Test: `test_manifest_contains_required_fields()` - name, short_name, start_url, display
- [ ] Implement: Create `static/manifest.json` with app metadata
  ```json
  {
    "name": "Alfred Web UI",
    "short_name": "Alfred",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#ffffff",
    "theme_color": "#3b82f6",
    "icons": [...]
  }
  ```
- [ ] Implement: Serve manifest from server root in `server.py`
- [ ] Run: `uv run pytest tests/webui/test_pwa_manifest.py -v`

### Icons

- [ ] Test: `test_all_icon_sizes_exist()` - 192x192, 512x512, maskable
- [ ] Implement: Generate PNG icons in required sizes
- [ ] Implement: Add SVG icon for scalability
- [ ] Run: Visual verification - icons display correctly in browser tab

---

## Phase 2: Install Prompt

### BeforeInstallPrompt

- [ ] Test: `test_install_prompt_triggers_when_criteria_met()` - PWA criteria satisfied
- [ ] Test: `test_custom_install_ui_shown()` - custom button appears
- [ ] Test: `test_install_prompt_deferred()` - prompt can be saved for later
- [ ] Implement: Listen for `beforeinstallprompt` event
- [ ] Implement: Custom install button in settings/command palette
- [ ] Implement: Defer prompt and trigger on user action
- [ ] Run: Browser test - verify install flow works

### Installed App Detection

- [ ] Test: `test_installed_app_hides_install_button()` - button hidden when installed
- [ ] Test: `test_standalone_mode_detected()` - `display-mode: standalone` detected
- [ ] Implement: Check `window.matchMedia('(display-mode: standalone)')`
- [ ] Implement: Hide install UI when already installed
- [ ] Run: Browser test - verify detection works

---

## Phase 3: Auto-Theme System Preference

### Theme Detection

- [ ] Test: `test_theme_follows_system_preference()` - matches system dark/light
- [ ] Test: `test_theme_updates_on_system_change()` - responds to system changes
- [ ] Test: `test_user_override_persists()` - manual theme choice saved
- [ ] Implement: `prefers-color-scheme` media query listener
- [ ] Implement: Theme persistence in localStorage
- [ ] Implement: Override logic (user choice > system preference)
- [ ] Run: Browser test - toggle system theme, verify UI updates

### Theme Toggle Enhancement

- [ ] Test: `test_theme_toggle_cycles_system_light_dark()` - three-state toggle
- [ ] Implement: Add "System" option to theme toggle
- [ ] Implement: Visual indicator for current theme mode
- [ ] Run: Manual test - cycle through all theme modes

---

## Phase 4: Share Target

### Web Share Target API

- [ ] Test: `test_share_target_registered_in_manifest()` - manifest has share_target
- [ ] Test: `test_shared_text_received()` - shared text opens in composer
- [ ] Test: `test_shared_files_received()` - shared files trigger upload
- [ ] Implement: Add `share_target` to manifest.json
  ```json
  "share_target": {
    "action": "/share",
    "method": "POST",
    "enctype": "multipart/form-data",
    "params": {
      "title": "title",
      "text": "text",
      "url": "url"
    }
  }
  ```
- [ ] Implement: `/share` endpoint handler in server
- [ ] Implement: Share receiver UI that populates composer
- [ ] Run: Browser test - share from another app to Alfred

### Mobile Share Sheet

- [ ] Test: `test_alfred_appears_in_mobile_share_sheet()` - app listed as share target
- [ ] Document: Platform-specific share sheet behavior
- [ ] Run: Test on iOS Safari and Chrome Android

---

## Phase 5: Lighthouse CI Integration

### CI Configuration

- [ ] Test: `test_lighthouse_ci_runs_on_pr()` - CI executes on pull requests
- [ ] Test: `test_lighthouse_fails_below_90_pwa()` - build fails if score < 90
- [ ] Implement: `.github/workflows/lighthouse.yml` workflow
- [ ] Implement: `lighthouserc.json` configuration
  ```json
  {
    "ci": {
      "assert": {
        "assertions": {
          "categories:pwa": ["error", {"minScore": 0.9}],
          "categories:performance": ["warn", {"minScore": 0.8}]
        }
      }
    }
  }
  ```
- [ ] Run: Local Lighthouse CI test - `lhci autorun`

### PWA Audit Compliance

- [ ] Test: `test_all_lighthouse_pwa_checks_pass()` - installable, service worker, HTTPS
- [ ] Verify: All PWA requirements met
  - [ ] HTTPS served
  - [ ] Valid manifest
  - [ ] Service worker with fetch handler
  - [ ] Icons present
  - [ ] Works offline
- [ ] Run: Lighthouse audit in Chrome DevTools - verify score > 90

---

## Phase 6: Standalone Window Mode Enhancements

### Standalone UI Adjustments

- [ ] Test: `test_standalone_hides_browser_chrome()` - no browser UI in standalone
- [ ] Test: `test_standalone_shows_custom_title_bar()` - app-like title bar
- [ ] Implement: CSS adjustments for `display-mode: standalone`
- [ ] Implement: Custom window controls if needed (close, minimize)
- [ ] Run: Install as PWA, verify standalone appearance

### Deep Linking

- [ ] Test: `test_deep_links_work_in_standalone()` - URL params handled correctly
- [ ] Test: `test_session_id_in_url_opens_correct_session()` - `/session/<id>` works
- [ ] Implement: URL routing for session deep links
- [ ] Run: Test opening specific session via URL in standalone mode

---

## Files to Create/Modify

1. `src/alfred/interfaces/webui/static/manifest.json` - NEW
2. `src/alfred/interfaces/webui/static/icons/` - NEW directory with icon files
3. `src/alfred/interfaces/webui/static/js/features/pwa/install-prompt.js` - NEW
4. `src/alfred/interfaces/webui/static/js/features/theme/auto-theme.js` - NEW
5. `src/alfred/interfaces/webui/server.py` - Add `/manifest.json` route, `/share` handler
6. `.github/workflows/lighthouse.yml` - NEW
7. `lighthouserc.json` - NEW
8. `tests/webui/test_pwa_manifest.py` - NEW
9. `tests/webui/test_pwa_install.py` - NEW
10. `tests/webui/test_auto_theme.py` - NEW

## Commit Strategy

- `feat(pwa): add web app manifest with icons`
- `feat(pwa): implement install prompt and detection`
- `feat(theme): add auto-theme based on system preference`
- `feat(pwa): add share target for receiving content`
- `ci: add lighthouse CI for PWA score enforcement`
- `feat(pwa): enhance standalone window mode UI`
