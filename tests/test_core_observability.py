"""Core observability tests for Alfred turn lifecycle logging."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from alfred.agent import ToolEvent
from alfred.alfred import Alfred, ContextSummary
from alfred.config import Config
from alfred.session import Message, Role, Session, SessionMeta
from alfred.support_policy import ResolvedSubject, ResolvedSupportPolicy, SupportTurnAssessment, compile_support_behavior_contract
from alfred.token_tracker import TokenTracker


@dataclass
class FakeEmbedder:
    """Minimal embedder fake that records calls."""

    calls: list[str] = field(default_factory=list)

    async def embed(self, message: str) -> list[float]:
        self.calls.append(message)
        return [0.1, 0.2, 0.3]


@dataclass
class FakeMemoryStore:
    """Minimal memory store fake that returns deterministic entries."""

    entries: list[str]
    calls: int = 0

    async def get_all_entries(self) -> list[str]:
        self.calls += 1
        return list(self.entries)


@dataclass
class FakeContextLoader:
    """Minimal context loader fake that records assembly inputs."""

    calls: list[dict[str, Any]] = field(default_factory=list)
    fail_with: Exception | None = None

    async def assemble(self) -> SimpleNamespace:
        """Return a simple assembled context for non-streaming chat tests."""

        return SimpleNamespace(system_prompt="## SYSTEM\n\nObservability test system prompt", memories=[])

    async def assemble_with_search(
        self,
        query_embedding: list[float],
        memories: list[Any],
        session_messages: list[tuple[str, str]] | None = None,
        session_messages_with_tools: list[Any] | None = None,
        alfred: Any | None = None,
    ) -> tuple[str, int]:
        self.calls.append(
            {
                "query_embedding": list(query_embedding),
                "memories_count": len(memories),
                "session_messages_count": len(session_messages or []),
                "session_messages_with_tools_count": len(session_messages_with_tools or []),
                "alfred": alfred,
            }
        )
        if self.fail_with is not None:
            raise self.fail_with
        return "## SYSTEM\n\nObservability test system prompt", 2

    async def assemble_with_self_model(
        self,
        alfred: Any,
        memories: list[Any] | None = None,
    ) -> SimpleNamespace:
        """Return assembled context with self-model for non-streaming chat tests."""
        return SimpleNamespace(
            system_prompt="## SYSTEM\n\nObservability test system prompt",
            memories=memories or [],
            self_model=None,
        )


@dataclass
class FakeAgent:
    """Minimal agent fake that streams fixed chunks."""

    chunks: list[str]
    calls: list[dict[str, Any]] = field(default_factory=list)
    fail_with: Exception | None = None
    block_after_chunks: int | None = None
    block_event: asyncio.Event | None = None

    async def run(
        self,
        messages: list[Any],
        system_prompt: str,
    ) -> str:
        self.calls.append(
            {
                "message_count": len(messages),
                "system_prompt": system_prompt,
                "has_usage_callback": False,
                "has_tool_callback": False,
            }
        )
        if self.fail_with is not None:
            raise self.fail_with
        return "".join(self.chunks)

    async def run_stream(
        self,
        messages: list[Any],
        system_prompt: str,
        usage_callback: Any | None = None,
        tool_callback: Any | None = None,
    ):
        self.calls.append(
            {
                "message_count": len(messages),
                "system_prompt": system_prompt,
                "has_usage_callback": usage_callback is not None,
                "has_tool_callback": tool_callback is not None,
            }
        )
        if self.fail_with is not None:
            raise self.fail_with
        if usage_callback is not None:
            usage_callback({"prompt_tokens": 12, "completion_tokens": 8})
        for index, chunk in enumerate(self.chunks, start=1):
            yield chunk
            if self.block_after_chunks is not None and index >= self.block_after_chunks:
                if self.block_event is None:
                    raise RuntimeError("block_event must be provided when blocking the agent fake")
                await self.block_event.wait()


class FakeTools:
    """Tiny tool registry fake used only for prompt rendering."""

    def list_tools(self) -> list[Any]:
        return []


class FakeSessionManager:
    """Session manager fake with the production-shaped methods chat_stream uses."""

    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.session = Session(
            meta=SessionMeta(
                session_id="session-observability",
                created_at=now,
                last_active=now,
                status="active",
                message_count=2,
            ),
            messages=[
                Message(idx=0, role=Role.USER, content="previous user"),
                Message(idx=1, role=Role.ASSISTANT, content="previous assistant"),
            ],
        )
        self.persist_calls: list[tuple[str, int]] = []
        self.token_updates: list[dict[str, Any]] = []
        self.add_message_calls: list[tuple[str, str, str | None]] = []

    def has_active_session(self) -> bool:
        return True

    def start_session(self) -> Session:
        return self.session

    def get_current_cli_session(self) -> Session:
        return self.session

    def get_or_create_session(self, session_id: str | None = None) -> Session:
        return self.session

    def get_session_messages(self, session_id: str | None = None) -> list[Message]:
        return list(self.session.messages)

    def get_messages_for_context(self, session_id: str | None = None) -> list[tuple[str, str]]:
        return [(message.role.value, message.content) for message in self.session.messages[:-1]]

    def get_messages_with_tools_for_context(self, session_id: str | None = None) -> list[Message]:
        return list(self.session.messages[:-1])

    def add_message(self, role: str, content: str, session_id: str | None = None) -> None:
        self.add_message_calls.append((role, content, session_id))
        message = Message(
            idx=len(self.session.messages),
            role=Role(role),
            content=content,
            timestamp=datetime.now(UTC),
        )
        self.session.messages.append(message)
        self.session.meta.last_active = datetime.now(UTC)
        self.session.meta.message_count = len(self.session.messages)

    def _spawn_persist_task(self, session_id: str, messages: list[Message]) -> None:
        self.persist_calls.append((session_id, len(messages)))

    def update_message_tokens(
        self,
        idx: int,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
        reasoning_tokens: int = 0,
        session_id: str | None = None,
    ) -> None:
        self.token_updates.append(
            {
                "idx": idx,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cached_tokens": cached_tokens,
                "reasoning_tokens": reasoning_tokens,
                "session_id": session_id,
            }
        )
        for message in self.session.messages:
            if message.idx == idx:
                message.input_tokens = input_tokens
                message.output_tokens = output_tokens
                message.cached_tokens = cached_tokens
                message.reasoning_tokens = reasoning_tokens
                break


def _make_alfred(tmp_path: Path) -> tuple[Alfred, FakeContextLoader, FakeAgent, FakeSessionManager]:
    config = Config(
        telegram_bot_token="test-token",
        openai_api_key="test-openai-key",
        kimi_api_key="test-kimi-key",
        kimi_base_url="https://example.invalid/v1",
        workspace_dir=tmp_path,
        data_dir=tmp_path / "data",
        memory_dir=tmp_path / "memory",
        context_files={},
        memory_budget=2048,
    )

    embedder = FakeEmbedder()
    memory_store = FakeMemoryStore(entries=["memory-1", "memory-2", "memory-3"])
    session_manager = FakeSessionManager()
    context_loader = FakeContextLoader()
    agent = FakeAgent(chunks=["Hello", " world"])

    alfred = object.__new__(Alfred)
    alfred.config = config
    alfred.core = SimpleNamespace(
        session_manager=session_manager,
        embedder=embedder,
        memory_store=memory_store,
    )
    alfred.context_loader = context_loader
    alfred.agent = agent
    alfred.tools = FakeTools()
    alfred.token_tracker = TokenTracker()
    alfred._last_usage = None
    alfred.context_summary = ContextSummary()

    return alfred, context_loader, agent, session_manager


@pytest.mark.asyncio
async def test_chat_logs_core_turn_lifecycle_on_success(
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """A successful non-streaming turn should emit structured core lifecycle logs."""

    alfred, _, agent, _ = _make_alfred(tmp_path)

    with caplog.at_level(logging.DEBUG, logger="alfred.alfred"):
        response = await alfred.chat("hello world")

    assert response == "Hello world"

    core_messages = [record.message for record in caplog.records if record.name == "alfred.alfred" and record.message.startswith("core.")]

    assert [message.split()[0] for message in core_messages] == [
        "core.turn.start",
        "core.context.start",
        "core.context.completed",
        "core.agent_loop.start",
        "core.agent_loop.completed",
        "core.turn.completed",
    ]
    assert "message_chars=11" in core_messages[0]
    assert "memories_count=0" in core_messages[2]
    assert "response_chars=11" in core_messages[4]
    assert "session_id=cli" in core_messages[5]

    assert agent.calls[0]["message_count"] == 1
    assert agent.calls[0]["system_prompt"].startswith("## SYSTEM")


@pytest.mark.asyncio
async def test_chat_stream_logs_core_turn_lifecycle_on_success(
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """A successful streamed turn should emit structured core lifecycle logs."""

    alfred, context_loader, agent, session_manager = _make_alfred(tmp_path)

    with caplog.at_level(logging.DEBUG, logger="alfred.alfred"):
        chunks = [chunk async for chunk in alfred.chat_stream("hello world")]

    assert chunks == ["Hello", " world"]

    core_messages = [record.message for record in caplog.records if record.name == "alfred.alfred" and record.message.startswith("core.")]

    assert [message.split()[0] for message in core_messages] == [
        "core.turn.start",
        "core.context.start",
        "core.context.completed",
        "core.agent_loop.start",
        "core.agent_loop.completed",
        "core.turn.completed",
    ]
    assert "message_chars=11" in core_messages[0]
    assert "available_memories=3" in core_messages[1]
    assert "session_messages=2" in core_messages[1]
    assert "memories_count=2" in core_messages[2]
    assert "response_chars=11" in core_messages[4]
    assert "duration_ms=" in core_messages[5]

    assert not any(record.message.startswith("Processing message:") for record in caplog.records if record.name == "alfred.alfred")
    assert not any(record.message == "Starting agent loop..." for record in caplog.records if record.name == "alfred.alfred")

    assert context_loader.calls[0]["session_messages_count"] == 2
    assert context_loader.calls[0]["memories_count"] == 3
    assert agent.calls[0]["message_count"] == 1
    assert agent.calls[0]["system_prompt"].startswith("## SYSTEM")
    assert session_manager.token_updates


@pytest.mark.asyncio
async def test_chat_stream_logs_core_turn_failed_when_agent_raises(
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """A failing streamed turn should emit a structured failure log."""

    alfred, _, agent, _ = _make_alfred(tmp_path)
    agent.fail_with = RuntimeError("agent exploded")

    with caplog.at_level(logging.DEBUG, logger="alfred.alfred"), pytest.raises(RuntimeError, match="agent exploded"):
        async for _chunk in alfred.chat_stream("hello world"):
            pass

    core_messages = [record.message for record in caplog.records if record.name == "alfred.alfred" and record.message.startswith("core.")]

    assert any(message.startswith("core.turn.failed") for message in core_messages)
    assert any("boundary=agent" in message for message in core_messages)
    assert any("error_type=RuntimeError" in message for message in core_messages)
    assert any("error=agent exploded" in message for message in core_messages)
    assert not any(message.startswith("core.turn.completed") for message in core_messages)


@pytest.mark.asyncio
async def test_chat_stream_logs_core_turn_cancelled_when_task_is_cancelled(
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """A cancelled streamed turn should emit a structured cancellation log."""

    alfred, _, agent, _ = _make_alfred(tmp_path)
    block_event = asyncio.Event()
    agent.chunks = ["Hello", " world"]
    agent.block_after_chunks = 1
    agent.block_event = block_event

    seen_first_chunk = asyncio.Event()
    collected: list[str] = []

    async def _consume() -> None:
        async for chunk in alfred.chat_stream("hello world"):
            collected.append(chunk)
            if chunk == "Hello":
                seen_first_chunk.set()

    task = asyncio.create_task(_consume())
    await asyncio.wait_for(seen_first_chunk.wait(), timeout=1.0)
    task.cancel()

    with caplog.at_level(logging.DEBUG, logger="alfred.alfred"), pytest.raises(asyncio.CancelledError):
        await task

    assert collected == ["Hello"]

    core_messages = [record.message for record in caplog.records if record.name == "alfred.alfred" and record.message.startswith("core.")]

    assert any(message.startswith("core.turn.cancelled") for message in core_messages)
    assert any("boundary=agent" in message for message in core_messages)
    assert any("duration_ms=" in message for message in core_messages)
    assert not any(message.startswith("core.turn.completed") for message in core_messages)


@pytest.mark.asyncio
async def test_chat_stream_records_ordered_text_blocks_around_tool_calls(
    tmp_path: Path,
) -> None:
    """Ordered text blocks should survive tool calls and reasoning boundaries."""

    from alfred.agent import ToolEnd, ToolStart

    class OrderedPartAgent:
        """Minimal agent fake that emits reasoning, text, and tool events."""

        async def run_stream(
            self,
            messages: list[Any],
            system_prompt: str,
            usage_callback: Any | None = None,
            tool_callback: Callable[[ToolEvent], None] | None = None,
        ):
            if usage_callback is not None:
                usage_callback({"prompt_tokens": 12, "completion_tokens": 8})

            stream_parts: list[str | ToolEvent] = [
                "[REASONING]thinking",
                "[/REASONING]",
                "Before ",
                ToolStart(
                    tool_call_id="call-1",
                    tool_name="bash",
                    arguments={"command": "ls"},
                ),
                "After ",
                ToolEnd(
                    tool_call_id="call-1",
                    tool_name="bash",
                    result="done",
                    is_error=False,
                ),
            ]

            for part in stream_parts:
                if isinstance(part, str):
                    yield part
                elif tool_callback is not None:
                    tool_callback(part)

    alfred, _, _, session_manager = _make_alfred(tmp_path)
    alfred.agent = OrderedPartAgent()

    chunks = [chunk async for chunk in alfred.chat_stream("hello world")]

    assert chunks == ["[REASONING]thinking", "[/REASONING]", "Before ", "After "]

    assistant_message = session_manager.session.messages[-1]
    assert assistant_message.role == Role.ASSISTANT
    assert assistant_message.content == "Before After "
    assert assistant_message.reasoning_blocks is not None
    assert assistant_message.text_blocks is not None
    assert assistant_message.tool_calls is not None
    assert [block.content for block in assistant_message.text_blocks] == ["Before ", "After "]
    assert [block.sequence for block in assistant_message.text_blocks] == [1, 3]
    assert assistant_message.tool_calls[0].sequence == 2
    assert assistant_message.reasoning_blocks[0].sequence == 0
    assert assistant_message.reasoning_blocks[0].content == "thinking"


@pytest.mark.asyncio
async def test_chat_stream_includes_compiled_support_contract_in_system_prompt(
    tmp_path: Path,
) -> None:
    """chat_stream should append the compiled support contract before agent streaming starts."""

    alfred, _, agent, _ = _make_alfred(tmp_path)

    class FakeSupportPolicyRuntime:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        async def build_prompt_section(
            self,
            *,
            message: str,
            query_embedding: list[float] | None,
            session_messages: list[tuple[str, str]],
            session_id: str | None,
        ) -> str:
            self.calls.append(
                {
                    "message": message,
                    "query_embedding": list(query_embedding or []),
                    "session_messages": list(session_messages),
                    "session_id": session_id,
                }
            )
            return (
                "## Runtime Support Contract\n\n"
                "- need: activate\n"
                "- response_mode: execute\n"
                "- subjects: [arc:webui_cleanup]\n"
                "- intervention_family: narrow\n"
            )

    runtime = FakeSupportPolicyRuntime()
    alfred._support_policy_runtime = runtime

    chunks = [chunk async for chunk in alfred.chat_stream("hello world")]

    assert chunks == ["Hello", " world"]
    assert runtime.calls == [
        {
            "message": "hello world",
            "query_embedding": [0.1, 0.2, 0.3],
            "session_messages": [("user", "previous user"), ("assistant", "previous assistant")],
            "session_id": None,
        }
    ]
    assert "## Runtime Support Contract" in agent.calls[0]["system_prompt"]
    assert "- need: activate" in agent.calls[0]["system_prompt"]
    assert "- intervention_family: narrow" in agent.calls[0]["system_prompt"]


@pytest.mark.asyncio
async def test_chat_stream_appends_reflection_guidance_only_when_a_pattern_should_be_surfaced(
    tmp_path: Path,
) -> None:
    """chat_stream should append bounded reflection guidance after the support contract when available."""

    alfred, _, agent, _ = _make_alfred(tmp_path)

    class FakeSupportPolicyRuntime:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        async def build_turn_contract(
            self,
            *,
            message: str,
            query_embedding: list[float] | None,
            session_messages: list[tuple[str, str]],
            session_id: str | None = None,
        ) -> Any:
            self.calls.append(
                {
                    "message": message,
                    "query_embedding": list(query_embedding or []),
                    "session_messages": list(session_messages),
                    "session_id": session_id,
                }
            )
            return SimpleNamespace(
                assessment=SupportTurnAssessment(
                    need="activate",
                    subjects=(ResolvedSubject(kind="arc", id="webui_cleanup"),),
                ),
                response_mode="execute",
                resolved_policy=ResolvedSupportPolicy(
                    assessment=SupportTurnAssessment(
                        need="activate",
                        subjects=(ResolvedSubject(kind="arc", id="webui_cleanup"),),
                    ),
                    response_mode="execute",
                    relational_values={
                        "warmth": "medium",
                        "companionship": "medium",
                        "candor": "medium",
                        "challenge": "medium",
                        "authority": "medium",
                        "emotional_attunement": "medium",
                        "analytical_depth": "medium",
                        "momentum_pressure": "medium",
                    },
                    support_values={
                        "planning_granularity": "minimal",
                        "option_bandwidth": "single",
                        "proactivity_level": "high",
                        "accountability_style": "firm",
                        "recovery_style": "steady",
                        "reflection_depth": "light",
                        "pacing": "brisk",
                        "recommendation_forcefulness": "high",
                    },
                    primary_arc_id="webui_cleanup",
                    domain_ids=("work",),
                ),
                behavior_contract=compile_support_behavior_contract(
                    ResolvedSupportPolicy(
                        assessment=SupportTurnAssessment(
                            need="activate",
                            subjects=(ResolvedSubject(kind="arc", id="webui_cleanup"),),
                        ),
                        response_mode="execute",
                        relational_values={
                            "warmth": "medium",
                            "companionship": "medium",
                            "candor": "medium",
                            "challenge": "medium",
                            "authority": "medium",
                            "emotional_attunement": "medium",
                            "analytical_depth": "medium",
                            "momentum_pressure": "medium",
                        },
                        support_values={
                            "planning_granularity": "minimal",
                            "option_bandwidth": "single",
                            "proactivity_level": "high",
                            "accountability_style": "firm",
                            "recovery_style": "steady",
                            "reflection_depth": "light",
                            "pacing": "brisk",
                            "recommendation_forcefulness": "high",
                        },
                        primary_arc_id="webui_cleanup",
                        domain_ids=("work",),
                    )
                ),
                trace=SimpleNamespace(),
            )

    class FakeSupportReflectionRuntime:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        async def build_prompt_section(
            self,
            *,
            runtime_result: Any,
            message: str,
            query_embedding: list[float] | None,
            session_messages: list[tuple[str, str]],
            session_id: str | None,
        ) -> str:
            self.calls.append(
                {
                    "message": message,
                    "query_embedding": list(query_embedding or []),
                    "session_messages": list(session_messages),
                    "session_id": session_id,
                    "response_mode": runtime_result.response_mode,
                }
            )
            return (
                "## Reflection Guidance\n\n"
                "Use relevant continuity silently unless the user benefits from hearing it.\n"
                "Single-step next moves work better here.\n"
            )

    policy_runtime = FakeSupportPolicyRuntime()
    reflection_runtime = FakeSupportReflectionRuntime()
    alfred._support_policy_runtime = policy_runtime
    alfred._support_reflection_runtime = reflection_runtime

    chunks = [chunk async for chunk in alfred.chat_stream("hello world")]

    assert chunks == ["Hello", " world"]
    assert policy_runtime.calls == [
        {
            "message": "hello world",
            "query_embedding": [0.1, 0.2, 0.3],
            "session_messages": [("user", "previous user"), ("assistant", "previous assistant")],
            "session_id": None,
        }
    ]
    assert reflection_runtime.calls == [
        {
            "message": "hello world",
            "query_embedding": [0.1, 0.2, 0.3],
            "session_messages": [("user", "previous user"), ("assistant", "previous assistant")],
            "session_id": None,
            "response_mode": "execute",
        }
    ]
    assert "## Runtime Support Contract" in agent.calls[0]["system_prompt"]
    assert "## Reflection Guidance" in agent.calls[0]["system_prompt"]
    assert "Single-step next moves work better here." in agent.calls[0]["system_prompt"]
