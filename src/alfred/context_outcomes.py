"""Compact derived tool outcomes for prompt context."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from alfred.session import ToolCallRecord


@dataclass(frozen=True)
class ToolOutcome:
    """A compact representation of a tool call outcome."""

    tool_name: str
    summary: str
    tokens: int


def collect_tool_outcome_lines(
    messages: Sequence[Any] | None,
    *,
    max_calls: int = 5,
    workspace_dir: Path | None = None,
    max_output_chars: int = 120,
) -> list[str]:
    """Return compact tool outcome summaries from session messages."""

    outcomes = collect_tool_outcomes(
        messages,
        max_calls=max_calls,
        workspace_dir=workspace_dir,
        max_output_chars=max_output_chars,
    )
    return [outcome.summary for outcome in outcomes]


def collect_tool_outcomes(
    messages: Sequence[Any] | None,
    *,
    max_calls: int = 5,
    workspace_dir: Path | None = None,
    max_output_chars: int = 120,
) -> list[ToolOutcome]:
    """Return compact tool outcomes from session messages."""

    if not messages:
        return []

    tool_calls: list[ToolCallRecord] = []
    for message in messages:
        message_tool_calls = getattr(message, "tool_calls", None)
        if message_tool_calls:
            tool_calls.extend(message_tool_calls)

    if not tool_calls:
        return []

    recent_calls = tool_calls[-max_calls:] if max_calls > 0 else []
    return [
        summarize_tool_call_record(
            tool_call,
            workspace_dir=workspace_dir,
            max_output_chars=max_output_chars,
        )
        for tool_call in recent_calls
    ]


def summarize_tool_call_record(
    tool_call: ToolCallRecord,
    *,
    workspace_dir: Path | None = None,
    max_output_chars: int = 120,
) -> ToolOutcome:
    """Summarize a single tool call record."""

    summary = summarize_tool_call(
        tool_name=tool_call.tool_name,
        arguments=tool_call.arguments,
        output=tool_call.output,
        status=tool_call.status,
        workspace_dir=workspace_dir,
        max_output_chars=max_output_chars,
    )
    return ToolOutcome(tool_name=tool_call.tool_name, summary=summary, tokens=_estimate_tokens(summary))


def summarize_tool_call(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    output: str,
    status: str,
    workspace_dir: Path | None = None,
    max_output_chars: int = 120,
) -> str:
    """Summarize a tool call in a compact, human-readable form."""

    normalized_name = tool_name.lower()
    if normalized_name == "bash":
        command = _first_text(arguments, "command", "cmd", "script")
        command = command.strip() if command else ""
        exit_code = 0 if status == "success" else 1
        preview = _preview_output(output, max_output_chars)
        summary = f"bash: {command} exited {exit_code}".rstrip()
        if preview:
            summary = f"{summary} — {preview}"
        return summary

    if normalized_name == "read":
        path = _normalize_path(_first_text(arguments, "path", "file_path", "file"), workspace_dir)
        return f"read: {path}" if path else "read"

    if normalized_name == "edit":
        path = _normalize_path(_first_text(arguments, "path", "file_path", "file"), workspace_dir)
        verb = _mutation_verb(output, default="updated")
        return f"edit: {verb} {path}".strip() if path else f"edit: {verb}"

    if normalized_name == "write":
        path = _normalize_path(_first_text(arguments, "path", "file_path", "file"), workspace_dir)
        verb = _mutation_verb(output, default="created")
        return f"write: {verb} {path}".strip() if path else f"write: {verb}"

    preview = _preview_output(output, max_output_chars)
    if preview:
        return f"{normalized_name}: {preview}"
    return f"{normalized_name}: {status}"


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def _first_text(arguments: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = arguments.get(key)
        if value:
            return str(value)
    return ""


def _normalize_path(raw_path: str, workspace_dir: Path | None) -> str:
    path = Path(raw_path)
    if not path.is_absolute():
        return path.as_posix()

    base_dir = (workspace_dir or Path.cwd()).resolve()
    try:
        return path.resolve().relative_to(base_dir).as_posix()
    except Exception:  # noqa: BLE001
        return path.as_posix()


def _preview_output(output: str, max_chars: int) -> str:
    text = output.strip()
    if not text:
        return ""

    first_line = text.splitlines()[0].strip()
    if len(first_line) > max_chars:
        return first_line[: max(0, max_chars - 1)].rstrip() + "…"
    return first_line


def _mutation_verb(output: str, *, default: str) -> str:
    lowered = output.lower()
    if "updated" in lowered:
        return "updated"
    if "created" in lowered:
        return "created"
    return default
