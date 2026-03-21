"""Utility functions for PyPiTUI components."""

from __future__ import annotations

import re

from pypitui.utils import wcwidth as _wcwidth

_ANSI_SGR_PATTERN = re.compile(r"\x1b\[[0-9;]*m")
_ANSI_RESET = "\x1b[0m"


def format_tokens(n: int) -> str:
    """Format token count: 1234567 -> 1.2M, 12345 -> 12K, 123 -> 123."""
    if n >= 1_000_000:
        value = n / 1_000_000
        if value == int(value):
            return f"{int(value)}M"
        return f"{value:.1f}M"
    elif n >= 1_000:
        value = n / 1_000
        if value == int(value):
            return f"{int(value)}K"
        return f"{value:.1f}K"
    return str(n)


def visible_width(text: str) -> int:
    """Measure visible width while ignoring ANSI escape sequences."""
    stripped = _ANSI_SGR_PATTERN.sub("", text)
    width = 0
    for char in stripped:
        char_width = _wcwidth(char)
        width += char_width if char_width > 0 else 0
    return width


def wrap_text_with_ansi(text: str, width: int) -> list[str]:
    """Wrap text to width while preserving ANSI escape sequences."""
    if width <= 0:
        return [text] if text else [""]

    lines: list[str] = []
    paragraphs = text.split("\n")
    for paragraph in paragraphs:
        lines.extend(_wrap_paragraph_with_ansi(paragraph, width))
    return lines


def _wrap_paragraph_with_ansi(paragraph: str, width: int) -> list[str]:
    if paragraph == "":
        return [""]

    lines: list[str] = []
    current_parts: list[str] = []
    current_width = 0
    active_prefix = ""

    for token in _iter_tokens(paragraph):
        if _ANSI_SGR_PATTERN.fullmatch(token):
            current_parts.append(token)
            if token == _ANSI_RESET:
                active_prefix = ""
            else:
                active_prefix += token
            continue

        token_width = _wcwidth(token)
        if token_width < 0:
            token_width = 0

        if current_width > 0 and current_width + token_width > width:
            lines.append(_finalize_wrapped_line(current_parts, active_prefix))
            current_parts = [active_prefix] if active_prefix else []
            current_width = 0

        current_parts.append(token)
        current_width += token_width

    lines.append(_finalize_wrapped_line(current_parts, active_prefix))
    return lines


def _iter_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    index = 0
    while index < len(text):
        if text[index] == "\x1b":
            match = _ANSI_SGR_PATTERN.match(text, index)
            if match is not None:
                tokens.append(match.group(0))
                index = match.end()
                continue
        tokens.append(text[index])
        index += 1
    return tokens


def _finalize_wrapped_line(parts: list[str], active_prefix: str) -> str:
    line = "".join(parts)
    if active_prefix and not line.endswith(_ANSI_RESET):
        return f"{line}{_ANSI_RESET}"
    return line
