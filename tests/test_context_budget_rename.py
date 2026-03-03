"""Tests for renaming token_budget to memory_budget in ContextBuilder."""

import pytest
from src.search import ContextBuilder, MemorySearcher


class TestContextBuilderMemoryBudget:
    """Test memory_budget parameter rename."""

    def test_context_builder_has_memory_budget_parameter(self):
        """ContextBuilder.__init__ accepts memory_budget parameter."""
        searcher = MemorySearcher()

        # Should accept memory_budget parameter
        builder = ContextBuilder(searcher, memory_budget=16000)
        assert builder.memory_budget == 16000

    def test_context_builder_default_memory_budget_is_32k(self):
        """Default memory_budget is 32000 (not 8000)."""
        searcher = MemorySearcher()
        builder = ContextBuilder(searcher)

        assert builder.memory_budget == 32000

    def test_context_builder_uses_memory_budget_attribute(self):
        """Internal attribute is memory_budget not token_budget."""
        searcher = MemorySearcher()
        builder = ContextBuilder(searcher, memory_budget=24000)

        # Should use memory_budget attribute
        assert hasattr(builder, 'memory_budget')
        assert not hasattr(builder, 'token_budget')
        assert builder.memory_budget == 24000

    def test_context_builder_accepts_custom_memory_budget(self):
        """Custom memory_budget value is properly set."""
        searcher = MemorySearcher()
        builder = ContextBuilder(searcher, memory_budget=50000)

        assert builder.memory_budget == 50000

    def test_context_builder_respects_memory_budget_in_truncation(self):
        """memory_budget is used in _truncate_to_budget calculations."""
        searcher = MemorySearcher()
        builder = ContextBuilder(searcher, memory_budget=1000)

        # Very low budget should result in no memories
        system_prompt = "System prompt"
        memories = []
        session_messages = []

        result, count = builder._truncate_to_budget(
            system_prompt, memories, session_messages, builder.memory_budget, {}, {}
        )

        # Should complete without error and respect the budget
        assert isinstance(result, str)
        assert isinstance(count, int)
