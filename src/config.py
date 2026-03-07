"""Configuration management for Alfred."""

from pathlib import Path

import tomli
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.data_manager import get_config_toml_path, get_data_dir, get_memory_dir, get_workspace_dir
from src.type_defs import JsonObject, ensure_json_object


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

    # Tool calls in context configuration
    tool_calls_enabled: bool = True
    tool_calls_max_calls: int = 5
    tool_calls_max_tokens: int = 2000
    tool_calls_include_output: bool = True
    tool_calls_include_arguments: bool = True

    # Session summarization settings (PRD #76)
    session_summarize_idle_minutes: int = 30
    session_summarize_message_threshold: int = 20
    session_cron_interval_minutes: int = 5

    # UI/TUI settings
    use_markdown_rendering: bool = True
    input_cursor_color: str = "cyan"  # "reverse", "green", "red", "blue", "cyan"


def _get_section(data: JsonObject, key: str) -> JsonObject | None:
    value = data.get(key)
    if isinstance(value, dict):
        return ensure_json_object(value)
    return None


def _load_toml_config(toml_path: Path) -> JsonObject:
    """Load and flatten TOML config to flat dict.

    Converts nested sections like [provider] default = "x"
    to flat keys like default_llm_provider = "x".
    """
    with open(toml_path, "rb") as f:
        toml_data = ensure_json_object(tomli.load(f))

    flat_config: JsonObject = {}

    # Map TOML sections to flat config keys
    provider = _get_section(toml_data, "provider")
    if provider:
        if "default" in provider:
            flat_config["default_llm_provider"] = provider["default"]
        if "chat_model" in provider:
            flat_config["chat_model"] = provider["chat_model"]

    embeddings = _get_section(toml_data, "embeddings")
    if embeddings:
        if "model" in embeddings:
            flat_config["embedding_model"] = embeddings["model"]
        if "provider" in embeddings:
            flat_config["embedding_provider"] = embeddings["provider"]
        if "local_model" in embeddings:
            flat_config["local_embedding_model"] = embeddings["local_model"]

    memory = _get_section(toml_data, "memory")
    if memory:
        if "budget" in memory:
            flat_config["memory_budget"] = memory["budget"]
        if "ttl_days" in memory:
            flat_config["memory_ttl_days"] = memory["ttl_days"]
        if "warning_threshold" in memory:
            flat_config["memory_warning_threshold"] = memory["warning_threshold"]

    # Session configuration
    session = _get_section(toml_data, "session")
    if session:
        if "summarize_idle_minutes" in session:
            flat_config["session_summarize_idle_minutes"] = session[
                "summarize_idle_minutes"
            ]
        if "summarize_message_threshold" in session:
            flat_config["session_summarize_message_threshold"] = session[
                "summarize_message_threshold"
            ]
        if "cron_interval_minutes" in session:
            flat_config["session_cron_interval_minutes"] = session[
                "cron_interval_minutes"
            ]

    # UI/TUI configuration
    ui = _get_section(toml_data, "ui")
    if ui:
        if "use_markdown_rendering" in ui:
            flat_config["use_markdown_rendering"] = ui["use_markdown_rendering"]
        if "input_cursor_color" in ui:
            flat_config["input_cursor_color"] = ui["input_cursor_color"]

    # Tool calls configuration
    context = _get_section(toml_data, "context")
    if context:
        tool_calls = _get_section(context, "tool_calls")
        if tool_calls:
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

    base_config: JsonObject = {}

    if toml_path.exists():
        base_config = _load_toml_config(toml_path)

    # Create config with defaults
    config = Config.model_validate(base_config)

    # Compute context_files if not provided
    # Note: TOOLS.md is phased out (content moved to SYSTEM.md and USER.md per PRD #102)
    if config.context_files is None:
        config.context_files = {
            "system": config.workspace_dir / "SYSTEM.md",
            "agents": config.workspace_dir / "AGENTS.md",
            "soul": config.workspace_dir / "SOUL.md",
            "user": config.workspace_dir / "USER.md",
        }

    return config
