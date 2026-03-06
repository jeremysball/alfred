# PRD: String Interpolation Variables

## Overview

**Issue**: #34
**Parent**: #10 (Alfred - The Rememberer)
**Status**: Planning
**Priority**: Medium
**Created**: 2026-02-17

Enable dynamic values in context files, skills, and templates using `${VAR_NAME}` syntax.

---

## Problem Statement

Alfred's files contain static content, but some values are dynamic:
- API endpoints need the current port: `http://localhost:${ALFRED_API_PORT}/memories`
- Date stamps for memories: `Created on ${DATE}`
- Working directory references: `Current project: ${WORKING_DIR}`

Without interpolation, users must hardcode values or use workarounds.

---

## Solution

### Variable Syntax

Use `${VAR_NAME}` anywhere in supported files:

```markdown
# SKILL.md

Call the API at:
```bash
curl http://localhost:${ALFRED_API_PORT}/memories
```

Created: ${DATETIME}
```

### Built-in Variables

| Variable | Type | Example | Description |
|----------|------|---------|-------------|
| `${DATE}` | string | 2026-02-17 | Current date (ISO 8601) |
| `${DATETIME}` | string | 2026-02-17T16:30:45Z | Current datetime (ISO 8601, UTC) |
| `${TIMESTAMP}` | int | 1708195845 | Unix timestamp (seconds) |
| `${WORKING_DIR}` | string | /workspace/project | Current working directory |
| `${HOME}` | string | /home/user | User home directory |
| `${USER}` | string | jeremy | Current user name |
| `${ALFRED_API_PORT}` | int | 8080 | API server port |
| `${ALFRED_VERSION}` | string | 1.0.0 | Alfred version |

### Where It Works

Interpolation applies to:

1. **Context files** — `AGENTS.md`, `SOUL.md`, `USER.md`, `TOOLS.md`, `MEMORY.md`
2. **Skills** — All `SKILL.md` files
3. **Templates** — All files in `templates/`

### Where It Does NOT Work

- Source code files (Python files)
- Memory files (`memory/YYYY-MM-DD.md`)
- Configuration files (`config.toml`)
- Shell scripts (unless explicitly passed through interpolation)

---

## Implementation

### Interpolator Class

```python
# src/interpolation.py

import os
import re
from datetime import datetime, timezone
from typing import Optional

from src.config import Config


class InterpolationError(Exception):
    """Raised when interpolation fails."""
    pass


class Interpolator:
    """Replace ${VAR_NAME} with dynamic values."""
    
    # Regex for ${VAR_NAME}
    VAR_PATTERN = re.compile(r'\$\{([A-Z_][A-Z0-9_]*)\}')
    
    def __init__(self, config: Config) -> None:
        self.config = config
        self._builtins = self._build_builtins()
    
    def _build_builtins(self) -> dict[str, str]:
        """Build built-in variable dictionary."""
        now = datetime.now(timezone.utc)
        
        return {
            'DATE': now.strftime('%Y-%m-%d'),
            'DATETIME': now.isoformat(),
            'TIMESTAMP': str(int(now.timestamp())),
            'WORKING_DIR': os.getcwd(),
            'HOME': os.path.expanduser('~'),
            'USER': os.environ.get('USER', 'unknown'),
            'ALFRED_API_PORT': str(self.config.api_port),
            'ALFRED_VERSION': '1.0.0',  # Import from package
        }
    
    def interpolate(self, content: str, context: Optional[dict[str, str]] = None) -> str:
        """Replace all variables in content.
        
        Args:
            content: String with ${VAR_NAME} placeholders
            context: Optional additional variables (not used for built-ins)
        
        Returns:
            Content with variables replaced
        
        Raises:
            InterpolationError: If unknown variable found
        """
        variables = self._builtins.copy()
        if context:
            variables.update(context)
        
        def replace_var(match: re.Match) -> str:
            var_name = match.group(1)
            
            if var_name not in variables:
                known = ', '.join(sorted(variables.keys()))
                raise InterpolationError(
                    f"Unknown variable '${{{var_name}}}'. "
                    f"Known variables: {known}"
                )
            
            return variables[var_name]
        
        return self.VAR_PATTERN.sub(replace_var, content)
    
    def extract_variables(self, content: str) -> set[str]:
        """Extract all variable names from content without replacing."""
        return set(self.VAR_PATTERN.findall(content))
    
    def has_variables(self, content: str) -> bool:
        """Check if content contains any variables."""
        return bool(self.VAR_PATTERN.search(content))
```

### Integration with File Reading

```python
# src/context.py (updated)

from src.interpolation import Interpolator


class ContextLoader:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.cache: dict[str, CacheEntry] = {}
        self.interpolator = Interpolator(config)
    
    async def load_file(self, path: Path, interpolate: bool = True) -> str:
        """Load file with optional interpolation.
        
        Args:
            path: File to load
            interpolate: Whether to replace ${VAR_NAME} (default: True)
        
        Returns:
            File content, interpolated if requested
        """
        # Check cache for raw content
        key = str(path)
        now = time.time()
        
        if key in self.cache:
            entry = self.cache[key]
            if now - entry.timestamp < self.config.cache_ttl:
                # Return cached (interpolated if requested)
                content = entry.content
            else:
                # Expired, reload
                content = await self._read_file(path)
                self.cache[key] = CacheEntry(content=content, timestamp=now)
        else:
            # Not cached
            content = await self._read_file(path)
            self.cache[key] = CacheEntry(content=content, timestamp=now)
        
        # Interpolate fresh each time
        if interpolate and self.interpolator.has_variables(content):
            return self.interpolator.interpolate(content)
        
        return content
    
    async def assemble(self) -> Context:
        """Assemble context with interpolation."""
        # Load all context files with interpolation
        agents = await self.load_file(self.paths['agents'])
        soul = await self.load_file(self.paths['soul'])
        user = await self.load_file(self.paths['user'])
        tools = await self.load_file(self.paths['tools'])
        memory = await self.load_file(self.paths['memory'])
        
        # ... rest of assembly ...
```

### Integration with Skills

```python
# src/skills.py (updated)

from src.interpolation import Interpolator


class SkillLoader:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.interpolator = Interpolator(config)
    
    def load_skill(self, path: Path) -> Skill:
        """Load and interpolate a skill."""
        content = path.read_text()
        
        # Interpolate variables in skill content
        if self.interpolator.has_variables(content):
            content = self.interpolator.interpolate(content)
        
        # Parse frontmatter and body
        frontmatter, body = self._parse_content(content)
        
        return Skill(
            name=frontmatter['name'],
            description=frontmatter['description'],
            content=content,
            path=path,
        )
```

### Integration with Templates

```python
# src/templates.py (updated)

from src.interpolation import Interpolator


class TemplateManager:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.interpolator = Interpolator(config)
    
    def load_template(self, name: str) -> str:
        """Load template with interpolation."""
        path = self.template_dir / f"{name}.md"
        content = path.read_text()
        
        # Always interpolate templates
        return self.interpolator.interpolate(content)
```

---

## Usage Examples

### In a Skill

```markdown
---
name: remember
description: Store information to Alfred's memory.
---

# Remember Skill

Store a memory to Alfred's long-term storage.

## Usage

```bash
curl -s -X POST http://localhost:${ALFRED_API_PORT}/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "Your memory here"}'
```

Stored at: ${DATETIME}
```

### In AGENTS.md

```markdown
# Agent Behavior Rules

## Environment

- Working directory: ${WORKING_DIR}
- Current date: ${DATE}
- Alfred version: ${ALFRED_VERSION}
```

### In a Template

```markdown
# USER.md

Created: ${DATETIME}
User: ${USER}
Home: ${HOME}
```

---

## Error Handling

### Unknown Variable

```python
try:
    content = interpolator.interpolate("Hello ${UNKNOWN}")
except InterpolationError as e:
    # e.message: "Unknown variable '${UNKNOWN}'. Known variables: ALFRED_API_PORT, ALFRED_VERSION, DATE, ..."
    raise
```

### Error Surfaces Immediately

If a context file contains an unknown variable, Alfred fails on startup with a clear error:

```
ERROR: Failed to load AGENTS.md: Unknown variable '${INVALID_VAR}'. Known variables: DATE, DATETIME, HOME, USER, WORKING_DIR, ALFRED_API_PORT, ALFRED_VERSION, TIMESTAMP
```

---

## Performance

- **File read**: Cached (expensive)
- **Interpolation**: Fresh each time (cheap)
- **Variable detection**: Regex scan (fast)

```python
# Interpolation is cheap
content = cache.get(path)           # Cached
if interpolator.has_variables(content):
    content = interpolator.interpolate(content)  # Fresh
```

---

## Milestones

| # | Milestone | Description |
|---|-----------|-------------|
| **1** | Interpolator class | `Interpolator` with 8 built-in variables |
| **2** | Error handling | `InterpolationError`, fail fast on unknown vars |
| **3** | Context integration | Update `ContextLoader.load_file()` |
| **4** | Skill integration | Update `SkillLoader.load_skill()` |
| **5** | Template integration | Update `TemplateManager.load_template()` |
| **6** | Tests | Unit tests, integration tests |

---

## Acceptance Criteria

- [ ] All 8 built-in variables work correctly
- [ ] `${DATE}` returns YYYY-MM-DD format
- [ ] `${DATETIME}` returns ISO 8601 UTC
- [ ] `${WORKING_DIR}` returns current working directory
- [ ] `${ALFRED_API_PORT}` uses config value
- [ ] Variables work in context files
- [ ] Variables work in skills
- [ ] Variables work in templates
- [ ] Unknown variable raises `InterpolationError`
- [ ] Error message lists all known variables
- [ ] Interpolation happens fresh on each load (not cached)
- [ ] No escaping mechanism (by design)

---

## Tests

```python
# tests/test_interpolation.py

import pytest
from datetime import datetime
from src.interpolation import Interpolator, InterpolationError
from src.config import Config


@pytest.fixture
def interpolator():
    config = Config(api_port=8080)
    return Interpolator(config)


def test_date_variable(interpolator):
    result = interpolator.interpolate("Today is ${DATE}")
    # Check format: YYYY-MM-DD
    assert len(result) == len("Today is 2026-02-17")
    assert result.startswith("Today is 20")


def test_api_port_variable(interpolator):
    result = interpolator.interpolate("Port: ${ALFRED_API_PORT}")
    assert result == "Port: 8080"


def test_multiple_variables(interpolator):
    result = interpolator.interpolate("${USER} at ${HOME}")
    assert " at " in result
    assert not result.startswith("$")


def test_unknown_variable_raises(interpolator):
    with pytest.raises(InterpolationError) as exc_info:
        interpolator.interpolate("${UNKNOWN_VAR}")
    
    assert "UNKNOWN_VAR" in str(exc_info.value)
    assert "known variables" in str(exc_info.value).lower()


def test_extract_variables(interpolator):
    content = "${DATE} and ${USER} and ${DATE} again"
    vars = interpolator.extract_variables(content)
    assert vars == {"DATE", "USER"}


def test_has_variables(interpolator):
    assert interpolator.has_variables("${DATE}") is True
    assert interpolator.has_variables("no variables") is False
    assert interpolator.has_variables("literal $100") is False
```

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2026-02-17 | 8 built-in variables | Cover common use cases | Extensible later |
| 2026-02-17 | No custom variables | Simplicity, avoid complexity | Revisit if needed |
| 2026-02-17 | No escaping | Rare need, YAGNI | Cannot have literal `${DATE}` |
| 2026-02-17 | Interpolate fresh | Variables change over time | Slight CPU overhead |
| 2026-02-17 | Fail fast | Surface errors immediately | Startup fails on bad vars |
| 2026-02-17 | `${VAR}` syntax | Common, recognizable | Matches shell style |

---

## File Structure

```
src/
└── interpolation.py      # Interpolator class
```

---

## Dependencies

- `re` — Regex for variable detection (built-in)
- `os` — Environment and path info (built-in)
- `datetime` — Date/time variables (built-in)

---

## Notes

- Variables are uppercase by convention
- Pattern is `${VAR_NAME}` — requires braces
- No nesting: `${DATE}` works, `${${DATE}}` does not
- Order: Built-ins can be overridden by context (future-proofing)
