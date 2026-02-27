# Execution Plan: Multi-line Input & Streaming Throbber

**PRDs**: 96-multiline-input, 97-streaming-throbber
**Status**: Ready to execute
**Estimated effort**: 4-6 hours

---

## Phase A: Streaming Throbber (PRD 97)

### A.1 Create Throbber Class

- [ ] Create file `src/interfaces/pypitui/throbber.py`
- [ ] Define `BRAILLE_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]`
- [ ] Define `ASCII_FRAMES = ["|", "/", "-", "\\"]`
- [ ] Create `Throbber` class with `__init__(self, use_braille: bool = True)`
- [ ] Add `self._frames` initialized to BRAILLE_FRAMES or ASCII_FRAMES
- [ ] Add `self._index = 0`
- [ ] Implement `tick(self) -> None` — advance index, wrap at len(frames)
- [ ] Implement `render(self) -> str` — return `self._frames[self._index]`
- [ ] Implement `reset(self) -> None` — set index to 0

### A.2 Test Throbber Class

- [ ] Create `tests/pypitui/test_throbber.py`
- [ ] Test: `test_throbber_render_returns_frame()` — render returns string
- [ ] Test: `test_throbber_tick_advances()` — tick moves to next frame
- [ ] Test: `test_throbber_loops_at_end()` — tick at last frame returns to first
- [ ] Test: `test_throbber_reset_sets_index_0()` — reset goes to first frame
- [ ] Test: `test_throbber_braille_vs_ascii()` — verify both frame sets work
- [ ] Run: `uv run pytest tests/pypitui/test_throbber.py -v`
- [ ] Fix any failures

### A.3 Add Throbber to StatusLine

- [ ] Open `src/interfaces/pypitui/status_line.py`
- [ ] Add import: `from src.interfaces.pypitui.throbber import Throbber`
- [ ] Add `self._throbber = Throbber()` in `__init__`
- [ ] Add `self._is_streaming = False` in `__init__`
- [ ] Add `streaming: bool = False` parameter to `update()` method
- [ ] Store `self._is_streaming = streaming` in `update()`
- [ ] Add `tick_throbber(self) -> None` method — call `self._throbber.tick()` if streaming
- [ ] In `_render_full()`, prepend throbber if streaming: `f"{self._throbber.render()} "`
- [ ] In `_render_medium()`, prepend throbber if streaming
- [ ] In `_render_compact()`, prepend throbber if streaming

### A.4 Test StatusLine Throbber Integration

- [ ] Test: `test_status_shows_throbber_when_streaming()` — throbber char in output
- [ ] Test: `test_status_hides_throbber_when_not_streaming()` — no throbber char
- [ ] Test: `test_throbber_position_before_model()` — throbber appears first
- [ ] Run: `uv run pytest tests/pypitui/test_status_line.py -v`

### A.5 Wire Throbber into AlfredTUI

- [ ] Open `src/interfaces/pypitui/tui.py`
- [ ] Add `self._is_streaming = False` in `__init__`
- [ ] In `_send_message()`, set `self._is_streaming = True` before streaming loop
- [ ] In `_send_message()`, set `self._is_streaming = False` in finally block
- [ ] Update `_update_status()` to pass `streaming=self._is_streaming`
- [ ] In `run()` main loop, call `self.status_line.tick_throbber()` before render
- [ ] Verify streaming flag passed correctly in all `_update_status()` calls

### A.6 Test AlfredTUI Streaming Flag

- [ ] Test: `test_is_streaming_false_on_init()` — `_is_streaming` starts False
- [ ] Test: `test_is_streaming_true_during_send()` — flag True during streaming
- [ ] Test: `test_is_streaming_false_after_send()` — flag False after complete
- [ ] Test: `test_is_streaming_false_on_error()` — flag False even on exception
- [ ] Run: `uv run pytest tests/pypitui/test_tui.py -v`

### A.7 Manual Throbber Test

- [ ] Run: `tmux new-session -d -s alfred "cd /workspace/alfred-prd && uv run alfred"`
- [ ] Wait 2 seconds for startup
- [ ] Run: `tmux send-keys -t alfred "hello" Enter`
- [ ] Run: `tmux capture-pane -t alfred -p`
- [ ] Verify throbber animation visible during response
- [ ] Wait for response complete
- [ ] Run: `tmux capture-pane -t alfred -p`
- [ ] Verify throbber gone after response
- [ ] Run: `tmux kill-session -t alfred`

### A.8 Final Checks for Throbber

- [ ] Run: `uv run ruff check src/interfaces/pypitui/`
- [ ] Run: `uv run mypy src/interfaces/pypitui/`
- [ ] Run: `uv run pytest tests/pypitui/ -v`
- [ ] Fix any issues
- [ ] Commit: `feat(throbber): add streaming animation to status line`

---

## Phase B: Multi-line Input - Basic (PRD 96, Phase 1)

### B.1 Understand Current Input

- [ ] Read `/workspace/pypitui/src/pypitui/components.py` Input class
- [ ] Document current `_value` storage (single string)
- [ ] Document current `_cursor_pos` (character index)
- [ ] Document current `render()` behavior (single line)
- [ ] Document current key handling in `_handle_key()`

### B.2 Add Shift+Enter Detection

- [ ] Check if pypitui supports Shift+Enter in key parsing
- [ ] If not, add Shift modifier detection to pypitui key handling
- [ ] Test: verify Shift+Enter produces distinct event from Enter

### B.3 Insert Newline on Shift+Enter

- [ ] In Input `_handle_key()`, detect Shift+Enter
- [ ] Insert `\n` at cursor position: `self._value = self._value[:pos] + "\n" + self._value[pos:]`
- [ ] Move cursor after newline: `self._cursor_pos += 1`
- [ ] Test: `test_shift_enter_inserts_newline()`
- [ ] Test: `test_shift_enter_at_start()` — newline at position 0
- [ ] Test: `test_shift_enter_at_end()` — newline at end
- [ ] Test: `test_shift_enter_in_middle()` — newline in middle

### B.4 Render Multi-line Value

- [ ] Modify Input `render()` to split value on `\n`
- [ ] Each line renders separately
- [ ] Cursor marker appears on correct line
- [ ] Test: `test_render_multiline_shows_all_lines()`
- [ ] Test: `test_render_multiline_cursor_on_line_1()`
- [ ] Test: `test_render_multiline_cursor_on_line_2()`

### B.5 Submit Multi-line

- [ ] Verify Enter (no shift) still submits
- [ ] Test: `test_enter_submits_multiline()` — full value with newlines sent
- [ ] Test: `test_multiline_preserved_in_submission()` — `\n` chars in message

### B.6 Manual Multi-line Test

- [ ] Run alfred in tmux
- [ ] Type: `line 1`
- [ ] Press Shift+Enter
- [ ] Type: `line 2`
- [ ] Press Enter
- [ ] Verify both lines appear in user message
- [ ] Verify Alfred receives multi-line message

### B.7 Commit Basic Multi-line

- [ ] Run: `uv run ruff check src/`
- [ ] Run: `uv run mypy src/`
- [ ] Run: `uv run pytest tests/pypitui/ -v`
- [ ] Commit: `feat(input): add Shift+Enter for multi-line input`

---

## Phase C: Multi-line Input - Arrow Navigation (PRD 96, Phase 2)

### C.1 Track Display Column

- [ ] Add `self._display_column: int = 0` to Input
- [ ] On horizontal movement, update display column to cursor position
- [ ] When moving vertically, use display column to find target position

### C.2 Calculate Line Positions

- [ ] Add method `_get_line_positions() -> list[tuple[int, int]]`
- [ ] Returns list of (start_pos, end_pos) for each line
- [ ] Account for `\n` characters between lines

### C.3 Implement Up Arrow

- [ ] In `_handle_key()`, detect Up arrow
- [ ] Find current line index
- [ ] If not first line, move to previous line
- [ ] Target column: `min(display_column, len(previous_line))`
- [ ] Update cursor_pos to target position
- [ ] Test: `test_up_arrow_moves_to_previous_line()`
- [ ] Test: `test_up_arrow_at_first_line_does_nothing()`
- [ ] Test: `test_up_arrow_maintains_column()` — stays in same column if line long enough

### C.4 Implement Down Arrow

- [ ] In `_handle_key()`, detect Down arrow
- [ ] Find current line index
- [ ] If not last line, move to next line
- [ ] Target column: `min(display_column, len(next_line))`
- [ ] Update cursor_pos to target position
- [ ] Test: `test_down_arrow_moves_to_next_line()`
- [ ] Test: `test_down_arrow_at_last_line_does_nothing()`
- [ ] Test: `test_down_arrow_maintains_column()`

### C.5 Handle Left/Right Across Lines

- [ ] Left arrow at line start → move to end of previous line
- [ ] Right arrow at line end → move to start of next line
- [ ] Test: `test_left_arrow_at_line_start_moves_up()`
- [ ] Test: `test_right_arrow_at_line_end_moves_down()`

### C.6 Manual Arrow Test

- [ ] Run alfred in tmux
- [ ] Type 3 lines with Shift+Enter
- [ ] Use arrow keys to navigate all lines
- [ ] Verify cursor moves correctly
- [ ] Verify column maintained when moving up/down

### C.7 Commit Arrow Navigation

- [ ] Run tests and lint
- [ ] Commit: `feat(input): add arrow key navigation for multi-line`

---

## Phase D: Multi-line Input - Word Wrapping (PRD 96, Phase 3)

### D.1 Use pypitui wrap_text_with_ansi

- [ ] Import `wrap_text_with_ansi` from pypitui.utils
- [ ] In Input `render(width)`, wrap each line to width
- [ ] Track which wrapped segment cursor is on

### D.2 Calculate Wrapped Cursor Position

- [ ] Add method `_get_wrapped_cursor_info(width) -> tuple[int, int]`
- [ ] Returns (line_index, column) in wrapped display
- [ ] Used for cursor marker placement

### D.3 Update Render for Wrapped Lines

- [ ] Render each logical line as potentially multiple display lines
- [ ] Place cursor marker at correct wrapped position
- [ ] Test: `test_long_line_wraps_at_width()`
- [ ] Test: `test_cursor_in_wrapped_segment()`
- [ ] Test: `test_wrap_preserves_ansi_codes()`

### D.4 Handle Resize

- [ ] On width change, re-wrap content
- [ ] Cursor stays with same character position
- [ ] Test: `test_resize_rewraps_content()`

### D.5 Commit Word Wrapping

- [ ] Run tests and lint
- [ ] Commit: `feat(input): add word wrapping for long lines`

---

## Phase E: Multi-line Input - Scrolling (PRD 96, Phase 4)

### E.1 Add Scroll State

- [ ] Add `self._scroll_offset = 0` to Input
- [ ] Add `MAX_INPUT_LINES = 5` constant
- [ ] Track how many display lines the input currently uses

### E.2 Calculate Visible Lines

- [ ] Add method `_get_visible_lines(width) -> list[str]`
- [ ] Returns only lines from scroll_offset to scroll_offset + MAX_INPUT_LINES
- [ ] Render only visible portion

### E.3 Scroll to Keep Cursor Visible

- [ ] When cursor moves, check if it's in visible range
- [ ] If not, adjust scroll_offset to bring cursor into view
- [ ] Test: `test_scroll_adjusts_when_cursor_moves_down()`
- [ ] Test: `test_scroll_adjusts_when_cursor_moves_up()`

### E.4 Page Up/Down

- [ ] Page Up: scroll_offset -= MAX_INPUT_LINES (min 0)
- [ ] Page Down: scroll_offset += MAX_INPUT_LINES (max total_lines - MAX_INPUT_LINES)
- [ ] Test: `test_page_up_scrolls_up()`
- [ ] Test: `test_page_down_scrolls_down()`

### E.5 Commit Scrolling

- [ ] Run tests and lint
- [ ] Commit: `feat(input): add scrolling for long multi-line input`

---

## Phase F: Final Integration & Polish

### F.1 Export Throbber

- [ ] Add Throbber to `src/interfaces/pypitui/__init__.py` exports
- [ ] Add Throbber to `src/interfaces/pypitui_cli.py` re-exports

### F.2 Update PRD Status

- [ ] Mark PRD 97 as complete
- [ ] Mark PRD 96 phases as complete
- [ ] Update summary checklist

### F.3 Full Test Suite

- [ ] Run: `uv run pytest tests/ -v`
- [ ] Verify all 650+ tests pass
- [ ] Check coverage report

### F.4 Manual E2E Test

- [ ] Run alfred
- [ ] Test multi-line input with 5+ lines
- [ ] Test throbber animation during response
- [ ] Test resize during typing
- [ ] Test paste of multi-line content
- [ ] Verify all features work together

### F.5 Final Commit

- [ ] Run: `uv run ruff check src/ && uv run mypy src/ && uv run pytest`
- [ ] Commit: `feat(cli): complete multi-line input and streaming throbber`
- [ ] Push: `git push origin feature/prd-95-pypitui-cli`

---

## Checklist Summary

| Phase | Items | Status |
|-------|-------|--------|
| A: Throbber | 25 | [ ] |
| B: Multi-line Basic | 20 | [ ] |
| C: Arrow Navigation | 20 | [ ] |
| D: Word Wrapping | 12 | [ ] |
| E: Scrolling | 12 | [ ] |
| F: Final Integration | 10 | [ ] |
| **Total** | **99** | **[ ]** |

---

## Dependencies

- pypitui must support Shift+Enter detection (verify first)
- pypitui `wrap_text_with_ansi()` must handle cursor tracking
- Terminal must report width correctly on resize

---

## Rollback Plan

If issues arise:
1. Throbber: Remove from StatusLine, keep Throbber class for later
2. Multi-line: Disable Shift+Enter handling, keep single-line mode
3. Each phase is independently commitable for easy revert
