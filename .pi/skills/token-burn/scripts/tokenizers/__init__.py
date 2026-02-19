# Tokenizers for different models
# Uses tiktoken as base and applies model-specific adjustments

import json
import re
from typing import List, Tuple

class BaseTokenizer:
    """Base tokenizer with character-based approximation."""
    
    def __init__(self, name: str, chars_per_token: float = 4.0):
        self.name = name
        self.chars_per_token = chars_per_token
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if not text:
            return 0
        # Character-based approximation with model-specific ratio
        return int(len(text) / self.chars_per_token)
    
    def count_message_tokens(self, message: dict) -> int:
        """Count tokens in a message dict."""
        total = 0
        # Count content
        content = message.get('content', '')
        if content:
            total += self.count_tokens(content)
        
        # Count tool calls if present
        tool_calls = message.get('tool_calls', [])
        for tc in tool_calls:
            total += self.count_tokens(str(tc))
        
        # Add overhead per message (formatting, role, etc.)
        total += 4  # Base overhead per message
        
        return total


class GLM47Tokenizer(BaseTokenizer):
    """Tokenizer for Z.AI GLM-4.7 model."""
    
    def __init__(self):
        super().__init__("zai/glm-4.7", chars_per_token=3.8)
    
    def count_message_tokens(self, message: dict) -> int:
        """GLM-4.7 uses ~3.8 chars per token for English, ~2.5 for Chinese."""
        content = message.get('content', '')
        
        # Detect Chinese characters
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        english_chars = len(content) - chinese_chars
        
        # Chinese uses more tokens per character
        tokens = int(chinese_chars / 2.5) + int(english_chars / 3.8)
        
        # Add overhead
        tokens += 4
        
        # Tool calls
        tool_calls = message.get('tool_calls', [])
        for tc in tool_calls:
            tokens += self.count_tokens(str(tc))
        
        return tokens


class KimiK25Tokenizer(BaseTokenizer):
    """Tokenizer for Kimi K2.5 model."""
    
    def __init__(self):
        super().__init__("kimi-coding/k2p5", chars_per_token=4.2)
    
    def count_message_tokens(self, message: dict) -> int:
        """Kimi K2.5 uses ~4.2 chars per token for mixed content."""
        content = message.get('content', '')
        
        # Kimi has efficient CJK handling
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        english_chars = len(content) - chinese_chars
        
        tokens = int(chinese_chars / 3.0) + int(english_chars / 4.2)
        
        # Add overhead
        tokens += 4
        
        # Tool calls
        tool_calls = message.get('tool_calls', [])
        for tc in tool_calls:
            tokens += self.count_tokens(str(tc))
        
        return tokens


class GPTTokenizer(BaseTokenizer):
    """GPT/Claude style tokenizer for fallback."""
    
    def __init__(self):
        super().__init__("gpt-claude", chars_per_token=4.0)


def get_tokenizer(model_name: str) -> BaseTokenizer:
    """Get appropriate tokenizer for model."""
    model_lower = model_name.lower()
    
    if 'glm' in model_lower or 'zai' in model_lower:
        return GLM47Tokenizer()
    elif 'kimi' in model_lower or 'k2' in model_lower:
        return KimiK25Tokenizer()
    else:
        return GPTTokenizer()
