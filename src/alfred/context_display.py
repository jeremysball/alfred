"""Context display formatting for /context command (PRD #101).

Provides functionality to gather and format system context information
for user inspection via the /context command.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from alfred.context import SYSTEM_PROMPT_SECTION_LABELS, SYSTEM_PROMPT_SECTION_ORDER
from alfred.context_outcomes import summarize_tool_call_record

if TYPE_CHECKING:
    from alfred.alfred import Alfred

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    """Estimate token count from character count (4 chars ≈ 1 token)."""
    return len(text) // 4


def _preview_text(text: str, max_length: int = 120) -> str:
    """Return a compact preview of text for summary displays."""
    normalized = " ".join(str(text or "").split()).strip()
    if not normalized:
        return ""
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max(0, max_length - 1)].rstrip() + "…"


def _context_file_name(file: Any) -> str:
    """Return a human-readable filename for a loaded context file."""
    path = getattr(file, "path", None)
    if path:
        return Path(str(path)).name
    name = getattr(file, "name", "")
    return f"{name}.md" if name and not str(name).endswith(".md") else str(name)


def _context_file_identifier(file: Any) -> str:
    """Return a stable identifier for a loaded context file."""
    name = getattr(file, "name", "")
    if name:
        return str(name)
    path = getattr(file, "path", None)
    if path:
        return Path(str(path)).stem
    return ""


async def get_context_display(alfred: Alfred, session_id: str | None = None) -> dict[str, Any]:
    """Get current context information for /context command.

    Args:
        alfred: The Alfred instance to gather context from
        session_id: Optional session ID. If None, uses current CLI session.

    Returns:
        Dictionary with context display data containing:
        - system_prompt: Breakdown of prompt sections with token counts
        - memories: Available memories with display limit info
        - session_history: Bounded preview of session messages with displayed/total counts
        - tool_calls: Compact derived tool outcomes from the session
        - total_tokens: Estimated total context size
    """
    logger.debug("get_context_display: gathering context for session=%s", session_id or "cli")

    # Get disabled sections before loading
    disabled_sections = alfred.context_loader.get_disabled_sections()
    logger.debug("get_context_display: disabled sections: %s", disabled_sections)

    # Load context files (this will exclude disabled sections)
    context_files = await alfred.context_loader.load_all()
    logger.debug("get_context_display: loaded %d context files", len(context_files))

    conflicted_context_files = [
        {
            "id": _context_file_identifier(file),
            "name": _context_file_identifier(file),
            "label": _context_file_name(file),
            "reason": getattr(file, "blocked_reason", None) or "Blocked context file",
        }
        for file in context_files.values()
        if getattr(file, "is_blocked", lambda: False)()
    ]
    if conflicted_context_files:
        logger.debug("get_context_display: found %d conflicted context files", len(conflicted_context_files))

    blocked_context_files = [file["label"] for file in conflicted_context_files]

    warnings = []

    # Add warning about disabled sections
    if disabled_sections:
        warnings.append(f"Disabled sections: {', '.join(disabled_sections)}")

    # Build system prompt sections with token counts
    system_sections = []
    total_system_tokens = 0
    for section_id in SYSTEM_PROMPT_SECTION_ORDER:
        file = context_files.get(section_id)
        if file is None or getattr(file, "is_blocked", lambda: False)():
            continue

        label = SYSTEM_PROMPT_SECTION_LABELS.get(section_id, f"{section_id.upper()}.md")
        tokens = _estimate_tokens(file.content)
        system_sections.append(
            {
                "id": section_id,
                "name": label,
                "label": label,
                "tokens": tokens,
            }
        )
        total_system_tokens += tokens

    # Get all memories
    all_memories = await alfred.core.memory_store.get_all_entries()

    # Get session messages for display
    session_manager = alfred.core.session_manager
    session_messages = session_manager.get_messages_for_context(session_id)
    if session_id is not None:
        full_messages = session_manager.get_session_messages(session_id)
    elif session_manager.has_active_session():
        full_messages = session_manager.get_session_messages()
    else:
        full_messages = []

    display_messages = [
        {"role": role, "content": content}
        for role, content in session_messages[-5:]  # Last 5 messages
    ]
    session_displayed_tokens = sum(_estimate_tokens(message["content"]) for message in display_messages)
    session_included_tokens = sum(_estimate_tokens(content) for _, content in session_messages)

    # Collect all tool calls from the session for display. These are separate from the
    # compact prompt-context tool outcomes and are allowed to show raw details.
    tool_call_records: list[Any] = []
    for message in full_messages:
        message_tool_calls = getattr(message, "tool_calls", None) or []
        tool_call_records.extend(message_tool_calls)

    tool_call_items = []
    tool_call_tokens = 0
    workspace_dir = getattr(getattr(alfred.context_loader, "config", None), "workspace_dir", None)
    for tool_call in tool_call_records:
        outcome = summarize_tool_call_record(
            tool_call,
            workspace_dir=workspace_dir,
            max_output_chars=120,
        )
        tool_call_tokens += outcome.tokens
        tool_call_items.append(
            {
                "tool_name": outcome.tool_name,
                "summary": outcome.summary,
                "tokens": outcome.tokens,
                "status": getattr(tool_call, "status", "success"),
                "arguments": getattr(tool_call, "arguments", {}) or {},
                "output": getattr(tool_call, "output", "") or "",
                "tool_call_id": getattr(tool_call, "tool_call_id", ""),
                "sequence": getattr(tool_call, "sequence", 0),
            }
        )

    total_tool_calls = len(tool_call_items)

    # Format all memories with full content (no truncation)
    memory_display = []
    memory_tokens = 0
    for mem in all_memories:
        content = getattr(mem, "content", "") or ""
        memory_tokens += _estimate_tokens(content)
        memory_display.append(
            {
                "content": content,
                "preview": _preview_text(content, 140),
                "role": mem.role,
                "timestamp": mem.timestamp.isoformat()[:10],  # Just date
                "tokens": _estimate_tokens(content),
            }
        )

    # Get self-model for display
    logger.debug("get_context_display: building self-model for context display")
    self_model = alfred.build_self_model()
    logger.debug(
        "get_context_display: self-model ready - interface=%s, tools=%d, memories=%d, messages=%d",
        self_model.runtime.interface.value if self_model.runtime.interface else None,
        len(self_model.capabilities.tools_available),
        self_model.context_pressure.memory_count,
        self_model.context_pressure.message_count,
    )
    self_model_display = {
        "identity": {
            "name": self_model.identity.name,
            "role": self_model.identity.role,
        },
        "runtime": {
            "interface": self_model.runtime.interface.value if self_model.runtime.interface else "unknown",
            "session_id": self_model.runtime.session_id,
            "daemon_mode": self_model.runtime.daemon_mode,
        },
        "capabilities": {
            "memory_enabled": self_model.capabilities.memory_enabled,
            "search_enabled": self_model.capabilities.search_enabled,
            "tools_count": len(self_model.capabilities.tools_available),
            "tools": self_model.capabilities.tools_available[:5],  # First 5 tools
        },
        "context_pressure": {
            "message_count": self_model.context_pressure.message_count,
            "memory_count": self_model.context_pressure.memory_count,
            "approximate_tokens": self_model.context_pressure.approximate_tokens,
        },
    }

    total_tokens = total_system_tokens + memory_tokens + session_included_tokens + tool_call_tokens

    logger.debug(
        "get_context_display: complete - system_tokens=%d, memory_tokens=%d, session_tokens=%d, tool_tokens=%d, total=%d",
        total_system_tokens,
        memory_tokens,
        session_included_tokens,
        tool_call_tokens,
        total_tokens,
    )

    session_displayed = len(display_messages)
    session_total = len(full_messages)

    return {
        "system_prompt": {
            "sections": system_sections,
            "total_tokens": total_system_tokens,
        },
        "blocked_context_files": blocked_context_files,
        "conflicted_context_files": conflicted_context_files,
        "disabled_sections": disabled_sections,
        "warnings": warnings,
        "memories": {
            "displayed": len(memory_display),
            "total": len(all_memories),
            "items": memory_display,
            "tokens": memory_tokens,
            "displayed_tokens": memory_tokens,
            "all_shown": len(memory_display) == len(all_memories),
        },
        "session_history": {
            "count": session_displayed,
            "displayed": session_displayed,
            "included": len(session_messages),
            "total": session_total,
            "messages": display_messages,
            "displayed_tokens": session_displayed_tokens,
            "included_tokens": session_included_tokens,
            "tokens": session_included_tokens,
        },
        "tool_calls": {
            "count": len(tool_call_items),
            "displayed": len(tool_call_items),
            "total": total_tool_calls,
            "items": tool_call_items,
            "tokens": tool_call_tokens,
            "displayed_tokens": tool_call_tokens,
            "all_shown": len(tool_call_items) == total_tool_calls,
        },
        "self_model": self_model_display,
        "total_tokens": total_tokens,
    }
