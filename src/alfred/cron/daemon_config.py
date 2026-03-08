"""Configuration for AlfredDaemon - inherits from main Alfred config.

Daemon config merges with main Config, with daemon.toml taking priority.
"""

import logging
from pathlib import Path
from typing import Any

import tomli

from alfred.config import Config
from alfred.config import load_config as load_alfred_config
from alfred.data_manager import get_config_dir


def _get_daemon_toml_path() -> Path:
    """Get path to daemon.toml config file."""
    return get_config_dir() / "daemon.toml"


def load_daemon_config(toml_path: Path | None = None) -> Config:
    """Load daemon configuration.

    Merges main Alfred config with daemon.toml overrides.
    Precedence (highest to lowest):
    1. daemon.toml file (overrides)
    2. Environment variables
    3. .env file
    4. config.toml file

    Args:
        toml_path: Path to daemon.toml. Defaults to XDG config directory.
    """
    # Start with base Alfred config (loads env, .env, config.toml)
    base_config = load_alfred_config()

    # Load daemon.toml overrides
    toml_path = toml_path or _get_daemon_toml_path()
    daemon_overrides: dict[str, Any] = {}

    if toml_path.exists():
        with open(toml_path, "rb") as f:
            toml_data = tomli.load(f)
            # Flatten [daemon] section if present
            daemon_overrides = toml_data.get("daemon", toml_data)

    # If no daemon.toml, just return base config
    if not daemon_overrides:
        return base_config

    # Merge: daemon.toml overrides base config
    # Get base config as dict, then update with overrides
    base_dict = base_config.model_dump()
    base_dict.update(daemon_overrides)

    return Config(**base_dict)


def setup_logging(config: Config) -> None:
    """Setup logging with daemon configuration."""
    # Use log_level from config if available, default to INFO
    log_level = getattr(config, "log_level", "INFO")
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
