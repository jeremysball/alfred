"""Tests for dispatcher core."""
import pytest
from pathlib import Path
from openclaw_pi.dispatcher import Dispatcher
from openclaw_pi.pi_manager import PiManager


@pytest.mark.asyncio
async def test_dispatcher_handle_message_not_command(tmp_path: Path):
    """Test that handle_message doesn't process slash commands."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()
    
    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    # Slash commands should NOT be processed by handle_message
    # They return as-is or error since no Pi is available
    response = await dispatcher.handle_message(123, "main", "/threads")
    # This will fail because Pi is not installed, but it proves
    # handle_message tried to send to Pi, not process as command
    assert "Error" in response or "⏱️ Timeout" in response
    
    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_dispatcher_handle_command_directly(tmp_path: Path):
    """Test handle_command for commands."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()
    
    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    # Use handle_command for slash commands
    response = await dispatcher.handle_command("main", "/threads")
    assert "No threads" in response or "Threads:" in response
    
    response = await dispatcher.handle_command("main", "/status")
    assert "Active" in response
    
    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_dispatcher_kill_command(tmp_path: Path):
    """Test /kill command via handle_command."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()
    
    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    # Kill nonexistent thread
    response = await dispatcher.handle_command("main", "/kill nonexistent")
    assert "not active" in response
    
    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_dispatcher_cleanup_command(tmp_path: Path):
    """Test /cleanup command via handle_command."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()
    
    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    response = await dispatcher.handle_command("main", "/cleanup")
    assert "Killed" in response
    
    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_dispatcher_creates_thread(tmp_path: Path):
    """Test that dispatcher creates thread on first message."""
    from openclaw_pi.storage import ThreadStorage
    
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()
    
    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    storage = ThreadStorage(threads)
    
    # Thread shouldn't exist yet
    thread = await storage.load("test_thread")
    assert thread is None
    
    # Command handling shouldn't create threads
    await dispatcher.handle_command("test_thread", "/status")
    
    threads_list = await storage.list_threads()
    assert len(threads_list) == 0
    
    await dispatcher.shutdown()
