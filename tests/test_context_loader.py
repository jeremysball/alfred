"""Tests for context loading."""
import pytest
from pathlib import Path
from alfred.context_loader import ContextLoader


class TestContextLoader:
    """Test context file loading."""

    def test_loads_agents_md(self, tmp_path):
        """Should load AGENTS.md when it exists."""
        # Arrange
        loader = ContextLoader(tmp_path)
        (tmp_path / "AGENTS.md").write_text("Be concise.")
        
        # Act
        context = loader.load_all_context()
        
        # Assert
        assert "AGENT BEHAVIOR" in context
        assert "Be concise." in context

    def test_loads_soul_md(self, tmp_path):
        """Should load SOUL.md when it exists."""
        loader = ContextLoader(tmp_path)
        (tmp_path / "SOUL.md").write_text("You are helpful.")
        
        context = loader.load_all_context()
        
        assert "PERSONALITY" in context
        assert "You are helpful." in context

    def test_loads_user_md(self, tmp_path):
        """Should load USER.md when it exists."""
        loader = ContextLoader(tmp_path)
        (tmp_path / "USER.md").write_text("Name: Test User")
        
        context = loader.load_all_context()
        
        assert "USER PROFILE" in context
        assert "Name: Test User" in context

    def test_skips_missing_files(self, tmp_path):
        """Should skip files that don't exist."""
        loader = ContextLoader(tmp_path)
        (tmp_path / "AGENTS.md").write_text("Be concise.")
        # SOUL.md and USER.md don't exist
        
        context = loader.load_all_context()
        
        assert "AGENT BEHAVIOR" in context
        assert "PERSONALITY" not in context
        assert "USER PROFILE" not in context

    def test_caching(self, tmp_path):
        """Should cache file contents."""
        loader = ContextLoader(tmp_path)
        (tmp_path / "AGENTS.md").write_text("Original.")
        
        # Load twice
        context1 = loader.load_all_context()
        context2 = loader.load_all_context()
        
        # Should be same object (cached)
        assert context1 == context2

    def test_get_system_prompt(self, tmp_path):
        """Should return formatted system prompt."""
        loader = ContextLoader(tmp_path)
        (tmp_path / "AGENTS.md").write_text("Be concise.")
        
        prompt = loader.get_system_prompt()
        
        assert "AGENT BEHAVIOR" in prompt
        assert "Be concise." in prompt
        assert "INSTRUCTIONS:" in prompt
        assert "You are Alfred" in prompt

    def test_default_prompt_when_no_files(self, tmp_path):
        """Should return default prompt when no context files exist."""
        loader = ContextLoader(tmp_path)
        
        prompt = loader.get_system_prompt()
        
        assert "Alfred" in prompt
        assert "coding assistant" in prompt
