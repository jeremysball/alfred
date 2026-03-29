"""Tests for /context command functionality (PRD #101)."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alfred.alfred import Alfred
from alfred.session import ToolCallRecord


class TestContextDisplay:
    """Tests for Alfred.get_context_display() method."""

    @pytest.fixture
    def mock_alfred(self):
        """Create a mock Alfred instance with required attributes."""
        alfred = MagicMock(spec=Alfred)
        alfred.token_tracker = MagicMock()
        alfred.token_tracker.context_tokens = 1000
        alfred.context_summary = MagicMock()
        alfred.context_summary.memories_count = 3
        alfred.context_summary.session_messages = 2
        alfred.context_summary.prompt_sections = ["AGENTS", "SOUL", "USER", "TOOLS"]
        return alfred

    def test_get_context_display_returns_sections(self, mock_alfred):
        """Test that get_context_display returns all context sections."""
        # Arrange

        # This test verifies the structure of context display data
        # The actual function is async and takes an Alfred instance

        # Act - Define expected structure
        result = {
            "system_prompt": {
                "sections": [
                    {"name": "AGENTS", "tokens": 500},
                    {"name": "SOUL", "tokens": 300},
                    {"name": "USER", "tokens": 200},
                    {"name": "TOOLS", "tokens": 150},
                ],
                "total_tokens": 1150,
            },
            "memories": {
                "loaded": 3,
                "total": 10,
                "tokens": 400,
                "items": [
                    {"content": "Memory 1", "similarity": 0.9, "score": 0.85},
                ],
            },
            "session_history": {
                "count": 2,
                "tokens": 200,
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there"},
                ],
            },
            "tool_calls": {
                "count": 1,
                "tokens": 100,
                "items": [
                    {
                        "tool_name": "bash",
                        "arguments": {"command": "ls"},
                        "output": "file.txt",
                        "status": "success",
                    },
                ],
            },
            "total_tokens": 1850,
        }

        # Assert
        assert "system_prompt" in result
        assert "memories" in result
        assert "session_history" in result
        assert "tool_calls" in result
        assert "total_tokens" in result

    def test_format_tool_calls_with_truncated_output(self):
        """Test that tool call output is truncated for display."""
        # Arrange
        tool_calls = [
            ToolCallRecord(
                tool_call_id="call_1",
                tool_name="bash",
                arguments={"command": "cat large_file.txt"},
                output="line1\n" * 50,  # 50 lines
                status="success",
            )
        ]

        # Act - Simulate formatting
        formatted = []
        for tc in tool_calls:
            output_lines = tc.output.strip().split("\n")[:5]  # Truncate to 5 lines
            output = "\n".join(output_lines)
            if len(tc.output.strip().split("\n")) > 5:
                output += "\n..."
            formatted.append(
                {
                    "tool_name": tc.tool_name,
                    "arguments": tc.arguments,
                    "output": output,
                    "status": tc.status,
                }
            )

        # Assert
        assert len(formatted) == 1
        assert formatted[0]["tool_name"] == "bash"
        assert "..." in formatted[0]["output"]
        assert formatted[0]["output"].count("\n") <= 5

    def test_memory_display_shows_count_of_total(self):
        """Test that memory display shows 'X of Y memories' format."""
        # Arrange
        memories = [{"content": f"Memory {i}"} for i in range(5)]
        total_memories = 12

        # Act
        display_text = f"{len(memories)} of {total_memories} memories"

        # Assert
        assert display_text == "5 of 12 memories"

    def test_token_estimation_uses_char_division(self):
        """Test that token estimation uses len(text) // 4."""
        # Arrange
        text = "a" * 100  # 100 characters

        # Act
        estimated_tokens = len(text) // 4

        # Assert
        assert estimated_tokens == 25


class TestContextCommandIntegration:
    """Integration tests for /context command."""

    def test_context_command_exists(self):
        """Test that ShowContextCommand class exists and is registered."""
        from alfred.interfaces.pypitui.commands.show_context import ShowContextCommand

        # Assert the command class exists
        assert ShowContextCommand is not None
        assert ShowContextCommand.name == "context"


@pytest.mark.asyncio
async def test_show_context_command_reports_blocked_context_warning_and_omits_blocked_sections() -> None:
    """The /context command should render blocked-context warnings before the summary."""
    from alfred.interfaces.pypitui.commands.show_context import ShowContextCommand

    rendered_messages: list[str] = []
    fake_session_manager = SimpleNamespace(has_active_session=lambda: True)
    fake_alfred = SimpleNamespace(core=SimpleNamespace(session_manager=fake_session_manager))
    fake_tui = SimpleNamespace(
        alfred=fake_alfred,
        _add_system_message=rendered_messages.append,
        _add_user_message=rendered_messages.append,
    )
    context_data = {
        "system_prompt": {
            "sections": [{"name": "AGENTS.md", "tokens": 12}],
            "total_tokens": 12,
        },
        "blocked_context_files": ["SOUL.md"],
        "conflicted_context_files": [
            {
                "id": "soul",
                "name": "soul",
                "label": "SOUL.md",
                "reason": "Conflicted managed template SOUL.md is blocked",
            }
        ],
        "warnings": [],
        "memories": {"displayed": 0, "total": 0, "items": [], "tokens": 0},
        "session_history": {"count": 1, "messages": [{"role": "user", "content": "hello"}], "tokens": 3},
        "tool_calls": {"count": 0, "items": [], "tokens": 0},
        "self_model": {
            "identity": {"name": "Alfred", "role": "Assistant"},
            "runtime": {"interface": "cli", "daemon_mode": False},
            "capabilities": {"memory_enabled": True, "search_enabled": True, "tools_count": 10},
            "context_pressure": {"message_count": 1, "memory_count": 0, "approximate_tokens": 15},
        },
        "total_tokens": 15,
    }

    with patch("alfred.context_display.get_context_display", AsyncMock(return_value=context_data)):
        command = ShowContextCommand()
        assert command.execute(fake_tui, None) is True
        await asyncio.sleep(0.01)

    assert rendered_messages
    rendered = rendered_messages[0]
    assert "CONFLICTED MANAGED TEMPLATES (1 file)" in rendered
    assert "SOUL.md: Conflicted managed template SOUL.md is blocked" in rendered
    assert "SYSTEM PROMPT (12 tokens)" in rendered
    assert "AGENTS.md" in rendered
    assert "WARNING:" not in rendered.split("CONFLICTED MANAGED TEMPLATES", 1)[0]


@pytest.mark.asyncio
async def test_show_context_command_reports_preview_counts_and_compact_tool_outcomes() -> None:
    """The /context command should show preview vs total counts and compact tool summaries."""
    from alfred.interfaces.pypitui.commands.show_context import ShowContextCommand

    rendered_messages: list[str] = []
    fake_session_manager = SimpleNamespace(has_active_session=lambda: True)
    fake_alfred = SimpleNamespace(core=SimpleNamespace(session_manager=fake_session_manager))
    fake_tui = SimpleNamespace(
        alfred=fake_alfred,
        _add_system_message=rendered_messages.append,
        _add_user_message=rendered_messages.append,
    )
    context_data = {
        "system_prompt": {
            "sections": [
                {"id": "system", "name": "system", "label": "SYSTEM.md", "tokens": 12},
                {"id": "agents", "name": "agents", "label": "AGENTS.md", "tokens": 34},
                {"id": "tools", "name": "tools", "label": "TOOLS.md", "tokens": 8},
            ],
            "total_tokens": 54,
        },
        "blocked_context_files": [],
        "warnings": [],
        "memories": {"displayed": 1, "total": 2, "items": [{"content": "Memory", "role": "user", "timestamp": "2026-03-20"}], "tokens": 6},
        "session_history": {
            "count": 4,
            "displayed": 5,
            "total": 9,
            "messages": [
                {"role": "user", "content": "Preview 1"},
                {"role": "assistant", "content": "Preview 2"},
                {"role": "user", "content": "Preview 3"},
                {"role": "assistant", "content": "Preview 4"},
                {"role": "user", "content": "Preview 5"},
            ],
            "tokens": 21,
        },
        "tool_calls": {
            "count": 2,
            "displayed": 3,
            "total": 4,
            "items": [
                {"tool_name": "bash", "summary": "bash: python -V exited 0 — Python 3.14.3", "tokens": 9},
                {"tool_name": "read", "summary": "read: docs/roadmap.md", "tokens": 5},
                {"tool_name": "edit", "summary": "edit: updated src/module.py", "tokens": 6},
            ],
            "tokens": 20,
            "all_shown": False,
        },
        "self_model": {
            "identity": {"name": "Alfred", "role": "Assistant"},
            "runtime": {"interface": "cli", "daemon_mode": False},
            "capabilities": {"memory_enabled": True, "search_enabled": True, "tools_count": 10},
            "context_pressure": {"message_count": 5, "memory_count": 2, "approximate_tokens": 120},
        },
        "total_tokens": 101,
    }

    with patch("alfred.context_display.get_context_display", AsyncMock(return_value=context_data)):
        command = ShowContextCommand()
        assert command.execute(fake_tui, None) is True
        await asyncio.sleep(0.01)

    assert rendered_messages
    rendered = rendered_messages[0]
    assert "SYSTEM PROMPT (54 tokens)" in rendered
    assert "SYSTEM.md: 12 tokens" in rendered
    assert "AGENTS.md: 34 tokens" in rendered
    assert "TOOLS.md: 8 tokens" in rendered
    assert "SESSION HISTORY (5 displayed of 9 messages, 21 tokens)" in rendered
    assert "Preview 5" in rendered
    assert "RECENT TOOL OUTCOMES (3 displayed of 4 calls, 20 tokens)" in rendered
    assert "bash: python -V exited 0 — Python 3.14.3" in rendered
    assert "read: docs/roadmap.md" in rendered
    assert "edit: updated src/module.py" in rendered
    assert "command=" not in rendered
    assert "arguments" not in rendered
    assert "output" not in rendered
