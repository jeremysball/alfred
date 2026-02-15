"""Integration tests for dispatcher."""
from pathlib import Path

import pytest

from alfred.dispatcher import Dispatcher
from alfred.pi_manager import PiManager


@pytest.mark.asyncio
async def test_dispatcher_command_flow(tmp_path: Path):
    """Test the full dispatcher command flow via handle_command."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()

    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)

    # Test /status via handle_command
    response = await dispatcher.handle_command("test_chat", "/status")
    assert "Active" in response

    # Test /threads via handle_command
    response = await dispatcher.handle_command("test_chat", "/threads")
    assert "No threads" in response or "Threads:" in response

    # Test unknown command
    response = await dispatcher.handle_command("test_chat", "/foobar")
    assert "Unknown command" in response

    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_dispatcher_multiple_threads(tmp_path: Path):
    """Test handling multiple threads via commands."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()

    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)

    # Handle commands from different threads
    response1 = await dispatcher.handle_command("thread_1", "/status")
    response2 = await dispatcher.handle_command("thread_2", "/status")

    assert "Active" in response1
    assert "Active" in response2

    await dispatcher.shutdown()
