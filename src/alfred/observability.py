"""Shared observability helpers for Alfred.

This module keeps the logging-surface contract in one place:
- stable surface names
- console prefixes that are colorized only in TTYs
- explicit surface fields in file logs
- lightweight metadata-oriented event formatting
"""

from __future__ import annotations

import json
import logging
import sys
from contextlib import suppress
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TextIO

ANSI_RESET = "\x1b[0m"
ANSI_COLORS: dict[Surface, str] = {
    # Populated after Surface is defined.
}


class Surface(StrEnum):
    """Log surfaces used throughout Alfred."""

    CORE = "core"
    WEBUI_SERVER = "webui-server"
    WEBUI_CLIENT = "webui-client"
    LLM = "llm"
    TOOLS = "tools"
    STORAGE = "storage"


ANSI_COLORS.update(
    {
        Surface.CORE: "\x1b[36m",  # cyan
        Surface.WEBUI_SERVER: "\x1b[35m",  # magenta
        Surface.WEBUI_CLIENT: "\x1b[33m",  # yellow
        Surface.LLM: "\x1b[32m",  # green
        Surface.TOOLS: "\x1b[34m",  # blue
        Surface.STORAGE: "\x1b[90m",  # bright black / gray
    }
)


_SURFACE_PREFIXES: tuple[tuple[str, Surface], ...] = (
    ("alfred.interfaces.webui.server", Surface.WEBUI_SERVER),
    ("alfred.interfaces.webui.validation", Surface.WEBUI_SERVER),
    ("alfred.interfaces.webui.protocol", Surface.WEBUI_SERVER),
    ("alfred.interfaces.webui", Surface.WEBUI_SERVER),
    ("alfred.cli.webui_hotswap", Surface.WEBUI_SERVER),
    ("alfred.llm", Surface.LLM),
    ("alfred.tools", Surface.TOOLS),
    ("alfred.storage", Surface.STORAGE),
    ("alfred.memory", Surface.STORAGE),
    ("alfred.agent", Surface.CORE),
    ("alfred.context", Surface.CORE),
    ("alfred.alfred", Surface.CORE),
    ("alfred.core", Surface.CORE),
    ("alfred.session", Surface.CORE),
    ("alfred.cli.main", Surface.CORE),
    ("alfred.cli", Surface.CORE),
    ("py.warnings", Surface.CORE),
)


@dataclass(frozen=True, slots=True)
class _LoggingConfig:
    level: int
    webui_debug: bool


class SurfaceRoutingFilter(logging.Filter):
    """Attach a surface and gate records by the configured verbosity."""

    def __init__(self, config: _LoggingConfig) -> None:
        super().__init__()
        self._config = config

    def filter(self, record: logging.LogRecord) -> bool:
        surface = resolve_surface(record)
        record.surface = surface.value
        return record.levelno >= self._config.level or (self._config.webui_debug and surface is Surface.WEBUI_SERVER)


class SurfaceFormatter(logging.Formatter):
    """Render log records with a stable surface prefix."""

    def __init__(self, *, kind: str, stream: TextIO | None = None) -> None:
        if kind not in {"console", "file"}:
            raise ValueError(f"Unknown formatter kind: {kind}")
        self.kind = kind
        self._stream = stream if stream is not None else sys.stderr
        fmt = (
            "%(surface_prefix)s %(message)s"
            if kind == "console"
            else "%(asctime)s %(levelname)s surface=%(surface)s logger=%(name)s %(message)s"
        )
        super().__init__(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        surface = resolve_surface(record)
        record.surface = surface.value
        record.surface_prefix = render_surface_prefix(
            surface,
            color=self.kind == "console" and self._stream_is_tty(),
        )
        # Get the full formatted message
        msg = record.getMessage()

        # Truncate embedding arrays (detect by pattern of many floats in brackets)
        import re
        # Pattern: [-0.123, 0.456, ...] with 10+ floats = likely embedding
        embedding_pattern = r'\[(\s*-?\d+\.\d+(?:[eE][+-]?\d+)?\s*,){10,}'
        if re.search(embedding_pattern, msg):
            # Replace full embedding with truncated version
            msg = re.sub(
                r'(\[\s*-?\d+\.\d+(?:[eE][+-]?\d+)?\s*,\s*){5}[^\]]*(\])',
                r'[... 20 of ~1536 embeddings truncated ...]',
                msg
            )
            record.msg = msg
            record.args = ()

        return super().format(record)

    def _stream_is_tty(self) -> bool:
        isatty = getattr(self._stream, "isatty", None)
        if callable(isatty):
            try:
                return bool(isatty())
            except Exception:
                return False
        return False


def surface_for_logger_name(logger_name: str) -> Surface:
    """Map a logger name to a stable Alfred surface."""
    for prefix, surface in _SURFACE_PREFIXES:
        if logger_name.startswith(prefix):
            return surface
    return Surface.CORE


def resolve_surface(record: logging.LogRecord) -> Surface:
    """Resolve a record's surface, preferring an explicit override when present."""
    surface = getattr(record, "surface", None)
    if isinstance(surface, Surface):
        return surface
    if isinstance(surface, str):
        try:
            return Surface(surface)
        except ValueError:
            return surface_for_logger_name(record.name)
    return surface_for_logger_name(record.name)


def render_surface_prefix(surface: Surface, *, color: bool) -> str:
    """Render a stable surface prefix, optionally colorized for a TTY."""
    prefix = f"[{surface.value}]"
    if not color:
        return prefix
    return f"{ANSI_COLORS[surface]}{prefix}{ANSI_RESET}"


def _render_field_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, str):
        if value == "" or any(ch.isspace() for ch in value) or "=" in value or '"' in value:
            return json.dumps(value, ensure_ascii=False)
        return value
    if isinstance(value, (list, tuple)):
        # Truncate long lists (e.g., embeddings) to prevent console spam
        if len(value) > 20:
            truncated = list(value[:10]) + [f"...({len(value) - 20} items)..."] + list(value[-10:])
            return json.dumps(truncated, ensure_ascii=False, separators=(",", ":"), default=str)
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)

    rendered = str(value)
    if rendered == "" or any(ch.isspace() for ch in rendered) or "=" in rendered:
        return json.dumps(rendered, ensure_ascii=False)
    return rendered


def event_message(event: str, **fields: object) -> str:
    """Build a consistent metadata-first event string."""
    parts = [f"event={event}"]
    for key, value in fields.items():
        if value is None:
            continue
        parts.append(f"{key}={_render_field_value(value)}")
    return " ".join(parts)


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    surface: Surface | str | None = None,
    **fields: object,
) -> None:
    """Emit a formatted event message at the requested log level."""
    extra: dict[str, object] = {}
    if surface is not None:
        extra["surface"] = surface.value if isinstance(surface, Surface) else str(surface)
    logger.log(level, event_message(event, **fields), extra=extra or None)


def configure_logging(
    *,
    level: int,
    log_file: Path | None,
    stream: TextIO | None = None,
    webui_debug: bool = False,
    toast_handler: logging.Handler | None = None,
) -> None:
    """Configure Alfred logging with surface-aware console and file handlers."""
    root = logging.getLogger()
    _reset_root_handlers(root)
    root.setLevel(logging.DEBUG)

    config = _LoggingConfig(level=level, webui_debug=webui_debug)

    console_stream = stream if stream is not None else sys.stderr
    console_handler = logging.StreamHandler(console_stream)
    _mark_owned(console_handler)
    console_handler.setLevel(logging.DEBUG)
    console_handler.addFilter(SurfaceRoutingFilter(config))
    console_handler.setFormatter(SurfaceFormatter(kind="console", stream=console_stream))
    root.addHandler(console_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        _mark_owned(file_handler)
        file_handler.setLevel(logging.DEBUG)
        file_handler.addFilter(SurfaceRoutingFilter(config))
        file_handler.setFormatter(SurfaceFormatter(kind="file"))
        root.addHandler(file_handler)

    if toast_handler is not None:
        toast_handler.setLevel(logging.WARNING)
        root.addHandler(toast_handler)

    logging.captureWarnings(True)

    for logger_name in ["markdown_it", "httpcore", "httpx", "urllib3", "asyncio"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def _mark_owned(handler: logging.Handler) -> None:
    handler._alfred_observability_owned = True  # type: ignore[attr-defined]


def _reset_root_handlers(root: logging.Logger) -> None:
    for handler in list(root.handlers):
        root.removeHandler(handler)
        if getattr(handler, "_alfred_observability_owned", False):
            with suppress(Exception):
                handler.close()
