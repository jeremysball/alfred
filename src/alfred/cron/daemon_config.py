"""Configuration for AlfredDaemon - separate from main Alfred config."""

import logging
from pathlib import Path
from typing import Any

import tomli
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from alfred.data_manager import get_data_dir


class DaemonConfig(BaseSettings):
    """Configuration for AlfredDaemon (daemon.toml)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Required API keys (from environment)
    kimi_api_key: str = Field(..., validation_alias="KIMI_API_KEY")
    openai_api_key: str = Field(..., validation_alias="OPENAI_API_KEY")

    # Daemon-specific settings
    log_level: str = "INFO"
    data_dir: Path = Field(default_factory=get_data_dir)

    # Scheduler settings
    check_interval: float = 60.0  # Seconds between schedule checks


class DaemonTomlConfig(BaseSettings):
    """Settings loaded from daemon.toml file."""

    model_config = SettingsConfigDict(extra="ignore")

    log_level: str = "INFO"
    check_interval: float = 60.0


def _get_daemon_toml_path() -> Path:
    """Get path to daemon.toml config file."""
    from alfred.data_manager import get_config_dir

    return get_config_dir() / "daemon.toml"


def load_daemon_config(toml_path: Path | None = None) -> DaemonConfig:
    """Load daemon configuration from daemon.toml.

    Precedence (highest to lowest):
    1. Environment variables
    2. .env file
    3. daemon.toml file
    4. Defaults

    Args:
        toml_path: Path to daemon.toml. Defaults to XDG config directory.
    """
    toml_path = toml_path or _get_daemon_toml_path()

    toml_config: dict[str, Any] = {}
    if toml_path.exists():
        with open(toml_path, "rb") as f:
            toml_data = tomli.load(f)
            # Flatten [daemon] section if present
            toml_config = toml_data.get("daemon", toml_data)

    return DaemonConfig(**toml_config)


def setup_logging(config: DaemonConfig) -> None:
    """Setup logging with daemon configuration."""
    level = getattr(logging, config.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
