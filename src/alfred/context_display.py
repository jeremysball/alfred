"""Context display formatting for /context command (PRD #101).

Provides functionality to gather and format system context information
for user inspection via the /context command.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from alfred.alfred import Alfred


def _estimate_tokens(text: str) -> int:
    """Estimate token count from character count (4 chars ≈ 1 token)."""
    return len(text) // 4


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
    # Load context files
    context_files = await alfred.context_loader.load_all()

    # Build system prompt sections with token counts
    system_sections = []
    total_system_tokens = 0
    for name in ["agents", "soul", "user", "tools"]:
        if name in context_files:
            content = context_files[name].content
            tokens = _estimate_tokens(content)
            system_sections.append(
                {
                    "name": name.upper() + ".md",
                    "tokens": tokens,
                }
            )
            total_system_tokens += tokens

    # Get all memories
    all_memories = await alfred.memory_store.get_all_entries()

    # Get session messages for display
    session_messages = alfred.session_manager.get_messages_for_context(session_id)
    full_messages = (
        alfred.session_manager.get_session_messages(session_id)
        if alfred.session_manager.has_active_session()
        else []
    )

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

    # Format memories - show first 5 with counts
    memory_display = []
    for mem in all_memories[:5]:
        memory_display.append(
            {
                "content": mem.content[:100] + "..." if len(mem.content) > 100 else mem.content,
                "role": mem.role,
                "timestamp": mem.timestamp.isoformat()[:10],  # Just date
            }
        )

    memory_tokens = sum(_estimate_tokens(m.content) for m in all_memories[:5])

    total_tokens = total_system_tokens + memory_tokens + session_tokens + tool_call_tokens

    return {
        "system_prompt": {
            "sections": system_sections,
            "total_tokens": total_system_tokens,
        },
        "memories": {
            "displayed": len(memory_display),
            "total": len(all_memories),
            "items": memory_display,
            "tokens": memory_tokens,
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
        "total_tokens": total_tokens,
    }
