# pi Extensions

Custom tools for the pi coding agent.

## Available Extensions

### terminal

Interactive terminal control for E2E testing of TUI applications.

Uses VHS (Charmbracelet) to provide:
- Full keystroke simulation (arrows, Enter, Ctrl+C, etc.)
- Screenshot capture (PNG)
- Plain text extraction

#### Actions

##### start
Start a terminal session.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| command | string | Yes | Shell command to run |

##### send
Send input to the session.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | No | Text to type |
| keys | string[] | No | Keystrokes (e.g., "Enter", "Up", "Ctrl+C") |
| sleep_ms | number | No | Milliseconds to wait after sending |

##### capture
Capture current terminal state.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| wait_pattern | string | No | Regex to wait for before capturing |

Returns:
```json
{
  "screenshot": "/path/to/screenshot.png",
  "text": "plain text content"
}
```

##### exit
Terminate the session and cleanup temp files.

#### Example Workflows

**Basic Message Flow:**
```
1. terminal(action="start", command="uv run alfred")
2. terminal(action="send", text="hello", keys=["Enter"], sleep_ms=10000)
3. terminal(action="capture")
4. terminal(action="send", text="exit", keys=["Enter"])
5. terminal(action="exit")
```

**Multiple Captures:**
```
1. terminal(action="start", command="htop")
2. terminal(action="capture")  # Initial state
3. terminal(action="send", keys=["Down", "Down"], sleep_ms=500)
4. terminal(action="capture")  # After navigation
5. terminal(action="send", keys=["q"])  # Quit htop
6. terminal(action="exit")
```

**Testing a CLI Prompt:**
```
1. terminal(action="start", command="my-cli --interactive")
2. terminal(action="capture")
3. terminal(action="send", text="option1", keys=["Enter"], sleep_ms=2000)
4. terminal(action="capture")
5. terminal(action="send", keys=["Ctrl+C"])
6. terminal(action="exit")
```

#### Supported Keys

| Key | VHS Command |
|-----|-------------|
| Enter | `Enter` |
| Tab | `Tab` |
| Space | `Space` |
| Backspace | `Backspace` |
| Escape | `Escape` |
| Up | `Up` |
| Down | `Down` |
| Left | `Left` |
| Right | `Right` |
| Home | `Home` |
| End | `End` |
| PageUp | `PageUp` |
| PageDown | `PageDown` |
| Ctrl+C | `Ctrl+C` |
| Ctrl+D | `Ctrl+D` |
| Ctrl+Z | `Ctrl+Z` |
| Ctrl+L | `Ctrl+L` |
| Ctrl+A | `Ctrl+A` |
| Ctrl+E | `Ctrl+E` |
| Ctrl+K | `Ctrl+K` |
| Ctrl+U | `Ctrl+U` |
| Ctrl+W | `Ctrl+W` |
| Ctrl+R | `Ctrl+R` |

#### Known Limitations

1. **Arrow key navigation**: VHS sends escape codes that some terminals (like prompt_toolkit) don't interpret correctly. For line editing, use text input only rather than navigating with arrow keys.

2. **LLM response timing**: LLM responses can take 5-15+ seconds. Always use `sleep_ms` with sufficient time:
   - Simple queries: `sleep_ms=5000`
   - Complex reasoning: `sleep_ms=15000`
   - Code generation: `sleep_ms=20000`

3. **Single session**: Only one terminal session at a time. Call `exit` before starting a new session.

#### Requirements

- **VHS**: Install with `go install github.com/charmbracelet/vhs@latest`
- **Environment**: Set `VHS_NO_SANDBOX=true` in containerized environments

#### Related

- PRD: https://github.com/jeremysball/alfred/issues/83
- VHS: https://github.com/charmbracelet/vhs
