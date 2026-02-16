"""Tests for dispatcher command handling."""
import pytest
from pathlib import Path
from openclaw_pi.dispatcher import Dispatcher
from openclaw_pi.pi_manager import PiManager


@pytest.mark.asyncio
async def test_handle_command_status_empty(tmp_path: Path):
    """Test /status with no active threads."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()
    
    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    response = await dispatcher.handle_command("any_thread", "/status")
    
    assert "Active: 0" in response
    assert "Stored: 0" in response
    assert "OpenClaw Pi Status" in response
    
    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_handle_command_threads_empty(tmp_path: Path):
    """Test /threads with no stored threads."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()
    
    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    response = await dispatcher.handle_command("any_thread", "/threads")
    
    assert "No threads stored" in response
    
    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_handle_command_kill_no_args(tmp_path: Path):
    """Test /kill without thread_id shows usage."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()
    
    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    response = await dispatcher.handle_command("any_thread", "/kill")
    
    assert "Usage: /kill" in response
    
    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_handle_command_kill_nonexistent(tmp_path: Path):
    """Test /kill with nonexistent thread."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()
    
    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    response = await dispatcher.handle_command("any_thread", "/kill fake_thread")
    
    assert "not active" in response
    
    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_handle_command_cleanup(tmp_path: Path):
    """Test /cleanup kills all processes."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()
    
    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    response = await dispatcher.handle_command("any_thread", "/cleanup")
    
    assert "Killed 0 processes" in response
    
    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_handle_command_unknown(tmp_path: Path):
    """Test unknown command returns error."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()
    
    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    response = await dispatcher.handle_command("any_thread", "/unknown")
    
    assert "Unknown command" in response
    
    await dispatcher.shutdown()
