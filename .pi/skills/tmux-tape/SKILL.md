---
name: tmux-tape
description: Control terminal sessions via ttyd + tmux with pixel-perfect screenshots. Use for E2E testing of TUI applications, CLI interactions, and asyncio apps. Use the tmux_tool.py module for terminal control, browser-based screenshots, and text extraction.
---

# tmux-tape Skill

Run terminal sessions programmatically using ttyd (browser terminal) + tmux (session control) + playwright (screenshots). Pixel-perfect rendering with proper box-drawing, colors, and text extraction.

## Overview

**Why this approach:**
- **ttyd** — Runs terminal in browser via xterm.js (pixel-perfect rendering)
- **tmux** — Controls the session, sends keystrokes, captures text
- **playwright** — Takes screenshots of the browser

**Advantages over VHS:**
- Works with asyncio apps (Alfred, etc.)
- Pixel-perfect rendering (box chars connect, proper colors)
- Real terminal emulation (xterm.js)

## Test Images

Example screenshots from Alfred CLI:

| Startup | Response |
|---------|----------|
| https://0x0.st/PSVr.png | https://0x0.st/PSVz.png |

---

## Quick Start

**Always use `uv run python script.py` to run scripts.**

### 1. Install Dependencies

```bash
# Python packages
pip install pyte pillow

# Playwright browser (for screenshots)
npx playwright install chromium

# System packages (usually pre-installed)
# ttyd, tmux, curl
```

### 2. Copy tmux_tool.py

Copy the module to your working directory:

```bash
cp .pi/skills/tmux-tape/tmux_tool.py /tmp/pi-tmux/
```

### 3. Write Your Script

```python
#!/usr/bin/env python3
from tmux_tool import TerminalSession

with TerminalSession("test", port=7681) as s:
    s.send("echo hello")
    s.send_key("Enter")
    s.sleep(1)
    
    result = s.capture("output.png")  # upload=False by default
    print(result["text"])
```

### 4. Run

```bash
cd /tmp/pi-tmux
uv run python script.py
```

---

## tmux_tool.py Module

The module is located at `.pi/skills/tmux-tape/tmux_tool.py`. Import it in your scripts:

```python
from tmux_tool import TerminalSession
```

### TerminalSession Class

```python
class TerminalSession:
    def __init__(self, name, cols=120, rows=35, port=7681):
        """Create terminal session."""
    
    def send(self, text: str) -> None:
        """Send text to terminal."""
    
    def send_key(self, key: str) -> None:
        """Send special key: Enter, C-c, C-d, C-l, Escape, Tab, Up, Down, etc."""
    
    def sleep(self, seconds: float) -> None:
        """Wait for duration."""
    
    def capture_text(self) -> str:
        """Get terminal text (ANSI-stripped)."""
    
    def capture_raw(self) -> str:
        """Get terminal text with ANSI codes preserved (for debugging)."""
    
    def capture_screenshot(self, filename=None, upload=False) -> dict:
        """Take screenshot via browser. Returns {screenshot, url?}."""
    
    def capture(self, filename=None, upload=False) -> dict:
        """Capture both text and screenshot. Returns {text, screenshot, url?}."""
    
    def upload(self, filepath: str) -> str:
        """Upload image to 0x0.st, returns URL."""
```

### Debugging with Raw ANSI

To see the raw ANSI output (useful for debugging colors/attributes):

```python
raw = s.capture_raw()
print(repr(raw[:500]))  # Show escaped ANSI codes
```

---

## Key Reference

| Key | Description |
|-----|-------------|
| `Enter` | Return/Enter |
| `C-c` | Ctrl+C (interrupt) |
| `C-d` | Ctrl+D (EOF) |
| `C-l` | Clear screen |
| `Escape` | Escape key |
| `Tab` | Tab key |
| `Space` | Space bar |
| `Up` / `Down` / `Left` / `Right` | Arrow keys |

---

## Common Patterns

### Start Alfred (asyncio app)
```python
with TerminalSession("alfred", port=7681) as s:
    s.send("bash")
    s.send_key("Enter")
    s.sleep(0.3)
    
    s.send("cd /workspace/alfred-prd && export $(grep -v '^#' .env | xargs) && .venv/bin/alfred")
    s.send_key("Enter")
    s.sleep(3)
    
    result = s.capture("startup.png")
    print(result["text"])
```

### Send Message and Capture Response
```python
s.send("what is 2+2?")
s.send_key("Enter")
s.sleep(12)  # LLM needs time

result = s.capture("response.png")
print(result["text"])
```

### Upload Screenshots for Sharing
```python
result = s.capture("important.png", upload=True)
print(f"Screenshot URL: {result['url']}")  # https://0x0.st/xxx.png
```

### Clean Exit
```python
s.send_key("C-c")
s.send("exit")
s.send_key("Enter")
s.sleep(0.5)
```

---

## Workflow

### 1. Create Session Directory
```bash
SESSION_DIR="/tmp/pi-tmux/$(date +%Y-%m-%d_%H-%M-%S)"
mkdir -p "$SESSION_DIR"
cp .pi/skills/tmux-tape/tmux_tool.py "$SESSION_DIR/"
cd "$SESSION_DIR"
```

### 2. Write Script
Create `script.py` using the `write` tool.

### 3. Run
```bash
uv run python script.py
```

### 4. Check Results
- Text output printed to stdout
- Screenshots saved in session directory
- Use `upload=True` to get shareable URLs

---

## Error Handling

**Retry pattern:**
1. Read error message
2. Check script.py
3. Fix issue (timing, typo, wrong port)
4. Run again
5. Stop after 3 attempts

**Common issues:**

| Error | Cause | Fix |
|-------|-------|-----|
| `ERR_CONNECTION_REFUSED` | ttyd not running | Check port, wait longer |
| `tmux: command not found` | tmux not installed | Install tmux |
| Empty screenshot | Page didn't load | Increase wait-for-timeout |
| Upload failed | Network issue | Retry or skip upload |

---

## Image Upload

Upload uses **0x0.st** — free, no API key required.

```python
# Upload during capture
result = s.capture("screen.png", upload=True)
url = result["url"]  # https://0x0.st/xxx.png

# Upload existing file
url = s.upload("existing.png")
```

**Features:**
- No registration or API key
- Direct image URLs
- Files kept indefinitely (30 day inactivity purge)

---

## Output Format

After running, report terminal text output and list uploaded URLs at the bottom.

**Always output uploaded URLs at the bottom of your response** so they're easy to find and click.

Example:

```
Session dir: /tmp/pi-tmux/2026-02-22_01-45-00
Script: script.py

Text:
[terminal text output]

---

Screenshots:
https://0x0.st/xxx.png
https://0x0.st/yyy.png
```

---

## Full Example

```python
#!/usr/bin/env python3
"""Test Alfred CLI."""

from tmux_tool import TerminalSession

def main():
    print("=== Alfred Test ===\n")
    
    with TerminalSession("alfred", port=7681) as s:
        print("Starting Alfred...")
        s.send("bash")
        s.send_key("Enter")
        s.sleep(0.3)
        s.send("cd /workspace/alfred-prd && export $(grep -v '^#' .env | xargs) && .venv/bin/alfred")
        s.send_key("Enter")
        s.sleep(3)
        
        result = s.capture("startup.png")
        print(result["text"])
        
        print("\nSending message...")
        s.send("what is 2+2?")
        s.send_key("Enter")
        s.sleep(12)
        
        result = s.capture("response.png")
        print(result["text"])
        
        s.send_key("C-c")
        s.send("exit")
        s.send_key("Enter")
    
    print("\n=== Done ===")


if __name__ == "__main__":
    main()
```

---

## Tips

1. **Use `uv run`** — Always run scripts with `uv run python script.py`
2. **Unique ports** — Use different ports for concurrent sessions (7681, 7682, etc.)
3. **Estimate waits** — LLM responses need 10s+
4. **Use bash** — Avoid fish/shell compatibility issues
5. **Upload selectively** — Use `upload=True` only when you need shareable URLs
6. **Check text** — Always print `result["text"]` for verification

---

## References

- ttyd: https://github.com/tsl0922/ttyd
- tmux: https://github.com/tmux/tmux
- playwright: https://playwright.dev
- 0x0.st: https://0x0.st
