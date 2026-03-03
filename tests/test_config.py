"""Tests for configuration loading."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config import load_config


def test_toml_import_works() -> None:
    """Verify tomli can be imported for TOML parsing."""
    import tomli

    # Verify it's usable
    test_data = "key = 'value'"
    result = tomli.loads(test_data)
    assert result == {"key": "value"}


def test_load_config_reads_toml():
    """Verify load_config() parses TOML file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text("""
[provider]
default = "kimi"
chat_model = "kimi-k2-5"

[embeddings]
model = "text-embedding-3-small"

[memory]
budget = 32000
""")
        with patch("src.config.get_config_toml_path", return_value=config_path):
            config = load_config()

            assert config.default_llm_provider == "kimi"
            assert config.chat_model == "kimi-k2-5"
            assert config.embedding_model == "text-embedding-3-small"
            assert config.memory_budget == 32000


def test_config_has_memory_budget_field():
    """Verify Config.memory_budget exists with default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text("""
[provider]
default = "kimi"
chat_model = "kimi-k2-5"

[embeddings]
model = "text-embedding-3-small"

[memory]
budget = 64000
""")
        with patch("src.config.get_config_toml_path", return_value=config_path):
            config = load_config()

            assert hasattr(config, "memory_budget")
            assert config.memory_budget == 64000


def test_memory_budget_loads_from_toml():
    """Verify [memory] section budget key loads."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text("""
[provider]
default = "kimi"
chat_model = "kimi-k2-5"

[embeddings]
model = "text-embedding-3-small"

[memory]
budget = 64000
""")
        with patch("src.config.get_config_toml_path", return_value=config_path):
            config = load_config()

            assert config.memory_budget == 64000


def test_default_llm_provider_from_toml():
    """Verify nested [provider] section loads correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text("""
[provider]
default = "anthropic"
chat_model = "claude-3"

[embeddings]
model = "text-embedding-3-small"

[memory]
budget = 32000
""")
        with patch("src.config.get_config_toml_path", return_value=config_path):
            config = load_config()

            assert config.default_llm_provider == "anthropic"
            assert config.chat_model == "claude-3"


def test_load_config_with_explicit_path():
    """Verify load_config() works with explicit path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "custom.toml"
        config_path.write_text("""
[provider]
default = "kimi"
chat_model = "kimi-k2-5"

[embeddings]
model = "text-embedding-3-small"

[memory]
budget = 32000
""")
        config = load_config(config_path=config_path)

        assert config.default_llm_provider == "kimi"
