"""Tests for shared /context display data."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from alfred.context import ContextFile, ContextFileState
from alfred.context_display import get_context_display


@pytest.mark.asyncio
async def test_get_context_display_reports_blocked_context_warning_and_omits_blocked_sections() -> None:
    """Blocked managed context files should be omitted from the summary and warned about explicitly."""
    active_agents = ContextFile(
        name="agents",
        path="/workspace/alfred/AGENTS.md",
        content="Agents body",
        last_modified=datetime(2026, 3, 23, tzinfo=UTC),
        state=ContextFileState.ACTIVE,
    )
    blocked_soul = ContextFile(
        name="soul",
        path="/workspace/alfred/SOUL.md",
        content="",
        last_modified=datetime(2026, 3, 23, tzinfo=UTC),
        state=ContextFileState.BLOCKED,
        blocked_reason="Conflicted managed template SOUL.md is blocked",
    )
    active_user = ContextFile(
        name="user",
        path="/workspace/alfred/USER.md",
        content="User body",
        last_modified=datetime(2026, 3, 23, tzinfo=UTC),
        state=ContextFileState.ACTIVE,
    )

    fake_context_loader = SimpleNamespace(
        load_all=AsyncMock(
            return_value={
                "agents": active_agents,
                "soul": blocked_soul,
                "user": active_user,
            }
        )
    )
    fake_session_manager = SimpleNamespace(
        has_active_session=lambda: False,
        get_messages_for_context=lambda session_id=None: [],
        get_session_messages=lambda session_id=None: [],
    )
    fake_memory_store = SimpleNamespace(get_all_entries=AsyncMock(return_value=[]))
    fake_alfred = SimpleNamespace(
        context_loader=fake_context_loader,
        core=SimpleNamespace(memory_store=fake_memory_store, session_manager=fake_session_manager),
    )

    result = await get_context_display(fake_alfred)

    assert result["blocked_context_files"] == ["SOUL.md"]
    assert result["warnings"] == ["Blocked context files: SOUL.md"]

    sections = result["system_prompt"]["sections"]
    section_names = [section["name"] for section in sections]
    assert section_names == ["AGENTS.md", "USER.md"]
    assert "SOUL.md" not in section_names
    assert result["system_prompt"]["total_tokens"] == sum(section["tokens"] for section in sections)
