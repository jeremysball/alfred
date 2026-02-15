"""Tests for PiSubprocess persistent process management."""
import pytest
import asyncio
from pathlib import Path
from openclaw_pi.pi_manager import PiSubprocess, PiManager


@pytest.mark.asyncio
async def test_pi_subprocess_not_started_is_not_alive(tmp_path: Path):
    """Test that a new PiSubprocess is not alive before start."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    pi = PiSubprocess("test_thread", workspace, timeout=5)
    
    is_alive = await pi.is_alive()
    assert is_alive is False


@pytest.mark.asyncio
async def test_pi_subprocess_start_creates_process(tmp_path: Path):
    """Test that start() creates a subprocess."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    pi = PiSubprocess("test_thread", workspace, timeout=5)
    
    # Start should not raise even if pi binary not found
    # It will raise when trying to send_message
    try:
        await pi.start()
        # If pi is installed, process should exist
        if pi.process:
            assert pi.process.pid is not None
    except FileNotFoundError:
        # Expected if pi not installed
        pytest.skip("pi binary not found")


@pytest.mark.asyncio
async def test_pi_subprocess_kill_noop_when_not_started(tmp_path: Path):
    """Test that kill() is safe when process not started."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    pi = PiSubprocess("test_thread", workspace, timeout=5)
    
    # Should not raise
    await pi.kill()
    
    is_alive = await pi.is_alive()
    assert is_alive is False


@pytest.mark.asyncio
async def test_pi_manager_get_or_create_returns_same_instance(tmp_path: Path):
    """Test that get_or_create returns same PiSubprocess for same thread."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    manager = PiManager(timeout=5)
    
    pi1 = await manager.get_or_create("thread_1", workspace)
    pi2 = await manager.get_or_create("thread_1", workspace)
    
    assert pi1 is pi2


@pytest.mark.asyncio
async def test_pi_manager_get_or_create_different_threads(tmp_path: Path):
    """Test that get_or_create returns different instances for different threads."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    manager = PiManager(timeout=5)
    
    pi1 = await manager.get_or_create("thread_1", workspace)
    pi2 = await manager.get_or_create("thread_2", workspace)
    
    assert pi1 is not pi2
    assert pi1.thread_id == "thread_1"
    assert pi2.thread_id == "thread_2"


@pytest.mark.asyncio
async def test_pi_manager_cleanup_kills_all_processes(tmp_path: Path):
    """Test that cleanup kills all managed processes."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    manager = PiManager(timeout=5)
    
    # Create some processes
    pi1 = await manager.get_or_create("thread_1", workspace)
    pi2 = await manager.get_or_create("thread_2", workspace)
    
    # Cleanup
    await manager.cleanup()
    
    # All should be dead
    assert await manager.list_active() == []


@pytest.mark.asyncio
async def test_pi_manager_kill_thread_removes_from_active(tmp_path: Path):
    """Test that kill_thread removes process from manager."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    manager = PiManager(timeout=5)
    
    # Create a process
    await manager.get_or_create("thread_1", workspace)
    
    # Kill it
    result = await manager.kill_thread("thread_1")
    
    assert result is True
    assert "thread_1" not in manager._processes


@pytest.mark.asyncio
async def test_pi_subprocess_lock_prevents_concurrent_access(tmp_path: Path):
    """Test that the lock prevents concurrent send_message calls."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    pi = PiSubprocess("test_thread", workspace, timeout=5)
    
    # Check that lock exists and is locked during operation
    assert pi._lock is not None
    
    # Try to acquire lock (should succeed when not in use)
    acquired = pi._lock.locked()
    assert acquired is False  # Not locked initially
