"""Tests for token tracking functionality."""
from datetime import datetime
from pathlib import Path

import pytest

from alfred.token_tracker import TokenTracker, TokenUsage


@pytest.fixture
def token_tracker(tmp_path):
    """Create a token tracker with temp directory."""
    return TokenTracker(tmp_path / "logs")


def test_token_tracker_logs_usage(token_tracker):
    """Test that token usage is logged correctly."""
    usage = TokenUsage(
        timestamp=datetime.now().isoformat(),
        thread_id="test_thread",
        provider="zai",
        model="glm-4-flash",
        input_tokens=10,
        output_tokens=20,
        cache_read=0,
        cache_write=0,
        total_tokens=30
    )

    token_tracker.log_usage(usage)

    stats = token_tracker.get_session_stats()
    assert stats["requests"] == 1
    assert stats["total_tokens"] == 30
    assert stats["input_tokens"] == 10
    assert stats["output_tokens"] == 20
    assert stats["last_model"] == "glm-4-flash"
    assert stats["last_provider"] == "zai"


def test_token_tracker_daily_stats_empty(token_tracker):
    """Test daily stats when no logs exist."""
    stats = token_tracker.get_daily_stats()

    assert stats["requests"] == 0
    assert stats["total_tokens"] == 0
    assert stats["input_tokens"] == 0
    assert stats["output_tokens"] == 0
    assert stats["by_thread"] == {}
    assert stats["by_provider"] == {}


def test_token_tracker_daily_stats_with_data(token_tracker):
    """Test daily stats with logged data."""
    usage1 = TokenUsage(
        timestamp=datetime.now().isoformat(),
        thread_id="thread1",
        provider="zai",
        model="model1",
        input_tokens=10,
        output_tokens=20,
        cache_read=0,
        cache_write=0,
        total_tokens=30
    )
    usage2 = TokenUsage(
        timestamp=datetime.now().isoformat(),
        thread_id="thread2",
        provider="openai",
        model="gpt-4",
        input_tokens=100,
        output_tokens=50,
        cache_read=0,
        cache_write=0,
        total_tokens=150
    )

    token_tracker.log_usage(usage1)
    token_tracker.log_usage(usage2)

    stats = token_tracker.get_daily_stats()

    assert stats["requests"] == 2
    assert stats["total_tokens"] == 180
    assert "zai" in stats["by_provider"]
    assert "openai" in stats["by_provider"]
    assert "thread1" in stats["by_thread"]
    assert "thread2" in stats["by_thread"]


def test_token_tracker_logs_for_thread(token_tracker):
    """Test retrieving logs for specific thread."""
    usages = [
        TokenUsage(
            timestamp=datetime.now().isoformat(),
            thread_id="thread1",
            provider="zai",
            model="model",
            input_tokens=10,
            output_tokens=20,
            cache_read=0,
            cache_write=0,
            total_tokens=30
        ),
        TokenUsage(
            timestamp=datetime.now().isoformat(),
            thread_id="thread2",
            provider="zai",
            model="model",
            input_tokens=15,
            output_tokens=25,
            cache_read=0,
            cache_write=0,
            total_tokens=40
        ),
        TokenUsage(
            timestamp=datetime.now().isoformat(),
            thread_id="thread1",
            provider="zai",
            model="model",
            input_tokens=5,
            output_tokens=10,
            cache_read=0,
            cache_write=0,
            total_tokens=15
        ),
    ]

    for usage in usages:
        token_tracker.log_usage(usage)

    thread1_logs = token_tracker.get_logs_for_thread("thread1", days=1)

    assert len(thread1_logs) == 2
    assert all(log.thread_id == "thread1" for log in thread1_logs)


def test_token_tracker_log_file_created(token_tracker):
    """Test that log file is created when logging usage."""
    usage = TokenUsage(
        timestamp=datetime.now().isoformat(),
        thread_id="thread1",
        provider="zai",
        model="model",
        input_tokens=10,
        output_tokens=20,
        cache_read=0,
        cache_write=0,
        total_tokens=30
    )

    token_tracker.log_usage(usage)

    assert token_tracker.daily_log.exists()

    content = token_tracker.daily_log.read_text()
    lines = content.strip().split('\n')
    assert len(lines) == 1

    import json
    data = json.loads(lines[0])
    assert data["thread_id"] == "thread1"
    assert data["provider"] == "zai"


def test_token_tracker_parse_session_file(token_tracker, tmp_path):
    """Test parsing token usage from Pi session file."""
    session_file = tmp_path / "test_thread.json"
    session_content = [
        {
            "type": "message",
            "timestamp": "2024-01-01T12:00:00",
            "message": {
                "role": "assistant",
                "provider": "zai",
                "model": "glm-4-flash",
                "usage": {
                    "input": 100,
                    "output": 50,
                    "cacheRead": 10,
                    "cacheWrite": 5,
                    "totalTokens": 155
                }
            }
        }
    ]

    import json
    with open(session_file, 'w') as f:
        for entry in session_content:
            f.write(json.dumps(entry) + '\n')

    usages = token_tracker.parse_session_file(session_file)

    assert len(usages) == 1
    assert usages[0].thread_id == "test_thread"
    assert usages[0].provider == "zai"
    assert usages[0].model == "glm-4-flash"
    assert usages[0].input_tokens == 100
    assert usages[0].output_tokens == 50
    assert usages[0].cache_read == 10
    assert usages[0].total_tokens == 155


def test_token_tracker_sync_from_session(token_tracker, tmp_path):
    """Test syncing token usage from session file."""
    session_file = tmp_path / "test_thread.json"
    session_content = [
        {
            "type": "message",
            "timestamp": "2024-01-01T12:00:00",
            "message": {
                "role": "assistant",
                "provider": "zai",
                "model": "glm-4-flash",
                "usage": {
                    "input": 100,
                    "output": 50,
                    "cacheRead": 0,
                    "cacheWrite": 0,
                    "totalTokens": 150
                }
            }
        }
    ]

    import json
    with open(session_file, 'w') as f:
        for entry in session_content:
            f.write(json.dumps(entry) + '\n')

    count = token_tracker.sync_from_session(session_file)

    assert count == 1
    stats = token_tracker.get_session_stats()
    assert stats["requests"] == 1
    assert stats["total_tokens"] == 150
