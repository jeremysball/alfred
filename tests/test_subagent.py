"""Tests for sub-agent spawning functionality."""
from pathlib import Path

import pytest

from alfred.dispatcher import Dispatcher
from alfred.models import Thread
from alfred.pi_manager import PiManager
from alfred.storage import ThreadStorage


@pytest.mark.asyncio
async def test_spawn_subagent_returns_subagent_id(tmp_path: Path):
    """Test that spawn_subagent returns a subagent ID."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()

    # Create parent thread first
    storage = ThreadStorage(threads)
    parent = Thread(thread_id="parent_1", chat_id=123)
    await storage.save(parent)

    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)

    response = await dispatcher.spawn_subagent(
        chat_id=123,
        thread_id="parent_1",
        task="Test task"
    )

    assert "Sub-agent" in response
    assert "started" in response

    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_spawn_subagent_fails_without_parent(tmp_path: Path):
    """Test that spawn_subagent fails if parent thread doesn't exist."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()

    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)

    response = await dispatcher.spawn_subagent(
        chat_id=123,
        thread_id="nonexistent_parent",
        task="Test task"
    )

    assert "not found" in response

    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_spawn_subagent_creates_subagent_workspace(tmp_path: Path):
    """Test that spawn_subagent creates workspace for subagent."""
    import asyncio

    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()

    # Create parent thread
    storage = ThreadStorage(threads)
    parent = Thread(thread_id="parent_2", chat_id=123)
    await storage.save(parent)

    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)

    # Spawn subagent
    await dispatcher.spawn_subagent(
        chat_id=123,
        thread_id="parent_2",
        task="Test task"
    )

    # Wait for background task to create workspace
    await asyncio.sleep(0.1)

    # Check that subagents directory was created
    subagents_dir = workspace / "subagents"
    assert subagents_dir.exists()

    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_spawn_subagent_updates_parent_thread(tmp_path: Path):
    """Test that spawn_subagent marks parent with active subagent."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()

    # Create parent thread
    storage = ThreadStorage(threads)
    parent = Thread(thread_id="parent_3", chat_id=123)
    await storage.save(parent)

    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)

    # Spawn subagent
    await dispatcher.spawn_subagent(
        chat_id=123,
        thread_id="parent_3",
        task="Test task"
    )

    # Check that parent was updated
    parent = await storage.load("parent_3")
    assert parent.active_subagent is not None
    assert "parent_3_sub_" in parent.active_subagent

    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_subagent_thread_id_format(tmp_path: Path):
    """Test that subagent thread ID has correct format."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()

    # Create parent thread
    storage = ThreadStorage(threads)
    parent = Thread(thread_id="parent_4", chat_id=123)
    await storage.save(parent)

    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)

    response = await dispatcher.spawn_subagent(
        chat_id=123,
        thread_id="parent_4",
        task="Test task"
    )

    # Extract subagent ID from response
    # Format: "🔄 Sub-agent {subagent_id} started"
    subagent_id = response.replace("🔄 Sub-agent ", "").replace(" started", "")

    # Verify format: parent_id_sub_timestamp
    # parent_id can contain underscores (e.g., "parent_4"), so check it ends with "_sub_<timestamp>"
    assert "_sub_" in subagent_id
    assert subagent_id.startswith("parent_4_sub_")

    await dispatcher.shutdown()
