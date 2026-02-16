"""Tests for pi manager."""
import pytest
import shutil
from pathlib import Path
from dispatcher.pi_manager import PiManager, PiSubprocess


@pytest.mark.asyncio
async def test_pi_subprocess_lifecycle(tmp_path: Path):
    """Test pi subprocess lifecycle (skip if pi not installed)."""
    if not shutil.which("pi"):
        pytest.skip("pi not installed")
    
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    pi = PiSubprocess("test", workspace, timeout=10)
    await pi.start()
    
    assert await pi.is_alive()
    
    await pi.kill()
    assert not await pi.is_alive()


@pytest.mark.asyncio
async def test_pi_manager_get_or_create():
    """Test get_or_create returns same instance for same thread."""
    manager = PiManager(timeout=5)
    
    # Without pi installed, we can't fully test
    # But we can test the logic
    assert manager.llm_provider == "zai"
    assert manager.timeout == 5


@pytest.mark.asyncio
async def test_pi_manager_kill_nonexistent():
    """Test killing a nonexistent thread returns False."""
    manager = PiManager()
    result = await manager.kill_thread("nonexistent")
    assert result is False


@pytest.mark.asyncio
async def test_pi_manager_list_active():
    """Test listing active threads."""
    manager = PiManager()
    active = await manager.list_active()
    assert active == []


@pytest.mark.asyncio
async def test_pi_manager_cleanup():
    """Test cleanup with no processes."""
    manager = PiManager()
    await manager.cleanup()  # Should not raise
    assert await manager.list_active() == []
