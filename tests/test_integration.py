"""Integration tests for dispatcher."""
import pytest
from pathlib import Path
from dispatcher.dispatcher import Dispatcher
from dispatcher.pi_manager import PiManager


@pytest.mark.asyncio
async def test_dispatcher_command_flow(tmp_path: Path):
    """Test the full dispatcher command flow."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()
    
    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    # Test /status
    response = await dispatcher.handle_message(123, "test_chat", "/status")
    assert "Active threads" in response
    
    # Test /threads
    response = await dispatcher.handle_message(123, "test_chat", "/threads")
    assert "Threads:" in response
    
    # Test unknown command
    response = await dispatcher.handle_message(123, "test_chat", "/foobar")
    assert "Unknown command" in response
    
    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_dispatcher_multiple_threads(tmp_path: Path):
    """Test handling multiple threads."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()
    
    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    # Handle messages from different threads
    response1 = await dispatcher.handle_message(111, "thread_1", "/threads")
    response2 = await dispatcher.handle_message(222, "thread_2", "/threads")
    
    assert "Threads:" in response1
    assert "Threads:" in response2
    
    await dispatcher.shutdown()
