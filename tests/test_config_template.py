"""Tests for config.toml template."""



from src.data_manager import BUNDLED_TEMPLATES


def test_config_toml_template_exists():
    """Verify templates/config.toml exists with required sections."""
    config_toml_path = BUNDLED_TEMPLATES / "config.toml"

    assert config_toml_path.exists(), "config.toml template should exist"

    content = config_toml_path.read_text()

    # Check required sections exist
    assert "[provider]" in content
    assert "[embeddings]" in content
    assert "[memory]" in content
    assert "[search]" in content
    assert "[ui.status_line]" in content
    assert "[session]" in content

    # Check key config values
    assert 'default = "kimi"' in content
    assert "budget = 32000" in content
    assert "summarize_idle_minutes = 30" in content
    assert "summarize_message_threshold = 20" in content
    assert "cron_interval_minutes = 5" in content
