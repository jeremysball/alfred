"""Integration tests for complex tool interactions and agent workflows."""

import os
import tempfile
from pathlib import Path

import pytest

from src.agent import Agent
from src.llm import ChatMessage
from src.tools import clear_registry, get_registry, register_builtin_tools
from src.tools.bash import BashTool
from src.tools.edit import EditTool
from src.tools.read import ReadTool
from src.tools.write import WriteTool


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset tool registry before each test."""
    clear_registry()
    yield
    clear_registry()


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for file operations."""
    import shutil
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        # Copy .env file to temp directory
        env_file = Path(original_cwd) / ".env"
        if env_file.exists():
            shutil.copy(env_file, Path(tmpdir) / ".env")
        os.chdir(tmpdir)
        yield tmpdir
        os.chdir(original_cwd)


class TestToolInteractions:
    """Test suite for complex tool interactions."""

    def test_read_write_sequence(self, temp_workspace):
        """Test writing then reading a file."""
        write_tool = WriteTool()
        read_tool = ReadTool()

        # Write a file
        write_result = write_tool.execute(
            path="test.txt",
            content="Hello World\nThis is a test\n"
        )
        assert write_result["success"] is True

        # Read it back
        read_result = read_tool.execute(path="test.txt")
        assert "Hello World" in read_result
        assert "This is a test" in read_result

    def test_write_edit_read_sequence(self, temp_workspace):
        """Test write, edit, then read sequence."""
        write_tool = WriteTool()
        edit_tool = EditTool()
        read_tool = ReadTool()

        # Write initial content
        write_tool.execute(
            path="config.txt",
            content="API_KEY=old_key\nDEBUG=false\n"
        )

        # Edit the file
        edit_result = edit_tool.execute(
            path="config.txt",
            old_text="API_KEY=old_key",
            new_text="API_KEY=new_key_123"
        )
        assert edit_result["success"] is True

        # Read and verify
        content = read_tool.execute(path="config.txt")
        assert "API_KEY=new_key_123" in content
        assert "DEBUG=false" in content
        assert "old_key" not in content

    def test_bash_write_read_sequence(self, temp_workspace):
        """Test bash to create file, then read it."""
        bash_tool = BashTool()
        read_tool = ReadTool()

        # Create file with bash
        bash_result = bash_tool.execute(
            command="echo 'Created by bash' > bash_output.txt"
        )
        assert bash_result["success"] is True

        # Read the file
        content = read_tool.execute(path="bash_output.txt")
        assert "Created by bash" in content

    def test_complex_editing_workflow(self, temp_workspace):
        """Test a complex editing workflow."""
        write_tool = WriteTool()
        edit_tool = EditTool()
        read_tool = ReadTool()
        bash_tool = BashTool()

        # 1. Create a Python file
        write_tool.execute(
            path="script.py",
            content='''#!/usr/bin/env python3
def greet(name):
    print(f"Hello, {name}!")

if __name__ == "__main__":
    greet("World")
'''
        )

        # 2. Edit to add a new function
        edit_tool.execute(
            path="script.py",
            old_text='def greet(name):',
            new_text='''def greet(name):
    """Greet someone."""
    print(f"Hello, {name}!")

def farewell(name):
    """Say goodbye."""
    print(f"Goodbye, {name}!")'''
        )

        # 3. Edit to update main block
        edit_tool.execute(
            path="script.py",
            old_text='    greet("World")',
            new_text='''    greet("World")
    farewell("World")'''
        )

        # 4. Verify with read
        content = read_tool.execute(path="script.py")
        assert "farewell" in content
        assert 'Goodbye' in content

        # 5. Run with bash
        bash_result = bash_tool.execute(command="python3 script.py")
        assert "Hello" in bash_result["stdout"]
        assert "Goodbye" in bash_result["stdout"]

    def test_file_tree_traversal(self, temp_workspace):
        """Test creating and traversing a directory tree."""
        bash_tool = BashTool()
        write_tool = WriteTool()
        read_tool = ReadTool()

        # Create directory structure
        bash_tool.execute(command="mkdir -p src/utils src/models tests")

        # Create files in directories
        write_tool.execute(path="src/main.py", content="# Main module")
        write_tool.execute(path="src/utils/helpers.py", content="# Helpers")
        write_tool.execute(path="src/models/data.py", content="# Data models")
        write_tool.execute(path="tests/test_main.py", content="# Tests")

        # List and verify structure
        result = bash_tool.execute(command="find . -type f | sort")
        files = result["stdout"].strip().split("\n")

        assert "./src/main.py" in files
        assert "./src/utils/helpers.py" in files
        assert "./src/models/data.py" in files
        assert "./tests/test_main.py" in files

    def test_large_file_handling(self, temp_workspace):
        """Test handling large files with truncation."""
        write_tool = WriteTool()
        read_tool = ReadTool()

        # Create a large file (more than 2000 lines)
        large_content = "\n".join([f"Line {i}" for i in range(1, 3000)])
        write_tool.execute(path="large.txt", content=large_content)

        # Read should be truncated
        result = read_tool.execute(path="large.txt")
        assert "[Output truncated" in result or len(result.split("\n")) <= 2000

        # Read with offset and limit
        partial = read_tool.execute(path="large.txt", offset=1000, limit=10)
        assert "Line 1000" in partial
        assert "Line 1009" in partial
        assert "Line 1010" not in partial


class TestToolRegistryIntegration:
    """Test tool registry in integration scenarios."""

    def test_all_tools_registered(self):
        """Test that all expected tools are registered."""
        register_builtin_tools()
        registry = get_registry()

        assert "read" in registry
        assert "write" in registry
        assert "edit" in registry
        assert "bash" in registry
        assert "remember" in registry
        assert "search_memories" in registry
        assert "update_memory" in registry
        assert "forget" in registry

        # Check we have exactly 8 tools
        assert len(registry) == 8

    def test_get_tool_schemas(self):
        """Test getting schemas for all tools."""
        register_builtin_tools()
        registry = get_registry()

        schemas = registry.get_schemas()
        assert len(schemas) == 8

        # Each schema should be OpenAI format
        for schema in schemas:
            assert schema["type"] == "function"
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]

    def test_tool_execution_via_registry(self, temp_workspace):
        """Test executing tools through registry lookup."""
        register_builtin_tools()
        registry = get_registry()

        # Write via registry
        write_tool = registry.get("write")
        write_tool.execute(path="via_registry.txt", content="Success")

        # Read via registry
        read_tool = registry.get("read")
        result = read_tool.execute(path="via_registry.txt")
        assert "Success" in result


class TestStreamingIntegration:
    """Test streaming functionality in integration scenarios."""

    @pytest.mark.asyncio
    async def test_bash_streaming_output(self, temp_workspace):
        """Test that bash tool streams output progressively."""
        bash_tool = BashTool()

        chunks = []
        async for chunk in bash_tool.execute_stream(
            command="echo 'Line 1' && echo 'Line 2' && echo 'Line 3'"
        ):
            chunks.append(chunk)

        full_output = "".join(chunks)
        assert "[Running:" in full_output
        assert "Line 1" in full_output
        assert "Line 2" in full_output
        assert "Line 3" in full_output

    @pytest.mark.asyncio
    async def test_read_streaming(self, temp_workspace):
        """Test read tool streaming."""
        write_tool = WriteTool()
        read_tool = ReadTool()

        # Create a multi-line file
        write_tool.execute(path="multiline.txt", content="A\nB\nC\nD\n")

        chunks = []
        async for chunk in read_tool.execute_stream(path="multiline.txt"):
            chunks.append(chunk)

        result = "".join(chunks)
        assert "A" in result
        assert "D" in result

    @pytest.mark.asyncio
    async def test_edit_streaming(self, temp_workspace):
        """Test edit tool streaming result."""
        write_tool = WriteTool()
        edit_tool = EditTool()

        write_tool.execute(path="to_edit.txt", content="old content here")

        chunks = []
        async for chunk in edit_tool.execute_stream(
            path="to_edit.txt",
            old_text="old",
            new_text="new"
        ):
            chunks.append(chunk)

        result = "".join(chunks)
        assert "success" in result.lower() or "edited" in result.lower()


@pytest.mark.skipif(
    os.environ.get("SKIP_LLM_TESTS"),
    reason="Skipping tests that require LLM"
)
class TestAgentWithRealLLM:
    """Integration tests requiring real LLM (optional)."""

    @pytest.mark.asyncio
    async def test_agent_reads_file(self, temp_workspace):
        """Test agent actually reading a file via LLM."""
        import os
        from pathlib import Path
        from src.config import load_config
        from src.llm import LLMFactory

        # Create a test file
        with open("test_content.txt", "w") as f:
            f.write("This is test content for the agent to read.")

        # Load config from original directory
        original_dir = "/workspace/alfred-prd"
        config = load_config(Path(original_dir) / "config.json")
        llm = LLMFactory.create(config)
        register_builtin_tools()
        registry = get_registry()

        agent = Agent(llm, registry, max_iterations=3)

        messages = [ChatMessage(role="user", content="Read the file test_content.txt")]

        result = await agent.run(messages)

        # Agent should have read and reported the content
        assert "test content" in result.lower()

    @pytest.mark.asyncio
    async def test_agent_writes_file(self, temp_workspace):
        """Test agent writing a file via LLM."""
        import os
        from pathlib import Path
        from src.config import load_config
        from src.llm import LLMFactory

        original_dir = "/workspace/alfred-prd"
        config = load_config(Path(original_dir) / "config.json")
        llm = LLMFactory.create(config)
        register_builtin_tools()
        registry = get_registry()

        agent = Agent(llm, registry, max_iterations=3)

        messages = [ChatMessage(
            role="user",
            content="Write 'Hello from Agent' to agent_output.txt"
        )]

        await agent.run(messages)

        # Verify file was created
        assert os.path.exists("agent_output.txt")
        with open("agent_output.txt") as f:
            content = f.read()
        assert "Hello from Agent" in content
