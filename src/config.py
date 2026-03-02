"""Configuration management for Alfred."""

import json
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.data_manager import get_config_path, get_memory_dir, get_workspace_dir


class Config(BaseSettings):
    """Application configuration with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram (required - no default)
    telegram_bot_token: str = Field(
        ..., validation_alias=AliasChoices("TELEGRAM_BOT_TOKEN", "telegram_bot_token")
    )

    # OpenAI (required - no default)
    openai_api_key: str = Field(
        ..., validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key")
    )

    # Kimi (required - no defaults)
    kimi_api_key: str = Field(..., validation_alias=AliasChoices("KIMI_API_KEY", "kimi_api_key"))
    kimi_base_url: str = Field(..., validation_alias=AliasChoices("KIMI_BASE_URL", "kimi_base_url"))

    # Runtime settings (from config.json or XDG defaults)
    default_llm_provider: str
    embedding_model: str
    chat_model: str
    workspace_dir: Path = Field(default_factory=get_workspace_dir)
    memory_dir: Path = Field(default_factory=get_memory_dir)
    context_files: dict[str, Path] | None = None


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration with config.json as source of truth.

    Precedence (highest to lowest):
    1. Environment variables
    2. .env file
    3. config.json file (source of truth for defaults)
    4. XDG directory defaults

    Args:
        config_path: Path to config.json. Defaults to XDG config directory.
    """
    if config_path is None:
        config_path = get_config_path()

    # Load base config from config.json
    base_config = {}
    if config_path.exists():
        with open(config_path) as f:
            base_config = json.load(f)

    # Create config with XDG defaults
    config = Config(**base_config)

    # Compute context_files if not provided
    if config.context_files is None:
        config.context_files = {
            "agents": config.workspace_dir / "AGENTS.md",
            "soul": config.workspace_dir / "SOUL.md",
            "user": config.workspace_dir / "USER.md",
            "tools": config.workspace_dir / "TOOLS.md",
        }

    return config
