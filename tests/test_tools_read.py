"""Tests for the read tool."""

import os
import tempfile

import pytest

from src.tools import clear_registry, get_registry, register_builtin_tools
from src.tools.read import ReadTool


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset tool registry before each test."""
    clear_registry()
    yield
    clear_registry()


@pytest.fixture
def read_tool():
    """Create a read tool instance."""
    return ReadTool()


@pytest.fixture
def temp_file():
    """Create a temporary file with content."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("Line 1\nLine 2\nLine 3\n")
        path = f.name
    yield path
    os.unlink(path)


class TestReadTool:
    """Test suite for read tool."""

    def test_read_entire_file(self, read_tool, temp_file):
        """Test reading an entire file."""
        result = read_tool.execute(path=temp_file)

        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_read_with_offset(self, read_tool, temp_file):
        """Test reading with offset parameter."""
        result = read_tool.execute(path=temp_file, offset=2)

        assert "Line 1" not in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_read_with_limit(self, read_tool, temp_file):
        """Test reading with limit parameter."""
        result = read_tool.execute(path=temp_file, limit=1)

        assert "Line 1" in result
        assert "Line 2" not in result

    def test_read_with_offset_and_limit(self, read_tool, temp_file):
        """Test reading with both offset and limit."""
        result = read_tool.execute(path=temp_file, offset=2, limit=1)

        assert "Line 1" not in result
        assert "Line 2" in result
        assert "Line 3" not in result

    def test_read_nonexistent_file(self, read_tool):
        """Test reading a file that doesn't exist."""
        result = read_tool.execute(path="/nonexistent/path/file.txt")

        assert "Error" in result
        assert "not found" in result.lower()

    def test_read_empty_file(self, read_tool):
        """Test reading an empty file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("")
            path = f.name

        try:
            result = read_tool.execute(path=path)
            assert "[File is empty]" in result or result == ""
        finally:
            os.unlink(path)

    def test_read_image_file(self, read_tool):
        """Test reading an image file returns image marker."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            path = f.name

        try:
            result = read_tool.execute(path=path)
            assert "[Image file:" in result
            assert "png" in result.lower()
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_read_streaming(self, read_tool, temp_file):
        """Test streaming read."""
        chunks = []
        async for chunk in read_tool.execute_stream(path=temp_file):
            chunks.append(chunk)

        result = "".join(chunks)
        assert "Line 1" in result
        assert "Line 2" in result

    def test_tool_registration(self):
        """Test that read tool registers correctly."""
        register_builtin_tools()
        registry = get_registry()

        assert "read" in registry
        tool = registry.get("read")
        assert tool.name == "read"
        assert "file" in tool.description.lower()

    def test_get_schema(self, read_tool):
        """Test schema generation."""
        schema = read_tool.get_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "read"
        assert "path" in schema["function"]["parameters"]["properties"]
        assert "offset" in schema["function"]["parameters"]["properties"]
        assert "limit" in schema["function"]["parameters"]["properties"]
