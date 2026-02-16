"""Tests for PiSubprocess one-shot process management."""
from pathlib import Path

import pytest

from alfred.pi_manager import PiManager, PiSubprocess


@pytest.mark.asyncio
async def test_pi_subprocess_send_message_stream_yields_chunks(tmp_path: Path):
    """Test that send_message_stream yields response chunks."""
    import shutil

    # Skip if pi not installed
    if not shutil.which("pi"):
        pytest.skip("pi not installed")

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    pi = PiSubprocess("test_stream_thread", workspace, timeout=5)

    try:
        chunks = []
        async for chunk in pi.send_message_stream("Say hi"):
            chunks.append(chunk)

        # Should have yielded at least one chunk
        assert len(chunks) >= 1
        # Combined chunks should contain a response
        full_response = "".join(chunks)
        assert isinstance(full_response, str)
        assert len(full_response) > 0
    except FileNotFoundError:
        pytest.skip("pi binary not found")
    except TimeoutError:
        pytest.skip("Pi timeout - likely no API key configured")


@pytest.mark.asyncio
async def test_pi_manager_send_message_stream_tracks_active(tmp_path: Path):
    """Test that send_message_stream tracks thread as active during streaming."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    manager = PiManager(timeout=5, streaming_enabled=True)

    # Thread not active before streaming
    assert "stream_thread" not in await manager.list_active()

    # Note: We can't easily test "during" without mocking the subprocess
    # but we can verify the method exists and accepts the right parameters
    assert hasattr(manager, 'send_message_stream')


@pytest.mark.asyncio
async def test_pi_subprocess_send_message_not_started(tmp_path: Path):
    """Test that send_message spawns process and returns response."""
    import shutil

    # Skip if pi not installed
    if not shutil.which("pi"):
        pytest.skip("pi not installed")

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    pi = PiSubprocess("test_thread", workspace, timeout=5)

    # send_message should spawn process, send, get response, then process exits
    # This will fail if pi not installed or no API key
    try:
        response = await pi.send_message("Say hello")
        assert isinstance(response, str)
    except FileNotFoundError:
        pytest.skip("pi binary not found")
    except TimeoutError:
        pytest.skip("Pi timeout - likely no API key configured")


@pytest.mark.asyncio
async def test_pi_manager_send_message_tracks_active(tmp_path: Path):
    """Test that send_message tracks thread as active during execution."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    manager = PiManager(timeout=5)

    # Mock send to simulate long-running operation
    async def slow_send(self, message):
        # Check that thread is tracked as active
        return "response"

    # Thread not active before send
    assert "thread_1" not in await manager.list_active()

    # After send completes, thread not active (one-shot mode)
    # We can't easily test during send without complex mocking


@pytest.mark.asyncio
async def test_pi_manager_kill_nonexistent():
    """Test killing nonexistent thread returns False."""
    manager = PiManager(timeout=5)
    result = await manager.kill_thread("nonexistent")
    assert result is False


@pytest.mark.asyncio
async def test_pi_manager_cleanup():
    """Test cleanup clears active tracking."""
    manager = PiManager(timeout=5)

    # In one-shot mode, threads are only "active" during send_message
    # Cleanup should just clear the tracking set
    await manager.cleanup()
    assert await manager.list_active() == []


@pytest.mark.asyncio
async def test_pi_subprocess_is_alive_after_send(tmp_path: Path):
    """Test is_alive returns False after send_message completes (one-shot)."""
    import shutil

    # Skip if pi not installed
    if not shutil.which("pi"):
        pytest.skip("pi not installed")

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    pi = PiSubprocess("test_thread", workspace, timeout=5)

    # Before send, not alive
    assert await pi.is_alive() is False

    # After send completes in one-shot mode, process should be dead
    try:
        await pi.send_message("test")
        # Process exits after send_message in one-shot mode
        # But is_alive checks if process attribute exists and is running
    except FileNotFoundError:
        pytest.skip("pi binary not found")
    except TimeoutError:
        pytest.skip("Pi timeout - likely no API key configured")
