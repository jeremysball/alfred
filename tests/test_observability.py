from __future__ import annotations

import io
import logging
from contextlib import contextmanager, suppress

from alfred.observability import (
    Surface,
    SurfaceFormatter,
    configure_logging,
    event_message,
    surface_for_logger_name,
)


class _TtyBuffer(io.StringIO):
    def isatty(self) -> bool:  # pragma: no cover - exercised by formatter
        return True


class _PlainBuffer(io.StringIO):
    def isatty(self) -> bool:  # pragma: no cover - exercised by formatter
        return False


@contextmanager
def _preserve_root_logging() -> None:
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    original_propagate = root.propagate
    try:
        yield
    finally:
        for handler in list(root.handlers):
            root.removeHandler(handler)
            with suppress(Exception):
                handler.close()
        for handler in original_handlers:
            root.addHandler(handler)
        root.setLevel(original_level)
        root.propagate = original_propagate


def test_surface_names_are_stable() -> None:
    assert {surface.value for surface in Surface} == {
        "core",
        "webui-server",
        "webui-client",
        "llm",
        "tools",
        "storage",
    }


def test_surface_for_logger_name_routes_known_modules() -> None:
    assert surface_for_logger_name("alfred.interfaces.webui.server") is Surface.WEBUI_SERVER
    assert surface_for_logger_name("alfred.interfaces.webui.validation") is Surface.WEBUI_SERVER
    assert surface_for_logger_name("alfred.llm") is Surface.LLM
    assert surface_for_logger_name("alfred.tools.search_sessions") is Surface.TOOLS
    assert surface_for_logger_name("alfred.storage.sqlite") is Surface.STORAGE
    assert surface_for_logger_name("alfred.context") is Surface.CORE
    assert surface_for_logger_name("something.else") is Surface.CORE


def test_event_message_formats_metadata_consistently() -> None:
    assert (
        event_message(
            "turn.start",
            session_id="abc123",
            message_chars=42,
            queued=False,
            note="hello world",
        )
        == 'event=turn.start session_id=abc123 message_chars=42 queued=false note="hello world"'
    )


def test_surface_formatter_colors_prefix_in_tty() -> None:
    formatter = SurfaceFormatter(kind="console", stream=_TtyBuffer())
    record = logging.LogRecord(
        name="alfred.context",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="event=turn.start",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)

    assert "\x1b[" in formatted
    assert "[core]" in formatted
    assert formatted.endswith("event=turn.start")


def test_surface_formatter_emits_plain_prefix_when_not_tty() -> None:
    formatter = SurfaceFormatter(kind="console", stream=_PlainBuffer())
    record = logging.LogRecord(
        name="alfred.interfaces.webui.server",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="event=webui.debug",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)

    assert "\x1b[" not in formatted
    assert formatted.startswith("[webui-server]")
    assert formatted.endswith("event=webui.debug")


def test_configure_logging_emits_file_records_with_surface_fields(tmp_path) -> None:
    log_file = tmp_path / "alfred.log"
    stream = _PlainBuffer()

    with _preserve_root_logging():
        configure_logging(level=logging.INFO, log_file=log_file, stream=stream, webui_debug=False)
        logging.getLogger("alfred.context").info("event=turn.start")

    output = log_file.read_text()
    assert "surface=core" in output
    assert "logger=alfred.context" in output
    assert "event=turn.start" in output
    assert "\x1b[" not in output


def test_configure_logging_allows_webui_debug_without_enabling_core_debug(tmp_path) -> None:
    log_file = tmp_path / "alfred.log"
    stream = _PlainBuffer()

    with _preserve_root_logging():
        configure_logging(level=logging.WARNING, log_file=log_file, stream=stream, webui_debug=True)
        logging.getLogger("alfred.context").debug("event=core.hidden")
        logging.getLogger("alfred.interfaces.webui.server").debug("event=webui.visible")

    console_output = stream.getvalue()
    file_output = log_file.read_text()

    assert "event=core.hidden" not in console_output
    assert "event=webui.visible" in console_output
    assert "[webui-server]" in console_output
    assert "event=core.hidden" not in file_output
    assert "event=webui.visible" in file_output
    assert "surface=webui-server" in file_output
