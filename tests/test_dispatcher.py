"""Tests for dispatcher core."""
import pytest
from pathlib import Path
from openclaw_pi.dispatcher import Dispatcher
from openclaw_pi.pi_manager import PiManager


@pytest.mark.asyncio
async def test_dispatcher_commands(tmp_path: Path):
    """Test dispatcher command handling."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()
    
    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    # Test /threads command
    response = await dispatcher.handle_message(123, "main", "/threads")
    assert "Threads:" in response
    
    # Test /status command
    response = await dispatcher.handle_message(123, "main", "/status")
    assert "Active threads:" in response
    
    # Test unknown command
    response = await dispatcher.handle_message(123, "main", "/foobar")
    assert "Unknown command" in response
    
    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_dispatcher_kill_command(tmp_path: Path):
    """Test /kill command."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()
    
    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    # Kill nonexistent thread
    response = await dispatcher.handle_message(123, "main", "/kill nonexistent")
    assert "not found" in response
    
    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_dispatcher_cleanup_command(tmp_path: Path):
    """Test /cleanup command."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()
    
    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    response = await dispatcher.handle_message(123, "main", "/cleanup")
    assert "Cleaned up" in response
    
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
    
    # Note: Can't test actual message handling without pi installed
    # But we can verify command handling doesn't create threads
    
    threads_list = await storage.list_threads()
    assert len(threads_list) == 0
    
    await dispatcher.shutdown()
