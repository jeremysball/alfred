# PRD: PyPiTUI CLI for Alfred

**Status**: In Progress
**Priority**: High
**Created**: 2026-02-26

---

## Problem Statement

Alfred needs a new CLI built on PyPiTUI. The critical feature is **scrollback** — users must be able to scroll through conversation history using their terminal's native scrollback buffer (Shift+PgUp, mouse wheel).

Current state:
- Old prompt_toolkit + rich implementation was removed
- No CLI exists
- `src/cli/main.py` imports `src.interfaces.pypitui_cli` which doesn't exist

---

## Solution Overview

Build a minimal CLI using PyPiTUI with:

1. **Native scrollback** — Content flows into terminal's scrollback buffer automatically
2. **Differential rendering** — Only changed lines update (no flickering)
3. **Streaming responses** — Real-time LLM output with smooth updates
4. **Status line** — Model name and token counts
5. **Input queue** — Messages typed during streaming are queued

---

## Architecture

### Component Hierarchy

```
AlfredTUI
├── ProcessTerminal
├── TUI (single instance, reused)
├── conversation: Container
│   ├── MessagePanel (user)
│   ├── MessagePanel (assistant, streaming)
│   ├── ToolCallPanel (inline)
│   └── ...
├── status_line: StatusLine
└── input_field: Input
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Scrollback | PyPiTUI built-in | Uses relative cursor movement, content flows to scrollback |
| TUI instance | Single, reused | Preserves `_previous_lines` for differential rendering |
| **NEVER clear** | No `tui.clear()` | Messages accumulate forever, flow into scrollback |
| Streaming | Update Text component | Call `request_render()` after each chunk |
| Tool display | Inline, dimmed | Simple, non-intrusive |
| Input during stream | Queue | Messages sent after streaming completes |

---

## Implementation TODO

> **TDD Workflow**: Write test first, run it (fail), implement, run test (pass), refactor.
>
> **Test locations**:
> - Unit tests: `tests/test_pypitui_cli.py`
> - E2E tests: `tests/e2e/test_cli_e2e.py` (uses tmux interactive)
>
> **Run tests**: `uv run pytest tests/test_pypitui_cli.py -v`

---

## Phase 1: Basic REPL

### 1.0 Test Setup

- [x] Create `tests/test_pypitui_cli.py`
- [x] Add pytest imports and fixtures
- [x] Create `MockAlfred` fixture that yields fake responses
- [x] Create `MockTerminal` setup (use pypitui's `MockTerminal`)

### 1.1 AlfredTUI Class Skeleton

**Tests first:**
- [x] `test_alfred_tui_init_creates_components()` — Verify `__init__` creates `conversation`, `status_line`, `input_field`
- [x] `test_alfred_tui_has_tui_instance()` — Verify single TUI instance exists
- [x] `test_alfred_tui_never_clears()` — Verify class has no `clear` method, no calls to `tui.clear()`

**Implementation:**
- [x] Create `src/interfaces/pypitui_cli.py`
- [x] Add `AlfredTUI.__init__(self, alfred: Alfred)`
- [x] Initialize `ProcessTerminal` and `TUI`
- [x] Create `self.conversation = Container()`
- [x] Create `self.input_field = Input(placeholder="...")`
- [x] Add children to TUI: conversation, spacer, input
- [x] Set focus to input field
- [x] Wire `input_field.on_submit = self._on_submit`

### 1.2 Main Loop

**Tests first:**
- [x] `test_run_yields_to_event_loop()` — Verify `run()` calls `await asyncio.sleep()`
- [x] `test_run_reads_terminal_input()` — Verify `terminal.read_sequence()` called
- [x] `test_run_handles_input()` — Verify `tui.handle_input()` called with data
- [x] `test_run_renders_frames()` — Verify `tui.render_frame()` called
- [x] `test_run_exits_on_running_false()` — Verify loop exits when `self.running = False`

**Implementation:**
- [x] Add `self.running = True` in `__init__`
- [x] Implement `async def run(self) -> None`
- [x] Call `tui.start()` at beginning
- [x] Add `try/finally` with `tui.stop()` in finally
- [x] Loop while `self.running`
- [x] Read input: `data = terminal.read_sequence(timeout=0.01)`
- [x] If data, call `tui.handle_input(data)`
- [x] Call `tui.request_render()` and `tui.render_frame()`
- [x] `await asyncio.sleep(0.016)` (~60fps)

### 1.3 Input Handling

**Tests first:**
- [x] `test_on_submit_adds_user_message()` — Verify user message added to conversation
- [x] `test_on_submit_clears_input()` — Verify input field cleared after submit
- [x] `test_on_submit_ignores_empty()` — Verify empty/whitespace ignored
- [x] `test_on_submit_starts_response_task()` — Verify asyncio task created for response

**Implementation:**
- [x] Implement `def _on_submit(self, text: str) -> None`
- [x] Strip whitespace, return if empty
- [x] Create `MessagePanel(role="user", content=text)` — Using Text for now, MessagePanel in Phase 1.5
- [x] `self.conversation.add_child(panel)`
- [x] Clear input: `self.input_field.set_value("")`
- [x] Create task: `asyncio.create_task(self._send_message(text))`

### 1.4 Response Handling (Non-Streaming First)

**Tests first:**
- [x] `test_send_message_adds_assistant_panel()` — Verify assistant panel created
- [x] `test_send_message_calls_alfred_chat_stream()` — Verify `alfred.chat_stream()` called
- [x] `test_send_message_updates_assistant_content()` — Verify panel content updated

**Implementation:**
- [x] Implement `async def _send_message(self, text: str) -> None`
- [x] Create `Text` for assistant message (MessagePanel integrated in Phase 1.8)
- [x] Add to conversation
- [x] Iterate `alfred.chat_stream(text)`:
  - [x] Accumulate chunks
  - [x] Call `text.set_content(accumulated)`
  - [x] Call `tui.request_render()`
- [x] Handle exceptions: show error in panel

### 1.5 MessagePanel Component (Component Only)

> **Note**: Build the component here, integrate it in Phase 1.8.

**Tests first:**
- [x] `test_message_panel_renders_with_title()` — Verify "You" or "Alfred" in title
- [x] `test_message_panel_user_has_cyan_border()` — Verify cyan styling for user
- [x] `test_message_panel_assistant_has_green_border()` — Verify green styling for assistant
- [x] `test_message_panel_error_has_red_border()` — Verify red styling for error state
- [x] `test_message_panel_set_content_updates()` — Verify `set_content()` changes rendered text
- [x] `test_message_panel_wraps_long_content()` — Verify Text handles wrapping (no special handling needed)

**Implementation:**
- [x] Create `class MessagePanel(BorderedBox)`
- [x] `__init__(self, role: Literal["user", "assistant"], content: str = "")`
- [x] Set title based on role: "You" / "Alfred"
- [x] Set border style: cyan for user, green for assistant (default)
- [x] Store `self._role` and `self._content`
- [x] Add `Text` child for content (Text handles wrapping internally)
- [x] `def set_content(self, text: str) -> None` — Clear children, add new Text
- [x] `def set_error(self, error_msg: str) -> None` — Set red border, show error text

### 1.6 Entry Point Integration

**Tests first:**
- [x] `test_main_imports_pypitui_cli()` — Verify `src.cli.main` can import `AlfredTUI`
- [x] `test_run_chat_creates_interface()` — Verify `_run_chat()` instantiates `AlfredTUI`

**Implementation:**
- [x] Update `src/interfaces/__init__.py` to export `AlfredTUI`
- [x] Verify `src/cli/main.py` imports and uses `AlfredTUI`
- [x] Run `alfred` command manually, verify basic REPL works

### 1.7 Manual Validation

- [x] Run `alfred`
- [x] Type "Hello"
- [x] Verify response appears
- [x] Press Ctrl+C
- [x] Verify clean exit (terminal restored)

### 1.8 MessagePanel Integration

> **Note**: Replace simple `Text` components with `MessagePanel` in AlfredTUI.

**Tests first:**
- [x] `test_on_submit_uses_message_panel()` — Verify user messages use MessagePanel
- [x] `test_send_message_uses_message_panel()` — Verify assistant messages use MessagePanel
- [x] `test_error_sets_red_border()` — Verify errors trigger `set_error()` on panel

**Implementation:**
- [x] Update `_on_submit()` to create `MessagePanel(role="user", content=text)`
- [x] Update `_send_message()` to create `MessagePanel(role="assistant")`
- [x] Update `_send_message()` to call `panel.set_content()` for streaming
- [x] Update `_send_message()` to call `panel.set_error()` on exception

---

## Phase 1.9: Ctrl-C Clear Input Then Exit

### Problem

Currently, Ctrl-C exits Alfred immediately. This can lead to accidental exits when the user meant to clear the input field. A common pattern in CLI tools is: first Ctrl-C clears input, second Ctrl-C exits.

### Behavior Specification

| State | Input Content | Action | Result |
|-------|---------------|--------|--------|
| Normal | Has text | Ctrl-C | Clear input, show hint |
| Normal | Empty | Ctrl-C | Show hint "Press Ctrl-C again to exit" |
| Pending exit | Any | Ctrl-C | Exit Alfred |
| Pending exit | Any | Any other key | Clear hint, return to Normal |

**Key rules:**
- No timeout window — second Ctrl-C works anytime
- Any non-Ctrl-C key resets to Normal state
- Visual feedback shows hint after first Ctrl-C
- Consistent behavior whether input has text or not

### Tests First

- [x] `test_ctrl_c_clears_input_when_has_text()` — Verify input cleared, hint shown
- [x] `test_ctrl_c_shows_hint_when_input_empty()` — Verify hint shown even with empty input
- [x] `test_second_ctrl_c_exits()` — Verify `running = False` after two Ctrl-C presses
- [x] `test_other_key_resets_ctrl_c_state()` — Verify any other key clears hint, resets state
- [x] `test_ctrl_c_state_persists_across_frames()` — Verify state doesn't auto-reset

### Implementation

- [x] Add `self._ctrl_c_pending = False` state flag in `__init__`
- [x] Update Ctrl-C handler in `run()`:
  - If `_ctrl_c_pending` is True: set `running = False`, exit
  - Else: clear input, set `_ctrl_c_pending = True`, show hint in status line
- [x] Add input listener that resets `_ctrl_c_pending = False` on any non-Ctrl-C key
- [x] Clear hint from status line when state resets

### Status Line Hint

> **Note**: Requires Phase 3 StatusLine component. The `_exit_hint_visible` flag is ready; display deferred to Phase 3.

After first Ctrl-C, show in status line:

```
Press Ctrl-C again to exit
```

Use a subtle/dimmed style (not alarming). Clear the hint when:
- Second Ctrl-C exits
- Any other key is pressed
- User starts typing

### Manual Validation

- [x] Type some text, press Ctrl-C → input cleared, hint appears
- [x] Press Ctrl-C again → Alfred exits
- [x] Type text, press Ctrl-C, type more → hint disappears, input has new text
- [x] Press Ctrl-C with empty input → hint appears
- [x] Press Ctrl-C, wait 10 seconds, press Ctrl-C → still exits (no timeout)

---

## Phase 2: Scrollback Verification

### 2.1 Scrollback Test (E2E)

**E2E test:**
- [x] Create `tests/e2e/test_cli_scrollback.py`
- [x] Launch Alfred in tmux session: `tmux new-session -d -s alfred "alfred"`
- [x] Send 25 messages in a loop using `tmux send-keys`
- [x] Capture terminal output: `tmux capture-pane -t alfred -p`
- [x] Verify early messages visible in captured output
- [x] Clean up: `tmux kill-session -t alfred`

### 2.2 Manual Validation

- [x] Run `alfred`
- [x] Send 20+ messages (use a loop script if helpful)
- [x] Press Shift+PgUp
- [x] Verify earlier messages visible
- [x] Scroll back down
- [x] Verify can still type and get responses

### 2.3 Long Response Test

**E2E test:**
- [x] `test_long_response_flows_to_scrollback()` — Send message that triggers 50+ line response
- [x] Verify content flows past viewport

**Manual:**
- [x] Ask for a long response ("Write a poem with 10 stanzas")
- [x] Verify text flows smoothly
- [x] Verify can scroll back to beginning of response

---

## Phase 3: Status Line

### 3.1 StatusLine Component

**Tests first:**
- [x] `test_status_line_init_empty()` — Verify initial state with no data
- [x] `test_status_line_render_model()` — Verify model name rendered
- [x] `test_status_line_render_tokens()` — Verify token counts formatted (1.2K, 345)
- [x] `test_status_line_hides_zero_ctx()` — Verify ctx hidden when 0
- [x] `test_status_line_hides_zero_cached()` — Verify cached hidden when 0
- [x] `test_status_line_hides_zero_reasoning()` — Verify reasoning hidden when 0
- [x] `test_status_line_shows_cached_when_nonzero()` — Verify cached shown when > 0
- [x] `test_status_line_shows_reasoning_when_nonzero()` — Verify reasoning shown when > 0
- [x] `test_status_line_render_exit_hint()` — Verify exit hint when flag set
- [x] `test_status_line_format_groups()` — Verify format: model | tokens | cache
- [x] `test_status_line_no_cache_group_when_all_zero()` — Verify cache group omitted when all zero
- [x] `test_format_tokens_*` — Verify token formatting (123, 1.2K, 12K, 1M)

**Implementation:**
- [x] Create `class StatusLine(Component)`
- [x] `__init__()` — Initialize empty state
- [x] `def update(model, ctx, in_tokens, out_tokens, cached, reasoning, exit_hint=False)`
- [x] `def render(width: int) -> list[str]` — Build status string
- [x] Format: `model | ctx N in N out N | cached N reasoning N`
- [x] Hide ctx/cached/reasoning when 0
- [x] Show dimmed "Press Ctrl-C again to exit" when exit_hint=True

### 3.2 StatusLine in AlfredTUI

**Tests first:**
- [x] `test_alfred_tui_has_status_line_instance()` — Verify status_line instance exists
- [x] `test_status_updates_during_streaming()` — Verify status updated during streaming
- [x] `test_status_shows_exit_hint()` — Verify exit hint shows in status line

**Implementation:**
- [x] Add `self.status_line = StatusLine()` in `AlfredTUI.__init__`
- [x] Add to TUI after conversation, before input
- [x] Add `_update_status(estimated_out=None)` method
- [x] In `_send_message`, call `_update_status(estimated_out)` every chunk
- [x] Estimate output tokens during streaming: `len(accumulated) // 4`
- [x] Final update after stream with actual token counts

### 3.3 Manual Validation

- [x] Run `alfred`
- [x] Send message
- [x] Verify status line shows model name and token counts
- [x] Send another message
- [x] Verify counts update

---

## Phase 3 COMPLETE ✅

---

## Phase 4: Tool Call Display

### 4.1 ToolCallPanel Component

**Tests first:**
- [x] `test_tool_call_panel_shows_tool_name()` — Verify tool name in title
- [x] `test_tool_call_panel_running_style()` — Verify dim blue border when running
- [x] `test_tool_call_panel_success_style()` — Verify dim green border on success
- [x] `test_tool_call_panel_error_style()` — Verify dim red border on error
- [x] `test_tool_call_panel_append_output()` — Verify output accumulates
- [x] `test_tool_call_panel_truncates_long_output()` — Verify output truncated to ~500 chars

**Implementation:**
- [x] Create `class ToolCallPanel(BorderedBox)`
- [x] `__init__(self, tool_name: str, tool_call_id: str)`
- [x] Set dim styling (not as prominent as messages)
- [x] `self._output = ""`
- [x] `def append_output(self, chunk: str)` — Accumulate, truncate if needed
- [x] `def set_status(self, status: Literal["running", "success", "error"])` — Update border color

### 4.2 Tool Callback Integration

**Tests first:**
- [x] `test_tool_callback_creates_panel_on_start()` — Verify `ToolStart` creates panel
- [x] `test_tool_callback_appends_on_output()` — Verify `ToolOutput` appends to panel
- [x] `test_tool_callback_finalizes_on_end()` — Verify `ToolEnd` sets final status
- [x] `test_tool_callback_error_style()` — Verify error sets red border

**Implementation:**
- [x] Add `self._tool_panels: dict[str, ToolCallPanel] = {}` in `AlfredTUI.__init__`
- [x] Implement `def _tool_callback(self, event: ToolEvent) -> None`
- [x] On `ToolStart`: create panel, add to conversation, store in dict
- [x] On `ToolOutput`: get panel from dict, call `append_output()`
- [x] On `ToolEnd`: get panel, call `set_status()`, remove from dict
- [x] Pass `tool_callback=self._tool_callback` to `alfred.chat_stream()`

### 4.3 Manual Validation

- [x] Run `alfred`
- [x] Say "Remember that my favorite color is blue"
- [x] Verify tool call panel appears inline
- [x] Verify panel shows tool name (e.g., "remember")
- [x] Verify panel shows success/error status
- [x] Say "What's my favorite color?"
- [x] Verify another tool call (search_memories) appears

---

## Phase 4 COMPLETE ✅

---

## Phase 4.5: Toast Notifications

**Problem**: Python logging warnings/errors go to stdout/stderr and clobber the TUI display.
Example: `WARNING:src.search:Context exceeds budget: 130000 > 128000 tokens, truncating`

**Solution**: Custom logging handler that routes WARNING+ logs to toast notifications displayed
at the bottom of the screen (overlay-style). Toasts fade after N seconds or on any keypress.

**Design Decisions:**
- Position: Bottom of screen, above status line (overlay-style)
- Dismissal: Auto-expire OR any keypress dismisses all visible toasts
- Styling: Colored prefix (⚠ yellow for warning, ✗ red for error)
- Max visible: 3 toasts (oldest discarded)

**Constants (no magic numbers):**
```python
TOAST_DURATION_SECONDS = 4  # Auto-dismiss after this time
MAX_VISIBLE_TOASTS = 3      # Maximum toasts on screen
```

### 4.5.1 ToastMessage Data Class

**Tests first:**
- [ ] `test_toast_message_defaults()` — Verify created timestamp auto-populated
- [ ] `test_toast_message_levels()` — Verify warning/error/info levels work

**Implementation:**
- [ ] Create `@dataclass ToastMessage`
- [ ] `message: str`
- [ ] `level: Literal["warning", "error", "info"]`
- [ ] `created: datetime = field(default_factory=...)`

### 4.5.2 ToastHandler (logging.Handler)

**Tests first:**
- [ ] `test_toast_handler_captures_warning()` — Verify WARNING logs create toast
- [ ] `test_toast_handler_captures_error()` — Verify ERROR logs create toast
- [ ] `test_toast_handler_ignores_info()` — Verify INFO logs don't create toast (optional)
- [ ] `test_toast_handler_filters_non_src()` — Verify only src.* modules captured

**Implementation:**
- [ ] Create `class ToastHandler(logging.Handler)`
- [ ] Add filter for `src.*` modules only
- [ ] `emit()` converts LogRecord to ToastMessage, calls callback
- [ ] Format: "module: message" (strip src. prefix)

### 4.5.3 ToastContainer Component

**Tests first:**
- [ ] `test_toast_container_empty_on_init()` — Verify no toasts initially
- [ ] `test_toast_container_add_toast()` — Verify toast added and rendered
- [ ] `test_toast_container_max_toasts()` — Verify only MAX_VISIBLE_TOASTS shown
- [ ] `test_toast_container_colors()` — Verify yellow for warning, red for error
- [ ] `test_toast_container_expiry()` — Verify old toasts removed after TOAST_DURATION_SECONDS
- [ ] `test_toast_container_dismiss_on_key()` — Verify all toasts cleared on keypress

**Implementation:**
- [ ] Create `class ToastContainer(Component)`
- [ ] `self._toasts: list[ToastMessage]`
- [ ] `def add_toast(self, toast: ToastMessage)` — Add, enforce MAX_VISIBLE_TOASTS
- [ ] `def prune_expired()` — Remove toasts older than TOAST_DURATION_SECONDS
- [ ] `def dismiss_all()` — Clear all toasts (called on keypress)
- [ ] `def render(width)` — Return lines with colored prefixes, bottom-positioned

### 4.5.4 AlfredTUI Integration

**Tests first:**
- [ ] `test_alfred_tui_has_toast_container()` — Verify container in layout
- [ ] `test_toast_handler_registered()` — Verify handler added to logging
- [ ] `test_keypress_dismisses_toasts()` — Verify any key calls dismiss_all()

**Implementation:**
- [ ] Add `self.toast_container = ToastContainer()` in `AlfredTUI.__init__`
- [ ] Position at bottom: above status_line, below conversation
- [ ] Create `ToastHandler` with callback to `toast_container.add_toast()`
- [ ] Register handler: `logging.getLogger().addHandler(toast_handler)`
- [ ] In `run()` loop, call `toast_container.prune_expired()` each frame
- [ ] On any keypress (except Ctrl-C), call `toast_container.dismiss_all()`

### 4.5.5 Manual Validation

- [ ] Run `alfred`
- [ ] Trigger a warning (e.g., exceed context budget with long conversation)
- [ ] Verify toast appears at bottom with yellow "⚠" prefix
- [ ] Verify toast disappears after ~4 seconds
- [ ] Trigger another warning, then press any key
- [ ] Verify toast dismissed immediately on keypress
- [ ] Trigger an error (if possible)
- [ ] Verify toast appears with red "✗" prefix

---

## Phase 5: Input Queue

### 5.1 Queue Mechanism

**Tests first:**
- [ ] `test_queue_empty_on_init()` — Verify queue starts empty
- [ ] `test_queue_message_during_streaming()` — Verify message queued when streaming
- [ ] `test_queue_processed_after_stream()` — Verify queued messages sent after stream ends
- [ ] `test_queue_multiple_messages()` — Verify multiple messages queue and send in order

**Implementation:**
- [ ] Add `self._message_queue: list[str] = []` in `__init__`
- [ ] Add `self._is_streaming = False` in `__init__`
- [ ] In `_on_submit`:
  - [ ] If `self._is_streaming`: append to queue, update status line
  - [ ] Else: create task as before
- [ ] In `_send_message`:
  - [ ] Set `self._is_streaming = True` at start
  - [ ] Set `self._is_streaming = False` at end
  - [ ] After end, check queue and send first message if any

### 5.2 Status Line Queue Indicator

**Tests first:**
- [ ] `test_status_line_shows_queue_count()` — Verify "queued:2" appears

**Implementation:**
- [ ] In `_on_submit`, call `self.status_line.update(..., queued=len(self._message_queue))`
- [ ] After processing queue, update status with `queued=0`

### 5.3 Manual Validation

- [ ] Run `alfred`
- [ ] Send message
- [ ] While streaming, type another message and press Enter
- [ ] Verify status shows "queued:1"
- [ ] Wait for first response to complete
- [ ] Verify second message sends automatically
- [ ] Verify status clears queue count

---

## Phase 6: Polish & Edge Cases

### 6.1 Clean Exit

**Tests first:**
- [ ] `test_ctrl_c_sets_running_false()` — Verify Ctrl+C sets `running = False`
- [ ] `test_ctrl_c_calls_tui_stop()` — Verify `tui.stop()` called on exit

**Implementation:**
- [ ] Add input listener for Ctrl+C: `tui.add_input_listener(self._intercept_ctrl_c)`
- [ ] `_intercept_ctrl_c` sets `self.running = False` and returns `{"consume": True}`
- [ ] Ensure `tui.stop()` always called in `finally` block

### 6.2 Empty Message Handling

**Tests first:**
- [ ] `test_empty_message_ignored()` — Verify whitespace-only ignored
- [ ] `test_message_trimmed()` — Verify leading/trailing whitespace stripped

**Implementation:**
- [ ] Already covered in Phase 1.3

### 6.3 Terminal Resize

**Tests first:**
- [ ] `test_resize_updates_width()` — Verify TUI adapts to new width
- [ ] `test_resize_preserves_content()` — Verify messages not lost on resize

**Implementation:**
- [ ] PyPiTUI handles this automatically via `terminal.get_size()` in render
- [ ] Verify no manual intervention needed

### 6.4 Streaming Error Handling

**Tests first:**
- [ ] `test_streaming_error_shows_in_panel()` — Verify error message in assistant panel
- [ ] `test_streaming_error_clears_streaming_state()` — Verify `_is_streaming = False` even on error

**Implementation:**
- [ ] Wrap streaming loop in `try/except`
- [ ] On exception, set panel content to error message
- [ ] Always set `_is_streaming = False` in `finally`

### 6.5 Very Long Messages

**Tests first:**
- [ ] `test_long_message_wraps()` — Verify 500+ char message wraps properly
- [ ] `test_message_panel_handles_multiline()` — Verify newlines preserved

**Implementation:**
- [ ] MessagePanel uses `Text` which wraps automatically
- [ ] Verify no special handling needed

### 6.6 Manual Edge Case Validation

- [ ] Send empty message (Enter with no text) — should do nothing
- [ ] Send message with 1000 characters — should wrap
- [ ] Disconnect network, send message — should show error
- [ ] Resize terminal while streaming — should adapt
- [ ] Press Ctrl+C during streaming — should exit cleanly

---

## Phase 7: Final Integration

### 7.1 Full E2E Test

- [ ] Create `tests/e2e/test_cli_full.py`
- [ ] Launch Alfred in tmux
- [ ] Send message
- [ ] Verify response
- [ ] Trigger tool call
- [ ] Verify tool panel
- [ ] Queue message during streaming
- [ ] Verify queue processed
- [ ] Scroll back
- [ ] Verify history visible
- [ ] Exit with Ctrl+C
- [ ] Verify clean exit

### 7.2 Documentation

- [ ] Update README with CLI usage
- [ ] Document keyboard shortcuts (Ctrl+C to exit)
- [ ] Document scrollback feature (Shift+PgUp)

### 7.3 Cleanup

- [ ] Remove any debug prints
- [ ] Add type hints to all methods
- [ ] Run `uv run ruff check src/interfaces/pypitui_cli.py`
- [ ] Run `uv run mypy src/interfaces/pypitui_cli.py`
- [ ] Run full test suite: `uv run pytest`

---

## Summary Checklist

| Phase | Tests | Implementation | Manual | Done |
|-------|-------|----------------|--------|------|
| 1. Basic REPL | 15 tests | 6 sections | 1 validation | [ ] |
| 2. Scrollback | 2 tests | — | 2 validations | [ ] |
| 3. Status Line | 5 tests | 2 sections | 1 validation | [ ] |
| 4. Tool Calls | 9 tests | 2 sections | 1 validation | [ ] |
| 5. Input Queue | 4 tests | 1 section | 1 validation | [ ] |
| 6. Polish | 8 tests | 4 sections | 6 validations | [ ] |
| 7. Final | 1 E2E | Documentation | Cleanup | [ ] |

---

## Code Structure

```
src/interfaces/
├── __init__.py
├── pypitui_cli.py       # Main CLI implementation
├── telegram.py          # Existing Telegram interface
└── notification_buffer.py

src/interfaces/pypitui_cli.py:
├── AlfredTUI            # Main class
│   ├── __init__(alfred)
│   ├── run() -> None
│   ├── _on_submit(text)
│   ├── _stream_response(user_input)
│   └── _update_status()
├── MessagePanel         # Conversation message
│   ├── __init__(role, content)
│   └── set_content(text)
├── ToolCallPanel        # Tool execution display
│   ├── __init__(tool_name)
│   └── append_output(chunk)
└── StatusLine           # Status bar
    └── update(model, tokens)
```

---

## Integration Points

### Alfred.chat_stream()

```python
async def chat_stream(
    self,
    message: str,
    tool_callback: Callable[[ToolEvent], None] | None = None,
    session_id: str | None = None,
) -> AsyncIterator[str]:
```

CLI will:
- Pass `tool_callback` to receive `ToolStart`, `ToolOutput`, `ToolEnd`
- Iterate over chunks for streaming response
- Use `session_id=None` for CLI session

### Agent Tool Events

```python
@dataclass
class ToolStart(ToolEvent):
    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any]

@dataclass
class ToolOutput(ToolEvent):
    tool_call_id: str
    tool_name: str
    chunk: str

@dataclass
class ToolEnd(ToolEvent):
    tool_call_id: str
    tool_name: str
    result: str
    is_error: bool
```

---

## Entry Point

Update `src/cli/main.py`:

```python
async def _run_chat(alfred: Alfred) -> None:
    """Run interactive CLI chat."""
    from src.interfaces.pypitui_cli import AlfredTUI

    interface = AlfredTUI(alfred)
    await alfred.start()
    await interface.run()
```

---

## Styling

### Message Panels

| Role | Border | Title |
|------|--------|-------|
| User | Cyan | "You" |
| Assistant | Green | "Alfred" |

### Tool Call Panels

| State | Style |
|-------|-------|
| Running | Dim blue border |
| Success | Dim green border |
| Error | Dim red border |

### Status Line

```
kimi/moonshot-v1 | in:1.2K | out:345 | ⏳ streaming...
```

---

## Dependencies

Already in `pyproject.toml`:
- `pypitui[rich]` — Terminal UI with Rich integration

---

## Testing Strategy

### Manual Testing

1. **Basic REPL**
   ```bash
   alfred
   # Type: "Hello"
   # Expect: Response appears
   # Press: Ctrl+C
   # Expect: Clean exit
   ```

2. **Scrollback**
   ```bash
   alfred
   # Send 20+ messages
   # Press: Shift+PgUp
   # Expect: Earlier messages visible
   ```

3. **Streaming**
   ```bash
   alfred
   # Type: "Write a long story"
   # Expect: Text appears smoothly as it streams
   ```

4. **Tool Calls**
   ```bash
   alfred
   # Type: "Remember that my favorite color is blue"
   # Expect: Tool call panel appears inline
   ```

5. **Input Queue**
   ```bash
   alfred
   # While streaming, type another message and press Enter
   # Expect: Message queued, sent after streaming completes
   ```

### E2E Testing

Use tmux interactive for automated terminal testing:

```bash
# Launch Alfred in tmux
tmux new-session -d -s alfred "alfred"

# Send input
tmux send-keys -t alfred "Hello" Enter

# Wait for response
sleep 2

# Capture output
tmux capture-pane -t alfred -p > /tmp/alfred_output.txt

# Verify output contains expected text
grep -q "Hello" /tmp/alfred_output.txt && echo "PASS" || echo "FAIL"

# Clean up
tmux kill-session -t alfred
```

---

## Success Criteria

- [ ] Basic REPL works (input → response)
- [ ] Scrollback shows conversation history
- [ ] Streaming is smooth (no flickering)
- [ ] Status line displays model and tokens
- [ ] Tool calls appear inline
- [ ] Input queue works during streaming
- [ ] Clean exit on Ctrl+C
- [ ] No crashes on edge cases

---

## Out of Scope (Future PRDs)

- Session commands (`/new`, `/resume`, `/sessions`)
- Overlays (session list, help)
- Markdown rendering in messages
- Keyboard shortcuts beyond basic (Ctrl+L, etc.)
- Collapsible tool panels

---

## References

- PyPiTUI LLMS.md: `/workspace/pypitui/LLMS.md`
- PyPiTUI scrollback docs: `/workspace/pypitui/docs/scrollback-and-streaming.md`
- PyPiTUI demo: `/workspace/pypitui/examples/demo.py`
- Alfred core: `/workspace/alfred-prd/src/alfred.py`
- Agent loop: `/workspace/alfred-prd/src/agent.py`
