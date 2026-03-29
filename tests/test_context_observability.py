"""Context observability tests for Alfred context assembly logging."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest

from alfred.context import ContextBuilder, approximate_tokens
from alfred.memory import MemoryEntry
from alfred.session import Message, Role, ToolCallRecord


@dataclass
class FakeMemoryStore:
    """Minimal store fake that returns deterministic search results."""

    results: list[dict[str, Any]]
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def search_memories(self, query_embedding: list[float], top_k: int = 10) -> list[dict[str, Any]]:
        self.calls.append({"query_embedding": list(query_embedding), "top_k": top_k})
        return list(self.results)


def _make_memory(entry_id: str, content: str, *, role: str = "assistant") -> MemoryEntry:
    return MemoryEntry(
        entry_id=entry_id,
        content=content,
        timestamp=datetime.now(UTC),
        role=role,
    )


@pytest.mark.asyncio
async def test_context_builder_emits_compact_derived_tool_outcomes() -> None:
    """Tool history should be folded into session context as compact outcomes."""

    store = FakeMemoryStore(results=[])
    builder = ContextBuilder(store, memory_budget=4096)
    session_messages = [("user", "Please inspect the repository."), ("assistant", "I checked the repository.")]
    assistant_message = Message(
        idx=1,
        role=Role.ASSISTANT,
        content="I checked the repository.",
        tool_calls=[
            ToolCallRecord(
                tool_call_id="call-read",
                tool_name="read",
                arguments={"path": "src/alfred/context.py"},
                output="from alfred.context import ContextBuilder\nclass ContextBuilder:\n    pass\n",
                status="success",
            ),
            ToolCallRecord(
                tool_call_id="call-bash",
                tool_name="bash",
                arguments={"command": 'rg "ContextViewer" src'},
                output="found 6 matches\nextra noise that should not be rendered",
                status="success",
            ),
            ToolCallRecord(
                tool_call_id="call-edit",
                tool_name="edit",
                arguments={"path": "tests/webui/test_context_viewer.py"},
                output="updated tests/webui/test_context_viewer.py",
                status="success",
            ),
            ToolCallRecord(
                tool_call_id="call-write",
                tool_name="write",
                arguments={"path": "tests/webui/test_context_viewer.py"},
                output="created tests/webui/test_context_viewer.py",
                status="success",
            ),
        ],
    )

    context, included = await builder.build_context(
        query_embedding=[0.1, 0.2, 0.3],
        memories=[],
        system_prompt="## SYSTEM\n\nBase prompt",
        session_messages=session_messages,
        session_messages_with_tools=[assistant_message],
    )

    assert included == 0
    assert "## RECENT TOOL CALLS" not in context
    assert "arguments=" not in context
    assert "output=" not in context
    assert 'bash: rg "ContextViewer" src' in context
    assert "exited 0" in context
    assert "found 6 matches" in context
    assert "read: src/alfred/context.py" in context
    assert "edit: updated tests/webui/test_context_viewer.py" in context
    assert "write: created tests/webui/test_context_viewer.py" in context


@pytest.mark.asyncio
async def test_context_builder_trims_derived_tool_outcomes_when_budget_is_tight() -> None:
    """Tool outcomes should stay compact enough to survive a tight budget."""

    store = FakeMemoryStore(results=[])
    builder = ContextBuilder(store, memory_budget=55)
    assistant_message = Message(
        idx=1,
        role=Role.ASSISTANT,
        content="Done",
        tool_calls=[
            ToolCallRecord(
                tool_call_id="call-bash",
                tool_name="bash",
                arguments={"command": 'rg "ContextViewer" src'},
                output="match 1 " + ("x" * 500),
                status="success",
            ),
        ],
    )

    context, included = await builder.build_context(
        query_embedding=[0.1, 0.2, 0.3],
        memories=[],
        system_prompt="## SYSTEM\n\nBase prompt",
        session_messages=[("user", "Run"), ("assistant", "Done")],
        session_messages_with_tools=[assistant_message],
        tool_calls_max_tokens=4,
    )

    assert included == 0
    assert approximate_tokens(context) <= builder.memory_budget
    assert 'bash: rg "ContextViewer" src exited 0' in context
    assert "match 1" in context
    assert "x" * 100 not in context
    assert "## RECENT TOOL CALLS" not in context
    assert "arguments=" not in context
    assert "output=" not in context


@pytest.mark.asyncio
async def test_context_builder_fills_remaining_budget_with_session_messages() -> None:
    """The newest session messages should occupy the remaining budget after higher-priority context."""

    store = FakeMemoryStore(results=[])
    builder = ContextBuilder(store, memory_budget=90)
    memories = [
        _make_memory("m1", "Keep this memory.", role="assistant"),
    ]
    session_messages = [
        ("user", "Old session message " + ("x" * 260)),
        ("assistant", "Middle session message"),
        ("user", "Newest session message"),
    ]

    context, included = await builder.build_context(
        query_embedding=[0.1, 0.2, 0.3],
        memories=memories,
        system_prompt="## SYSTEM\n\nBase prompt",
        session_messages=session_messages,
    )

    assert approximate_tokens(context) <= builder.memory_budget
    assert "Middle session message" in context
    assert "Newest session message" in context
    assert "Old session message" not in context
    assert context.index("Middle session message") < context.index("Newest session message")


@pytest.mark.asyncio
async def test_context_builder_logs_assembly_summary_and_budget_usage(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Context assembly should emit start and completion summaries."""

    store = FakeMemoryStore(
        results=[
            {
                "entry_id": "m1",
                "content": "Alpha memory content",
                "timestamp": datetime.now(UTC).isoformat(),
                "role": "assistant",
                "tags": [],
                "permanent": False,
                "similarity": 0.98,
            },
            {
                "entry_id": "m2",
                "content": "Beta memory content",
                "timestamp": datetime.now(UTC).isoformat(),
                "role": "user",
                "tags": [],
                "permanent": False,
                "similarity": 0.91,
            },
        ]
    )
    builder = ContextBuilder(store, memory_budget=4096)
    memories = [
        _make_memory("m1", "Alpha memory content"),
        _make_memory("m2", "Beta memory content", role="user"),
        _make_memory("m3", "Gamma memory content"),
    ]

    with caplog.at_level(logging.DEBUG, logger="alfred.context"):
        context, included = await builder.build_context(
            query_embedding=[0.1, 0.2, 0.3],
            memories=memories,
            system_prompt="## SYSTEM\n\nBase prompt",
            session_messages=[("user", "hello"), ("assistant", "hi")],
        )

    assert included == 2
    assert "## RELEVANT MEMORIES" in context

    messages = [record.message for record in caplog.records if record.name == "alfred.context"]
    assert any(message.startswith("core.context.start") for message in messages)
    assert any(message.startswith("core.context.completed") for message in messages)
    assert any("available_memories=3" in message for message in messages)
    assert any("session_messages=2" in message for message in messages)
    assert any("selected_memories=2" in message for message in messages)
    assert any("memory_budget=4096" in message for message in messages)
    assert any("duration_ms=" in message for message in messages)

    assert store.calls == [{"query_embedding": [0.1, 0.2, 0.3], "top_k": 20}]


@pytest.mark.asyncio
async def test_context_builder_logs_truncation_when_budget_is_exceeded(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Context assembly should log when the budget forces truncation."""

    store = FakeMemoryStore(
        results=[
            {
                "entry_id": "long-1",
                "content": "L" * 2000,
                "timestamp": datetime.now(UTC).isoformat(),
                "role": "assistant",
                "tags": [],
                "permanent": False,
                "similarity": 0.97,
            },
            {
                "entry_id": "long-2",
                "content": "M" * 2000,
                "timestamp": datetime.now(UTC).isoformat(),
                "role": "user",
                "tags": [],
                "permanent": False,
                "similarity": 0.95,
            },
        ]
    )
    builder = ContextBuilder(store, memory_budget=220)
    memories = [
        _make_memory("long-1", "L" * 2000),
        _make_memory("long-2", "M" * 2000, role="user"),
    ]

    with caplog.at_level(logging.DEBUG, logger="alfred.context"):
        context, included = await builder.build_context(
            query_embedding=[0.4, 0.5, 0.6],
            memories=memories,
            system_prompt="## SYSTEM\n\n" + ("S" * 400),
            session_messages=[("user", "hello"), ("assistant", "hi")],
        )

    assert included <= 2
    assert "## CURRENT CONVERSATION" in context

    messages = [record.message for record in caplog.records if record.name == "alfred.context"]
    assert any(message.startswith("core.context.truncated") for message in messages)
    assert any("memory_budget=220" in message for message in messages)
    assert any("truncated_count=" in message for message in messages)
    assert any("token_count=" in message for message in messages)
