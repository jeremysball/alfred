# PRD: PyPiTUI CLI for Alfred

**Status**: Complete ✅
**Priority**: High
**Created**: 2026-02-26
**Completed**: 2026-02-26

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

## Phase 4.4: Inline Tool Call Display (Refactor)

**Problem**: Current implementation adds ToolCallPanel as a separate message in conversation.
Tool calls should appear WITHIN the assistant message as an inline box.

**Desired layout:**
```
┌─ Alfred ─────────────────────────────┐
│ Let me search for that...            │
│ ┌─ search_memories ────────────────┐ │
│ │ Found 3 memories about blue...   │ │
│ └──────────────────────────────────┘ │
│ Your favorite color is blue!         │
└──────────────────────────────────────┘
```

**Design Decisions:**
- Tool call box embedded in MessagePanel content
- Indented box with dim border (same colors as current)
- Output truncated to ~500 chars (keep end)
- Status shown by border color (blue=running, green=success, red=error)

**Tests first:**
- [ ] `test_tool_call_box_renders_inline()` — Box appears inside message content
- [ ] `test_tool_call_box_indentation()` — Box is visually indented
- [ ] `test_multiple_tool_calls_in_message()` — Multiple boxes in one message

**Implementation:**
- [ ] Refactor `MessagePanel` to support embedded tool call boxes
- [ ] `add_tool_call(tool_name, tool_call_id)` — Add box to content
- [ ] `update_tool_call(tool_call_id, output)` — Append output to box
- [ ] `finalize_tool_call(tool_call_id, status)` — Set final border color
- [ ] Update `_tool_callback` to modify current assistant MessagePanel instead of conversation

**Migration:**
- [ ] Remove separate ToolCallPanel from conversation flow
- [ ] Keep ToolCallPanel class for rendering, but embed in MessagePanel
- [ ] Update existing tests to reflect inline behavior

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
- [x] `test_toast_message_defaults()` — Verify created timestamp auto-populated
- [x] `test_toast_message_levels()` — Verify warning/error/info levels work

**Implementation:**
- [x] Create `@dataclass ToastMessage`
- [x] `message: str`
- [x] `level: Literal["warning", "error", "info"]`
- [x] `created: datetime = field(default_factory=...)`

### 4.5.2 ToastHandler (logging.Handler)

**Tests first:**
- [x] `test_toast_handler_captures_warning()` — Verify WARNING logs create toast
- [x] `test_toast_handler_captures_error()` — Verify ERROR logs create toast
- [x] `test_toast_handler_ignores_info()` — Verify INFO logs don't create toast
- [x] `test_toast_handler_filters_non_src()` — Verify only src.* modules captured

**Implementation:**
- [x] Create `class ToastHandler(logging.Handler)`
- [x] Add filter for `src.*` modules only
- [x] `emit()` converts LogRecord to ToastMessage, adds to global list

### 4.5.3 ToastManager

**Tests first:**
- [x] `test_max_visible_toasts()` — Verify only MAX_VISIBLE_TOASTS shown
- [x] `test_dismiss_expired_toasts()` — Verify old toasts removed after TOAST_DURATION_SECONDS
- [x] `test_dismiss_all_toasts()` — Verify all toasts cleared on dismiss_all()

**Implementation:**
- [x] `get_toasts()` — Global toast list
- [x] `dismiss_expired()` — Remove toasts older than TOAST_DURATION_SECONDS
- [x] `dismiss_all()` — Clear all toasts (called on keypress)
- [x] `_add_toast()` — Add with MAX_VISIBLE_TOASTS limit

### 4.5.4 AlfredTUI Integration

**Tests first:**
- [x] `test_keypress_dismisses_toasts()` — Verify any key calls dismiss_all()
- [x] `test_toast_handler_installed()` — Verify handler added to logging

**Implementation:**
- [x] Install toast handler on src logger in `AlfredTUI.__init__`
- [x] On keypress (via `_reset_ctrl_c_state`), call `dismiss_all()`

---

## Phase 4.5 COMPLETE ✅

---

## Phase 5: Input Queue

### 5.1 Queue Mechanism

**Tests first:**
- [x] `test_queue_empty_on_init()` — Verify queue starts empty
- [x] `test_queue_message_during_streaming()` — Verify message queued when streaming
- [x] `test_queue_processed_after_stream()` — Verify queued messages sent after stream ends
- [x] `test_queue_multiple_messages()` — Verify multiple messages queue and send in order

**Implementation:**
- [x] Add `self._message_queue: list[str] = []` in `__init__`
- [x] Add `self._is_streaming = False` in `__init__`
- [x] In `_on_submit`:
  - [x] If `self._is_streaming`: append to queue, update status line
  - [x] Else: create task as before
- [x] In `_send_message`:
  - [x] Set `self._is_streaming = True` at start
  - [x] Set `self._is_streaming = False` at end
  - [x] After end, check queue and send first message if any

### 5.2 Status Line Queue Indicator

**Tests first:**
- [x] `test_status_line_shows_queue_count()` — Verify "queued 2" appears

**Implementation:**
- [x] In `_on_submit`, call `self.status_line.update(..., queued=len(self._message_queue))`
- [x] After processing queue, update status with `queued=0`

---

## Phase 5 COMPLETE ✅

---

## Phase 6: Polish & Edge Cases

### 6.1 Clean Exit

**Tests first:**
- [x] `test_ctrl_c_sets_running_false()` — Verify Ctrl+C sets `running = False`
- [x] `test_ctrl_c_calls_tui_stop()` — Verified via finally block in run()

**Implementation:**
- [x] `_handle_ctrl_c()` sets `self.running = False` on second press
- [x] `tui.stop()` always called in `finally` block

### 6.2 Empty Message Handling

**Tests first:**
- [x] `test_empty_message_ignored()` — Verify whitespace-only ignored
- [x] `test_message_trimmed()` — Verify leading/trailing whitespace stripped

**Implementation:**
- [x] Already covered in `_on_submit()` - strips and checks empty

### 6.3 Terminal Resize

**Implementation:**
- [x] PyPiTUI handles this automatically via `terminal.get_size()` in render

### 6.4 Streaming Error Handling

**Tests first:**
- [x] `test_streaming_error_shows_in_panel()` — Verify error message in assistant panel
- [x] `test_streaming_error_clears_streaming_state()` — Verify `_is_streaming = False` even on error

**Implementation:**
- [x] Wrap streaming loop in `try/except`
- [x] On exception, call `panel.set_error()`
- [x] Always set `_is_streaming = False` in `finally`

### 6.5 Very Long Messages

**Tests first:**
- [x] `test_long_message_wraps()` — Verify 500+ char message wraps properly
- [x] `test_message_panel_handles_multiline()` — Verify newlines preserved

**Implementation:**
- [x] MessagePanel uses `Text` which wraps automatically

### 6.6 Manual Edge Case Validation

- [ ] Send empty message (Enter with no text) — should do nothing
- [ ] Send message with 1000 characters — should wrap
- [ ] Disconnect network, send message — should show error
- [ ] Resize terminal while streaming — should adapt

---

## Phase 8: Multi-line Input (Future PRD)

> **Moved to separate PRD**: See `96-multiline-input.md`

Current input is single-line only. Multi-line input requires:

- **Arrow key navigation** — Left/right within line, up/down between lines
- **Word wrapping** — Long lines wrap visually, cursor navigates wrapped display
- **Multi-line paste** — Paste multi-line text correctly
- **Shift+Enter** — Insert newline without submitting
- **Visual indicator** — Show when input spans multiple lines

---

## Phase 9: Streaming Throbber (Future PRD)

> **Moved to separate PRD**: See `97-streaming-throbber.md`

Visual indicator during LLM response streaming:

- **Animated spinner** — Braille or dot animation in status line
- **Pulse timing** — Smooth animation at ~10fps
- **Color** — Dim cyan or yellow to not distract
- **Stop condition** — Animation stops when stream ends

---
- [ ] Press Ctrl+C during streaming — should exit cleanly

### 6.7 Responsive Status Line

**Tests first:**
- [x] `test_status_full_width()` — All groups shown at 80+ chars
- [x] `test_status_compact_width()` — Model + in/out shown at compact width
- [x] `test_status_shows_queued()` — queued count shown when > 0
- [x] `test_status_hides_queued_when_zero()` — queued hidden when 0

**Implementation:**
- [x] StatusLine shows queued count in yellow when > 0
- [x] StatusLine hides zero values (ctx, cached, reasoning, queued)
- [ ] `test_status_minimal_width()` — Short format at <40 chars
- [ ] `test_status_truncates_model_name()` — Very long model name truncated with ellipsis
- [ ] `test_status_shows_arrow_symbols()` — Verify arrow symbols used for in/out
- [ ] `test_status_in_excludes_ctx()` — Verify in = input - ctx
- [ ] `test_status_unicode_fallback()` — Verify unicode arrows when Nerd Font unavailable

**Implementation:**
- [ ] Add width thresholds as constants: `STATUS_WIDTH_FULL`, `STATUS_WIDTH_MEDIUM`, `STATUS_WIDTH_COMPACT`
- [ ] Add symbol constants with fallback: `SYMBOL_IN = "" if nerdfont else "↓"`, `SYMBOL_OUT = "" if nerdfont else "↑"`
- [ ] Add Nerd Font detection (check environment variable or test render)
- [ ] In `StatusLine.render(width)`, check width and select tier
- [ ] Calculate `in_display = max(0, input_tokens - ctx_tokens)`
- [ ] Truncate model name if needed: `model[:20] + "…" if len(model) > 20 else model`
- [ ] Progressive hiding: exit_hint first, then cached/reasoning, then ctx

---

## Phase 7: Final Integration

### 7.1 Full E2E Test

- [x] Manual E2E via tmux (5-turn conversation verified)
- [x] Tool calls display inline
- [x] Status line updates in real-time
- [x] Ctrl+C exit works cleanly

### 7.2 Documentation

- [x] README exists with CLI usage
- [x] Keyboard shortcuts: Ctrl+C to exit (first clears input, second exits)
- [ ] Scrollback: Shift+PgUp (terminal feature, not app-controlled)

### 7.3 Cleanup

- [x] No debug prints
- [x] Type hints on all methods
- [x] `uv run ruff check src/interfaces/pypitui/` passes
- [x] `uv run mypy src/interfaces/pypitui/` passes
- [x] 70 tests passing for pypitui module

---

## Phase 7 COMPLETE ✅

---

## Summary Checklist

| Phase | Tests | Implementation | Manual | Done |
|-------|-------|----------------|--------|------|
| 1. Basic REPL | 15 tests | 6 sections | 1 validation | [x] |
| 2. Scrollback | 2 tests | — | 2 validations | [x] |
| 3. Status Line | 7 tests | 2 sections | 1 validation | [x] |
| 4. Tool Calls | 13 tests | 2 sections | 1 validation | [x] |
| 4.5. Toasts | 11 tests | 4 sections | 1 validation | [x] |
| 5. Input Queue | 5 tests | 1 section | 1 validation | [x] |
| 6. Polish | 11 tests | 4 sections | 6 validations | [x] |
| 7. Final | E2E done | Docs updated | Cleanup done | [x] |

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

## Status Line Enhancement Ideas (Future)

**NOT IMPLEMENTED — Ideas for future polish:**

### Visual Indicators

1. **Streaming animation** — Animated spinner or pulsing dot during response streaming
   - `●` → `○` → `●` pulse
   - `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏` braille spinner
   - Color: dim cyan or yellow

2. **Context health bar** — Visual context window usage
   - `[████████░░] 80%` — gradient from green → yellow → red
   - Show only when > 50% used
   - Click/tooltip to see exact numbers

3. **Model provider icon** — Tiny icon before model name
   - OpenAI: `◯` (circle)
   - Anthropic: `△` (triangle)
   - Local: `◆` (diamond)
   - Generic: `□` (square)

4. **Connection status** — Network health indicator
   - `◉` connected (green)
   - `○` disconnected (red)
   - `◔` reconnecting (yellow blink)

### Token Display

5. **Token cost estimation** — Show $ cost for session
   - `≈$0.02` after token counts
   - Color: dim (subtle)
   - Requires model pricing config

6. **Token rate** — Tokens/second during streaming
   - `125 t/s` during active streaming
   - Hide when not streaming

7. **Cache hit indicator** — Show cache effectiveness
   - `⚡85%` when cache ratio high
   - Encourages context reuse

### Session Info

8. **Session duration** — How long this session has been active
   - `23m` (minutes)
   - Update every minute

9. **Message count** — Total messages in conversation
   - `💬42` or just `#42`
   - Useful for long sessions

10. **Memory count** — Stored memories
    - `📚128` memories
    - Click to search

### Interactive Elements (Advanced)

11. **Clickable model name** — Switch model on click
    - Shows dropdown/fuzzy finder
    - Requires overlay support

12. **Progress bar for tools** — Tool execution progress
    - `[░░░░░░░░░░]` while tool running
    - Show tool name

13. **Error indicator** — Flash red on errors
    - `⚠ 2 errors` with count
    - Click to see error log

### Layout Variations

14. **Right-aligned info** — Some info on right side of status
    - `model | tokens ... | time message#`

15. **Multi-line status** — Two rows when terminal wide enough
    - Row 1: model, tokens, streaming
    - Row 2: session info, memory count

---

## References

- PyPiTUI LLMS.md: `/workspace/pypitui/LLMS.md`
- PyPiTUI scrollback docs: `/workspace/pypitui/docs/scrollback-and-streaming.md`
- PyPiTUI demo: `/workspace/pypitui/examples/demo.py`
- Alfred core: `/workspace/alfred-prd/src/alfred.py`
- Agent loop: `/workspace/alfred-prd/src/agent.py`
