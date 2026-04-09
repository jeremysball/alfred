"""Context display formatting for /context command (PRD #101).

Provides functionality to gather and format system context information
for user inspection via the /context command.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from alfred.context import SYSTEM_PROMPT_SECTION_LABELS, SYSTEM_PROMPT_SECTION_ORDER
from alfred.context_outcomes import summarize_tool_call_record

if TYPE_CHECKING:
    from alfred.alfred import Alfred

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ContextConflictStatus:
    """Structured record for one blocked/conflicted context file."""

    id: str
    name: str
    label: str
    reason: str

    def to_payload(self) -> dict[str, str]:
        """Serialize to the existing JSON-friendly payload shape."""
        return {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class ContextStatus:
    """Typed snapshot of current context health for UI/status surfaces."""

    blocked_context_files: list[str] = field(default_factory=list)
    conflicted_context_files: list[ContextConflictStatus] = field(default_factory=list)
    disabled_sections: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_display_payload(self) -> dict[str, Any]:
        """Serialize to the snake_case /context payload shape."""
        return {
            "blocked_context_files": list(self.blocked_context_files),
            "conflicted_context_files": [item.to_payload() for item in self.conflicted_context_files],
            "disabled_sections": list(self.disabled_sections),
            "warnings": list(self.warnings),
        }

    def to_websocket_payload(self) -> dict[str, Any]:
        """Serialize to the camelCase status.update payload shape."""
        return {
            "blockedContextFiles": list(self.blocked_context_files),
            "conflictedContextFiles": [item.to_payload() for item in self.conflicted_context_files],
            "warnings": list(self.warnings),
        }


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


def _serialize_support_scope(scope: Any) -> dict[str, str]:
    """Serialize one support-profile scope for /context display."""
    scope_type = str(getattr(scope, "type", "unknown"))
    scope_id = str(getattr(scope, "id", "unknown"))
    return {
        "type": scope_type,
        "id": scope_id,
        "label": f"{scope_type}:{scope_id}",
    }


def _serialize_pattern_summary(pattern: Any) -> dict[str, Any]:
    """Serialize one compact pattern summary for /context display."""
    return {
        "pattern_id": str(getattr(pattern, "pattern_id", "")),
        "kind": str(getattr(pattern, "kind", "unknown")),
        "scope": _serialize_support_scope(getattr(pattern, "scope", None)),
        "status": str(getattr(pattern, "status", "unknown")),
        "claim": str(getattr(pattern, "claim", "")),
        "confidence": float(getattr(pattern, "confidence", 0.0)),
    }


def _serialize_update_event_summary(event: Any) -> dict[str, Any]:
    """Serialize one compact support-profile update event for /context display."""
    timestamp = getattr(event, "timestamp", None)
    return {
        "event_id": str(getattr(event, "event_id", "")),
        "registry": str(getattr(event, "registry", "unknown")),
        "dimension": str(getattr(event, "dimension", "unknown")),
        "scope": _serialize_support_scope(getattr(event, "scope", None)),
        "status": str(getattr(event, "status", "unknown")),
        "old_value": getattr(event, "old_value", None),
        "new_value": str(getattr(event, "new_value", "")),
        "reason": str(getattr(event, "reason", "")),
        "confidence": float(getattr(event, "confidence", 0.0)),
        "timestamp": timestamp.isoformat() if timestamp is not None else None,
    }


def _serialize_value_ledger_entry_summary(entry: Any) -> dict[str, Any]:
    """Serialize one v2 support value ledger entry summary for /context display."""
    updated_at = getattr(entry, "updated_at", None)
    return {
        "value_id": str(getattr(entry, "value_id", "")),
        "registry": str(getattr(entry, "registry", "unknown")),
        "dimension": str(getattr(entry, "dimension", "unknown")),
        "scope": _serialize_support_scope(getattr(entry, "scope", None)),
        "value": str(getattr(entry, "value", "")),
        "status": str(getattr(entry, "status", "unknown")),
        "confidence": float(getattr(entry, "confidence", 0.0)),
        "evidence_count": int(getattr(entry, "evidence_count", 0)),
        "contradiction_count": int(getattr(entry, "contradiction_count", 0)),
        "last_case_id": getattr(entry, "last_case_id", None),
        "updated_at": updated_at.isoformat() if updated_at is not None else None,
        "why": str(getattr(entry, "why", "")),
    }


def _serialize_ledger_update_event_summary(event: Any) -> dict[str, Any]:
    """Serialize one v2 support ledger update event summary for /context display."""
    created_at = getattr(event, "created_at", None)
    trigger_case_ids = getattr(event, "trigger_case_ids", ())
    return {
        "event_id": str(getattr(event, "event_id", "")),
        "entity_type": str(getattr(event, "entity_type", "unknown")),
        "entity_id": str(getattr(event, "entity_id", "")),
        "registry": str(getattr(event, "registry", "unknown")),
        "dimension_or_kind": str(getattr(event, "dimension_or_kind", "unknown")),
        "scope": _serialize_support_scope(getattr(event, "scope", None)),
        "old_status": getattr(event, "old_status", None),
        "new_status": str(getattr(event, "new_status", "unknown")),
        "old_value": getattr(event, "old_value", None),
        "new_value": getattr(event, "new_value", None),
        "trigger_case_ids": [str(item) for item in trigger_case_ids] if trigger_case_ids else [],
        "reason": str(getattr(event, "reason", "")),
        "confidence": float(getattr(event, "confidence", 0.0)),
        "created_at": created_at.isoformat() if created_at is not None else None,
    }


def _serialize_learning_situation_summary(situation: Any) -> dict[str, Any]:
    """Serialize one recent learning-situation summary for /context display."""
    recorded_at = getattr(situation, "recorded_at", None)
    return {
        "situation_id": str(getattr(situation, "situation_id", "")),
        "session_id": str(getattr(situation, "session_id", "")),
        "response_mode": str(getattr(situation, "response_mode", "unknown")),
        "intervention_family": str(getattr(situation, "intervention_family", "unknown")),
        "behavior_contract_summary": str(getattr(situation, "behavior_contract_summary", "")),
        "recorded_at": recorded_at.isoformat() if recorded_at is not None else None,
    }


def _serialize_active_domain(domain: Any) -> dict[str, Any]:
    """Serialize one active life domain for /context display."""
    return {
        "domain_id": str(getattr(domain, "domain_id", "")),
        "name": str(getattr(domain, "name", "")),
        "status": str(getattr(domain, "status", "unknown")),
        "salience": float(getattr(domain, "salience", 0.0)),
    }


def _serialize_active_arc(arc: Any) -> dict[str, Any]:
    """Serialize one active operational arc for /context display."""
    return {
        "arc_id": str(getattr(arc, "arc_id", "")),
        "title": str(getattr(arc, "title", "")),
        "kind": str(getattr(arc, "kind", "unknown")),
        "status": str(getattr(arc, "status", "unknown")),
        "salience": float(getattr(arc, "salience", 0.0)),
        "primary_domain_id": getattr(arc, "primary_domain_id", None),
    }


async def _get_support_state_display(alfred: Alfred) -> dict[str, Any]:
    """Build a compact support-state summary for /context when available."""
    runtime_getter = getattr(alfred, "_get_support_reflection_runtime", None)
    if not callable(runtime_getter):
        return {"enabled": False}

    runtime = runtime_getter()
    if runtime is None:
        return {"enabled": False}

    build_snapshot = getattr(runtime, "build_inspection_snapshot", None)
    if not callable(build_snapshot):
        return {"enabled": False}

    try:
        snapshot = await build_snapshot(response_mode="execute", arc_id=None)
    except Exception as exc:  # pragma: no cover - defensive fallback for live runtime inspection
        logger.exception("get_context_display: failed to build support inspection snapshot")
        return {
            "enabled": False,
            "error": str(exc),
        }

    request = {
        "response_mode": str(getattr(getattr(snapshot, "request", None), "response_mode", "execute")),
        "arc_id": getattr(getattr(snapshot, "request", None), "arc_id", None),
    }

    active_patterns = [
        _serialize_pattern_summary(pattern)
        for pattern in getattr(getattr(snapshot, "active_runtime_state", None), "active_patterns", ())
    ]
    candidate_patterns = [
        _serialize_pattern_summary(pattern)
        for pattern in getattr(getattr(snapshot, "learned_state", None), "candidate_patterns", ())
    ]
    confirmed_patterns = [
        _serialize_pattern_summary(pattern)
        for pattern in getattr(getattr(snapshot, "learned_state", None), "confirmed_patterns", ())
    ]
    learned_state = getattr(snapshot, "learned_state", None)

    recent_update_events = [_serialize_update_event_summary(event) for event in getattr(learned_state, "recent_update_events", ())]

    value_ledger_entries = [
        _serialize_value_ledger_entry_summary(entry)
        for entry in getattr(learned_state, "value_ledger_entries", ())
    ]

    raw_value_ledger_summary = getattr(learned_state, "value_ledger_summary", None)
    if isinstance(raw_value_ledger_summary, dict):
        value_ledger_summary = {
            "total": int(raw_value_ledger_summary.get("total", 0)),
            "counts_by_status": dict(raw_value_ledger_summary.get("counts_by_status", {})),
            "counts_by_registry": dict(raw_value_ledger_summary.get("counts_by_registry", {})),
        }
    else:
        value_ledger_summary = {
            "total": 0,
            "counts_by_status": {},
            "counts_by_registry": {},
        }

    recent_ledger_update_events = [
        _serialize_ledger_update_event_summary(event)
        for event in getattr(learned_state, "recent_ledger_update_events", ())
    ]

    recent_interventions = [
        _serialize_learning_situation_summary(situation)
        for situation in getattr(learned_state, "recent_interventions", ())
    ]
    active_domains = [_serialize_active_domain(domain) for domain in getattr(snapshot, "active_domains", ())]
    active_arcs = [_serialize_active_arc(arc) for arc in getattr(snapshot, "active_arcs", ())]

    summary_active_arc_id = getattr(getattr(snapshot, "active_runtime_state", None), "active_arc_id", None)
    if summary_active_arc_id is None and active_arcs:
        summary_active_arc_id = active_arcs[0]["arc_id"]

    return {
        "enabled": True,
        "request": request,
        "summary": {
            "response_mode": request["response_mode"],
            "active_arc_id": summary_active_arc_id,
            "active_pattern_count": len(active_patterns),
            "candidate_pattern_count": len(candidate_patterns),
            "confirmed_pattern_count": len(confirmed_patterns),
            "recent_update_event_count": len(recent_update_events),
            "recent_intervention_count": len(recent_interventions),
            "active_domain_count": len(active_domains),
            "active_arc_count": len(active_arcs),
        },
        "active_runtime_state": {
            "response_mode": str(getattr(getattr(snapshot, "active_runtime_state", None), "response_mode", request["response_mode"])),
            "active_arc_id": getattr(getattr(snapshot, "active_runtime_state", None), "active_arc_id", None),
            "effective_support_values": dict(getattr(getattr(snapshot, "active_runtime_state", None), "effective_support_values", {})),
            "effective_relational_values": dict(
                getattr(getattr(snapshot, "active_runtime_state", None), "effective_relational_values", {})
            ),
            "active_patterns": active_patterns,
        },
        "learned_state": {
            "candidate_patterns_count": len(candidate_patterns),
            "confirmed_patterns_count": len(confirmed_patterns),
            "recent_update_event_count": len(recent_update_events),
            "recent_intervention_count": len(recent_interventions),
            "candidate_patterns": candidate_patterns,
            "confirmed_patterns": confirmed_patterns,
            "recent_update_events": recent_update_events,
            "value_ledger_entries": value_ledger_entries,
            "value_ledger_summary": value_ledger_summary,
            "recent_ledger_update_events": recent_ledger_update_events,
            "recent_interventions": recent_interventions,
        },
        "active_domains": active_domains,
        "active_arcs": active_arcs,
    }


def _build_context_status(
    context_files: dict[str, Any],
    disabled_sections: list[str],
) -> ContextStatus:
    """Build the shared blocked/conflicted context status snapshot."""
    conflicted_context_files = [
        ContextConflictStatus(
            id=_context_file_identifier(file),
            name=_context_file_identifier(file),
            label=_context_file_name(file),
            reason=getattr(file, "blocked_reason", None) or "Blocked context file",
        )
        for file in context_files.values()
        if getattr(file, "is_blocked", lambda: False)()
    ]
    if conflicted_context_files:
        logger.debug("context_status: found %d conflicted context files", len(conflicted_context_files))

    warnings: list[str] = []
    if disabled_sections:
        warnings.append(f"Disabled sections: {', '.join(disabled_sections)}")

    return ContextStatus(
        blocked_context_files=[file.label for file in conflicted_context_files],
        conflicted_context_files=conflicted_context_files,
        disabled_sections=list(disabled_sections),
        warnings=warnings,
    )


async def get_context_status(alfred: Alfred) -> ContextStatus:
    """Get the lightweight context-health snapshot used by Web UI status updates."""
    logger.debug("get_context_status: gathering current context health")
    disabled_sections = alfred.context_loader.get_disabled_sections()
    context_files = await alfred.context_loader.load_all()
    logger.debug("get_context_status: loaded %d context files", len(context_files))
    return _build_context_status(context_files, disabled_sections)


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
        - self_model: Compact runtime self-model snapshot
        - support_state: Compact support runtime snapshot when available
        - total_tokens: Estimated total context size
    """
    logger.debug("get_context_display: gathering context for session=%s", session_id or "cli")

    disabled_sections = alfred.context_loader.get_disabled_sections()
    logger.debug("get_context_display: disabled sections: %s", disabled_sections)

    context_files = await alfred.context_loader.load_all()
    logger.debug("get_context_display: loaded %d context files", len(context_files))

    context_status = _build_context_status(context_files, disabled_sections)
    blocked_context_files = list(context_status.blocked_context_files)
    conflicted_context_files = [item.to_payload() for item in context_status.conflicted_context_files]
    warnings = list(context_status.warnings)

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

    all_memories = await alfred.core.memory_store.get_all_entries()

    session_manager = alfred.core.session_manager
    session_messages = session_manager.get_messages_for_context(session_id)
    if session_id is not None:
        full_messages = session_manager.get_session_messages(session_id)
    elif session_manager.has_active_session():
        full_messages = session_manager.get_session_messages()
    else:
        full_messages = []

    display_messages = [{"role": role, "content": content} for role, content in session_messages[-5:]]
    session_displayed_tokens = sum(_estimate_tokens(message["content"]) for message in display_messages)
    session_included_tokens = sum(_estimate_tokens(content) for _, content in session_messages)

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
                "timestamp": mem.timestamp.isoformat()[:10],
                "tokens": _estimate_tokens(content),
            }
        )

    support_state = await _get_support_state_display(alfred)
    support_error = support_state.get("error")
    if isinstance(support_error, str) and support_error:
        warnings.append(f"Support state unavailable: {support_error}")

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
            "tools": self_model.capabilities.tools_available[:5],
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
        "support_state": support_state,
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
