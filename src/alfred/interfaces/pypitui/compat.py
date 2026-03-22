"""Compatibility helpers for Alfred's legacy PyPiTUI integration.

This module bridges the current Alfred TUI code to the real pypitui v2
component/overlay/terminal primitives without forcing the rest of Alfred to
rewrite all at once.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import BinaryIO

from pypitui import TUI, Component, Overlay, OverlayPosition, RenderedLine, Terminal

CURSOR_MARKER = "\x1b_pi:c\x07"


class Focusable:
    """Marker mixin for components that can be focused."""

    focused: bool


@dataclass(frozen=True)
class OverlayOptions:
    """Compatibility overlay configuration used by Alfred's legacy TUI."""

    anchor: str | None = None
    width: int = -1
    max_height: int = -1
    offset_y: int = 0
    margin: int = 0


class ProcessTerminal(Terminal):
    """Process-backed terminal with a polling input queue.

    The real pypitui Terminal handles raw mode and threaded input, but Alfred's
    current run loop expects to poll input sequences. This adapter preserves that
    contract while still using the real terminal I/O implementation.
    """

    def __init__(self, fd: int | None = None, buffer: BinaryIO | None = None) -> None:
        super().__init__(fd=fd, buffer=buffer)
        self._fallback_width = 80
        self._fallback_height = 24
        self._input_queue: list[str] = []

    def get_size(self) -> tuple[int, int]:
        """Return the current terminal size."""
        try:
            import os

            size = os.get_terminal_size(self._fd)
            return (size.columns, size.lines)
        except OSError:
            return (self._fallback_width, self._fallback_height)

    def queue_input(self, data: str) -> None:
        """Queue input for polling via ``read_sequence``.

        The queue stores raw string sequences so tests can inject keypresses
        without a real terminal.
        """
        if not data:
            return
        self._input_queue.extend(list(data))

    def read_sequence(self, timeout: float = 0.0) -> str:
        """Poll the next queued input sequence."""
        if self._input_queue:
            return self._input_queue.pop(0)
        if timeout > 0:
            import time

            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if self._input_queue:
                    return self._input_queue.pop(0)
                time.sleep(0.01)
        return ""

    def start(self, on_input: Callable[[bytes], None] | None = None) -> None:
        """Start the raw-mode input thread and mirror sequences to the queue."""

        def _handle_input(data: bytes) -> None:
            text = data.decode("utf-8", errors="ignore")
            self.queue_input(text)
            if on_input is not None:
                on_input(data)

        super().start(on_input=_handle_input)

    def stop(self) -> None:
        super().stop()


class OverlayHandle:
    """Compatibility handle for legacy overlay lifecycle calls."""

    def __init__(self, tui: CompatTUI, overlay: Overlay) -> None:
        self._tui = tui
        self._overlay = overlay

    def hide(self) -> None:
        """Hide the overlay."""
        self._overlay.visible = False
        self._tui.close_overlay(self._overlay)

    def is_hidden(self) -> bool:
        """Return whether the overlay is hidden."""
        return not self._overlay.visible


class CompatTUI(TUI):
    """pypitui TUI with the legacy Alfred helper methods added back."""

    def __init__(self, terminal: Terminal) -> None:
        super().__init__(terminal)
        self.children: list[Component] = []
        self._input_listeners: list[Callable[[str], dict[str, bool] | None]] = []
        self._render_requested = False
        self._last_known_size: tuple[int, int] | None = None

    def add_child(self, component: Component) -> None:  # type: ignore[override]
        """Append a top-level child component.

        Alfred's current layout stacks multiple root-level components instead of
        using a single container root.
        """
        self.children.append(component)

    def add_input_listener(self, listener: Callable[[str], dict[str, bool] | None]) -> Callable[[], None]:
        """Register a high-priority input listener.

        Returns:
            A callable that removes the listener when invoked.
        """
        self._input_listeners.append(listener)

        def _remove() -> None:
            if listener in self._input_listeners:
                self._input_listeners.remove(listener)

        return _remove

    def request_render(self, force: bool = False) -> None:
        """Mark the next frame as dirty.

        The legacy Alfred loop renders every frame already, so this just records
        that a render was requested.
        """
        self._render_requested = True
        if force:
            self._render_requested = True

    def request_resize_check(self) -> None:
        """Re-run resize handling if the terminal size changed."""
        if not hasattr(self.terminal, "get_size"):
            return

        size = self.terminal.get_size()  # type: ignore[no-any-return]
        if size != self._last_known_size:
            self._last_known_size = size
            self.on_resize(*size)

    def start(self) -> None:
        """Start the TUI session."""
        if hasattr(self.terminal, "start"):
            self.terminal.start()  # type: ignore[misc]
        if hasattr(self.terminal, "hide_cursor"):
            self.terminal.hide_cursor()
        self._render_requested = True

    def stop(self) -> None:
        """Stop the TUI session."""
        if hasattr(self.terminal, "stop"):
            self.terminal.stop()  # type: ignore[misc]
        if hasattr(self.terminal, "show_cursor"):
            self.terminal.show_cursor()
        self._render_requested = False

    def handle_input(self, data: str) -> dict[str, bool] | None:
        """Dispatch raw input to listeners and the focused component."""
        result: dict[str, bool] | None = None

        for listener in list(self._input_listeners):
            listener_result = listener(data)
            if listener_result is not None:
                result = listener_result
                if listener_result.get("consume", False):
                    return listener_result

        focused = self._focused
        if focused is not None:
            handler = getattr(focused, "handle_input", None)
            if callable(handler):
                handler_result = handler(data)
                if isinstance(handler_result, dict):
                    result = handler_result

        return result

    def render_frame(self) -> None:
        """Render the current root component and visible overlays.

        The real pypitui TUI focuses on differential rendering. Alfred's current
        lifecycle expects a single explicit render call, so this compatibility
        method performs a full redraw from the current component tree.
        """
        if not self.children:
            return

        width, height = self._get_terminal_size()
        rendered: list[RenderedLine] = []
        for child in self.children:
            rendered.extend(self._normalize_rendered_lines(child.render(width)))

        for overlay in sorted(self._overlays, key=lambda item: item.z_index):
            rendered = self._composite_overlay_lines(rendered, overlay, width, height)

        self.terminal.clear_screen()
        self.terminal.move_cursor(0, 0)
        for line in rendered:
            self.terminal.write(f"{line.content}\r\n")

        self._render_requested = False

    def show_overlay(  # type: ignore[override]
        self,
        overlay_or_content: Overlay | Component,
        options: OverlayOptions | None = None,
    ) -> OverlayHandle:
        """Show an overlay and return a compatibility handle.

        Alfred's legacy overlay calls pass a component and a compatibility
        options object. The real pypitui overlay system wants an Overlay.
        """
        if isinstance(overlay_or_content, Overlay):
            overlay = overlay_or_content
        else:
            overlay = Overlay(
                content=overlay_or_content,
                position=self._options_to_position(overlay_or_content, options),
            )

        super().show_overlay(overlay)
        return OverlayHandle(self, overlay)

    def close_overlay(self, overlay: Overlay) -> None:
        """Hide and remove an overlay."""
        overlay.visible = False
        super().close_overlay(overlay)

    def reset_scrollback_state(self) -> None:
        """Reset cached render state after a full clear."""
        self._previous_lines.clear()
        self._max_lines_rendered = 0
        self._viewport_top = 0
        self._hardware_cursor_row = 0
        self._hardware_cursor_col = 0

    def _get_terminal_size(self) -> tuple[int, int]:
        if hasattr(self.terminal, "get_size"):
            size = self.terminal.get_size()  # type: ignore[no-any-return]
            return size
        return (80, 24)

    def _normalize_rendered_lines(self, lines: Iterable[str | RenderedLine]) -> list[RenderedLine]:
        normalized: list[RenderedLine] = []
        for line in lines:
            if isinstance(line, RenderedLine):
                normalized.append(line)
            else:
                normalized.append(RenderedLine(content=line, styles=[]))
        return normalized

    def _composite_overlay_lines(
        self,
        base_lines: list[RenderedLine],
        overlay: Overlay,
        term_width: int,
        term_height: int,
    ) -> list[RenderedLine]:
        if not overlay.visible:
            return base_lines

        row, col, overlay_width, overlay_height = self._resolve_position(overlay.position, term_width, term_height)

        result = list(base_lines)
        while len(result) < row + overlay_height:
            result.append(RenderedLine(content=" " * term_width, styles=[]))

        overlay_lines = self._normalize_rendered_lines(overlay.content.render(overlay_width))

        for index, overlay_line in enumerate(overlay_lines[:overlay_height]):
            target_row = row + index
            if target_row >= len(result):
                break

            base = result[target_row].content
            content = overlay_line.content[:overlay_width]
            before = base[:col]
            after_start = col + len(content)
            after = base[after_start:]
            new_content = (before + content + after)[:term_width].ljust(term_width)

            result[target_row] = RenderedLine(
                content=new_content,
                styles=result[target_row].styles,
            )

        return result

    def _options_to_position(
        self,
        content: Component,
        options: OverlayOptions | None,
    ) -> OverlayPosition:
        width, height = self._get_terminal_size()
        rendered = self._normalize_rendered_lines(content.render(width))
        content_width = max((len(line.content) for line in rendered), default=0)
        content_height = max(len(rendered), 1)

        if options is None:
            return OverlayPosition(row=0, col=0, width=content_width or width, height=content_height)

        overlay_width = options.width if options.width > 0 else max(content_width, 1)
        overlay_height = options.max_height if options.max_height > 0 else content_height
        anchor = options.anchor or "top-left"

        if anchor == "center":
            row = max(0, (height - overlay_height) // 2 + options.offset_y)
            col = max(0, (width - overlay_width) // 2)
        elif anchor == "bottom-left":
            row = max(0, height - overlay_height + options.offset_y)
            col = max(0, options.margin)
        elif anchor == "bottom-right":
            row = max(0, height - overlay_height + options.offset_y)
            col = max(0, width - overlay_width - options.margin)
        else:
            row = max(0, options.offset_y)
            col = max(0, options.margin)

        overlay_width = max(1, min(overlay_width, width - col))
        overlay_height = max(1, min(overlay_height, height - row))
        return OverlayPosition(
            row=row,
            col=col,
            width=overlay_width,
            height=overlay_height,
            anchor=anchor,
        )


__all__ = [
    "CURSOR_MARKER",
    "Focusable",
    "OverlayHandle",
    "OverlayOptions",
    "CompatTUI",
    "ProcessTerminal",
]
