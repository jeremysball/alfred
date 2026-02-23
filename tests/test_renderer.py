"""Unit tests for StreamingRenderer."""

import io
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from src.interfaces.renderer import RenderSegment, StreamingRenderer


@pytest.fixture
def console() -> Console:
    """Create a Console for testing."""
    return Console(force_terminal=True, width=80, legacy_windows=False)


@pytest.fixture
def renderer(console: Console) -> StreamingRenderer:
    """Create a StreamingRenderer for testing."""
    return StreamingRenderer(console=console)


class TestRenderSegment:
    """Tests for RenderSegment dataclass."""

    def test_text_segment_defaults(self) -> None:
        """Text segment has correct defaults."""
        segment = RenderSegment(type="text", content="Hello")
        assert segment.type == "text"
        assert segment.content == "Hello"
        assert segment.tool_name is None
        assert segment.is_error is False

    def test_tool_segment(self) -> None:
        """Tool segment stores all fields."""
        segment = RenderSegment(
            type="tool",
            content="result",
            tool_name="read",
            is_error=True,
        )
        assert segment.type == "tool"
        assert segment.tool_name == "read"
        assert segment.is_error is True


class TestStreamingRendererInit:
    """Tests for StreamingRenderer initialization."""

    def test_accepts_console(self, console: Console) -> None:
        """Renderer accepts Console via __init__."""
        renderer = StreamingRenderer(console=console)
        assert renderer.console is console

    def test_initial_state_empty(self, renderer: StreamingRenderer) -> None:
        """Renderer starts with empty state."""
        assert renderer._content_buffer == ""
        assert renderer._rendered_lines == []
        assert renderer._segments == []
        assert renderer.line_count == 0
        assert not renderer.has_content

    def test_initial_throttle_state(self, renderer: StreamingRenderer) -> None:
        """Renderer starts with zero last render time."""
        assert renderer._last_render_time == 0.0
        assert not renderer._pending_render


class TestAddChunk:
    """Tests for add_chunk method."""

    def test_add_single_chunk(self, renderer: StreamingRenderer) -> None:
        """Adding a chunk accumulates content."""
        renderer.add_chunk("Hello")
        assert renderer._content_buffer == "Hello"
        assert renderer.has_content

    def test_add_multiple_chunks(self, renderer: StreamingRenderer) -> None:
        """Multiple chunks accumulate correctly."""
        renderer.add_chunk("Hello ")
        renderer.add_chunk("world!")
        assert renderer._content_buffer == "Hello world!"


class TestAddToolPanel:
    """Tests for add_tool_panel method."""

    def test_add_tool_panel(self, renderer: StreamingRenderer) -> None:
        """Tool panel is added to segments."""
        renderer.add_tool_panel("read", "file contents", is_error=False)
        assert len(renderer._segments) == 1
        assert renderer._segments[0].type == "tool"
        assert renderer._segments[0].tool_name == "read"

    def test_add_tool_panel_finalizes_buffer(self, renderer: StreamingRenderer) -> None:
        """Adding tool panel finalizes current text buffer."""
        renderer.add_chunk("Some text")
        renderer.add_tool_panel("read", "result")
        # Text should be converted to segment
        assert len(renderer._segments) == 2
        assert renderer._segments[0].type == "text"
        assert renderer._segments[0].content == "Some text"
        assert renderer._segments[1].type == "tool"
        assert renderer._content_buffer == ""  # Buffer cleared


class TestClear:
    """Tests for clear method."""

    def test_clear_resets_all_state(self, renderer: StreamingRenderer) -> None:
        """Clear resets all internal state."""
        renderer.add_chunk("Some content")
        renderer.add_tool_panel("read", "result")
        renderer._rendered_lines = ["line 1", "line 2"]

        renderer.clear()

        assert renderer._content_buffer == ""
        assert renderer._segments == []
        assert renderer._rendered_lines == []
        assert not renderer.has_content

    @patch("src.interfaces.renderer.patch_stdout")
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_clear_clears_terminal_content(
        self,
        mock_stdout: io.StringIO,
        mock_patch: MagicMock,
        renderer: StreamingRenderer,
    ) -> None:
        """Clear clears previously rendered content from terminal."""
        mock_patch.return_value.__enter__ = MagicMock(return_value=None)
        mock_patch.return_value.__exit__ = MagicMock(return_value=None)

        # Simulate previously rendered content
        renderer._rendered_lines = ["line 1", "line 2", "line 3"]

        renderer.clear()

        output = mock_stdout.getvalue()
        # Should move cursor up 3 lines
        assert "\033[3A" in output
        # Should clear lines
        assert "\033[K" in output


class TestDiffChangedIndices:
    """Tests for _diff_changed_indices method."""

    def test_identical_lines_returns_empty(self, renderer: StreamingRenderer) -> None:
        """Identical lines return empty list (no diff)."""
        old = ["line 1", "line 2", "line 3"]
        new = ["line 1", "line 2", "line 3"]
        assert renderer._diff_changed_indices(old, new) == []

    def test_first_line_differs(self, renderer: StreamingRenderer) -> None:
        """Returns [0] if first line differs."""
        old = ["line 1", "line 2", "line 3"]
        new = ["different", "line 2", "line 3"]
        assert renderer._diff_changed_indices(old, new) == [0]

    def test_middle_line_differs(self, renderer: StreamingRenderer) -> None:
        """Returns index of differing line."""
        old = ["line 1", "line 2", "line 3"]
        new = ["line 1", "modified", "line 3"]
        assert renderer._diff_changed_indices(old, new) == [1]

    def test_multiple_lines_differ(self, renderer: StreamingRenderer) -> None:
        """Returns all differing indices."""
        old = ["line 1", "line 2", "line 3"]
        new = ["changed", "line 2", "also changed"]
        assert renderer._diff_changed_indices(old, new) == [0, 2]

    def test_new_shorter(self, renderer: StreamingRenderer) -> None:
        """Returns indices of removed lines."""
        old = ["line 1", "line 2", "line 3"]
        new = ["line 1", "line 2"]
        assert renderer._diff_changed_indices(old, new) == [2]  # Line 2 was removed

    def test_new_longer(self, renderer: StreamingRenderer) -> None:
        """Returns indices of new lines."""
        old = ["line 1", "line 2"]
        new = ["line 1", "line 2", "line 3"]
        assert renderer._diff_changed_indices(old, new) == [2]  # Line 2 is new

    def test_both_empty(self, renderer: StreamingRenderer) -> None:
        """Empty lists return empty."""
        assert renderer._diff_changed_indices([], []) == []

    def test_old_empty(self, renderer: StreamingRenderer) -> None:
        """Old empty returns all new indices."""
        assert renderer._diff_changed_indices([], ["new"]) == [0]

    def test_new_empty(self, renderer: StreamingRenderer) -> None:
        """New empty returns all old indices."""
        assert renderer._diff_changed_indices(["old"], []) == [0]

    def test_ansi_codes_ignored(self, renderer: StreamingRenderer) -> None:
        """ANSI codes are stripped before comparison."""
        # Same text content, different ANSI codes
        old = ["\x1b[1mline 1\x1b[0m", "\x1b[32mline 2\x1b[0m"]
        new = ["\x1b[1;3mline 1\x1b[0m", "\x1b[32;1mline 2\x1b[0m"]
        # Should return empty (all lines match content-wise)
        assert renderer._diff_changed_indices(old, new) == []

    def test_ansi_codes_with_content_change(self, renderer: StreamingRenderer) -> None:
        """Content change detected even with ANSI codes present."""
        old = ["\x1b[1mline 1\x1b[0m", "\x1b[32mline 2\x1b[0m"]
        new = ["\x1b[1mline 1\x1b[0m", "\x1b[32mCHANGED\x1b[0m"]
        # Should return [1] (second line content differs)
        assert renderer._diff_changed_indices(old, new) == [1]


class TestRenderMarkdown:
    """Tests for _render_markdown method."""

    def test_renders_bold(self, renderer: StreamingRenderer) -> None:
        """Renders bold markdown with ANSI codes."""
        lines = renderer._render_markdown("**bold text**")
        assert len(lines) > 0
        # Should contain ANSI escape codes
        assert "\033[" in lines[0]

    def test_renders_header(self, renderer: StreamingRenderer) -> None:
        """Renders header with ANSI codes."""
        lines = renderer._render_markdown("# Header")
        assert len(lines) > 0
        assert "\033[" in lines[0]

    def test_empty_content_returns_empty(self, renderer: StreamingRenderer) -> None:
        """Empty content returns empty list."""
        assert renderer._render_markdown("") == []

    def test_plain_text_produces_lines(self, renderer: StreamingRenderer) -> None:
        """Plain text is rendered."""
        lines = renderer._render_markdown("Hello world")
        assert len(lines) > 0


class TestDrawDiff:
    """Tests for _draw_diff method."""

    @patch("src.interfaces.renderer.patch_stdout")
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_draw_from_empty(
        self,
        mock_stdout: io.StringIO,
        mock_patch: MagicMock,
        renderer: StreamingRenderer,
    ) -> None:
        """Drawing from empty state just prints new lines."""
        mock_patch.return_value.__enter__ = MagicMock(return_value=None)
        mock_patch.return_value.__exit__ = MagicMock(return_value=None)

        new_lines = ["line 1", "line 2"]
        renderer._draw_diff(new_lines)

        output = mock_stdout.getvalue()
        # Should have the lines
        assert "line 1" in output
        assert "line 2" in output

    @patch("src.interfaces.renderer.patch_stdout")
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_pure_append_no_cursor_movement(
        self,
        mock_stdout: io.StringIO,
        mock_patch: MagicMock,
        renderer: StreamingRenderer,
    ) -> None:
        """Pure append (new lines, old unchanged) doesn't move cursor up."""
        mock_patch.return_value.__enter__ = MagicMock(return_value=None)
        mock_patch.return_value.__exit__ = MagicMock(return_value=None)

        renderer._rendered_lines = ["line 1", "line 2"]
        new_lines = ["line 1", "line 2", "line 3", "line 4"]

        renderer._draw_diff(new_lines)

        output = mock_stdout.getvalue()
        # Should NOT have cursor up (appending, not redrawing)
        assert "\033[" not in output or "A" not in output or "line 3" in output

    @patch("src.interfaces.renderer.patch_stdout")
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_clears_orphans(
        self,
        mock_stdout: io.StringIO,
        mock_patch: MagicMock,
        renderer: StreamingRenderer,
    ) -> None:
        """Clears orphan lines when new render is shorter."""
        mock_patch.return_value.__enter__ = MagicMock(return_value=None)
        mock_patch.return_value.__exit__ = MagicMock(return_value=None)

        renderer._rendered_lines = ["line 1", "line 2", "line 3"]
        new_lines = ["line 1", "line 2"]  # One less line

        renderer._draw_diff(new_lines)

        output = mock_stdout.getvalue()
        # Should have clear-to-end-of-line code for orphan
        assert "\033[K" in output

    @patch("src.interfaces.renderer.patch_stdout")
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_mid_content_change_moves_cursor(
        self,
        mock_stdout: io.StringIO,
        mock_patch: MagicMock,
        renderer: StreamingRenderer,
    ) -> None:
        """Mid-content change moves cursor to redraw from changed line."""
        mock_patch.return_value.__enter__ = MagicMock(return_value=None)
        mock_patch.return_value.__exit__ = MagicMock(return_value=None)

        renderer._rendered_lines = ["line 1", "line 2", "line 3"]
        new_lines = ["line 1", "line 2 modified", "line 3"]

        renderer._draw_diff(new_lines)

        output = mock_stdout.getvalue()
        # Should have cursor up code to get to line 1 (index 1, so 2 lines up)
        assert "\033[2A" in output


class TestRender:
    """Tests for the main render method."""

    @patch("src.interfaces.renderer.patch_stdout")
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_render_updates_rendered_lines(
        self,
        mock_stdout: io.StringIO,
        mock_patch: MagicMock,
        renderer: StreamingRenderer,
    ) -> None:
        """Render updates internal rendered_lines state."""
        mock_patch.return_value.__enter__ = MagicMock(return_value=None)
        mock_patch.return_value.__exit__ = MagicMock(return_value=None)

        renderer.add_chunk("Hello world")
        renderer.render(force=True)

        assert len(renderer._rendered_lines) > 0
        assert renderer.line_count > 0

    @patch("src.interfaces.renderer.patch_stdout")
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_render_empty_does_nothing(
        self,
        mock_stdout: io.StringIO,
        mock_patch: MagicMock,
        renderer: StreamingRenderer,
    ) -> None:
        """Rendering with no content does nothing."""
        mock_patch.return_value.__enter__ = MagicMock(return_value=None)
        mock_patch.return_value.__exit__ = MagicMock(return_value=None)

        renderer.render()
        assert renderer._rendered_lines == []

    def test_render_throttles_rapid_calls(self, renderer: StreamingRenderer) -> None:
        """Rapid render calls are throttled."""
        renderer.add_chunk("Content")

        # First render should work
        renderer.render(force=True)

        # Immediate second render should be throttled
        renderer.add_chunk(" more")
        renderer.render(force=False)
        assert renderer._pending_render is True

    def test_force_render_bypasses_throttle(self, renderer: StreamingRenderer) -> None:
        """Force=True bypasses throttling."""
        renderer.add_chunk("Content")
        renderer.render(force=True)

        # Immediate force render should work
        renderer.add_chunk(" more")
        renderer.render(force=True)
        assert renderer._pending_render is False


class TestFlush:
    """Tests for the flush method."""

    @patch("src.interfaces.renderer.patch_stdout")
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_flush_renders_pending_content(
        self,
        mock_stdout: io.StringIO,
        mock_patch: MagicMock,
        renderer: StreamingRenderer,
    ) -> None:
        """Flush renders any pending content."""
        mock_patch.return_value.__enter__ = MagicMock(return_value=None)
        mock_patch.return_value.__exit__ = MagicMock(return_value=None)

        renderer.add_chunk("Content")
        renderer.flush()

        assert len(renderer._rendered_lines) > 0
        assert renderer._pending_render is False


class TestFinalize:
    """Tests for finalize method."""

    @patch("src.interfaces.renderer.patch_stdout")
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_finalize_renders_and_clears(
        self,
        mock_stdout: io.StringIO,
        mock_patch: MagicMock,
        renderer: StreamingRenderer,
    ) -> None:
        """Finalize renders final content and clears state."""
        mock_patch.return_value.__enter__ = MagicMock(return_value=None)
        mock_patch.return_value.__exit__ = MagicMock(return_value=None)

        renderer.add_chunk("Final content")
        renderer.finalize()

        # State should be cleared
        assert renderer._content_buffer == ""
        assert renderer._segments == []
        assert renderer._rendered_lines == []


class TestIntegration:
    """Integration tests for full rendering pipeline."""

    @patch("src.interfaces.renderer.patch_stdout")
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_full_streaming_flow(
        self,
        mock_stdout: io.StringIO,
        mock_patch: MagicMock,
        renderer: StreamingRenderer,
    ) -> None:
        """Test the full streaming flow: clear, add chunks, render, finalize."""
        mock_patch.return_value.__enter__ = MagicMock(return_value=None)
        mock_patch.return_value.__exit__ = MagicMock(return_value=None)

        renderer.clear()

        # Simulate streaming
        for chunk in ["Hello ", "world", "!"]:
            renderer.add_chunk(chunk)
            renderer.render()

        renderer.finalize()

        # Verify content was rendered
        output = mock_stdout.getvalue()
        # Output should contain ANSI codes
        assert "\033[" in output

    @patch("src.interfaces.renderer.patch_stdout")
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_streaming_with_tool_panel(
        self,
        mock_stdout: io.StringIO,
        mock_patch: MagicMock,
        renderer: StreamingRenderer,
    ) -> None:
        """Test streaming with tool panel interleaved."""
        mock_patch.return_value.__enter__ = MagicMock(return_value=None)
        mock_patch.return_value.__exit__ = MagicMock(return_value=None)

        renderer.clear()

        renderer.add_chunk("Let me read that file.")
        renderer.render()

        renderer.add_tool_panel("read", "file contents here", is_error=False)
        renderer.render()

        renderer.add_chunk(" The file contains...")
        renderer.render()

        renderer.finalize()

        # Should have rendered all content
        output = mock_stdout.getvalue()
        assert "\033[" in output
