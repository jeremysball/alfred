"""Configuration management for Alfred."""

from pathlib import Path
from typing import Any

import tomli
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from alfred.data_manager import (
    get_config_toml_path,
    get_data_dir,
    get_memory_dir,
    get_workspace_dir,
)


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

    # Runtime settings (from config.toml or XDG defaults)
    default_llm_provider: str
    embedding_model: str
    chat_model: str
    memory_budget: int = 32000
    memory_ttl_days: int = 90
    memory_warning_threshold: int = 1000
    data_dir: Path = Field(default_factory=get_data_dir)
    workspace_dir: Path = Field(default_factory=get_workspace_dir)
    memory_dir: Path = Field(default_factory=get_memory_dir)
    context_files: dict[str, Path] | None = None

    # Embedding provider settings (PRD #105)
    embedding_provider: str = "openai"  # "openai" or "local"
    local_embedding_model: str = "bge-base"  # "bge-small", "bge-base", "bge-large"

    # Memory store settings
    memory_store: str = "sqlite"  # Only SQLite is supported now

    # Tool calls in context configuration
    tool_calls_enabled: bool = True
    tool_calls_max_calls: int = 5
    tool_calls_max_tokens: int = 2000
    tool_calls_include_output: bool = True
    tool_calls_include_arguments: bool = True

    # UI/TUI settings
    use_markdown_rendering: bool = True


def _load_toml_config(toml_path: Path) -> dict[str, Any]:
    """Load and flatten TOML config to flat dict.

    Converts nested sections like [provider] default = "x"
    to flat keys like default_llm_provider = "x".
    """
    with open(toml_path, "rb") as f:
        toml_data = tomli.load(f)

    flat_config: dict[str, Any] = {}

    # Map TOML sections to flat config keys
    if "provider" in toml_data:
        provider = toml_data["provider"]
        if "default" in provider:
            flat_config["default_llm_provider"] = provider["default"]
        if "chat_model" in provider:
            flat_config["chat_model"] = provider["chat_model"]

    if "embeddings" in toml_data:
        embeddings = toml_data["embeddings"]
        if "model" in embeddings:
            flat_config["embedding_model"] = embeddings["model"]
        if "provider" in embeddings:
            flat_config["embedding_provider"] = embeddings["provider"]
        if "local_model" in embeddings:
            flat_config["local_embedding_model"] = embeddings["local_model"]

    if "memory" in toml_data:
        memory = toml_data["memory"]
        if "budget" in memory:
            flat_config["memory_budget"] = memory["budget"]
        if "store" in memory:
            flat_config["memory_store"] = memory["store"]
        if "ttl_days" in memory:
            flat_config["memory_ttl_days"] = memory["ttl_days"]
        if "warning_threshold" in memory:
            flat_config["memory_warning_threshold"] = memory["warning_threshold"]

    # Tool calls configuration
    if "context" in toml_data:
        context = toml_data["context"]
        if "tool_calls" in context:
            tool_calls = context["tool_calls"]
            if "enabled" in tool_calls:
                flat_config["tool_calls_enabled"] = tool_calls["enabled"]
            if "max_calls" in tool_calls:
                flat_config["tool_calls_max_calls"] = tool_calls["max_calls"]
            if "max_tokens" in tool_calls:
                flat_config["tool_calls_max_tokens"] = tool_calls["max_tokens"]
            if "include_output" in tool_calls:
                flat_config["tool_calls_include_output"] = tool_calls["include_output"]
            if "include_arguments" in tool_calls:
                flat_config["tool_calls_include_arguments"] = tool_calls["include_arguments"]

    return flat_config


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration from config.toml.

    Precedence (highest to lowest):
    1. Environment variables
    2. .env file
    3. config.toml file (source of truth for defaults)
    4. XDG directory defaults

    Args:
        config_path: Path to config file. Defaults to XDG config directory.
    """
    toml_path = config_path or get_config_toml_path()

    base_config: dict[str, Any] = {}

    if toml_path.exists():
        base_config = _load_toml_config(toml_path)

    # Create config with defaults
    config = Config(**base_config)

    # Compute context_files if not provided
    if config.context_files is None:
        config.context_files = {
            "system": config.workspace_dir / "SYSTEM.md",
            "agents": config.workspace_dir / "AGENTS.md",
            "soul": config.workspace_dir / "SOUL.md",
            "user": config.workspace_dir / "USER.md",
        }

    return config
