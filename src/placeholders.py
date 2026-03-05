"""Unified placeholder resolution system.

Supports multiple placeholder types:
- File includes: {{path/to/file.md}}
- ANSI colors: {cyan}, {reset}, etc.
- Extensible for future placeholder types
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


class CircularReferenceError(Exception):
    """Raised when a circular placeholder reference is detected."""

    pass


class ResolutionContext:
    """Context passed through placeholder resolution.

    Tracks recursion state and provides utilities for resolvers.
    """

    def __init__(
        self,
        base_dir: Path,
        max_depth: int = 5,
    ):
        """Initialize resolution context.

        Args:
            base_dir: Base directory for relative file paths
            max_depth: Maximum nesting depth for placeholders
        """
        self.base_dir = base_dir
        self.max_depth = max_depth
        self._loaded: set[Path] = set()
        self._depth: int = 0

    def with_loaded(self, path: Path) -> ResolutionContext:
        """Create new context with path added to loaded set.

        Args:
            path: Path to mark as loaded

        Returns:
            New ResolutionContext with updated loaded set
        """
        ctx = ResolutionContext(self.base_dir, self.max_depth)
        ctx._loaded = self._loaded | {path}
        ctx._depth = self._depth
        return ctx

    def with_incremented_depth(self) -> ResolutionContext:
        """Create new context with depth + 1.

        Returns:
            New ResolutionContext with incremented depth
        """
        ctx = ResolutionContext(self.base_dir, self.max_depth)
        ctx._loaded = self._loaded.copy()
        ctx._depth = self._depth + 1
        return ctx

    def is_circular(self, path: Path) -> bool:
        """Check for circular references.

        Args:
            path: Path to check

        Returns:
            True if path already loaded (circular reference)
        """
        return path in self._loaded

    def is_depth_exceeded(self) -> bool:
        """Check if max depth exceeded.

        Returns:
            True if current depth exceeds max_depth
        """
        if self._depth > self.max_depth:
            logger.warning(
                f"Max placeholder depth ({self.max_depth}) exceeded, stopping resolution"
            )
            return True
        return False


class PlaceholderResolver(Protocol):
    """Protocol for placeholder resolvers."""

    pattern: re.Pattern

    def resolve(self, match: re.Match, context: ResolutionContext) -> str:
        """Resolve a placeholder match to its replacement text.

        Args:
            match: Regex match object for the placeholder
            context: Resolution context for state tracking

        Returns:
            Replacement text for the placeholder
        """
        ...


class FileIncludeResolver:
    """Resolves {{path}} file include placeholders."""

    pattern = re.compile(r"\{\{([^}]+)\}\}")

    def resolve(self, match: re.Match, context: ResolutionContext) -> str:
        """Resolve file include placeholder.

        Args:
            match: Regex match with captured file path
            context: Resolution context

        Returns:
            File content wrapped in HTML comments, or error comment
        """
        include_path = match.group(1).strip()
        file_path = context.base_dir / include_path

        # Check for circular reference
        if context.is_circular(file_path.resolve()):
            logger.error(f"Circular reference detected: {include_path}")
            return f"<!-- circular: {include_path} -->"

        # Check depth
        if context.is_depth_exceeded():
            logger.warning(f"Max depth exceeded, skipping: {include_path}")
            return match.group(0)  # Return original placeholder

        # Try to load file
        try:
            content = file_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning(f"Placeholder file not found: {include_path}")
            return f"<!-- missing: {include_path} -->"
        except Exception as e:
            logger.error(f"Error reading placeholder file {include_path}: {e}")
            return f"<!-- error: {include_path} -->"

        # Wrap in comments and recursively resolve
        new_context = context.with_loaded(file_path.resolve()).with_incremented_depth()
        resolved = resolve_placeholders(content, new_context)

        return f"<!-- included: {include_path} -->\n{resolved}\n<!-- end: {include_path} -->"


class ColorResolver:
    """Resolves {color} ANSI placeholder syntax."""

    pattern = re.compile(r"\{([a-z_]+)\}")

    # ANSI escape codes
    CODES = {
        # Reset
        "reset": "\033[0m",
        # Styles
        "bold": "\033[1m",
        "dim": "\033[2m",
        "italic": "\033[3m",
        "underline": "\033[4m",
        "blink": "\033[5m",
        "reverse": "\033[7m",
        "strike": "\033[9m",
        # Foreground colors
        "black": "\033[30m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        # Bright foreground
        "bright_black": "\033[90m",
        "bright_red": "\033[91m",
        "bright_green": "\033[92m",
        "bright_yellow": "\033[93m",
        "bright_blue": "\033[94m",
        "bright_magenta": "\033[95m",
        "bright_cyan": "\033[96m",
        "bright_white": "\033[97m",
        # Background colors
        "on_black": "\033[40m",
        "on_red": "\033[41m",
        "on_green": "\033[42m",
        "on_yellow": "\033[43m",
        "on_blue": "\033[44m",
        "on_magenta": "\033[45m",
        "on_cyan": "\033[46m",
        "on_white": "\033[47m",
        # Bright backgrounds
        "on_bright_black": "\033[100m",
        "on_bright_red": "\033[101m",
        "on_bright_green": "\033[102m",
        "on_bright_yellow": "\033[103m",
        "on_bright_blue": "\033[104m",
        "on_bright_magenta": "\033[105m",
        "on_bright_cyan": "\033[106m",
        "on_bright_white": "\033[107m",
    }

    def resolve(self, match: re.Match, context: ResolutionContext) -> str:
        """Resolve color placeholder.

        Args:
            match: Regex match with color name
            context: Resolution context (unused for colors)

        Returns:
            ANSI escape code or original if not found
        """
        placeholder = match.group(1)
        return self.CODES.get(placeholder, match.group(0))


# Default resolvers
DEFAULT_RESOLVERS = [
    FileIncludeResolver(),
    ColorResolver(),
]


def resolve_placeholders(
    text: str,
    context: ResolutionContext,
    resolvers: list[PlaceholderResolver] | None = None,
) -> str:
    """Resolve all placeholders in text.

    Args:
        text: Text with placeholders to resolve
        context: Resolution context (base_dir, depth tracking, etc.)
        resolvers: List of resolvers to use (defaults to all)

    Returns:
        Text with placeholders resolved

    Example:
        >>> ctx = ResolutionContext(base_dir=Path("/workspace"))
        >>> resolve_placeholders("{{README.md}}", ctx)
        '<!-- included: README.md -->\\n...content...\\n<!-- end: README.md -->'
    """
    from functools import partial

    resolvers = resolvers or DEFAULT_RESOLVERS
    result = text

    for resolver in resolvers:
        # Use partial to bind resolver immediately
        result = resolver.pattern.sub(
            partial(_resolve_match, resolver=resolver, context=context), result
        )

    return result


def _resolve_match(
    match: re.Match,
    resolver: PlaceholderResolver,
    context: ResolutionContext,
) -> str:
    """Helper function to resolve a match with bound resolver.

    Args:
        match: Regex match object
        resolver: The resolver to use
        context: Resolution context

    Returns:
        Resolved text
    """
    return resolver.resolve(match, context)


# Convenience functions for common use cases


def resolve_file_includes(
    text: str,
    base_dir: Path,
    max_depth: int = 5,
) -> str:
    """Resolve only file includes ({{path}}).

    Args:
        text: Text with file include placeholders
        base_dir: Base directory for relative paths
        max_depth: Maximum nesting depth

    Returns:
        Text with file includes resolved
    """
    context = ResolutionContext(base_dir=base_dir, max_depth=max_depth)
    return resolve_placeholders(text, context, resolvers=[FileIncludeResolver()])


def resolve_colors(text: str) -> str:
    """Resolve only color placeholders ({color}).

    Args:
        text: Text with color placeholders

    Returns:
        Text with ANSI escape codes
    """
    context = ResolutionContext(base_dir=Path("."))  # Base dir not needed
    return resolve_placeholders(text, context, resolvers=[ColorResolver()])


def resolve_all(text: str, base_dir: Path, max_depth: int = 5) -> str:
    """Resolve all placeholder types.

    Args:
        text: Text with placeholders
        base_dir: Base directory for file includes
        max_depth: Maximum nesting depth for includes

    Returns:
        Text with all placeholders resolved
    """
    context = ResolutionContext(base_dir=base_dir, max_depth=max_depth)
    return resolve_placeholders(text, context)
