"""XDG directory initialization and management.

Handles creation of XDG-compliant directories and copying of bundled
configuration and data files on first run.
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


def get_config_toml_path() -> Path:
    """Get path to config.toml in XDG config directory.

    Returns:
        Path to $XDG_CONFIG_HOME/alfred/config.toml (default: ~/.config/alfred/config.toml)
    """
    return get_config_dir() / "config.toml"


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
        - templates/* -> $XDG_DATA_HOME/alfred/workspace/* (as data files)
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

    # Copy config.toml template if missing
    config_toml_path = get_config_toml_path()
    bundled_config_toml = BUNDLED_TEMPLATES / "config.toml"
    if not config_toml_path.exists() and bundled_config_toml.exists():
        try:
            shutil.copy2(bundled_config_toml, config_toml_path)
            logger.info(f"Created default config.toml: {config_toml_path}")
        except Exception as e:
            logger.warning(f"Failed to copy default config.toml: {e}")
    elif config_toml_path.exists():
        logger.debug(f"Using existing config.toml: {config_toml_path}")

    # Copy templates as data files to workspace
    # These become the user's editable context files (SOUL.md, USER.md, etc.)
    if BUNDLED_TEMPLATES.exists():
        for template_file in BUNDLED_TEMPLATES.glob("*.md"):
            target_path = workspace_dir / template_file.name
            if not target_path.exists():
                try:
                    shutil.copy2(template_file, target_path)
                    logger.info(f"Created workspace file: {target_path}")
                except Exception as e:
                    logger.warning(f"Failed to copy {template_file.name}: {e}")
            else:
                logger.debug(f"Using existing workspace file: {target_path}")
