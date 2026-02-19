"""Configuration management for Alfred."""

import json
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    kimi_api_key: str = Field(
        ..., validation_alias=AliasChoices("KIMI_API_KEY", "kimi_api_key")
    )
    kimi_base_url: str = Field(
        ..., validation_alias=AliasChoices("KIMI_BASE_URL", "kimi_base_url")
    )

    # Runtime settings (no defaults - from config.json)
    default_llm_provider: str
    embedding_model: str
    chat_model: str
    memory_context_limit: int
    workspace_dir: Path
    memory_dir: Path
    context_files: dict[str, Path]


def load_config(config_path: Path = Path("config.json")) -> Config:
    """Load configuration with config.json as source of truth.

    Precedence (highest to lowest):
    1. Environment variables
    2. .env file
    3. config.json file (source of truth for defaults)
    """
    # Load base config from config.json
    base_config = {}
    if config_path.exists():
        with open(config_path) as f:
            base_config = json.load(f)

    # Pydantic merges: env vars override base_config values
    return Config(**base_config)
