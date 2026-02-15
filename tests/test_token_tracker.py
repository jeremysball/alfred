"""Tests for token tracking functionality."""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from alfred.token_tracker import TokenTracker, TokenUsage


@pytest.fixture
def token_tracker(tmp_path):
    """Create a token tracker with temp directory."""
    return TokenTracker(tmp_path / "logs")


@pytest.mark.asyncio
async def test_token_tracker_logs_usage(token_tracker):
    """Test that token usage is logged correctly."""
    usage = token_tracker.log_usage(
        thread_id="test_thread",
        provider="zai",
        model="glm-4-flash",
        input_text="Hello, how are you?",
        output_text="I'm doing well, thank you!"
    )
    
    assert isinstance(usage, TokenUsage)
    assert usage.thread_id == "test_thread"
    assert usage.provider == "zai"
    assert usage.model == "glm-4-flash"
    assert usage.input_tokens > 0
    assert usage.output_tokens > 0
    assert usage.total_tokens == usage.input_tokens + usage.output_tokens
    assert usage.cost_usd >= 0


@pytest.mark.asyncio
async def test_token_tracker_estimates_tokens(token_tracker):
    """Test token estimation from text length."""
    # 1 token ≈ 4 characters
    short_text = "Hi"  # ~0.5 tokens, rounds to 0
    long_text = "Hello world this is a longer text"  # ~8 tokens
    
    short_tokens = token_tracker._estimate_tokens(short_text)
    long_tokens = token_tracker._estimate_tokens(long_text)
    
    assert short_tokens == 0  # len("Hi") // 4 = 0
    assert long_tokens == 8   # len("Hello...") // 4 = 8


@pytest.mark.asyncio
async def test_token_tracker_calculates_cost(token_tracker):
    """Test cost calculation for different providers."""
    # ZAI is free tier
    zai_cost = token_tracker._calculate_cost("zai", 1000, 500)
    assert zai_cost == 0.0
    
    # OpenAI GPT-4 has costs
    openai_cost = token_tracker._calculate_cost("openai/gpt-4", 1000, 500)
    expected_cost = (1000/1000 * 0.03) + (500/1000 * 0.06)  # $0.06
    assert openai_cost == round(expected_cost, 6)


@pytest.mark.asyncio
async def test_token_tracker_daily_stats_empty(token_tracker):
    """Test daily stats when no logs exist."""
    stats = token_tracker.get_daily_stats()
    
    assert stats["requests"] == 0
    assert stats["total_tokens"] == 0
    assert stats["cost_usd"] == 0.0
    assert stats["by_thread"] == {}
    assert stats["by_provider"] == {}


@pytest.mark.asyncio
async def test_token_tracker_daily_stats_with_data(token_tracker):
    """Test daily stats with logged data."""
    # Log some usage
    token_tracker.log_usage("thread1", "zai", "model1", "input", "output")
    token_tracker.log_usage("thread2", "openai/gpt-4", "model2", "input text here", "output text here")
    
    stats = token_tracker.get_daily_stats()
    
    assert stats["requests"] == 2
    assert stats["total_tokens"] > 0
    assert "zai" in stats["by_provider"]
    assert "openai/gpt-4" in stats["by_provider"]
    assert "thread1" in stats["by_thread"]
    assert "thread2" in stats["by_thread"]


@pytest.mark.asyncio
async def test_token_tracker_logs_for_thread(token_tracker):
    """Test retrieving logs for specific thread."""
    # Log usage for different threads
    token_tracker.log_usage("thread1", "zai", "model", "input1", "output1")
    token_tracker.log_usage("thread2", "zai", "model", "input2", "output2")
    token_tracker.log_usage("thread1", "zai", "model", "input3", "output3")
    
    # Get logs for thread1
    thread1_logs = token_tracker.get_logs_for_thread("thread1", days=1)
    
    assert len(thread1_logs) == 2
    assert all(log.thread_id == "thread1" for log in thread1_logs)


@pytest.mark.asyncio
async def test_token_tracker_log_file_created(token_tracker):
    """Test that log file is created when logging usage."""
    token_tracker.log_usage("thread1", "zai", "model", "input", "output")
    
    # Check that log file exists
    assert token_tracker.daily_log.exists()
    
    # Check content is valid JSON
    content = token_tracker.daily_log.read_text()
    lines = content.strip().split('\n')
    assert len(lines) == 1
    
    # Verify it's valid JSON
    import json
    data = json.loads(lines[0])
    assert data["thread_id"] == "thread1"
    assert data["provider"] == "zai"
