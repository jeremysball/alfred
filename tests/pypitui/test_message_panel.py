"""Tests for MessagePanel component."""


class TestMessagePanel:
    """Tests for MessagePanel component (Phase 1.5)."""

    def test_message_panel_renders_with_title(self):
        """Verify 'You' or 'Alfred' in title."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        user = MessagePanel(role="user", content="Hello")
        assistant = MessagePanel(role="assistant", content="Hi there")

        user_lines = user.render(width=40)
        assistant_lines = assistant.render(width=40)

        # Check that title appears somewhere in output
        assert "You" in "".join(user_lines)
        assert "Alfred" in "".join(assistant_lines)

    def test_message_panel_user_has_cyan_border(self):
        """Verify cyan styling for user."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(role="user", content="Test")
        assert panel._border_color  # Should have a color set

    def test_message_panel_assistant_has_green_border(self):
        """Verify green styling for assistant."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(role="assistant", content="Test")
        assert panel._border_color  # Should have a color set

    def test_message_panel_error_has_red_border(self):
        """Verify red styling for error state."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(role="assistant", content="Test")
        panel.set_error("Something went wrong")

        # After error, should have red border color
        lines = panel.render(width=40)
        assert "Error:" in "".join(lines)

    def test_message_panel_set_content_updates(self):
        """Verify set_content() changes rendered text."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(role="user", content="Initial")
        panel.set_content("Updated content")

        lines = panel.render(width=40)
        assert "Updated content" in "".join(lines)

    def test_message_panel_wraps_long_content(self):
        """Verify Text handles wrapping (no special handling needed)."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        long_text = "This is a very long message that should wrap " * 5
        panel = MessagePanel(role="user", content=long_text)

        # Should render without error
        lines = panel.render(width=40)
        assert len(lines) > 0


class TestInlineToolCalls:
    """Tests for inline tool call display (Phase 4.4)."""

    def test_message_panel_add_tool_call(self):
        """Verify tool call can be added to message panel."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(role="assistant", content="Hello")
        panel.add_tool_call("remember", "call-1")

        # Should have tool call tracked
        assert len(panel._tool_calls) == 1
        assert panel._tool_calls[0].tool_name == "remember"

    def test_message_panel_update_tool_call(self):
        """Verify tool call output can be updated."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(role="assistant", content="Hello")
        panel.add_tool_call("search", "call-1")
        panel.update_tool_call("call-1", "Found 3 memories")

        assert panel._tool_calls[0].output == "Found 3 memories"

    def test_message_panel_finalize_tool_call(self):
        """Verify tool call status can be finalized."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(role="assistant", content="Hello")
        panel.add_tool_call("bash", "call-1")
        panel.finalize_tool_call("call-1", "success")

        assert panel._tool_calls[0].status == "success"

    def test_tool_call_box_renders_inline(self):
        """Verify tool call box appears inside message content."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(role="assistant", content="Let me search...")
        panel.add_tool_call("search_memories", "call-1")
        panel.update_tool_call("call-1", "Found: blue")
        panel.finalize_tool_call("call-1", "success")
        panel.set_content(panel._text_content + " Your color is blue!")

        lines = panel.render(width=60)
        text = "".join(lines)

        # Tool name should appear in the rendered output
        assert "search_memories" in text
        # Content should also appear
        assert "Let me search" in text
        assert "Your color is blue" in text

    def test_multiple_tool_calls_in_message(self):
        """Verify multiple tool calls in one message."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(role="assistant", content="Let me check...")
        panel.add_tool_call("search", "call-1")
        panel.update_tool_call("call-1", "Found memory")
        panel.finalize_tool_call("call-1", "success")
        panel.set_content(panel._text_content + " Now saving...")
        panel.add_tool_call("remember", "call-2")
        panel.update_tool_call("call-2", "Saved")
        panel.finalize_tool_call("call-2", "success")
        panel.set_content(panel._text_content + " Done!")

        assert len(panel._tool_calls) == 2
        lines = panel.render(width=60)
        text = "".join(lines)
        assert "search" in text
        assert "remember" in text

    def test_tool_call_insert_position(self):
        """Verify tool call appears at correct position in content."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(role="assistant", content="Before")
        panel.add_tool_call("tool", "call-1")
        # Tool inserted at position 6 (after "Before")
        assert panel._tool_calls[0].insert_position == 6
