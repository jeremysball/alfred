# PRD #83: Interactive Terminal Tool for AI Agent E2E Testing

**Status**: Complete
**Priority**: High
**Issue**: https://github.com/jeremysball/alfred/issues/83
**Created**: 2026-02-21

---

## Problem

AI coding agents cannot properly verify TUI (Terminal User Interface) applications:

1. **Limited to stdin piping** — Agents can send input to a process but cannot send keystrokes like arrow keys, Enter, Ctrl+C, or Tab
2. **No visual verification** — Agents cannot see terminal output as a human would (colors, layout, Rich formatting, cursor positioning)
3. **No interactive control** — Cannot navigate menus, respond to prompts, or interact with running CLIs

This makes developing and testing TUI apps like Alfred unreliable. The agent writes code but cannot verify it works correctly.

---

## Solution

Build an interactive terminal tool that gives AI agents:

1. **Full interactive control** — Send keystrokes (arrows, Enter, Esc, Ctrl+C) and text input
2. **Visual capture** — Take terminal screenshots as PNG images for vision models to analyze
3. **Text capture** — Extract plain text content for programmatic verification
4. **Session lifecycle** — Start, interact, capture, and exit terminal sessions

The tool will be available to the AI coding agent (pi) and potentially reusable by Alfred itself.

---

## Goals

- Enable end-to-end testing of TUI applications by AI agents
- Allow agents to visually verify UI elements (layout, colors, text, positioning)
- Support the full range of terminal interactions (navigation, input, control keys)
- Be model-agnostic — work with any LLM/vision model combination

---

## Non-Goals

- Building a general-purpose terminal automation framework (scope is TUI testing for AI agents)
- Supporting GUI applications (terminal only)
- Real-time streaming of terminal output (capture on demand is sufficient)
- Multi-session management (one session at a time is enough for MVP)

---

## Technical Approach

### Core Technology: VHS (Charmbracelet)

VHS is a terminal recording tool designed for this exact use case — programmable terminal sessions with output capture.

**Why VHS:**
- Designed for recording terminal sessions
- Supports keystroke simulation
- Can capture output as GIF, PNG, or text
- Active maintenance, good documentation

### Tool Interface

Single tool with actions (following established patterns):

```python
terminal(
    action: "start" | "send" | "capture" | "exit",
    command: str = None,       # for "start"
    keys: list[str] = None,    # for "send" - keystrokes
    text: str = None,          # for "send" - text input
    sleep_ms: int = None,      # for "send" - sleep duration in milliseconds
    wait_pattern: str = None,  # for "capture" - regex to wait for
)
```

**Actions:**
- `start` — Spawn a terminal session with the given command
- `send` — Send keystrokes, text, and/or sleep to the running session
- `capture` — Take a screenshot (PNG) and extract text; returns both
- `exit` — Terminate the session

### Output Format

The `capture` action returns:

```python
{
    "screenshot": "/path/to/screenshot.png",  # PNG image path
    "text": "plain text content of terminal", # Stripped ANSI
}
```

The agent can then:
- Display the screenshot to a vision model for visual analysis
- Parse the text for programmatic assertions
- Compare against expected output

---

## Use Cases

### UC1: Develop Alfred TUI Feature
1. Agent implements a new command in Alfred
2. Agent runs `terminal(action="start", command="alfred")`
3. Agent navigates to the new feature: `terminal(action="send", keys=["j", "j", "Enter"])`
4. Agent captures output: `terminal(action="capture")`
5. Agent verifies the UI is correct (visually and textually)
6. Agent exits: `terminal(action="exit")`

### UC2: Debug TUI Layout Issue
1. Agent receives bug report: "menu items are misaligned"
2. Agent starts Alfred and navigates to the menu
3. Agent captures screenshot
4. Agent analyzes the visual output to identify the layout problem
5. Agent fixes the code and repeats verification

### UC3: E2E Test Verification
1. Agent writes an e2e test for a TUI feature
2. Agent runs the test via terminal tool
3. Agent captures output at each step
4. Agent verifies the flow works as expected

---

## Milestones

- [x] **M1: Research & Prototype** — Evaluate VHS integration, test keystroke sending and capture capabilities
- [x] **M2: Core Tool Implementation** — Build `terminal` tool with start/send/capture/exit actions
- [x] **M3: Screenshot Capture** — Implement PNG capture with proper terminal emulation
- [x] **M4: Text Extraction** — Strip ANSI codes and extract plain text content
- [x] **M5: Integration with pi** — Add tool to the agent's available tools
- [x] **M6: Documentation** — Document tool usage with examples
- [x] **M7: Test with Alfred** — Verify the tool works with Alfred CLI for real workflows

---

## Success Criteria

- Agent can start Alfred and navigate its TUI interface
- Agent can capture screenshots that accurately represent the terminal display
- Agent can verify visual elements (layout, colors, text positioning)
- Agent can extract text content for assertions
- Tool works with any LLM/vision model combination
- Full e2e test workflow completes successfully

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| VHS may not support all terminal features | Test early with Alfred; fallback to pyte if needed |
| Screenshot quality may vary by terminal | Standardize on consistent terminal settings |
| Keystroke timing may cause flaky tests | Add configurable delays between keystrokes |
| Large screenshots may hit token limits | Optimize image size, consider compression |

---

## Dependencies

- VHS installed in the environment (via Go or package manager)
- Vision model capability in the agent (for visual analysis)
- Terminal emulator compatibility (VT100/ANSI standard)

---

## Open Questions

1. ~~Should the tool support multiple concurrent sessions, or is single-session sufficient?~~ → **Resolved**: Single-session sufficient for MVP
2. What's the optimal screenshot resolution for vision models?
3. ~~Should there be a "wait" action for slow-rendering TUIs?~~ → **Resolved**: Use VHS `Wait /pattern/` command
4. Do we need to support mouse interactions (rare for CLIs but possible)?

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-21 | Use `VHS_NO_SANDBOX=true` | Required in containerized/restricted environments where Chrome sandbox fails |
| 2026-02-21 | Single-session for MVP | Tape file approach generates one session at a time; simpler implementation |
| 2026-02-21 | Use `Wait /pattern/` for timing | VHS supports regex-based waiting; better than fixed delays for slow TUIs |
| 2026-02-21 | Add `wait_pattern` parameter to capture | Allows optional regex-based waiting before screenshot; falls back to 500ms sleep |
| 2026-02-21 | Add `sleep_ms` parameter to send | Allows timing control for slow operations (e.g., LLM responses need 10+ seconds) |
| 2026-02-21 | Document arrow key limitation | VHS sends escape codes that prompt_toolkit doesn't interpret; use text input only |

## Known Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| Arrow key navigation | Escape codes not interpreted by prompt_toolkit in VHS terminal | Use text input only; avoid line editing |
| LLM response timing | Requires explicit sleep for responses | Use `sleep_ms=10000+` for LLM calls |

---

## References

- VHS: https://github.com/charmbracelet/vhs
- Related: Alfred ROADMAP (TUI testing needs)
