"""Tests for the edit tool."""

import os
import tempfile

import pytest

from src.tools import clear_registry, get_registry, register_builtin_tools
from src.tools.edit import EditTool


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset tool registry before each test."""
    clear_registry()
    yield
    clear_registry()


@pytest.fixture
def edit_tool():
    """Create an edit tool instance."""
    return EditTool()


@pytest.fixture
def temp_file():
    """Create a temporary file with content."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("Line 1\nLine 2\nLine 3\n")
        path = f.name
    yield path
    os.unlink(path)


class TestEditTool:
    """Test suite for edit tool."""

    def test_edit_simple_replacement(self, edit_tool, temp_file):
        """Test simple text replacement."""
        result = edit_tool.execute(
            path=temp_file,
            old_text="Line 2",
            new_text="Modified Line 2"
        )

        assert result["success"] is True
        assert result["edited"] is True

        with open(temp_file) as f:
            content = f.read()

        assert "Modified Line 2" in content
        assert "Line 1" in content  # Other lines unchanged

    def test_edit_multiline_replacement(self, edit_tool, temp_file):
        """Test replacing multiple lines."""
        result = edit_tool.execute(
            path=temp_file,
            old_text="Line 1\nLine 2",
            new_text="Replaced\nLines"
        )

        assert result["success"] is True

        with open(temp_file) as f:
            content = f.read()

        assert "Replaced" in content
        assert "Lines" in content
        assert "Line 3" in content  # Third line preserved

    def test_edit_only_first_occurrence(self, edit_tool, temp_file):
        """Test that only first occurrence is replaced."""
        # Create file with duplicate content
        with open(temp_file, "w") as f:
            f.write("dup\ndup\ndup\n")

        edit_tool.execute(
            path=temp_file,
            old_text="dup",
            new_text="unique"
        )

        with open(temp_file) as f:
            content = f.read()

        # Only first should be replaced
        assert content.count("unique") == 1
        assert content.count("dup") == 2

    def test_edit_nonexistent_file(self, edit_tool):
        """Test editing a file that doesn't exist."""
        result = edit_tool.execute(
            path="/nonexistent/file.txt",
            old_text="old",
            new_text="new"
        )

        assert result["success"] is False
        assert "not found" in result.get("error", "").lower()

    def test_edit_old_text_not_found(self, edit_tool, temp_file):
        """Test when old_text is not in file."""
        result = edit_tool.execute(
            path=temp_file,
            old_text="This text does not exist",
            new_text="New text"
        )

        assert result["success"] is False
        assert result["edited"] is False
        assert "not found" in result.get("error", "").lower()

    def test_edit_whitespace_sensitive(self, edit_tool, temp_file):
        """Test that edit is whitespace-sensitive."""
        with open(temp_file, "w") as f:
            f.write("  indented line\n")

        # Try to match with wrong whitespace
        result = edit_tool.execute(
            path=temp_file,
            old_text="indented line  ",  # trailing spaces
            new_text="changed"
        )

        assert result["success"] is False  # Should fail - whitespace matters

    @pytest.mark.asyncio
    async def test_streaming(self, edit_tool, temp_file):
        """Test streaming edit."""
        chunks = []
        async for chunk in edit_tool.execute_stream(
            path=temp_file,
            old_text="Line 2",
            new_text="Modified"
        ):
            chunks.append(chunk)

        result = "".join(chunks)
        assert "success" in result.lower() or "edited" in result.lower()

    def test_tool_registration(self):
        """Test that edit tool registers correctly."""
        register_builtin_tools()
        registry = get_registry()

        assert "edit" in registry
        tool = registry.get("edit")
        assert tool.name == "edit"

    def test_get_schema(self, edit_tool):
        """Test schema generation."""
        schema = edit_tool.get_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "edit"
        params = schema["function"]["parameters"]["properties"]
        assert "path" in params
        assert "old_text" in params
        assert "new_text" in params
