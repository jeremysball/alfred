# VHS Prototype Findings

## Summary

VHS works for our use case. All core capabilities validated.

## Environment Setup

```bash
# Install dependencies (Arch Linux)
sudo pacman -S go ttyd ffmpeg

# Install VHS
go install github.com/charmbracelet/vhs@latest

# Add to PATH
export PATH="$PATH:$(go env GOPATH)/bin"

# Required for containers/restricted environments
export VHS_NO_SANDBOX=true
```

## Validated Capabilities

### ✅ Text Output (`.txt` / `.ascii`)
- ANSI codes automatically stripped
- Captures terminal content as plain text
- Multiple frames recorded with `──────` separators
- Use for programmatic assertions

### ✅ Screenshot Capture (`Screenshot` command)
- PNG format, 1200x600 by default
- Colors preserved (ANSI rendering)
- Capture at specific points in execution
- Use for visual verification

### ✅ Keyboard Input
| Key | Tape Command | Status |
|-----|--------------|--------|
| Text | `Type "text"` | ✅ Works |
| Enter | `Enter` | ✅ Works |
| Arrow keys | `Up`, `Down`, `Left`, `Right` | ✅ Works |
| Tab | `Tab` | ✅ Works |
| Space | `Space` | ✅ Works |
| Backspace | `Backspace` | ✅ Works |
| Ctrl+C | `Ctrl+C` | ✅ Works |
| Ctrl+D | `Ctrl+D` | ✅ Works |

### ✅ Timing Control
- `Sleep 500ms` - Wait without interaction
- `Wait /pattern/` - Wait for output match (regex)
- `Set TypingSpeed 100ms` - Control typing speed

## Tool Design (Python)

```python
class TerminalTool:
    """Interactive terminal tool using VHS."""
    
    def start(self, command: str) -> None:
        """Start a terminal session with the given command."""
        # Generate tape file with:
        # - Output session.txt
        # - Type command + Enter
        # - Screenshot at capture points
    
    def send(self, keys: list[str] = None, text: str = None) -> None:
        """Send keystrokes or text to the session."""
        # Append to tape: Down, Up, Ctrl+C, Type "text", etc.
    
    def capture(self) -> dict:
        """Capture current terminal state.
        
        Returns:
            {
                "screenshot": "/path/to/frame.png",
                "text": "plain text content"
            }
        """
        # Append Screenshot command
        # Run VHS
        # Read .txt and .png outputs
    
    def exit(self) -> None:
        """Terminate the session."""
        # Send Ctrl+C or Ctrl+D
        # Clean up temp files
```

## Key Implementation Notes

1. **Tape file approach**: Generate temp `.tape` file dynamically, run VHS, read outputs
2. **Session model**: One session at a time (simpler for MVP)
3. **Capture flow**: Each `capture()` call runs VHS on the accumulated tape
4. **Text parsing**: Post-process `.txt` to extract final frame content
5. **Screenshot path**: VHS writes to specified path, tool returns path for vision model

## Limitations Found

1. **Frame separators**: `.txt` output includes `──────` between frames; need to extract final frame
2. **No streaming**: VHS runs to completion, no real-time output
3. **Single session**: No concurrent sessions (acceptable for MVP)
4. **Requires sandbox bypass**: `VHS_NO_SANDBOX=true` needed in containers

## Recommended Next Steps

1. **M2: Core Tool Implementation** - Build `terminal` tool with start/send/capture/exit actions
2. Use `tempfile.TemporaryDirectory()` for session isolation
3. Post-process `.txt` to strip frame separators and return clean content
4. Return PNG path for vision model consumption

## Example Tape File

```elixir
# Generated dynamically by TerminalTool
Output /tmp/session_xxx/output.txt
Set TypingSpeed 50ms
Set Shell bash

Type "alfred"
Enter
Sleep 1s
Screenshot /tmp/session_xxx/frame_1.png

Down
Sleep 100ms
Screenshot /tmp/session_xxx/frame_2.png

Enter
Sleep 500ms
Screenshot /tmp/session_xxx/frame_3.png
```
