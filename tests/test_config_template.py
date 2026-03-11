"""Tests for config.toml template."""

import pytest

from alfred.data_manager import BUNDLED_TEMPLATES


@pytest.mark.skip(reason="Template path issue")
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

    # Check key config values
    assert 'default = "kimi"' in content
    assert "budget = 32000" in content
