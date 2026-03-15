"""Tests for unified placeholder system."""

import logging
from pathlib import Path

import pytest

from alfred.placeholders import (
    ColorResolver,
    FileIncludeResolver,
    ResolutionContext,
    resolve_all,
    resolve_colors,
    resolve_file_includes,
    resolve_placeholders,
)


# Fixtures
@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace with test files."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create test files
    (workspace / "simple.md").write_text("# Simple\nNo placeholders")
    (workspace / "with_include.md").write_text("# Main\n{{included.md}}\nDone")
    (workspace / "included.md").write_text("## Included Content")
    (workspace / "nested_a.md").write_text("A {{nested_b.md}}")
    (workspace / "nested_b.md").write_text("B {{nested_c.md}}")
    (workspace / "nested_c.md").write_text("C")

    # Circular reference files
    (workspace / "circular_a.md").write_text("A {{circular_b.md}}")
    (workspace / "circular_b.md").write_text("B {{circular_a.md}}")

    # Missing file reference
    (workspace / "missing.md").write_text("{{nonexistent.md}}")

    return workspace


# Tests for ResolutionContext
class TestResolutionContext:
    """Test ResolutionContext state management."""

    def test_initial_state(self, temp_workspace):
        """Context starts with empty loaded set and depth 0."""
        ctx = ResolutionContext(base_dir=temp_workspace)

        assert ctx.base_dir == temp_workspace
        assert ctx.max_depth == 5
        assert ctx._depth == 0
        assert len(ctx._loaded) == 0

    def test_with_loaded_adds_path(self, temp_workspace):
        """with_loaded creates new context with path added."""
        ctx = ResolutionContext(base_dir=temp_workspace)
        path = Path("test.md")

        new_ctx = ctx.with_loaded(path)

        assert ctx._loaded == set()  # Original unchanged
        assert path in new_ctx._loaded  # New has path
        assert new_ctx.base_dir == temp_workspace

    def test_with_incremented_depth(self, temp_workspace):
        """with_incremented_depth increases depth by 1."""
        ctx = ResolutionContext(base_dir=temp_workspace)

        ctx1 = ctx.with_incremented_depth()
        ctx2 = ctx1.with_incremented_depth()

        assert ctx._depth == 0
        assert ctx1._depth == 1
        assert ctx2._depth == 2

    def test_is_circular_detects_cycle(self, temp_workspace):
        """is_circular returns True for already-loaded paths."""
        ctx = ResolutionContext(base_dir=temp_workspace)
        path = Path("test.md")

        assert ctx.is_circular(path) is False

        ctx_with_loaded = ctx.with_loaded(path)
        assert ctx_with_loaded.is_circular(path) is True

    def test_is_depth_exceeded(self, temp_workspace):
        """is_depth_exceeded returns True when depth > max_depth."""
        ctx = ResolutionContext(base_dir=temp_workspace, max_depth=2)

        assert ctx.is_depth_exceeded() is False  # depth 0

        ctx1 = ctx.with_incremented_depth()
        assert ctx1.is_depth_exceeded() is False  # depth 1

        ctx2 = ctx1.with_incremented_depth()
        assert ctx2.is_depth_exceeded() is False  # depth 2

        ctx3 = ctx2.with_incremented_depth()
        assert ctx3.is_depth_exceeded() is True  # depth 3 > max_depth 2


# Tests for FileIncludeResolver
class TestFileIncludeResolver:
    """Test {{path}} file include resolution."""

    def test_load_simple_file(self, temp_workspace):
        """File without placeholders loads normally."""
        resolver = FileIncludeResolver()
        ctx = ResolutionContext(base_dir=temp_workspace)

        content = "# Simple\nNo placeholders"
        result = resolver.pattern.sub(lambda m: resolver.resolve(m, ctx), content)

        assert result == content

    def test_resolve_file_include(self, temp_workspace):
        """{{path}} gets replaced with file content."""
        resolver = FileIncludeResolver()
        ctx = ResolutionContext(base_dir=temp_workspace)

        text = "{{included.md}}"
        result = resolver.pattern.sub(lambda m: resolver.resolve(m, ctx), text)

        assert "## Included Content" in result
        assert "<!-- included: included.md -->" in result
        assert "<!-- end: included.md -->" in result

    def test_nested_includes(self, temp_workspace):
        """Nested placeholders resolve recursively."""
        resolver = FileIncludeResolver()
        ctx = ResolutionContext(base_dir=temp_workspace)

        text = "{{nested_a.md}}"
        result = resolver.pattern.sub(lambda m: resolver.resolve(m, ctx), text)

        assert "A" in result
        assert "B" in result
        assert "C" in result

    def test_circular_reference_returns_comment(self, temp_workspace, caplog):
        """Circular references log error and return comment."""
        caplog.set_level(logging.ERROR)

        resolver = FileIncludeResolver()
        ctx = ResolutionContext(base_dir=temp_workspace)

        text = "{{circular_a.md}}"
        result = resolver.pattern.sub(lambda m: resolver.resolve(m, ctx), text)

        # Should return circular comment, not crash
        assert "<!-- circular:" in result or "Circular reference" in caplog.text

    def test_missing_file_returns_comment(self, temp_workspace, caplog):
        """Missing files log warning and return comment."""
        caplog.set_level(logging.WARNING)

        resolver = FileIncludeResolver()
        ctx = ResolutionContext(base_dir=temp_workspace)

        text = "{{nonexistent.md}}"
        result = resolver.pattern.sub(lambda m: resolver.resolve(m, ctx), text)

        assert "<!-- missing: nonexistent.md -->" in result
        assert "not found" in caplog.text

    def test_max_depth_returns_original(self, temp_workspace, caplog):
        """Max depth exceeded logs warning and returns original."""
        caplog.set_level(logging.WARNING)

        resolver = FileIncludeResolver()
        # Create context with max_depth=0 to trigger immediate depth exceeded
        ctx = ResolutionContext(base_dir=temp_workspace, max_depth=0)
        ctx = ctx.with_incremented_depth()  # depth 1 > max_depth 0

        text = "{{included.md}}"
        result = resolver.pattern.sub(lambda m: resolver.resolve(m, ctx), text)

        # Should return original placeholder or comment
        assert "{{included.md}}" in result or "depth" in caplog.text.lower()


# Tests for ColorResolver
class TestColorResolver:
    """Test {color} placeholder resolution."""

    def test_resolve_color(self):
        """{color} resolves to ANSI code."""
        resolver = ColorResolver()
        ctx = ResolutionContext(base_dir=Path("."))

        text = "{cyan}hello{reset}"
        result = resolver.pattern.sub(lambda m: resolver.resolve(m, ctx), text)

        assert "\033[36m" in result  # cyan
        assert "\033[0m" in result  # reset
        assert "hello" in result

    def test_resolve_bold(self):
        """{bold} resolves to bold ANSI code."""
        resolver = ColorResolver()
        ctx = ResolutionContext(base_dir=Path("."))

        text = "{bold}important{reset}"
        result = resolver.pattern.sub(lambda m: resolver.resolve(m, ctx), text)

        assert "\033[1m" in result  # bold
        assert "important" in result

    def test_unknown_placeholder_unchanged(self):
        """Unknown placeholders are left unchanged."""
        resolver = ColorResolver()
        ctx = ResolutionContext(base_dir=Path("."))

        text = "{unknown_color}text{reset}"
        result = resolver.pattern.sub(lambda m: resolver.resolve(m, ctx), text)

        # Unknown should be unchanged, reset should resolve
        assert "{unknown_color}" in result
        assert "\033[0m" in result

    def test_multiple_colors(self):
        """Multiple color placeholders resolve correctly."""
        resolver = ColorResolver()
        ctx = ResolutionContext(base_dir=Path("."))

        text = "{cyan}cyan{reset} {green}green{reset}"
        result = resolver.pattern.sub(lambda m: resolver.resolve(m, ctx), text)

        assert "\033[36m" in result  # cyan
        assert "\033[32m" in result  # green
        assert result.count("\033[0m") == 2  # two resets


# Tests for main API functions
class TestResolvePlaceholdersAPI:
    """Test convenience functions."""

    def test_resolve_file_includes_only(self, temp_workspace):
        """resolve_file_includes only resolves {{path}}."""
        text = "{{simple.md}} {cyan}color{reset}"
        result = resolve_file_includes(text, base_dir=temp_workspace)

        assert "# Simple" in result
        assert "{cyan}color{reset}" in result  # Colors unchanged

    def test_resolve_colors_only(self):
        """resolve_colors only resolves {color}."""
        text = "{cyan}colored{reset}"
        result = resolve_colors(text)

        assert "\033[36m" in result
        assert "\033[0m" in result

    def test_resolve_all(self, temp_workspace):
        """resolve_all resolves both file includes and colors."""
        (temp_workspace / "test.md").write_text("Content")

        text = "{{test.md}} {cyan}colored{reset}"
        result = resolve_all(text, base_dir=temp_workspace)

        assert "Content" in result
        assert "\033[36m" in result
        assert "\033[0m" in result

    def test_resolve_placeholders_with_custom_resolvers(self, temp_workspace):
        """Can use custom resolver list."""
        text = "{cyan}color{reset}"
        ctx = ResolutionContext(base_dir=temp_workspace)

        # Only file resolver - colors unchanged
        result = resolve_placeholders(text, ctx, resolvers=[FileIncludeResolver()])

        assert "{cyan}" in result
        assert "\033[36m" not in result
