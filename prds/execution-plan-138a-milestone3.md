# Execution Plan: Sub-PRD 138A - Milestone 3

## Milestone
Audio & Music

## Overview
Add the theme's sound effects and looping music with the simplest possible control model: a visible play control and a visible mute / stop control. No full audio settings panel.

---

## 1. Audio Manager Foundation

### 1.1 Add failing audio-manager coverage
- [x] **Test**: `test_audio_manager_exists_and_requires_explicit_start()`
  - Created `tests/webui/test_kidcore_audio.py`
  - Asserted `audio-manager.js` exists
  - Asserted it exposes explicit methods for starting music and stopping/muting audio
  - Asserted it does not imply autoplay on load
  - Run: `uv run pytest tests/webui/test_kidcore_audio.py::test_audio_manager_exists_and_requires_explicit_start -v`

### 1.2 Create audio manager
- [x] **Implement**: Create `src/alfred/interfaces/webui/static/js/audio-manager.js`
  - Manage music playback
  - Manage sound effect playback
  - Fail gracefully if audio is blocked or unsupported

### 1.3 Verify audio manager
- [x] **Run**: `uv run pytest tests/webui/test_kidcore_audio.py::test_audio_manager_exists_and_requires_explicit_start -v`

---

## 2. Audio Controls in the UI

### 2.1 Add failing UI-control coverage
- [x] **Test**: `test_index_includes_kidcore_audio_controls_and_script()`
  - Asserted `index.html` loads `audio-manager.js`
  - Asserted `index.html` contains a visible play control and a visible mute / stop control
  - Run: `uv run pytest tests/webui/test_kidcore_audio.py::test_index_includes_kidcore_audio_controls_and_script -v`

### 2.2 Add audio controls
- [x] **Implement**: Update `src/alfred/interfaces/webui/static/index.html`
  - Added the audio manager script
  - Added one play button
  - Added one mute / stop button

### 2.3 Verify audio controls
- [x] **Run**: `uv run pytest tests/webui/test_kidcore_audio.py::test_index_includes_kidcore_audio_controls_and_script -v`

---

## 3. Interaction Wiring

### 3.1 Add failing wiring coverage
- [x] **Test**: `test_main_wires_kidcore_audio_to_core_interactions()`
  - Asserted `main.js` calls audio behavior for send, success, error, and toast or equivalent visible interactions
  - Run: `uv run pytest tests/webui/test_kidcore_audio.py::test_main_wires_kidcore_audio_to_core_interactions -v`

### 3.2 Wire audio into the app
- [x] **Implement**: Update `src/alfred/interfaces/webui/static/js/main.js`
  - Triggered click/send/error/success-ish sounds on meaningful events
  - Hooked play and mute controls to the audio manager
  - Did not block chat if audio fails

### 3.3 Verify wiring
- [x] **Run**: `uv run pytest tests/webui/test_kidcore_audio.py::test_main_wires_kidcore_audio_to_core_interactions -v`

---

## 4. Static Audio Assets

### 4.1 Add failing asset coverage
- [x] **Test**: `test_kidcore_audio_assets_exist()`
  - Asserted expected static assets exist under `src/alfred/interfaces/webui/static/audio/`
  - Suggested assets:
    - `kidcore-loop.mp3`
    - `click.mp3`
    - `send.mp3`
    - `success.mp3`
    - `error.mp3`
  - Run: `uv run pytest tests/webui/test_kidcore_audio.py::test_kidcore_audio_assets_exist -v`

### 4.2 Add audio assets
- [x] **Implement**: Add local static audio files under `src/alfred/interfaces/webui/static/audio/`
  - Generated theme-appropriate noisy assets locally
  - Kept filenames stable for JS wiring

### 4.3 Verify assets
- [x] **Run**: `uv run pytest tests/webui/test_kidcore_audio.py::test_kidcore_audio_assets_exist -v`

---

## Files to Modify

1. `tests/webui/test_kidcore_audio.py`
2. `src/alfred/interfaces/webui/static/js/audio-manager.js`
3. `src/alfred/interfaces/webui/static/js/main.js`
4. `src/alfred/interfaces/webui/static/index.html`
5. `src/alfred/interfaces/webui/static/audio/`

---

## Verification Commands

```bash
uv run pytest tests/webui/test_kidcore_audio.py -v
uv run pytest tests/webui/ -v -k kidcore
uv run alfred webui --port 8080
```

### Browser Check
- click play and confirm music starts
- click mute / stop and confirm audio dies
- send a message and confirm sound effects fire
- verify the app still works if the browser blocks or delays audio

---

## Commit Strategy

- `test(webui): cover kidcore audio manager behavior`
- `feat(webui): add kidcore audio manager`
- `test(webui): cover kidcore audio controls`
- `feat(webui): add kidcore play and mute controls`
- `test(webui): cover kidcore audio wiring`
- `feat(webui): wire kidcore sounds into chat interactions`
- `test(webui): cover kidcore audio assets`
- `chore(webui): add kidcore audio assets`

---

## Milestone Status

Milestone 3 is complete.
Continue with Milestone 4: Browser Verification & Final Polish in `prds/execution-plan-138a-milestone4.md`.
