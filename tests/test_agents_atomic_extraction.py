"""Tests for AGENTS.md atomic unit extraction (PRD #102 M2)."""

from pathlib import Path

import pytest

from alfred.context import ContextLoader
from alfred.templates import TemplateManager


class TestAgentsAtomicExtraction:
    """Test that AGENTS.md atomic sections are properly extracted to prompts/agents/."""

    def test_all_atomic_files_exist(self, tmp_path: Path) -> None:
        """All atomic prompt files should exist in templates/prompts/agents/."""
        manager = TemplateManager(tmp_path)
        template_dir = manager.template_dir
        prompts_dir = template_dir / "prompts" / "agents"

        expected_files = [
            "memory-system.md",
            "beta-notice.md",
            "pre-flight.md",
            "design-questions.md",
            "tdd.md",
            "secrets.md",
            "running-project.md",
            "tui-colors.md",
            "rules-index.md",
        ]

        for filename in expected_files:
            file_path = prompts_dir / filename
            assert file_path.exists(), f"Missing atomic file: {filename}"

    def test_atomic_files_have_markdown_structure(self, tmp_path: Path) -> None:
        """Each atomic file should be valid markdown with proper structure."""
        manager = TemplateManager(tmp_path)
        template_dir = manager.template_dir
        prompts_dir = template_dir / "prompts" / "agents"

        atomic_files = [
            "beta-notice.md",
            "pre-flight.md",
            "design-questions.md",
            "tdd.md",
            "secrets.md",
            "running-project.md",
            "tui-colors.md",
            "rules-index.md",
        ]

        for filename in atomic_files:
            content = (prompts_dir / filename).read_text()

            # Should have a markdown heading
            assert content.startswith("## "), f"{filename} should start with ## heading"

            # Should have substantial content (not just a heading)
            assert len(content) > 100, f"{filename} should have substantial content"

            # Should not have unresolved placeholders (except for colors)
            assert "{{prompts/agents/" not in content, f"{filename} should not reference other atomic files"

    def test_agents_md_uses_placeholders(self, tmp_path: Path) -> None:
        """AGENTS.md should use placeholders for all atomic sections."""
        manager = TemplateManager(tmp_path)
        content = manager.load_template("AGENTS.md")

        assert content is not None
        # Should only have header and placeholders
        assert "# Agent Behavior Rules" in content

        # Should have placeholders for all sections
        expected_placeholders = [
            "{{prompts/agents/memory-system.md}}",
            "{{prompts/agents/beta-notice.md}}",
            "{{prompts/agents/pre-flight.md}}",
            "{{prompts/agents/design-questions.md}}",
            "{{prompts/agents/tdd.md}}",
            "{{prompts/agents/secrets.md}}",
            "{{prompts/agents/running-project.md}}",
            "{{prompts/agents/tui-colors.md}}",
            "{{prompts/agents/rules-index.md}}",
        ]

        for placeholder in expected_placeholders:
            assert placeholder in content, f"Missing placeholder: {placeholder}"

    def test_agents_md_minimal_inline_content(self, tmp_path: Path) -> None:
        """AGENTS.md should have minimal inline content (just header)."""
        manager = TemplateManager(tmp_path)
        content = manager.load_template("AGENTS.md")

        # Should not have section content inline anymore
        assert "## Beta Product Notice" not in content
        assert "## Pre-Flight Check" not in content
        assert "## Test-Driven Development" not in content
        assert "## Secrets and Authentication" not in content

    @pytest.mark.asyncio
    async def test_placeholders_resolve_correctly(self, tmp_path: Path) -> None:
        """All placeholders should resolve when loading through ContextLoader."""
        from alfred.config import Config

        # Create a minimal workspace
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        manager = TemplateManager(tmp_path)
        template_dir = manager.template_dir

        # Create minimal context files
        (workspace_dir / "SYSTEM.md").write_text("# System\nTest system")
        (workspace_dir / "SOUL.md").write_text("# Soul\nTest soul")
        (workspace_dir / "USER.md").write_text("# User\nTest user")

        # Create AGENTS.md with placeholders
        agents_content = (template_dir / "AGENTS.md").read_text()
        (workspace_dir / "AGENTS.md").write_text(agents_content)

        # Create prompts directory structure
        prompts_dir = workspace_dir / "prompts" / "agents"
        prompts_dir.mkdir(parents=True)

        # Copy all atomic files from templates
        template_prompts = template_dir / "prompts" / "agents"
        if template_prompts.exists():
            for f in template_prompts.iterdir():
                if f.is_file():
                    (prompts_dir / f.name).write_text(f.read_text())

        # Load through ContextLoader
        config = Config(workspace_dir=workspace_dir)
        loader = ContextLoader(config)

        # Load AGENTS.md
        agents_path = workspace_dir / "AGENTS.md"
        context_file = await loader.load_file("agents", agents_path)

        # All placeholders should be resolved (no {{prompts/agents/...}} left)
        assert "{{prompts/agents/" not in context_file.content

        # Should have resolved content from atomic files
        assert "## Beta Product Notice" in context_file.content
        assert "## Pre-Flight Check" in context_file.content
        assert "## Testing Guidance" in context_file.content
        assert "## Secrets and Authentication" in context_file.content
        assert "## Rule Index" in context_file.content

    def test_atomic_files_are_self_contained(self, tmp_path: Path) -> None:
        """Each atomic file should make sense standalone without external references."""
        manager = TemplateManager(tmp_path)
        template_dir = manager.template_dir
        prompts_dir = template_dir / "prompts" / "agents"

        atomic_files = [
            "beta-notice.md",
            "pre-flight.md",
            "design-questions.md",
            "tdd.md",
            "secrets.md",
            "running-project.md",
            "tui-colors.md",
            "rules-index.md",
        ]

        for filename in atomic_files:
            content = (prompts_dir / filename).read_text()

            # Should have a clear heading
            assert content.startswith("## "), f"{filename} should start with ## heading"

            # Should not reference other atomic files
            assert "{{prompts/agents/" not in content, f"{filename} should not reference other atomic files"

            # Should have substantial content (not just a heading)
            assert len(content) > 100, f"{filename} should have substantial content"

    def test_rules_index_has_core_rules(self, tmp_path: Path) -> None:
        """Rules index should contain the core generic rules."""
        manager = TemplateManager(tmp_path)
        template_dir = manager.template_dir
        rules_file = template_dir / "prompts" / "agents" / "rules-index.md"

        content = rules_file.read_text()

        # Should have Rule Index heading
        assert "## Rule Index" in content

        # Should have the key generic rules we expect runtime to use
        assert "### 1. Capability First" in content
        assert "### 2. Use `bash` as the Fallback" in content
        assert "### 4. Search Before Asking" in content
        assert "### 5. Ask Before External or Irreversible Actions" in content
        assert "### 6. Verify Meaningful Code Changes" in content

    def test_memory_system_md_exists_and_is_valid(self, tmp_path: Path) -> None:
        """Memory system guidance should exist and be valid."""
        manager = TemplateManager(tmp_path)
        content = manager.load_template("prompts/agents/memory-system.md")

        assert content is not None
        assert content.startswith("## ")
        # Should have tool references
        assert "remember(" in content or "search_memories" in content
