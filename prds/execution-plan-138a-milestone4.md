# Execution Plan: Sub-PRD 138A - Milestone 4

## Milestone
Browser Verification & Final Polish

## Overview
Verify the full chaos theme in a real browser, confirm the audio controls work, and fix the most obvious regressions. This phase is where we make sure the theme is absurd without making Alfred totally unusable.

---

## 1. Regression Test Sweep

### 1.1 Run targeted kidcore tests
- [ ] **Run**: `uv run pytest tests/webui/test_kidcore_theme.py -v`
- [ ] **Run**: `uv run pytest tests/webui/test_kidcore_chaos.py -v`
- [ ] **Run**: `uv run pytest tests/webui/test_kidcore_audio.py -v`

### 1.2 Run broader Web UI coverage
- [ ] **Run**: `uv run pytest tests/webui/ -v`

### 1.3 Run code-quality checks on touched frontend files
- [ ] **Run**: `uv run ruff check src/ tests/`
- [ ] **Run**: `uv run mypy --strict src/alfred`

---

## 2. Real Browser Verification

### 2.1 Start the app
- [ ] **Run**: `uv run alfred webui --port 8080`

### 2.2 Verify theme behavior in browser
- [ ] **Verify**: theme appears in selector
- [ ] **Verify**: selecting Kidcore Playground changes the whole UI
- [ ] **Verify**: refresh preserves theme selection
- [ ] **Verify**: messages still render correctly
- [ ] **Verify**: composer still accepts input and send works

### 2.3 Verify audio behavior in browser
- [ ] **Verify**: music does not start before clicking play
- [ ] **Verify**: clicking play starts music
- [ ] **Verify**: clicking mute / stop kills the noise
- [ ] **Verify**: interaction sounds fire during normal use

### 2.4 Prefer browser automation where practical
- [ ] **Verify**: use Playwright or equivalent browser-level checks before calling the theme done

---

## 3. Mobile / Small Viewport Check

### 3.1 Verify narrow layout survival
- [ ] **Verify**: header still fits
- [ ] **Verify**: audio controls remain usable
- [ ] **Verify**: composer and send button remain reachable
- [ ] **Verify**: scrolling still works

### 3.2 Fix obvious mobile breakage
- [ ] **Implement**: patch any glaring layout failures found during verification
- [ ] **Run**: rerun affected kidcore tests after fixes

---

## 4. Final Polish Pass

### 4.1 Tone adjustment
- [ ] **Implement**: if the theme is not obnoxious enough, make it worse in safe places
- [ ] **Implement**: if the theme makes chat unreadable, dial back only the content surfaces

### 4.2 Final acceptance check
- [ ] **Verify**: the result feels like a bad old-web fever dream
- [ ] **Verify**: it is opt-in
- [ ] **Verify**: it is stoppable
- [ ] **Verify**: it does not completely wreck Alfred

---

## Files to Modify

Expected only if regressions are found:

1. `src/alfred/interfaces/webui/static/css/themes/kidcore-playground.css`
2. `src/alfred/interfaces/webui/static/index.html`
3. `src/alfred/interfaces/webui/static/js/main.js`
4. `src/alfred/interfaces/webui/static/js/audio-manager.js`
5. `tests/webui/test_kidcore_theme.py`
6. `tests/webui/test_kidcore_chaos.py`
7. `tests/webui/test_kidcore_audio.py`

---

## Verification Commands

```bash
uv run pytest tests/webui/ -v
uv run ruff check src/ tests/
uv run mypy --strict src/alfred
uv run alfred webui --port 8080
```

---

## Commit Strategy

- `test(webui): add kidcore browser regression coverage`
- `fix(webui): patch kidcore theme regressions`
- `style(webui): tune kidcore chaos theme for final polish`

---

## Exit Criteria

- [ ] Kidcore Playground theme is selectable
- [ ] Theme is visually chaotic and obviously intentional
- [ ] Play button starts music only after user action
- [ ] Mute / stop control works
- [ ] Core chat flow still works in browser
- [ ] No glaring mobile layout failure remains
