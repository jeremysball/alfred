# PRD: Rich Markdown Output for CLI

**Issue**: #70
**Status**: Planning
**Priority**: High
**Created**: 2026-02-19

---

## Problem Statement

Alfred's CLI streams plain text responses. Headers, lists, code blocks, and tables all look the same, making responses harder to scan and less professional. Users cannot quickly distinguish between different content types.

---

## Solution Overview

Implement streaming markdown-to-ANSI rendering using Rich. Most elements render eagerly (mode-switching as delimiters appear). Code blocks buffer for syntax highlighting. No redrawing—draw once in the correct style.

---

## Design Principles

### 1. Eager Rendering
When a delimiter appears, immediately switch to that output mode. No buffering-and-re-rendering.

### 2. Code Blocks Are Special
Code blocks require syntax highlighting, which needs the complete code and language identifier. Buffer these, then render.

### 3. No Redraw
Never erase and redraw. Each character appears once in its final style.

### 4. Rich as the Engine
Use Rich's markdown parsing and ANSI generation. We provide streaming state management, Rich provides formatting.

---

## Technical Architecture

### Streaming State Machine

```python
class StreamState(Enum):
    PLAIN = "plain"           # Default text streaming
    HEADER = "header"         # After #, ##, etc.
    CODE_BLOCK = "code_block" # Between ``` ... ```
    TABLE = "table"           # Lines starting with |
    QUOTE = "quote"           # Lines starting with >
    LIST = "list"             # Lines starting with - or 1.
```

### Component: StreamingMarkdownRenderer

```python
class StreamingMarkdownRenderer:
    """Renders markdown to ANSI with streaming support."""

    def __init__(self, console: Console):
        self.console = console
        self.state = StreamState.PLAIN
        self.buffer: list[str] = []  # For code blocks
        self.code_lang: str | None = None

    def feed(self, chunk: str) -> None:
        """Process incoming chunk, emit formatted output."""
        # State machine logic here

    def flush(self) -> None:
        """Complete any pending output."""
        # Handle any remaining buffered content
```

### Element Handling

| Element | Detection | Strategy |
|---------|-----------|----------|
| `# Header` | Line starts with `#` | Eager: color as header until newline |
| ` ```python ` | Line starts with ` ``` ` | Buffer until closing ` ``` `, render with syntax highlighting |
| `| Table |` | Line starts with `|` | Eager: render as Rich Table row by row |
| `> Quote` | Line starts with `>` | Eager: color as quote until non-quote line |
| `- List` | Line starts with `-` or `*` | Eager: render with bullet styling |
| `1. List` | Line starts with digit + `.` | Eager: render with number styling |
| `**bold**` | `**` delimiters | Eager: bold styling within delimiters |
| `` `code` `` | Backtick delimiters | Eager: inline code styling |
| `[link](url)` | `[text](url)` pattern | Eager: link styling for text, dim for URL |

### Integration Point

The renderer integrates into the CLI interface:

```python
# src/interfaces/cli.py
async def run(self) -> None:
    renderer = StreamingMarkdownRenderer(Console())

    async for chunk in self.alfred.chat_stream(user_input):
        renderer.feed(chunk)

    renderer.flush()
```

---

## File Structure

```
src/
├── output/
│   ├── __init__.py
│   ├── renderer.py       # StreamingMarkdownRenderer
│   └── states.py         # StreamState enum
├── interfaces/
│   └── cli.py            # Updated to use renderer
```

---

## Milestone Roadmap

| # | Milestone | Description |
|---|-----------|-------------|
| M1 | **Core Renderer** | StreamingMarkdownRenderer with state machine, plain text passthrough |
| M2 | **Headers** | H1-H6 detection and coloring |
| M3 | **Code Blocks** | Buffer + syntax highlighting with Rich Syntax |
| M4 | **Lists** | Bullet and numbered list formatting |
| M5 | **Tables** | Rich Table row-by-row streaming |
| M6 | **Blockquotes** | Quote styling with border |
| M7 | **Inline Formatting** | Bold, italic, inline code, links |
| M8 | **CLI Integration** | Wire into existing CLI interface |
| M9 | **Testing** | Unit tests for all element types |

---

## Success Criteria

- [ ] Headers display in distinct colors/sizes
- [ ] Code blocks render with syntax highlighting
- [ ] Tables render as proper Rich tables
- [ ] Lists display with proper bullets/numbers
- [ ] Blockquotes have visual distinction
- [ ] Inline formatting (bold, italic, code) works
- [ ] No visible redraw or flicker during streaming
- [ ] Plain text streams with low latency
- [ ] All tests passing

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `rich` | Markdown parsing, ANSI generation, syntax highlighting (already installed) |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-19 | Eager rendering for most elements | No redraw, lower latency, simpler implementation |
| 2026-02-19 | Buffer code blocks only | Syntax highlighting requires complete code + language |
| 2026-02-19 | CLI only, not Telegram | Telegram has its own markdown rendering |
| 2026-02-19 | Use Rich | Already a dependency, battle-tested, good API |
| 2026-02-19 | State machine approach | Clean separation of rendering modes |

---

## Open Questions

**Q: How do we handle malformed markdown?**
A: Best effort. If a code block never closes, render as code on flush. If inline `**` never closes, render the stars literally.

**Q: What about nested elements?**
A: Rich handles this. A list item can contain inline code, bold, etc.

**Q: Performance impact?**
A: Minimal. Rich is fast. The state machine is O(n) on input size.

**Q: What about very long lines?**
A: Rich handles line wrapping. We don't need to do anything special.
