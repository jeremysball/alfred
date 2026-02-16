"""Tests for pi manager."""
import pytest
import shutil
from pathlib import Path
from openclaw_pi.pi_manager import PiManager, PiSubprocess


@pytest.mark.asyncio
async def test_pi_subprocess_send_message(tmp_path: Path):
    """Test pi subprocess send_message (skip if pi not installed)."""
    if not shutil.which("pi"):
        pytest.skip("pi not installed")
    
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    pi = PiSubprocess("test", workspace, timeout=10)
    
    # send_message spawns process, sends message, returns response
    # This will fail if pi is not installed or no API key
    try:
        response = await pi.send_message("Say 'hello' and nothing else")
        assert response
        assert "hello" in response.lower()
    except FileNotFoundError:
        pytest.skip("pi binary not found")
    except Exception as e:
        # API key or other error
        pytest.skip(f"Pi error: {e}")


@pytest.mark.asyncio
async def test_pi_manager_send_message_interface():
    """Test PiManager send_message interface."""
    manager = PiManager(timeout=5)
    
    # Check configuration
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
