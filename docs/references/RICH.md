# Rich Library Reference

> **Version**: Rich 14.1.0  
> **Source**: https://rich.readthedocs.io/  
> **GitHub**: https://github.com/Textualize/rich  
> **Purpose**: Python library for rich text and beautiful formatting in the terminal

---

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Console API](#console-api)
3. [Console Markup](#console-markup)
4. [Markdown Rendering](#markdown-rendering)
5. [Rich Text](#rich-text)
6. [Styles](#styles)
7. [Live Display](#live-display)
8. [Integration with PyPiTUI](#integration-with-pypitui)
9. [Common Patterns](#common-patterns)
10. [API Reference](#api-reference)

---

## Core Concepts

### What is Rich?

Rich is a Python library for rendering rich text, tables, progress bars, syntax highlighting, markdown, and more to the terminal. It works on macOS, Linux, and Windows.

**Key Features:**
- **Console Markup**: BBCode-inspired syntax for styling text inline
- **Markdown**: Full markdown rendering with syntax highlighting
- **Rich Text**: Programmatic text styling with spans
- **Live Display**: Dynamic, updating terminal output
- **Progress Bars**: Animated progress indicators
- **Tables**: Complex table layouts with styling
- **Panels**: Bordered containers for content
- **Syntax Highlighting**: Code rendering for many languages

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Console                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   print()   │  │    log()    │  │   print_markup()    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                      Renderables                             │
│  ┌─────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐ ┌───────┐ │
│  │  Text   │ │ Markdown │ │  Panel │ │  Table   │ │ Rule  │ │
│  └─────────┘ └──────────┘ └────────┘ └──────────┘ └───────┘ │
├─────────────────────────────────────────────────────────────┤
│                      Output                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│  │  Terminal  │  │  StringIO  │  │    File    │              │
│  └────────────┘  └────────────┘  └────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

---

## Console API

### Basic Console Usage

```python
from rich.console import Console

# Create console instance
console = Console()

# Basic printing
console.print("Hello, World!")
console.print("Hello", "World!")  # Multiple args joined with space

# Styled printing
console.print("Hello", style="bold red on white")
```

### Console Constructor Parameters

```python
Console(
    color_system: str | None = "auto",      # "auto", "standard", "256", "truecolor", "windows"
    force_terminal: bool | None = None,     # Force terminal detection
    force_jupyter: bool | None = None,      # Force Jupyter detection
    force_interactive: bool | None = None,  # Force interactive mode
    soft_wrap: bool = False,                # Disable word wrapping
    theme: Theme | None = None,             # Custom color theme
    stderr: bool = False,                   # Write to stderr
    file: IO[str] | None = None,            # Write to file
    quiet: bool = False,                    # Suppress output
    width: int | None = None,               # Console width (None = auto)
    height: int | None = None,              # Console height (None = auto)
    style: StyleType | None = None,         # Default style
    no_color: bool | None = None,           # Disable color
    tab_size: int = 8,                      # Tab character width
    record: bool = False,                   # Enable output recording
    markup: bool = True,                    # Enable console markup
    highlight: bool = True,                 # Enable auto-highlighting
    emoji: bool = True,                     # Enable emoji codes
    emoji_variant: str = "emoji",           # "emoji" or "text"
    log_path: bool = True,                  # Show path in log()
    log_time: bool = True,                  # Show time in log()
    log_time_format: str = "[%X]",          # Time format string
    highlighter: HighlighterType | None = None,  # Default highlighter
)
```

### Key Console Methods

#### print()

```python
console.print(
    *objects: Any,                    # Objects to print
    sep: str = " ",                   # Separator between objects
    end: str = "\n",                  # Ending character
    style: StyleType | None = None,   # Style for all objects
    justify: JustifyMethod | None = None,  # "left", "center", "right", "full"
    overflow: OverflowMethod | None = None,  # "fold", "crop", "ellipsis"
    no_wrap: bool | None = None,      # Disable wrapping
    emoji: bool | None = None,        # Enable emoji
    markup: bool | None = None,       # Enable markup
    highlight: bool | None = None,    # Enable highlighting
    width: int | None = None,         # Width for wrapping
    height: int | None = None,        # Height limit
    crop: bool = True,                # Crop to width
    soft_wrap: bool | None = None,    # Soft wrap mode
    new_line_start: bool = False,     # Start with newline
)
```

#### log()

Same as `print()` but adds timestamp and file:line info:

```python
console.log("Application started")
# [14:32:08] Application started          <stdin>:1
```

#### print_json()

Pretty print JSON with syntax highlighting:

```python
console.print_json('[false, true, null, "foo"]')
```

#### status()

Display a spinner with status message:

```python
with console.status("[bold green]Fetching data...") as status:
    do_work()
    # Spinner animates automatically
```

#### rule()

Draw a horizontal rule:

```python
console.rule("[bold red]Chapter 1")
# ─────────────────────────── Chapter 1 ───────────────────────────
```

---

## Console Markup

Rich supports BBCode-inspired markup syntax for inline styling.

### Basic Syntax

```python
from rich import print

# Style until closed
print("[bold red]alert![/bold red] Something happened")

# Shorthand close (closes last opened style)
print("[bold red]Bold and red[/] not bold or red")

# Multiple overlapping styles
print("[bold]Bold[italic] bold and italic [/bold]italic[/italic]")

# Style to end of line
print("[bold italic yellow on red blink]This text is styled")
```

### Available Styles

| Style | Description |
|-------|-------------|
| `bold` | Bold text |
| `dim` | Dimmed/faded text |
| `italic` | Italic text |
| `underline` | Underlined text |
| `blink` | Blinking text |
| `blink2` | Rapid blinking |
| `reverse` | Reversed foreground/background |
| `conceal` | Hidden text |
| `strike` | Strikethrough |
| `underline2` | Double underline |
| `frame` | Framed text |
| `encircle` | Encircled text |
| `overline` | Overlined text |

### Colors

**Standard Colors:**
- `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`
- `bright_black`, `bright_red`, `bright_green`, etc.

**Extended Colors:**
- Numbered: `color(0)` through `color(255)`
- RGB: `rgb(255, 128, 0)` or `#ff8000`

### Background Colors

Prefix with `on_`:
```python
print("[white on blue]White text on blue background[/]")
print("[bold red on yellow]Bold red on yellow[/]")
```

### Links

```python
print("Visit my [link=https://example.com]blog[/link]!")
```

### Emoji

```python
print(":warning:")              # ⚠️
print(":red_heart-emoji:")      # ❤️ (emoji variant)
print(":red_heart-text:")       # ♥ (text variant)
```

Use `python -m rich.emoji` to see all available emojis.

### Escaping Markup

To print literal square brackets:

```python
print(r"foo\[bar]")  # foo[bar]

# Or use escape() function
from rich.markup import escape
print(f"Hello {escape(name)}!")
```

### Markup Errors

Rich raises `MarkupError` for:
- Mismatched tags: `"[bold]Hello[/red]"`
- Implicit close with no open tag: `"no tags[/]"`

---

## Markdown Rendering

Rich can render full Markdown documents with syntax highlighting.

### Basic Usage

```python
from rich.console import Console
from rich.markdown import Markdown

console = Console()

MARKDOWN = """
# This is an h1

Rich can render **bold**, *italic*, and `code`.

1. First item
2. Second item
   - Nested bullet
   - Another nested

```python
def hello():
    print("Hello, World!")
```

> This is a blockquote

| Table | Header |
|-------|--------|
| Cell1 | Cell2  |
"""

md = Markdown(MARKDOWN)
console.print(md)
```

### Markdown Constructor

```python
Markdown(
    markup: str,                      # Markdown text
    code_theme: str = "monokai",      # Pygments theme for code blocks
    justify: JustifyMethod | None = None,  # Text justification
    style: str = "none",              # Base style
    hyperlinks: bool = True,          # Enable hyperlink rendering
    inline_code_lexer: str | None = None,  # Default lexer for inline code
    inline_code_theme: str | None = None,  # Theme for inline code
)
```

### Supported Markdown Elements

| Element | Support |
|---------|---------|
| Headers (H1-H6) | ✅ |
| Paragraphs | ✅ |
| Bold/Italic | ✅ |
| Code blocks | ✅ (with syntax highlighting) |
| Inline code | ✅ |
| Blockquotes | ✅ |
| Unordered lists | ✅ |
| Ordered lists | ✅ |
| Links | ✅ (terminal hyperlinks) |
| Images | ❌ (text representation) |
| Tables | ✅ |
| Horizontal rules | ✅ |
| Strikethrough | ✅ |
| Task lists | ✅ |
| Footnotes | ❌ |
| Definition lists | ❌ |

### Code Themes

Popular themes: `monokai`, `default`, `vim`, `emacs`, `friendly`, `colorful`, `autumn`, `murphy`, `manni`, `perldoc`, `pastie`, `borland`, `trac`, `native`, `fruity`, `bw`, `vs`, `tango`, `rrt`, `xcode`, `igor`, `paraiso-light`, `paraiso-dark`, `lovelace`, `algol`, `algol_nu`, `arduino`, `rainbow_dash`, `abap`, `solarized-dark`, `solarized-light`, `sas`, `stata`, `stata-light`, `stata-dark`, `inkpot`, `zenburn`

---

## Rich Text

The `Text` class provides programmatic text styling with fine-grained control.

### Creating Text

```python
from rich.text import Text

# Simple text
text = Text("Hello, World!")

# From markup
text = Text.from_markup("[bold red]Hello[/] World")

# From ANSI codes
text = Text.from_ansi("\033[1;35mHello\033[0m, World!")

# Assemble from parts
text = Text.assemble(
    ("Hello ", "bold magenta"),
    ("World!", "italic"),
)
```

### Text Methods

```python
text = Text("Hello, World!")

# Apply style to range
text.stylize("bold magenta", 0, 6)  # "Hello," in bold magenta

# Append with style
text.append(" More text", style="dim")

# Highlight words
text.highlight_words(["Hello", "World"], "bold red")

# Highlight regex
text.highlight_regex(r"\d+", "bold green")

# Set properties
text.justify = "center"  # "left", "center", "right", "full"
text.overflow = "ellipsis"  # "fold", "crop", "ellipsis"
text.no_wrap = True
text.tab_size = 4
```

### Text Properties

| Property | Description |
|----------|-------------|
| `plain` | Plain text without styles (str) |
| `spans` | List of style spans |
| `justify` | Justification method |
| `overflow` | Overflow handling |
| `no_wrap` | Disable wrapping |
| `tab_size` | Tab character width |
| `end` | Ending string (default "\n") |

---

## Styles

### Style Definition

```python
from rich.style import Style

# Parse from string
style = Style.parse("bold red on white")

# Constructor
style = Style(
    color="red",
    bgcolor="white",
    bold=True,
    italic=False,
    underline=True,
    strike=False,
    dim=False,
    blink=False,
    reverse=False,
    conceal=False,
)

# Copy with modifications
new_style = style + Style(bold=False, italic=True)
```

### Style Themes

```python
from rich.theme import Theme

# Define theme
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "danger": "bold red",
    "success": "bold green",
})

# Use theme in console
console = Console(theme=custom_theme)
console.print("[info]This is info[/]")
console.print("[danger]This is dangerous![/]")
```

---

## Live Display

Live display allows dynamic, updating terminal output.

### Basic Live Display

```python
from rich.live import Live
from rich.console import Console

console = Console()

with Live("Loading...", console=console) as live:
    for i in range(100):
        live.update(f"Loading... {i}%")
        time.sleep(0.1)
```

### Live Constructor

```python
Live(
    renderable: RenderableType | None = None,  # Initial renderable
    console: Console | None = None,            # Console instance
    screen: bool = False,                      # Use alternate screen
    auto_refresh: bool = True,                 # Auto refresh
    refresh_per_second: float = 4,             # Refresh rate
    transient: bool = False,                   # Clear on exit
    redirect_stdout: bool = True,              # Capture stdout
    redirect_stderr: bool = True,              # Capture stderr
    vertical_overflow: str = "ellipsis",       # "crop", "ellipsis", "visible"
    get_renderable: Callable[[], RenderableType] | None = None,
)
```

### Live Update Patterns

```python
# Pattern 1: Update with new renderable
with Live(console=console) as live:
    live.update(Panel("Step 1"))
    time.sleep(1)
    live.update(Panel("Step 2"))

# Pattern 2: Update mutable renderable
table = Table()
table.add_column("Status")
table.add_row("Pending...")

with Live(table, console=console) as live:
    time.sleep(1)
    table.add_row("Complete!")
    # Table updates automatically

# Pattern 3: Get renderable callback
def get_progress():
    return f"Progress: {current}/{total}"

with Live(get_renderable=get_progress) as live:
    while working:
        time.sleep(0.1)
        # Live calls get_progress() each refresh
```

---

## Integration with PyPiTUI

### The Challenge

PyPiTUI uses a custom rendering system based on ANSI escape sequences. Rich uses its own `Console` and `RenderResult` protocols. To integrate Rich markdown/markup rendering into PyPiTUI:

**Key Insight**: Rich can render to a `StringIO` buffer, producing ANSI-colored text that PyPiTUI can display.

### Integration Pattern

```python
from io import StringIO
from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text
from pypitui import Text as PypituiText

def render_rich_to_pypitui(rich_renderable, width: int = 80) -> PypituiText:
    """Convert a Rich renderable to PyPiTUI Text."""
    # Create StringIO buffer
    buffer = StringIO()
    
    # Create console that writes to buffer
    console = Console(
        file=buffer,
        width=width,
        force_terminal=True,  # Enable ANSI codes
        color_system="truecolor",
    )
    
    # Render to buffer
    console.print(rich_renderable)
    
    # Get ANSI output
    ansi_text = buffer.getvalue()
    
    # Return PyPiTUI text (which handles ANSI sequences)
    return PypituiText(ansi_text)


# Usage in MessagePanel
class MessagePanel(BorderedBox):
    def set_content(self, text: str, use_markdown: bool = True) -> None:
        """Set content with optional markdown rendering."""
        self.clear()
        
        if use_markdown:
            # Render markdown via Rich
            md = Markdown(text)
            pypitui_text = render_rich_to_pypitui(md, width=self._width)
            self.add_child(pypitui_text)
        else:
            # Plain text
            self.add_child(PypituiText(text))
```

### Streaming Markdown

For streaming LLM responses that may contain markdown:

```python
class MessagePanel(BorderedBox):
    def __init__(self):
        super().__init__()
        self._content_buffer = ""
        self._use_markdown = True
    
    def append_content(self, chunk: str) -> None:
        """Append streaming content."""
        self._content_buffer += chunk
        
        # Re-render with markdown
        self.clear()
        if self._use_markdown:
            md = Markdown(self._content_buffer)
            text = render_rich_to_pypitui(md, width=self._width)
            self.add_child(text)
        else:
            self.add_child(PypituiText(self._content_buffer))
```

### Performance Considerations

1. **Batch Updates**: Don't re-render on every chunk - batch chunks and render every 50-100ms
2. **Incremental Rendering**: For very long content, consider rendering only visible portions
3. **Cache Parsed Markdown**: The `Markdown` object can be reused with updated text

### Alternative: Rich Console Capture

```python
from rich.console import Console

def capture_rich_output(renderable) -> str:
    """Capture Rich output as string with ANSI codes."""
    console = Console(force_terminal=True, color_system="truecolor")
    with console.capture() as capture:
        console.print(renderable)
    return capture.get()

# Usage
md = Markdown("# Hello\n\n**Bold text**")
ansi_output = capture_rich_output(md)
# ansi_output now contains ANSI escape sequences for colors/styles
```

---

## Common Patterns

### Pattern 1: Styled Status Messages

```python
from rich.text import Text

def status_message(message: str, level: str = "info") -> Text:
    """Create a styled status message."""
    styles = {
        "info": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "red",
    }
    style = styles.get(level, "white")
    
    text = Text()
    text.append("● ", style=style)
    text.append(message)
    return text

console.print(status_message("Connected", "success"))
console.print(status_message("Failed", "error"))
```

### Pattern 2: Code Blocks with Language

```python
from rich.syntax import Syntax

def print_code(code: str, language: str = "python"):
    """Print syntax-highlighted code."""
    syntax = Syntax(
        code,
        language,
        theme="monokai",
        line_numbers=True,
        word_wrap=True,
    )
    console.print(syntax)
```

### Pattern 3: Information Panels

```python
from rich.panel import Panel
from rich.text import Text

def info_panel(title: str, content: str, style: str = "blue") -> Panel:
    """Create an information panel."""
    return Panel(
        Text(content),
        title=title,
        border_style=style,
        padding=(1, 2),
    )

console.print(info_panel("Note", "This is important information", "yellow"))
```

### Pattern 4: Streaming Text with Live

```python
from rich.live import Live
from rich.text import Text

async def stream_response(generator):
    """Stream text with live updating."""
    text = Text()
    
    with Live(text, console=console, refresh_per_second=10) as live:
        async for chunk in generator:
            text.append(chunk)
            # Live automatically re-renders
```

### Pattern 5: Tables for Data

```python
from rich.table import Table

def create_results_table(data: list[dict]) -> Table:
    """Create a table from data."""
    table = Table(title="Results")
    
    # Add columns
    if data:
        for key in data[0].keys():
            table.add_column(key, style="cyan")
    
    # Add rows
    for row in data:
        table.add_row(*[str(v) for v in row.values()])
    
    return table
```

---

## API Reference

### Console

```python
class Console:
    def print(self, *objects, **kwargs) -> None: ...
    def log(self, *objects, **kwargs) -> None: ...
    def print_json(self, json: str, **kwargs) -> None: ...
    def out(self, *objects, **kwargs) -> None: ...
    def rule(self, title: str = "", **kwargs) -> None: ...
    def status(self, status: RenderableType, **kwargs) -> Status: ...
    def input(self, prompt: TextType = "", **kwargs) -> str: ...
    def export_text(self) -> str: ...
    def export_html(self, **kwargs) -> str: ...
    def export_svg(self, **kwargs) -> str: ...
    def capture(self) -> Capture: ...
    def pager(self, **kwargs) -> PagerContext: ...
    def screen(self, **kwargs) -> ScreenContext: ...
```

### Markdown

```python
class Markdown:
    def __init__(
        self,
        markup: str,
        code_theme: str = "monokai",
        justify: JustifyMethod | None = None,
        style: str = "none",
        hyperlinks: bool = True,
        inline_code_lexer: str | None = None,
        inline_code_theme: str | None = None,
    ) -> None: ...
```

### Text

```python
class Text:
    def __init__(
        self,
        text: str = "",
        style: StyleType = "none",
        justify: JustifyMethod | None = None,
        overflow: OverflowMethod | None = None,
        no_wrap: bool | None = None,
        end: str = "\n",
        tab_size: int | None = None,
    ) -> None: ...
    
    @classmethod
    def from_markup(cls, text: str, **kwargs) -> Text: ...
    @classmethod
    def from_ansi(cls, text: str, **kwargs) -> Text: ...
    @classmethod
    def assemble(cls, *parts: str | Tuple[str, StyleType]) -> Text: ...
    
    def stylize(self, style: StyleType, start: int, end: int) -> None: ...
    def append(self, text: str | Text, style: StyleType = None) -> None: ...
    def highlight_words(self, words: list[str], style: StyleType) -> None: ...
    def highlight_regex(self, regex: str, style: StyleType) -> None: ...
```

### Style

```python
class Style:
    @classmethod
    def parse(cls, style_definition: str) -> Style: ...
    
    def __init__(
        self,
        color: ColorType | None = None,
        bgcolor: ColorType | None = None,
        bold: bool | None = None,
        dim: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
        blink: bool | None = None,
        blink2: bool | None = None,
        reverse: bool | None = None,
        conceal: bool | None = None,
        strike: bool | None = None,
        underline2: bool | None = None,
        frame: bool | None = None,
        encircle: bool | None = None,
        overline: bool | None = None,
    ) -> None: ...
```

---

## Resources

- **Documentation**: https://rich.readthedocs.io/
- **GitHub**: https://github.com/Textualize/rich
- **PyPI**: https://pypi.org/project/rich/
- **Examples**: https://github.com/Textualize/rich/tree/master/examples

---

## Installation

```bash
# Basic install
pip install rich

# With markdown support (includes markdown-it)
pip install "rich[markdown]"

# All extras
pip install "rich[all]"
```

---

*Document compiled for Alfred PRD - Rich TUI Integration*
