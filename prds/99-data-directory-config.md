# PRD #99: XDG Directory Configuration

## Overview

Implement XDG-compliant directory configuration. Store config in XDG_CONFIG_HOME and data/templates in XDG_DATA_HOME. This follows Linux standards and makes Alfred package-friendly.

## Problem Statement

Currently Alfred requires:
- `config.json` in the working directory
- `templates/` directory in the working directory
- `data/` directory in the working directory

This is problematic for:
- Package installations (pip install) where source is read-only
- Cluttered working directories
- No separation of config vs data
- Not following platform conventions

## Solution

Use XDG Base Directory Specification:
- **Config**: `$XDG_CONFIG_HOME/alfred/` (default: `~/.config/alfred/`)
- **Data**: `$XDG_DATA_HOME/alfred/` (default: `~/.local/share/alfred/`)

On startup:
1. Check if `$XDG_CONFIG_HOME/alfred/config.json` exists
2. If not, copy default config.json there
3. Check if `$XDG_DATA_HOME/alfred/templates/` exists
4. If not, copy templates/ there
5. Check if `$XDG_DATA_HOME/alfred/workspace/` exists
6. If not, create it
7. Load everything from XDG directories

## Implementation

### New Module: data_manager.py

```python
"""XDG directory initialization and management."""

import os
import shutil
from pathlib import Path

APP_NAME = "alfred"

# Default paths (bundled with package)
BUNDLED_CONFIG = Path(__file__).parent.parent / "config.json"
BUNDLED_TEMPLATES = Path(__file__).parent.parent / "templates"

def get_config_dir() -> Path:
    """Get XDG config directory for Alfred.
    
    Returns: $XDG_CONFIG_HOME/alfred (default: ~/.config/alfred)
    """
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / APP_NAME
    return Path.home() / ".config" / APP_NAME

def get_data_dir() -> Path:
    """Get XDG data directory for Alfred.
    
    Returns: $XDG_DATA_HOME/alfred (default: ~/.local/share/alfred)
    """
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        return Path(xdg_data) / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME

def get_config_path() -> Path:
    """Get path to config.json in XDG config directory."""
    return get_config_dir() / "config.json"

def get_templates_dir() -> Path:
    """Get path to templates in XDG data directory."""
    return get_data_dir() / "templates"

def get_workspace_dir() -> Path:
    """Get path to workspace in XDG data directory."""
    return get_data_dir() / "workspace"

def init_xdg_directories() -> None:
    """Initialize XDG directories with defaults if missing."""
    # Create directories
    get_config_dir().mkdir(parents=True, exist_ok=True)
    get_data_dir().mkdir(parents=True, exist_ok=True)
    get_workspace_dir().mkdir(parents=True, exist_ok=True)
    
    # Copy config if missing
    config_path = get_config_path()
    if not config_path.exists() and BUNDLED_CONFIG.exists():
        shutil.copy2(BUNDLED_CONFIG, config_path)
    
    # Copy templates if missing
    templates_dir = get_templates_dir()
    if not templates_dir.exists() and BUNDLED_TEMPLATES.exists():
        shutil.copytree(BUNDLED_TEMPLATES, templates_dir)
```

### Updated Config Loading

```python
# In main.py or entry point
from src.data_manager import init_xdg_directories, get_config_path

# Initialize XDG directories on startup
init_xdg_directories()

# Load config from XDG config directory
config = load_config(get_config_path())
```

### Updated Default Config

The bundled config.json should use XDG paths:
```json
{
  "default_llm_provider": "kimi",
  "embedding_model": "text-embedding-3-small",
  "chat_model": "kimi-k2-5",
  "workspace_dir": "{XDG_DATA_HOME}/alfred/workspace",
  "memory_dir": "{XDG_DATA_HOME}/alfred/memory",
  "context_files": {
    "agents": "{XDG_DATA_HOME}/alfred/workspace/AGENTS.md",
    "soul": "{XDG_DATA_HOME}/alfred/workspace/SOUL.md",
    "user": "{XDG_DATA_HOME}/alfred/workspace/USER.md",
    "tools": "{XDG_DATA_HOME}/alfred/workspace/TOOLS.md"
  }
}
```

Or better yet, don't store paths in config - compute them at runtime using XDG.

## Key Behaviors

| Scenario | Action |
|----------|--------|
| First run | Create ~/.config/alfred/ and ~/.local/share/alfred/ |
| Config missing | Copy bundled config.json to ~/.config/alfred/ |
| Templates missing | Copy bundled templates/ to ~/.local/share/alfred/templates/ |
| Existing files | Never overwrite user files |
| XDG vars set | Respect XDG_CONFIG_HOME and XDG_DATA_HOME |

## Success Criteria

- [ ] XDG directories created on first run
- [ ] Config stored in ~/.config/alfred/config.json
- [ ] Templates stored in ~/.local/share/alfred/templates/
- [ ] Workspace stored in ~/.local/share/alfred/workspace/
- [ ] Respects XDG_CONFIG_HOME environment variable
- [ ] Respects XDG_DATA_HOME environment variable
- [ ] User can edit files without affecting source
- [ ] Updates to bundled files don't overwrite user changes

## Implementation Status

**Status:** 🔄 IN PROGRESS

**Branch:** feature/prd-99-xdg-directories
