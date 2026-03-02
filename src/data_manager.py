"""XDG directory initialization and management.

Handles creation of XDG-compliant directories and copying of bundled
configuration files on first run.
"""

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

APP_NAME = "alfred"

# Default paths (bundled with package)
BUNDLED_CONFIG = Path(__file__).parent.parent / "config.json"
BUNDLED_TEMPLATES = Path(__file__).parent.parent / "templates"


def get_config_dir() -> Path:
    """Get XDG config directory for Alfred.

    Returns:
        Path to $XDG_CONFIG_HOME/alfred (default: ~/.config/alfred)
    """
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / APP_NAME
    return Path.home() / ".config" / APP_NAME


def get_data_dir() -> Path:
    """Get XDG data directory for Alfred.

    Returns:
        Path to $XDG_DATA_HOME/alfred (default: ~/.local/share/alfred)
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


def get_memory_dir() -> Path:
    """Get path to memory storage in XDG data directory."""
    return get_data_dir() / "memory"


def init_xdg_directories() -> None:
    """Initialize XDG directories with defaults if missing.

    Creates the following directories:
        - $XDG_CONFIG_HOME/alfred/
        - $XDG_DATA_HOME/alfred/
        - $XDG_DATA_HOME/alfred/workspace/
        - $XDG_DATA_HOME/alfred/memory/

    Copies bundled files only if they don't exist:
        - config.json -> $XDG_CONFIG_HOME/alfred/config.json
        - templates/ -> $XDG_DATA_HOME/alfred/templates/
    """
    # Create directories
    config_dir = get_config_dir()
    data_dir = get_data_dir()
    workspace_dir = get_workspace_dir()
    memory_dir = get_memory_dir()

    config_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    memory_dir.mkdir(parents=True, exist_ok=True)

    logger.debug(f"Config directory: {config_dir}")
    logger.debug(f"Data directory: {data_dir}")
    logger.debug(f"Workspace directory: {workspace_dir}")
    logger.debug(f"Memory directory: {memory_dir}")

    # Copy config if missing
    config_path = get_config_path()
    if not config_path.exists() and BUNDLED_CONFIG.exists():
        try:
            shutil.copy2(BUNDLED_CONFIG, config_path)
            logger.info(f"Created default config: {config_path}")
        except Exception as e:
            logger.warning(f"Failed to copy default config: {e}")
    elif config_path.exists():
        logger.debug(f"Using existing config: {config_path}")

    # Copy templates if missing
    templates_dir = get_templates_dir()
    if not templates_dir.exists() and BUNDLED_TEMPLATES.exists():
        try:
            shutil.copytree(BUNDLED_TEMPLATES, templates_dir)
            logger.info(f"Created default templates: {templates_dir}")
        except Exception as e:
            logger.warning(f"Failed to copy default templates: {e}")
    elif templates_dir.exists():
        logger.debug(f"Using existing templates: {templates_dir}")
