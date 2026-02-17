"""Tests for the write tool."""

import os
import tempfile
from pathlib import Path

import pytest

from src.tools import clear_registry, get_registry, register_builtin_tools
from src.tools.write import WriteTool


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset tool registry before each test."""
    clear_registry()
    yield
    clear_registry()


@pytest.fixture
def write_tool():
    """Create a write tool instance."""
    return WriteTool()


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestWriteTool:
    """Test suite for write tool."""

    def test_write_new_file(self, write_tool, temp_dir):
        """Test writing a new file."""
        path = os.path.join(temp_dir, "test.txt")
        content = "Hello World"
        
        result = write_tool.execute(path=path, content=content)
        
        assert result["success"] is True
        assert result["path"] == path
        assert os.path.exists(path)
        
        with open(path) as f:
            assert f.read() == content

    def test_overwrite_existing_file(self, write_tool, temp_dir):
        """Test overwriting an existing file."""
        path = os.path.join(temp_dir, "test.txt")
        
        # Create initial file
        with open(path, "w") as f:
            f.write("Old content")
        
        # Overwrite
        result = write_tool.execute(path=path, content="New content")
        
        assert result["success"] is True
        with open(path) as f:
            assert f.read() == "New content"

    def test_create_parent_directories(self, write_tool, temp_dir):
        """Test that parent directories are created."""
        path = os.path.join(temp_dir, "nested", "deep", "file.txt")
        
        result = write_tool.execute(path=path, content="Nested content")
        
        assert result["success"] is True
        assert os.path.exists(path)

    def test_write_empty_content(self, write_tool, temp_dir):
        """Test writing empty content."""
        path = os.path.join(temp_dir, "empty.txt")
        
        result = write_tool.execute(path=path, content="")
        
        assert result["success"] is True
        assert os.path.exists(path)
        assert os.path.getsize(path) == 0

    def test_write_bytes_written(self, write_tool, temp_dir):
        """Test bytes_written in result."""
        path = os.path.join(temp_dir, "test.txt")
        content = "Hello"
        
        result = write_tool.execute(path=path, content=content)
        
        assert result["bytes_written"] == len(content.encode("utf-8"))

    @pytest.mark.asyncio
    async def test_streaming(self, write_tool, temp_dir):
        """Test streaming write."""
        path = os.path.join(temp_dir, "stream_test.txt")
        content = "Streamed content"
        
        chunks = []
        async for chunk in write_tool.execute_stream(path=path, content=content):
            chunks.append(chunk)
        
        # Should complete and file should exist
        assert os.path.exists(path)
        with open(path) as f:
            assert f.read() == content

    def test_tool_registration(self):
        """Test that write tool registers correctly."""
        register_builtin_tools()
        registry = get_registry()
        
        assert "write" in registry
        tool = registry.get("write")
        assert tool.name == "write"

    def test_get_schema(self, write_tool):
        """Test schema generation."""
        schema = write_tool.get_schema()
        
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "write"
        params = schema["function"]["parameters"]["properties"]
        assert "path" in params
        assert "content" in params
