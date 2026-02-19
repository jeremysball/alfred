#!/usr/bin/env python3
"""
Tests for token-burn skill.
"""

import json
import tempfile
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from tokenizers import get_tokenizer, GLM47Tokenizer, KimiK25Tokenizer


def test_tokenizers():
    """Test tokenizer implementations."""
    print("Testing tokenizers...")
    
    # Test GLM47Tokenizer
    glm = GLM47Tokenizer()
    assert glm.name == "zai/glm-4.7"
    
    # Test English text
    en_text = "Hello world, this is a test message."
    en_tokens = glm.count_tokens(en_text)
    assert en_tokens > 0
    print(f"  GLM English: '{en_text[:20]}...' = {en_tokens} tokens")
    
    # Test Chinese text
    cn_text = "你好世界，这是一个测试消息。"
    cn_tokens = glm.count_tokens(cn_text)
    assert cn_tokens > 0
    print(f"  GLM Chinese: '{cn_text[:10]}...' = {cn_tokens} tokens")
    
    # Test KimiK25Tokenizer
    kimi = KimiK25Tokenizer()
    assert kimi.name == "kimi-coding/k2p5"
    
    tokens = kimi.count_tokens(en_text)
    assert tokens > 0
    print(f"  Kimi English: '{en_text[:20]}...' = {tokens} tokens")
    
    print("  ✓ Tokenizers work")


def test_get_tokenizer():
    """Test tokenizer selection."""
    print("\nTesting tokenizer selection...")
    
    glm = get_tokenizer("zai/glm-4.7")
    assert isinstance(glm, GLM47Tokenizer)
    print("  ✓ GLM-4.7 detected")
    
    kimi = get_tokenizer("kimi-coding/k2p5")
    assert isinstance(kimi, KimiK25Tokenizer)
    print("  ✓ Kimi K2.5 detected")
    
    default = get_tokenizer("unknown-model")
    assert default.name == "gpt-claude"
    print("  ✓ Default fallback works")


def test_jsonl_parsing():
    """Test JSONL file parsing."""
    print("\nTesting JSONL parsing...")
    
    # Create test JSONL file
    test_data = [
        {"type": "session", "version": 3, "id": "test-session"},
        {
            "type": "message",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Hello"}],
                "provider": "zai",
                "model": "glm-4.7",
                "usage": {"input": 100, "output": 50, "totalTokens": 150}
            }
        },
        {
            "type": "message", 
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "Test message"}]
            }
        },
        {
            "type": "message",
            "message": {
                "role": "assistant",
                "provider": "kimi",
                "model": "k2p5",
                "usage": {"input": 200, "output": 100, "totalTokens": 300}
            }
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        for item in test_data:
            f.write(json.dumps(item) + '\n')
        temp_path = f.name
    
    try:
        # Import and test processing
        from token_burn import process_jsonl_file
        
        result = process_jsonl_file(temp_path)
        
        assert result['lines_processed'] == 4
        assert result['messages_processed'] == 2
        assert result['total_tokens'] == 450
        assert result['total_input'] == 300
        assert result['total_output'] == 150
        
        print(f"  Lines: {result['lines_processed']}")
        print(f"  Messages: {result['messages_processed']}")
        print(f"  Total tokens: {result['total_tokens']}")
        print("  ✓ JSONL parsing works")
        
    finally:
        os.unlink(temp_path)


def test_streaming():
    """Test buffered streaming with large file."""
    print("\nTesting buffered streaming...")
    
    # Create a larger test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        for i in range(1000):
            item = {
                "type": "message",
                "message": {
                    "role": "assistant" if i % 2 == 0 else "user",
                    "content": [{"type": "text", "text": f"Message {i}"}],
                    "usage": {"input": 10, "output": 5, "totalTokens": 15}
                }
            }
            f.write(json.dumps(item) + '\n')
        temp_path = f.name
    
    try:
        from token_burn import process_jsonl_file
        
        # Process with small buffer
        result = process_jsonl_file(temp_path, buffer_size=1024)
        
        assert result['lines_processed'] == 1000
        assert result['total_tokens'] == 15000
        
        print(f"  Processed {result['lines_processed']} lines")
        print(f"  Total tokens: {result['total_tokens']}")
        print("  ✓ Streaming with small buffer works")
        
    finally:
        os.unlink(temp_path)


def test_model_detection():
    """Test model detection from various formats."""
    print("\nTesting model detection...")
    
    from token_burn import extract_model_info, get_model_name
    
    # Test message with model
    msg_data = {
        "message": {
            "provider": "zai",
            "model": "glm-4.7",
            "content": [{"text": "test"}]
        }
    }
    provider, model = extract_model_info(msg_data)
    assert provider == "zai"
    assert model == "glm-4.7"
    print("  ✓ Message model detection")
    
    # Test model-snapshot
    snapshot = {
        "type": "custom",
        "customType": "model-snapshot",
        "data": {
            "provider": "kimi",
            "modelId": "k2p5"
        }
    }
    provider, model = extract_model_info(snapshot)
    assert model == "kimi/k2p5"
    print("  ✓ Snapshot model detection")
    
    # Test get_model_name
    assert get_model_name("zai", "glm-4.7") == "zai/glm-4.7"
    assert get_model_name(None, "model-name") == "model-name"
    assert get_model_name("openclaw", None) == "openclaw"
    print("  ✓ Model name formatting")


def run_all_tests():
    """Run all tests."""
    print("="*60)
    print("TOKEN-BURN TEST SUITE")
    print("="*60)
    
    tests = [
        test_tokenizers,
        test_get_tokenizer,
        test_model_detection,
        test_jsonl_parsing,
        test_streaming,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
