"""Tests for runtime tool metadata and ordering."""

from types import SimpleNamespace

import pytest

from alfred.tools import clear_registry, get_registry, register_builtin_tools


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset tool registry before each test."""
    clear_registry()
    yield
    clear_registry()


class TestToolMetadata:
    """Test suite for runtime tool reinforcement metadata."""

    def test_builtin_tool_order_prioritizes_retrieval_before_memory_writes(self):
        """Search tools should be registered before remember/update/forget."""
        register_builtin_tools(
            memory_store=SimpleNamespace(),
            session_manager=SimpleNamespace(),
            embedder=SimpleNamespace(),
        )

        names = [tool.name for tool in get_registry().list_tools()]
        assert names[:9] == [
            "read",
            "write",
            "edit",
            "bash",
            "search_memories",
            "search_sessions",
            "remember",
            "update_memory",
            "forget",
        ]

    def test_core_tool_descriptions_reinforce_fallback_and_retrieval(self):
        """Core tool descriptions should steer the model toward better tool use."""
        register_builtin_tools(
            memory_store=SimpleNamespace(),
            session_manager=SimpleNamespace(),
            embedder=SimpleNamespace(),
        )
        registry = get_registry()

        read = registry.get("read")
        assert read is not None
        assert "before changing" in read.description.lower()

        write = registry.get("write")
        assert write is not None
        assert "prefer edit" in write.description.lower()

        edit = registry.get("edit")
        assert edit is not None
        assert "read the file first" in edit.description.lower()

        bash = registry.get("bash")
        assert bash is not None
        assert "fallback" in bash.description.lower()
        assert "do not refuse" in bash.description.lower()

        search_memories = registry.get("search_memories")
        assert search_memories is not None
        assert "before asking the user to repeat" in search_memories.description.lower()
        assert "memories" in search_memories.description.lower()

        search_sessions = registry.get("search_sessions")
        assert search_sessions is not None
        assert "prior discussions" in search_sessions.description.lower()
        assert "memory" in search_sessions.description.lower()

        remember = registry.get("remember")
        assert remember is not None
        assert "curated" in remember.description.lower()
        assert "future retrieval" in remember.description.lower()
