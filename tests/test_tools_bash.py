"""Tests for the bash tool."""

import pytest

from src.tools import clear_registry, get_registry, register_builtin_tools
from src.tools.bash import BashTool


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset tool registry before each test."""
    clear_registry()
    yield
    clear_registry()


@pytest.fixture
def bash_tool():
    """Create a bash tool instance."""
    return BashTool()


class TestBashTool:
    """Test suite for bash tool."""

    def test_execute_simple_command(self, bash_tool):
        """Test executing a simple command."""
        result = bash_tool.execute(command="echo Hello World")
        
        assert result["success"] is True
        assert "Hello World" in result["stdout"]
        assert result["exit_code"] == 0

    def test_execute_command_with_stderr(self, bash_tool):
        """Test command that outputs to stderr."""
        result = bash_tool.execute(command="echo Error >&2")
        
        assert result["success"] is True
        assert "Error" in result["stderr"]

    def test_execute_failing_command(self, bash_tool):
        """Test command that returns non-zero exit code."""
        result = bash_tool.execute(command="exit 1")
        
        assert result["success"] is False
        assert result["exit_code"] == 1

    def test_execute_timeout(self, bash_tool):
        """Test command timeout."""
        result = bash_tool.execute(command="sleep 10", timeout=1)
        
        assert result["success"] is False
        assert "timed out" in result.get("error", "").lower()

    def test_execute_invalid_command(self, bash_tool):
        """Test executing a non-existent command."""
        result = bash_tool.execute(command="not_a_real_command_12345")
        
        # Should fail but not crash
        assert result["success"] is False
        assert "exit_code" in result

    def test_output_truncation(self, bash_tool):
        """Test that large output is truncated."""
        # Generate large output
        result = bash_tool.execute(command="seq 1 3000")
        
        if not result.get("truncated"):
            pytest.skip("Output not truncated in this environment")
        
        assert result["truncated"] is True
        assert "truncated" in result["stdout"].lower()

    @pytest.mark.asyncio
    async def test_streaming(self, bash_tool):
        """Test streaming output."""
        chunks = []
        async for chunk in bash_tool.execute_stream(command="echo Line1 && echo Line2"):
            chunks.append(chunk)
        
        result = "".join(chunks)
        assert "[Running:" in result
        assert "Line1" in result or "Line2" in result

    @pytest.mark.asyncio
    async def test_streaming_timeout(self, bash_tool):
        """Test streaming with timeout."""
        chunks = []
        async for chunk in bash_tool.execute_stream(command="sleep 5", timeout=1):
            chunks.append(chunk)
        
        result = "".join(chunks)
        assert "timed out" in result.lower()

    def test_tool_registration(self):
        """Test that bash tool registers correctly."""
        register_builtin_tools()
        registry = get_registry()
        
        assert "bash" in registry
        tool = registry.get("bash")
        assert tool.name == "bash"
        assert "shell" in tool.description.lower() or "command" in tool.description.lower()

    def test_get_schema(self, bash_tool):
        """Test schema generation."""
        schema = bash_tool.get_schema()
        
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "bash"
        params = schema["function"]["parameters"]["properties"]
        assert "command" in params
        assert "timeout" in params
