"""Tests for thread storage."""
import pytest
from pathlib import Path
from dispatcher.models import Thread
from dispatcher.storage import ThreadStorage


@pytest.mark.asyncio
async def test_save_and_load_thread(tmp_path: Path):
    """Test saving and loading a thread."""
    storage = ThreadStorage(tmp_path)
    thread = Thread(thread_id="test_123", chat_id=456)
    thread.add_message("user", "Hello")
    
    await storage.save(thread)
    loaded = await storage.load("test_123")
    
    assert loaded is not None
    assert loaded.thread_id == "test_123"
    assert loaded.chat_id == 456
    assert len(loaded.messages) == 1
    assert loaded.messages[0].content == "Hello"


@pytest.mark.asyncio
async def test_load_nonexistent_thread(tmp_path: Path):
    """Test loading a thread that doesn't exist."""
    storage = ThreadStorage(tmp_path)
    loaded = await storage.load("nonexistent")
    assert loaded is None


@pytest.mark.asyncio
async def test_list_threads(tmp_path: Path):
    """Test listing all threads."""
    storage = ThreadStorage(tmp_path)
    
    # Create some threads
    thread1 = Thread(thread_id="thread_1", chat_id=111)
    thread2 = Thread(thread_id="thread_2", chat_id=222)
    await storage.save(thread1)
    await storage.save(thread2)
    
    threads = await storage.list_threads()
    assert set(threads) == {"thread_1", "thread_2"}


@pytest.mark.asyncio
async def test_delete_thread(tmp_path: Path):
    """Test deleting a thread."""
    storage = ThreadStorage(tmp_path)
    thread = Thread(thread_id="to_delete", chat_id=999)
    await storage.save(thread)
    
    # Verify it exists
    loaded = await storage.load("to_delete")
    assert loaded is not None
    
    # Delete it
    deleted = await storage.delete("to_delete")
    assert deleted is True
    
    # Verify it's gone
    loaded = await storage.load("to_delete")
    assert loaded is None


@pytest.mark.asyncio
async def test_thread_add_message():
    """Test adding messages to a thread."""
    thread = Thread(thread_id="msg_test", chat_id=123)
    
    thread.add_message("user", "Hello")
    thread.add_message("assistant", "Hi there!")
    
    assert len(thread.messages) == 2
    assert thread.messages[0].role == "user"
    assert thread.messages[1].role == "assistant"
