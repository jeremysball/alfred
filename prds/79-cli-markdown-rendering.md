# PRD: CLI Markdown Rendering

## Overview

| Field | Value |
|-------|-------|
| **Issue** | #79 |
| **Status** | Open |
| **Priority** | High |
| **Created** | 2026-02-21 |
| **Parent PRD** | #48 (Alfred v1.0 Vision) |

---

## Problem Statement

Alfred's CLI outputs plain text, making it hard to read structured responses. Code blocks lack syntax highlighting. Tables overflow on narrow screens. Headers, lists, and emphasis run together. This is especially painful when SSHing from a phone—the primary use case.

---

## Solution Overview

Integrate the Rich library to render full markdown in LLM responses:

- **Full markdown support**: bold, italic, code, headers, lists, blockquotes, links, tables
- **Syntax highlighting**: Language-specific highlighting for fenced code blocks
- **Hybrid streaming**: Plain text during streaming, formatted markdown on completion
- **Smart fallback**: Raw markdown output for non-ANSI terminals

---

## Scope

### In Scope

| Feature | Details |
|---------|---------|
| Markdown rendering | All standard elements (bold, italic, strikethrough, headers, lists, blockquotes, links, tables) |
| Code blocks | Fenced blocks with language-specific syntax highlighting |
| Streaming | Plain text during stream, markdown render on completion |
| Terminal detection | Fallback to raw markdown when ANSI not supported |
| Library | Rich (drop-in, feature-complete) |

### Out of Scope

- User message rendering (unchanged)
- Configuration/toggle (always on)
- Image rendering (display URLs as-is)
- HTML rendering

---

## Technical Approach

### Library: Rich

Rich provides:
- `Markdown` class for rendering markdown to ANSI
- `Syntax` class for code highlighting (via Pygments)
- Automatic terminal detection via `Console.force_terminal`
- Table rendering with auto-width

### Integration Points

1. **`src/interfaces/cli.py`** — Primary integration point
   - Detect ANSI support at startup
   - During streaming: output plain text chunks
   - On completion: render full response as markdown

2. **Streaming Flow**
   ```
   LLM stream chunk → print plain text → accumulate buffer
   Stream complete → pass buffer to Rich Markdown → render to console
   ```

### Terminal Detection

```python
from rich.console import Console

console = Console()
if console.is_terminal and not os.environ.get("NO_COLOR"):
    # Use markdown rendering
else:
    # Output raw markdown
```

---

## Milestones

| # | Milestone | Description | Status |
|---|-----------|-------------|--------|
| M1 | Rich integration | Add Rich dependency, create markdown renderer utility | ✅ Done |
| M2 | Streaming hybrid | Implement plain-text-during-stream, markdown-on-complete | ✅ Done |
| M3 | Syntax highlighting | Enable Pygments-based code block highlighting | ✅ Done |
| M4 | Terminal detection | Detect non-ANSI terminals, fallback to raw output | ✅ Done |
| M5 | Testing | Unit tests for renderer, integration tests with CLI | ✅ Done |

---

## Success Criteria

- [ ] Bold, italic, headers, lists, blockquotes render correctly
- [ ] Tables display with auto-width (readable on narrow terminals)
- [ ] Code blocks highlight based on language tag
- [ ] Streaming shows plain text, final output is formatted
- [ ] Non-ANSI terminals receive raw markdown
- [ ] No visible latency increase on response completion

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Rich adds latency on large responses | Benchmark; consider truncation for very long outputs |
| Streaming-to-markdown transition feels jumpy | Accept as MVP; can improve with block-level buffering later |
| Pygments missing obscure languages | Default to plain monospace for unknown languages |

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `rich` | Markdown rendering, syntax highlighting, terminal detection |
| `pygments` | Syntax highlighting (Rich dependency) |

---

## Notes

- Always-on behavior; no configuration needed
- User messages remain unchanged (plain text input)
- Links render as underlined text; URLs visible
