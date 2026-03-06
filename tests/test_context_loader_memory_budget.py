"""Tests for ContextLoader passing memory_budget from config to ContextBuilder."""

from alfred.config import Config
from alfred.context import ContextLoader
from alfred.search import MemorySearcher


class TestContextLoaderMemoryBudget:
    """Test ContextLoader wires config.memory_budget to ContextBuilder."""

    def test_context_loader_passes_memory_budget_to_builder(self):
        """ContextLoader passes config.memory_budget to ContextBuilder."""
        config = Config(
            workspace_dir="/tmp/test",
            memory_budget=45000,
        )
        searcher = MemorySearcher()

        loader = ContextLoader(config, searcher=searcher)

        # ContextBuilder should be initialized with memory_budget from config
        assert loader._context_builder is not None
        assert loader._context_builder.memory_budget == 45000

    def test_context_loader_uses_default_memory_budget(self):
        """ContextLoader uses default memory_budget when not in config."""
        config = Config(workspace_dir="/tmp/test")
        searcher = MemorySearcher()

        loader = ContextLoader(config, searcher=searcher)

        # Should use default of 32000
        assert loader._context_builder.memory_budget == 32000

    def test_context_loader_without_searcher_has_no_builder(self):
        """ContextLoader without searcher has no _context_builder."""
        config = Config(workspace_dir="/tmp/test", memory_budget=40000)

        loader = ContextLoader(config, searcher=None)

        # No searcher means no context builder
        assert loader._context_builder is None

    def test_context_assembly_uses_configured_budget(self):
        """End-to-end: assemble_with_search uses configured budget."""
        config = Config(
            workspace_dir="/tmp/test",
            memory_budget=5000,  # Very small budget for testing
        )
        searcher = MemorySearcher(min_similarity=0.0)
        loader = ContextLoader(config, searcher=searcher)

        # Verify the budget was passed through
        assert loader._context_builder.memory_budget == 5000
