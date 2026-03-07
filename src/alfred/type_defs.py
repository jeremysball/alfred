"""Type definitions for Alfred.

Shared types used across the codebase.
"""

from typing import Any

# JSON object type - dict with string keys and JSON-compatible values
JsonObject = dict[str, Any]


def ensure_json_object(value: Any) -> JsonObject:
    """Ensure value is a JSON object (dict with string keys).

    Args:
        value: Any value to check/convert

    Returns:
        A JsonObject (dict with string keys)

    Raises:
        TypeError: If value cannot be converted to JsonObject
    """
    if isinstance(value, dict):
        return {str(k): v for k, v in value.items()}
    raise TypeError(f"Expected dict, got {type(value).__name__}")
