"""Context display formatting for /context command (PRD #101).

Provides functionality to gather and format system context information
for user inspection via the /context command.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from alfred.alfred import Alfred

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    """Estimate token count from character count (4 chars ≈ 1 token)."""
    return len(text) // 4


def _context_file_name(file: Any) -> str:
    """Return a human-readable filename for a loaded context file."""
    path = getattr(file, "path", None)
    if path:
        return Path(str(path)).name
    name = getattr(file, "name", "")
    return f"{name}.md" if name and not str(name).endswith(".md") else str(name)


async def get_context_display(alfred: "Alfred", session_id: str | None = None) -> dict[str, Any]:
    """Get current context information for /context command.

    Args:
        alfred: The Alfred instance to gather context from
        session_id: Optional session ID. If None, uses current CLI session.

    Returns:
        Dictionary with context display data containing:
        - system_prompt: Breakdown of prompt sections with token counts
        - memories: Available memories with display limit info
        - session_history: Recent session messages
        - tool_calls: Recent tool calls from the session
        - total_tokens: Estimated total context size
    """
    logger.debug("get_context_display: gathering context for session=%s", session_id or "cli")

    # Get disabled sections before loading
    disabled_sections = alfred.context_loader.get_disabled_sections()
    logger.debug("get_context_display: disabled sections: %s", disabled_sections)

    # Load context files (this will exclude disabled sections)
    context_files = await alfred.context_loader.load_all()
    logger.debug("get_context_display: loaded %d context files", len(context_files))

    blocked_context_files = [_context_file_name(file) for file in context_files.values() if getattr(file, "is_blocked", lambda: False)()]
    if blocked_context_files:
        logger.debug("get_context_display: found %d blocked context files", len(blocked_context_files))

    warnings = [f"Blocked context files: {', '.join(blocked_context_files)}"] if blocked_context_files else []

    # Add warning about disabled sections
    if disabled_sections:
        warnings.append(f"Disabled sections: {', '.join(disabled_sections)}")

    # Build system prompt sections with token counts
    system_sections = []
    total_system_tokens = 0
    for name in ["agents", "soul", "user", "tools"]:
        file = context_files.get(name)
        if file is None or getattr(file, "is_blocked", lambda: False)():
            continue

        content = file.content
        tokens = _estimate_tokens(content)
        system_sections.append(
            {
                "name": name.upper() + ".md",
                "tokens": tokens,
            }
        )
        total_system_tokens += tokens

    # Get all memories
    all_memories = await alfred.core.memory_store.get_all_entries()

    # Get session messages for display
    session_messages = alfred.core.session_manager.get_messages_for_context(session_id)
    full_messages = alfred.core.session_manager.get_session_messages(session_id) if alfred.core.session_manager.has_active_session() else []

    # Get recent tool calls from session
    recent_tool_calls: list[dict[str, Any]] = []
    tool_call_tokens = 0
    for msg in full_messages:
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tc_data = {
                    "tool_name": tc.tool_name,
                    "arguments": tc.arguments,
                    "output": tc.output[:200] + "..." if len(tc.output) > 200 else tc.output,
                    "status": tc.status,
                }
                recent_tool_calls.append(tc_data)
                tool_call_tokens += _estimate_tokens(str(tc_data))

    # Limit to last 3 tool calls
    recent_tool_calls = recent_tool_calls[-3:]

    # Format session messages for display
    display_messages = [
        {"role": role, "content": content[:200] + "..." if len(content) > 200 else content}
        for role, content in session_messages[-5:]  # Last 5 messages
    ]

    session_tokens = sum(_estimate_tokens(m["content"]) for m in display_messages)

    # Format all memories with full content (no truncation)
    memory_display = []
    for mem in all_memories:
        memory_display.append(
            {
                "content": mem.content,
                "role": mem.role,
                "timestamp": mem.timestamp.isoformat()[:10],  # Just date
            }
        )

    memory_tokens = sum(_estimate_tokens(m.content) for m in all_memories)

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

    total_tokens = total_system_tokens + memory_tokens + session_tokens + tool_call_tokens

    logger.debug(
        "get_context_display: complete - system_tokens=%d, memory_tokens=%d, session_tokens=%d, tool_tokens=%d, total=%d",
        total_system_tokens,
        memory_tokens,
        session_tokens,
        tool_call_tokens,
        total_tokens,
    )

    return {
        "system_prompt": {
            "sections": system_sections,
            "total_tokens": total_system_tokens,
        },
        "blocked_context_files": blocked_context_files,
        "disabled_sections": disabled_sections,
        "warnings": warnings,
        "memories": {
            "displayed": len(memory_display),
            "total": len(all_memories),
            "items": memory_display,
            "tokens": memory_tokens,
            "all_shown": len(memory_display) == len(all_memories),
        },
        "session_history": {
            "count": len(display_messages),
            "messages": display_messages,
            "tokens": session_tokens,
        },
        "tool_calls": {
            "count": len(recent_tool_calls),
            "items": recent_tool_calls,
            "tokens": tool_call_tokens,
        },
        "self_model": self_model_display,
        "total_tokens": total_tokens,
    }
