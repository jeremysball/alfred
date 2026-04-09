"""Tests for shared /context display data."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from alfred.context import ContextFile, ContextFileState
from alfred.context_display import get_context_display


@pytest.mark.asyncio
async def test_get_context_display_reports_conflicted_context_files_and_omits_blocked_sections() -> None:
    """Blocked managed context files should be omitted from the summary and surfaced as structured conflicts."""
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
        ),
        get_disabled_sections=lambda: [],
    )
    fake_session_manager = SimpleNamespace(
        has_active_session=lambda: False,
        get_messages_for_context=lambda session_id=None: [],
        get_session_messages=lambda session_id=None: [],
    )
    fake_memory_store = SimpleNamespace(get_all_entries=AsyncMock(return_value=[]))

    # Create a minimal self-model for the fake
    from alfred.self_model import (
        Capabilities,
        ContextPressure,
        Identity,
        InterfaceType,
        Runtime,
        RuntimeSelfModel,
        World,
    )

    fake_self_model = RuntimeSelfModel(
        identity=Identity(),
        runtime=Runtime(interface=InterfaceType.CLI),
        world=World(),
        capabilities=Capabilities(),
        context_pressure=ContextPressure(),
    )

    fake_alfred = SimpleNamespace(
        context_loader=fake_context_loader,
        core=SimpleNamespace(memory_store=fake_memory_store, session_manager=fake_session_manager),
        build_self_model=lambda: fake_self_model,
    )

    result = await get_context_display(fake_alfred)

    assert result["blocked_context_files"] == ["SOUL.md"]
    assert result["conflicted_context_files"] == [
        {
            "id": "soul",
            "name": "soul",
            "label": "SOUL.md",
            "reason": "Conflicted managed template SOUL.md is blocked",
        }
    ]
    assert result["warnings"] == []

    sections = result["system_prompt"]["sections"]
    section_names = [section["name"] for section in sections]
    assert section_names == ["AGENTS.md", "USER.md"]
    assert "SOUL.md" not in section_names
    assert result["system_prompt"]["total_tokens"] == sum(section["tokens"] for section in sections)


@pytest.mark.asyncio
async def test_get_context_display_includes_system_md_and_matches_prompt_order() -> None:
    """System prompt sections should include SYSTEM.md and follow prompt assembly order."""

    active_system = ContextFile(
        name="system",
        path="/workspace/alfred/SYSTEM.md",
        content="System body",
        last_modified=datetime(2026, 3, 23, tzinfo=UTC),
        state=ContextFileState.ACTIVE,
    )
    active_agents = ContextFile(
        name="agents",
        path="/workspace/alfred/AGENTS.md",
        content="Agents body",
        last_modified=datetime(2026, 3, 23, tzinfo=UTC),
        state=ContextFileState.ACTIVE,
    )
    active_tools = ContextFile(
        name="tools",
        path="/workspace/alfred/TOOLS.md",
        content="Tools body",
        last_modified=datetime(2026, 3, 23, tzinfo=UTC),
        state=ContextFileState.ACTIVE,
    )
    active_soul = ContextFile(
        name="soul",
        path="/workspace/alfred/SOUL.md",
        content="Soul body",
        last_modified=datetime(2026, 3, 23, tzinfo=UTC),
        state=ContextFileState.ACTIVE,
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
                "system": active_system,
                "agents": active_agents,
                "tools": active_tools,
                "soul": active_soul,
                "user": active_user,
            }
        ),
        get_disabled_sections=lambda: [],
    )
    fake_session_manager = SimpleNamespace(
        has_active_session=lambda: False,
        get_messages_for_context=lambda session_id=None: [],
        get_session_messages=lambda session_id=None: [],
    )
    fake_memory_store = SimpleNamespace(get_all_entries=AsyncMock(return_value=[]))

    from alfred.self_model import (
        Capabilities,
        ContextPressure,
        Identity,
        InterfaceType,
        Runtime,
        RuntimeSelfModel,
        World,
    )

    fake_self_model = RuntimeSelfModel(
        identity=Identity(),
        runtime=Runtime(interface=InterfaceType.CLI),
        world=World(),
        capabilities=Capabilities(),
        context_pressure=ContextPressure(),
    )

    fake_alfred = SimpleNamespace(
        context_loader=fake_context_loader,
        core=SimpleNamespace(memory_store=fake_memory_store, session_manager=fake_session_manager),
        build_self_model=lambda: fake_self_model,
    )

    result = await get_context_display(fake_alfred)

    sections = result["system_prompt"]["sections"]
    assert [section["id"] for section in sections] == ["system", "agents", "tools", "soul", "user"]
    assert [section["label"] for section in sections] == ["SYSTEM.md", "AGENTS.md", "TOOLS.md", "SOUL.md", "USER.md"]
    assert [section["name"] for section in sections] == ["SYSTEM.md", "AGENTS.md", "TOOLS.md", "SOUL.md", "USER.md"]
    assert result["system_prompt"]["total_tokens"] == sum(section["tokens"] for section in sections)


@pytest.mark.asyncio
async def test_get_context_display_reports_session_history_preview_and_total() -> None:
    """Session history should distinguish previewed messages from total messages."""

    preview_messages = [("user", f"Preview {index}") for index in range(8)]
    full_messages = [SimpleNamespace(tool_calls=None) for _ in range(9)]

    fake_context_loader = SimpleNamespace(
        load_all=AsyncMock(return_value={}),
        get_disabled_sections=lambda: [],
    )
    fake_session_manager = SimpleNamespace(
        has_active_session=lambda: False,
        get_messages_for_context=lambda session_id=None: preview_messages,
        get_session_messages=lambda session_id=None: full_messages,
    )
    fake_memory_store = SimpleNamespace(get_all_entries=AsyncMock(return_value=[]))

    from alfred.self_model import (
        Capabilities,
        ContextPressure,
        Identity,
        InterfaceType,
        Runtime,
        RuntimeSelfModel,
        World,
    )

    fake_self_model = RuntimeSelfModel(
        identity=Identity(),
        runtime=Runtime(interface=InterfaceType.CLI),
        world=World(),
        capabilities=Capabilities(),
        context_pressure=ContextPressure(),
    )

    fake_alfred = SimpleNamespace(
        context_loader=fake_context_loader,
        core=SimpleNamespace(memory_store=fake_memory_store, session_manager=fake_session_manager),
        build_self_model=lambda: fake_self_model,
    )

    result = await get_context_display(fake_alfred, session_id="session-123")

    session_history = result["session_history"]
    assert session_history["displayed"] == 5
    assert session_history["included"] == 8
    assert session_history["total"] == 9
    assert len(session_history["messages"]) == 5
    assert session_history["displayed_tokens"] == sum(len(content) // 4 for _, content in preview_messages[-5:])
    assert session_history["included_tokens"] == sum(len(content) // 4 for _, content in preview_messages)
    assert session_history["tokens"] == session_history["included_tokens"]
    assert session_history["displayed_tokens"] < session_history["included_tokens"]
    assert [message["content"] for message in session_history["messages"]] == [
        "Preview 3",
        "Preview 4",
        "Preview 5",
        "Preview 6",
        "Preview 7",
    ]


@pytest.mark.asyncio
async def test_get_context_display_reports_compact_tool_outcomes() -> None:
    """Tool activity should be summarized compactly with preview and total counts."""

    workspace_dir = Path("/workspace/alfred-prd")
    tool_messages = [
        SimpleNamespace(
            tool_calls=[
                SimpleNamespace(
                    tool_name="read",
                    arguments={"path": str(workspace_dir / "docs" / "roadmap.md")},
                    output="roadmap contents",
                    status="success",
                ),
            ]
        ),
        SimpleNamespace(
            tool_calls=[
                SimpleNamespace(
                    tool_name="bash",
                    arguments={"command": "python -V"},
                    output="x" * 300,
                    status="success",
                ),
            ]
        ),
        SimpleNamespace(
            tool_calls=[
                SimpleNamespace(
                    tool_name="edit",
                    arguments={"path": str(workspace_dir / "src" / "module.py")},
                    output="updated file",
                    status="success",
                ),
            ]
        ),
        SimpleNamespace(
            tool_calls=[
                SimpleNamespace(
                    tool_name="write",
                    arguments={"path": str(workspace_dir / "tests" / "module_test.py")},
                    output="created file",
                    status="success",
                ),
            ]
        ),
    ]

    fake_context_loader = SimpleNamespace(
        load_all=AsyncMock(return_value={}),
        get_disabled_sections=lambda: [],
        config=SimpleNamespace(workspace_dir=workspace_dir),
    )
    fake_session_manager = SimpleNamespace(
        has_active_session=lambda: False,
        get_messages_for_context=lambda session_id=None: [],
        get_session_messages=lambda session_id=None: tool_messages,
    )
    fake_memory_store = SimpleNamespace(get_all_entries=AsyncMock(return_value=[]))

    from alfred.self_model import (
        Capabilities,
        ContextPressure,
        Identity,
        InterfaceType,
        Runtime,
        RuntimeSelfModel,
        World,
    )

    fake_self_model = RuntimeSelfModel(
        identity=Identity(),
        runtime=Runtime(interface=InterfaceType.CLI),
        world=World(),
        capabilities=Capabilities(),
        context_pressure=ContextPressure(),
    )

    fake_alfred = SimpleNamespace(
        context_loader=fake_context_loader,
        core=SimpleNamespace(memory_store=fake_memory_store, session_manager=fake_session_manager),
        build_self_model=lambda: fake_self_model,
    )

    result = await get_context_display(fake_alfred, session_id="session-123")

    tool_calls = result["tool_calls"]
    assert tool_calls["count"] == 4
    assert tool_calls["displayed"] == 4
    assert tool_calls["total"] == 4
    assert tool_calls["all_shown"] is True
    assert tool_calls["tokens"] == sum(item["tokens"] for item in tool_calls["items"])
    assert [item["tool_name"] for item in tool_calls["items"]] == ["read", "bash", "edit", "write"]
    assert tool_calls["items"][0]["summary"] == "read: docs/roadmap.md"
    assert tool_calls["items"][0]["arguments"]["path"].endswith("docs/roadmap.md")
    assert tool_calls["items"][0]["output"] == "roadmap contents"
    assert tool_calls["items"][1]["summary"].startswith("bash: python -V exited 0")
    assert tool_calls["items"][1]["summary"].endswith("…")
    assert tool_calls["items"][1]["arguments"]["command"] == "python -V"
    assert tool_calls["items"][1]["output"] == "x" * 300
    assert tool_calls["items"][2]["summary"] == "edit: updated src/module.py"
    assert tool_calls["items"][2]["arguments"]["path"].endswith("src/module.py")
    assert tool_calls["items"][2]["output"] == "updated file"
    assert tool_calls["items"][3]["summary"] == "write: created tests/module_test.py"
    assert tool_calls["items"][3]["arguments"]["path"].endswith("tests/module_test.py")
    assert tool_calls["items"][3]["output"] == "created file"


@pytest.mark.asyncio
async def test_get_context_display_includes_self_model() -> None:
    """Verify self-model is included in context display with correct structure."""
    from alfred.self_model import (
        Capabilities,
        ContextPressure,
        Identity,
        InterfaceType,
        Runtime,
        RuntimeSelfModel,
        World,
    )

    # Create a self-model
    self_model = RuntimeSelfModel(
        identity=Identity(name="Alfred", role="assistant"),
        runtime=Runtime(interface=InterfaceType.CLI, session_id="test-session", daemon_mode=False),
        world=World(working_directory="/workspace", python_version="3.12.0", platform="Linux"),
        capabilities=Capabilities(
            tools_available=["read", "write", "bash"],
            memory_enabled=True,
            search_enabled=True,
        ),
        context_pressure=ContextPressure(
            message_count=5,
            memory_count=3,
            approximate_tokens=1500,
        ),
    )

    fake_context_loader = SimpleNamespace(
        load_all=AsyncMock(return_value={}),
        get_disabled_sections=lambda: [],
    )
    fake_session_manager = SimpleNamespace(
        has_active_session=lambda: False,
        get_messages_for_context=lambda session_id=None: [],
        get_session_messages=lambda session_id=None: [],
    )
    fake_memory_store = SimpleNamespace(get_all_entries=AsyncMock(return_value=[]))

    # Create fake Alfred with build_self_model method
    fake_alfred = SimpleNamespace(
        context_loader=fake_context_loader,
        core=SimpleNamespace(memory_store=fake_memory_store, session_manager=fake_session_manager),
        build_self_model=lambda: self_model,
    )

    result = await get_context_display(fake_alfred)

    # Verify self-model section exists
    assert "self_model" in result
    sm = result["self_model"]

    # Verify identity
    assert sm["identity"]["name"] == "Alfred"
    assert sm["identity"]["role"] == "assistant"

    # Verify runtime
    assert sm["runtime"]["interface"] == "cli"
    assert sm["runtime"]["session_id"] == "test-session"
    assert sm["runtime"]["daemon_mode"] is False

    # Verify capabilities
    assert sm["capabilities"]["memory_enabled"] is True
    assert sm["capabilities"]["search_enabled"] is True
    assert sm["capabilities"]["tools_count"] == 3
    assert "read" in sm["capabilities"]["tools"]

    # Verify context pressure
    assert sm["context_pressure"]["message_count"] == 5
    assert sm["context_pressure"]["memory_count"] == 3
    assert sm["context_pressure"]["approximate_tokens"] == 1500


@pytest.mark.asyncio
async def test_get_context_display_includes_support_state_summary() -> None:
    """/context data should expose the current support runtime snapshot when available."""

    now = datetime(2026, 3, 23, tzinfo=UTC)

    fake_context_loader = SimpleNamespace(
        load_all=AsyncMock(return_value={}),
        get_disabled_sections=lambda: [],
    )
    fake_session_manager = SimpleNamespace(
        has_active_session=lambda: False,
        get_messages_for_context=lambda session_id=None: [],
        get_session_messages=lambda session_id=None: [],
    )
    fake_memory_store = SimpleNamespace(get_all_entries=AsyncMock(return_value=[]))

    from alfred.self_model import (
        Capabilities,
        ContextPressure,
        Identity,
        InterfaceType,
        Runtime,
        RuntimeSelfModel,
        World,
    )

    fake_self_model = RuntimeSelfModel(
        identity=Identity(),
        runtime=Runtime(interface=InterfaceType.CLI),
        world=World(),
        capabilities=Capabilities(),
        context_pressure=ContextPressure(),
    )

    support_snapshot = SimpleNamespace(
        request=SimpleNamespace(response_mode="execute", arc_id="webui_cleanup"),
        active_runtime_state=SimpleNamespace(
            response_mode="execute",
            active_arc_id="webui_cleanup",
            effective_support_values={"pacing": "brisk", "planning_granularity": "minimal"},
            effective_relational_values={"warmth": "medium", "candor": "medium"},
            active_patterns=(
                SimpleNamespace(
                    pattern_id="pattern-runtime-1",
                    kind="support_preference",
                    scope=SimpleNamespace(type="arc", id="webui_cleanup"),
                    status="confirmed",
                    claim="Short next steps work better here.",
                    confidence=0.91,
                ),
            ),
        ),
        learned_state=SimpleNamespace(
            candidate_patterns=(
                SimpleNamespace(
                    pattern_id="pattern-candidate-1",
                    kind="recurring_blocker",
                    scope=SimpleNamespace(type="arc", id="webui_cleanup"),
                    status="candidate",
                    claim="Ambiguous scope repeatedly slows starts.",
                    confidence=0.74,
                ),
            ),
            confirmed_patterns=(
                SimpleNamespace(
                    pattern_id="pattern-confirmed-1",
                    kind="support_preference",
                    scope=SimpleNamespace(type="global", id="user"),
                    status="confirmed",
                    claim="A single next step works better than many options.",
                    confidence=0.95,
                ),
            ),
            recent_update_events=(
                SimpleNamespace(
                    event_id="event-1",
                    registry="support",
                    dimension="pacing",
                    scope=SimpleNamespace(type="arc", id="webui_cleanup"),
                    status="applied",
                    old_value="steady",
                    new_value="brisk",
                    reason="The narrower pace improved follow-through.",
                    confidence=0.88,
                    timestamp=now,
                ),
            ),
            recent_interventions=(
                SimpleNamespace(
                    situation_id="sit-1",
                    session_id="session-123",
                    response_mode="execute",
                    intervention_family="narrow",
                    behavior_contract_summary="One practical next step with firm pacing.",
                    recorded_at=now,
                ),
            ),
        ),
        active_domains=(
            SimpleNamespace(domain_id="work", name="Work", status="active", salience=0.92),
        ),
        active_arcs=(
            SimpleNamespace(
                arc_id="webui_cleanup",
                title="Web UI cleanup",
                kind="project",
                status="active",
                salience=0.97,
                primary_domain_id="work",
            ),
        ),
    )

    support_runtime = SimpleNamespace(build_inspection_snapshot=AsyncMock(return_value=support_snapshot))

    fake_alfred = SimpleNamespace(
        context_loader=fake_context_loader,
        core=SimpleNamespace(memory_store=fake_memory_store, session_manager=fake_session_manager),
        build_self_model=lambda: fake_self_model,
        _get_support_reflection_runtime=lambda: support_runtime,
    )

    result = await get_context_display(fake_alfred)

    support_state = result["support_state"]
    assert support_state["enabled"] is True
    assert support_state["request"] == {"response_mode": "execute", "arc_id": "webui_cleanup"}
    assert support_state["summary"] == {
        "response_mode": "execute",
        "active_arc_id": "webui_cleanup",
        "active_pattern_count": 1,
        "candidate_pattern_count": 1,
        "confirmed_pattern_count": 1,
        "recent_update_event_count": 1,
        "recent_intervention_count": 1,
        "active_domain_count": 1,
        "active_arc_count": 1,
    }
    assert support_state["active_runtime_state"]["effective_support_values"] == {
        "pacing": "brisk",
        "planning_granularity": "minimal",
    }
    assert support_state["active_runtime_state"]["effective_relational_values"] == {
        "warmth": "medium",
        "candor": "medium",
    }
    assert support_state["active_runtime_state"]["active_patterns"] == [
        {
            "pattern_id": "pattern-runtime-1",
            "kind": "support_preference",
            "scope": {"type": "arc", "id": "webui_cleanup", "label": "arc:webui_cleanup"},
            "status": "confirmed",
            "claim": "Short next steps work better here.",
            "confidence": 0.91,
        }
    ]
    assert support_state["learned_state"]["candidate_patterns_count"] == 1
    assert support_state["learned_state"]["confirmed_patterns_count"] == 1
    assert support_state["learned_state"]["recent_update_events"] == [
        {
            "event_id": "event-1",
            "registry": "support",
            "dimension": "pacing",
            "scope": {"type": "arc", "id": "webui_cleanup", "label": "arc:webui_cleanup"},
            "status": "applied",
            "old_value": "steady",
            "new_value": "brisk",
            "reason": "The narrower pace improved follow-through.",
            "confidence": 0.88,
            "timestamp": now.isoformat(),
        }
    ]
    assert support_state["learned_state"]["recent_interventions"] == [
        {
            "situation_id": "sit-1",
            "session_id": "session-123",
            "response_mode": "execute",
            "intervention_family": "narrow",
            "behavior_contract_summary": "One practical next step with firm pacing.",
            "recorded_at": now.isoformat(),
        }
    ]
    assert support_state["active_domains"] == [
        {
            "domain_id": "work",
            "name": "Work",
            "status": "active",
            "salience": 0.92,
        }
    ]
    assert support_state["active_arcs"] == [
        {
            "arc_id": "webui_cleanup",
            "title": "Web UI cleanup",
            "kind": "project",
            "status": "active",
            "salience": 0.97,
            "primary_domain_id": "work",
        }
    ]
