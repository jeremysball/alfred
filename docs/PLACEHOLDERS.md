# Placeholder System

Alfred's placeholder system enables modular, composable prompts through two placeholder types:

- **File includes**: `{{path/to/file.md}}` — Include content from other files
- **ANSI colors**: `{cyan}`, `{reset}` — Add terminal colors to text

---

## Overview

Placeholders are resolved when `ContextLoader` loads context files. All `.md` files in the workspace have placeholders resolved automatically.

**Resolution order:**
1. File includes (`{{path}}`) processed first
2. Color placeholders (`{color}`) processed second
3. Nested includes resolved recursively (max depth: 5)

---

## File Includes

### Syntax

```markdown
{{relative/path/from/workspace.md}}
```

The path is relative to the workspace directory (`~/.local/share/alfred/workspace/`).

### Example

**Directory structure:**
```
workspace/
├── USER.md
└── prompts/
    ├── communication-style.md
    └── tech-stack.md
```

**USER.md:**
```markdown
# User Profile

{{prompts/communication-style.md}}

## Technical Preferences
{{prompts/tech-stack.md}}
```

**prompts/communication-style.md:**
```markdown
## Communication Style

- Prefers concise responses
- Appreciates code examples over prose
```

**Resolved output:**
```markdown
# User Profile

<!-- included: prompts/communication-style.md -->
## Communication Style

- Prefers concise responses
- Appreciates code examples over prose
<!-- end: prompts/communication-style.md -->

## Technical Preferences
<!-- included: prompts/tech-stack.md -->
...
<!-- end: prompts/tech-stack.md -->
```

### Features

- **Nested includes**: Files can include other files (up to 5 levels deep)
- **Circular detection**: Circular references are detected and logged
- **Missing file handling**: Missing files produce a comment, not a crash
- **Transparency**: HTML comments show what was included

### Error Handling

| Situation | Behavior |
|-----------|----------|
| Missing file | `<!-- missing: path.md -->` + warning log |
| Circular reference | `<!-- circular: path.md -->` + error log |
| Max depth exceeded | Original placeholder preserved + warning log |
| Read error | `<!-- error: path.md -->` + error log |

---

## Color Placeholders

### Syntax

```markdown
{color}text{reset}
```

### Available Colors

| Placeholder | ANSI Code | Example |
|-------------|-----------|---------|
| `{black}` | `\033[30m` | Black text |
| `{red}` | `\033[31m` | Red text |
| `{green}` | `\033[32m` | Green text |
| `{yellow}` | `\033[33m` | Yellow text |
| `{blue}` | `\033[34m` | Blue text |
| `{magenta}` | `\033[35m` | Magenta text |
| `{cyan}` | `\033[36m` | Cyan text |
| `{white}` | `\033[37m` | White text |

### Bright Colors

| Placeholder | ANSI Code |
|-------------|-----------|
| `{bright_black}` | `\033[90m` |
| `{bright_red}` | `\033[91m` |
| `{bright_green}` | `\033[92m` |
| `{bright_yellow}` | `\033[93m` |
| `{bright_blue}` | `\033[94m` |
| `{bright_magenta}` | `\033[95m` |
| `{bright_cyan}` | `\033[96m` |
| `{bright_white}` | `\033[97m` |

### Background Colors

Prefix any color with `on_`:

| Placeholder | ANSI Code |
|-------------|-----------|
| `{on_red}` | `\033[41m` |
| `{on_green}` | `\033[42m` |
| `{on_cyan}` | `\033[46m` |

Bright backgrounds: `{on_bright_red}`, `{on_bright_green}`, etc.

### Styles

| Placeholder | ANSI Code | Effect |
|-------------|-----------|--------|
| `{bold}` | `\033[1m` | Bold text |
| `{dim}` | `\033[2m` | Dimmed text |
| `{italic}` | `\033[3m` | Italic text |
| `{underline}` | `\033[4m` | Underlined text |
| `{reset}` | `\033[0m` | Reset all styles |

### Example

```markdown
{cyan}alfred{reset} {bold}ready{reset}

{yellow}Warning:{reset} {dim}deprecated{reset}
```

**Rendered:**
- "alfred" in cyan
- "ready" in bold
- "Warning:" in yellow
- "deprecated" in dim

---

## API

### Convenience Functions

```python
from pathlib import Path
from alfred.placeholders import resolve_all, resolve_file_includes, resolve_colors

# Resolve everything (recommended)
content = resolve_all(text, base_dir=Path("/workspace"))

# Resolve only file includes
content = resolve_file_includes(text, base_dir=Path("/workspace"))

# Resolve only colors
content = resolve_colors(text)
```

### Low-Level API

```python
from alfred.placeholders import (
    ResolutionContext,
    resolve_placeholders,
    FileIncludeResolver,
    ColorResolver,
)

# Create context
ctx = ResolutionContext(
    base_dir=Path("/workspace"),
    max_depth=5,  # default
)

# Resolve with specific resolvers
result = resolve_placeholders(
    text,
    ctx,
    resolvers=[FileIncludeResolver()],  # only file includes
)
```

### ResolutionContext

Tracks state during resolution:

```python
ctx = ResolutionContext(base_dir=workspace_path, max_depth=5)

# Check for circular references
if ctx.is_circular(file_path):
    # handle circular

# Check depth limit
if ctx.is_depth_exceeded():
    # handle max depth

# Create new context with updated state
new_ctx = ctx.with_loaded(file_path).with_incremented_depth()
```

---

## Architecture

### Protocol-Based Design

The system uses a `PlaceholderResolver` protocol for extensibility:

```python
class PlaceholderResolver(Protocol):
    pattern: re.Pattern

    def resolve(self, match: re.Match, context: ResolutionContext) -> str:
        ...
```

**Built-in resolvers:**
- `FileIncludeResolver` — `{{path}}` syntax
- `ColorResolver` — `{color}` syntax

**Adding custom resolvers:**

```python
class VariableResolver:
    """Resolve {{var:name}} placeholders."""
    pattern = re.compile(r'\{\{var:(\w+)\}\}')

    def __init__(self, variables: dict[str, str]):
        self.variables = variables

    def resolve(self, match: re.Match, context: ResolutionContext) -> str:
        name = match.group(1)
        return self.variables.get(name, match.group(0))

# Use custom resolver
resolve_placeholders(text, ctx, resolvers=[VariableResolver({"user": "Alice"})])
```

### ContextLoader Integration

`ContextLoader.load_file()` resolves placeholders automatically:

```python
async def load_file(self, name: str, path: Path) -> ContextFile:
    # ... load content from disk ...

    # Resolve placeholders
    content = resolve_all(content, self.config.workspace_dir)

    # ... cache and return ...
```

**Implications:**
- Cached content contains resolved placeholders
- Original content is not preserved in cache
- Changes to included files require cache invalidation

---

## Testing

Tests are in `tests/test_placeholders.py` and `tests/test_context_integration.py`:

```bash
# Run placeholder tests
uv run pytest tests/test_placeholders.py -v

# Run integration tests (includes placeholder resolution in ContextLoader)
uv run pytest tests/test_context_integration.py -v
```

### Test Coverage

| Area | Tests |
|------|-------|
| ResolutionContext | State management, circular detection, depth tracking |
| FileIncludeResolver | Simple includes, nested, circular, missing, max depth |
| ColorResolver | Colors, styles, unknown placeholders |
| API functions | `resolve_all`, `resolve_file_includes`, `resolve_colors` |
| ContextLoader | Integration with file loading, caching |

---

## Best Practices

### For Prompt Authors

1. **Use `prompts/` subdirectory** — Keep modular components organized
2. **Document dependencies** — Comment what each file expects/provides
3. **Keep includes atomic** — Each file should be self-contained
4. **Limit nesting** — Avoid deeply nested includes (harder to debug)

### For Developers

1. **Use `resolve_all()`** — Handles both placeholder types
2. **Check logs for warnings** — Missing files and circular refs are logged
3. **Invalidate cache after changes** — Included file changes don't auto-invalidate
4. **Test with real files** — Unit tests are good, integration tests are better

---

## Related Documentation

- [ROADMAP.md](ROADMAP.md) — Overall architecture and milestones
- [MEMORY.md](MEMORY.md) — Memory system design
- [PRD #102](../prds/102-unified-memory-system.md) — Unified Memory System design
