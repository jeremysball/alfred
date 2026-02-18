"""Tests for session context integration (PRD #54 Milestone 3)."""

import pytest
from unittest.mock import Mock, patch

from src.session import Message, Role, Session, SessionManager
from src.session_context import SessionContextBuilder


class TestSessionContextBuilder:
    """Tests for building context with session history."""

    def test_build_context_empty_session(self):
        """Context includes system prompt even with empty session."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        manager.start_session()
        
        builder = SessionContextBuilder(manager)
        context = builder.build_context("What time is it?")
        
        assert "## CONVERSATION HISTORY" in context
        assert "## CURRENT MESSAGE" in context
        assert "What time is it?" in context

    def test_build_context_with_history(self):
        """Context includes session messages in order."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        manager.start_session()
        manager.add_message("user", "Hello")
        manager.add_message("assistant", "Hi there")
        
        builder = SessionContextBuilder(manager)
        context = builder.build_context("How are you?")
        
        assert "User: Hello" in context
        assert "Assistant: Hi there" in context
        assert "## CURRENT MESSAGE" in context
        assert "How are you?" in context

    def test_build_context_message_format(self):
        """Messages formatted as simple prefix."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        manager.start_session()
        manager.add_message("user", "My question")
        manager.add_message("assistant", "My answer")
        
        builder = SessionContextBuilder(manager)
        context = builder.build_context("Follow up")
        
        # Verify simple prefix format (Option A from decisions)
        lines = context.split("\n")
        history_section = False
        user_line = None
        assistant_line = None
        
        for line in lines:
            if "## CONVERSATION HISTORY" in line:
                history_section = True
                continue
            if history_section and line.startswith("User: "):
                user_line = line
            if history_section and line.startswith("Assistant: "):
                assistant_line = line
        
        assert user_line == "User: My question"
        assert assistant_line == "Assistant: My answer"

    def test_build_context_without_session_raises(self):
        """Raises if no active session."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        
        builder = SessionContextBuilder(manager)
        
        with pytest.raises(RuntimeError, match="No active session"):
            builder.build_context("Hello")

    def test_system_messages_included(self):
        """System messages included in context (for tool results)."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        manager.start_session()
        manager.add_message("user", "Do something")
        manager.add_message("system", "Tool result: file created")
        manager.add_message("assistant", "Done")
        
        builder = SessionContextBuilder(manager)
        context = builder.build_context("Next")
        
        assert "System: Tool result: file created" in context

    def test_build_context_with_many_messages(self):
        """Context includes all messages (no limit in PRD #54)."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        manager.start_session()
        
        # Add 50 messages
        for i in range(25):
            manager.add_message("user", f"Message {i}")
            manager.add_message("assistant", f"Response {i}")
        
        builder = SessionContextBuilder(manager)
        context = builder.build_context("Final")
        
        # All messages should be present
        for i in range(25):
            assert f"User: Message {i}" in context
            assert f"Assistant: Response {i}" in context


class TestSessionContextAutoStart:
    """Tests for session auto-start on first message."""

    def test_auto_start_on_first_message(self):
        """Session auto-starts when first message is added."""
        manager = SessionManager.get_instance()
        manager.clear_session()
        
        assert not manager.has_active_session()
        
        # Simulate what CLI does - add message triggers start
        if not manager.has_active_session():
            manager.start_session()
        manager.add_message("user", "First message")
        
        assert manager.has_active_session()
        assert len(manager.get_messages()) == 1
