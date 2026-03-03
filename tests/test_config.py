"""Tests for configuration loading."""


def test_toml_import_works() -> None:
    """Verify tomli can be imported for TOML parsing."""
    import tomli

    # Verify it's usable
    test_data = "key = 'value'"
    result = tomli.loads(test_data)
    assert result == {"key": "value"}
