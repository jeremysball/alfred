"""Regression tests for assistant message rendering with MessagePanel.

These tests verify that assistant messages render correctly during streaming,
especially after the MessagePanel content block architecture refactor.
"""

import pytest


class TestAssistantMessageRendering:
    """Tests for assistant message rendering during streaming."""

    @pytest.mark.asyncio
    async def test_assistant_message_content_appears_in_render(self, mock_alfred, mock_terminal):
        """Verify assistant message content is actually visible in rendered output.

        This is a regression test for the issue where assistant messages
        would render as empty boxes after the MessagePanel refactor.
        """
        from alfred.interfaces.pypitui.message_panel import MessagePanel
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        await tui._send_message("Hello")

        # Get the last message panel (should be assistant)
        assistant_panels = [
            c for c in tui.conversation.children
            if isinstance(c, MessagePanel) and c._role == "assistant"
        ]
        assert len(assistant_panels) >= 1, "Should have at least one assistant panel"

        assistant_panel = assistant_panels[-1]

        # Render the panel and check content appears
        lines = assistant_panel.render(width=80)
        rendered_text = "".join(lines)

        # The mock alfred returns "Hello world!" as response
        msg = f"Assistant content not in render. Got: {rendered_text[:500]}"
        assert "Hello" in rendered_text, msg

    @pytest.mark.asyncio
    async def test_assistant_message_with_streaming_chunks(self, mock_alfred, mock_terminal):
        """Verify streaming content accumulates correctly in assistant panel."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        # Create a custom stream that sends chunks
        chunks = ["Hello", " ", "world", "!"]
        async def chunk_stream(*args, **kwargs):
            for chunk in chunks:
                yield chunk

        mock_alfred.chat_stream = chunk_stream
        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        await tui._send_message("Test")

        from alfred.interfaces.pypitui.message_panel import MessagePanel
        assistant_panels = [
            c for c in tui.conversation.children
            if isinstance(c, MessagePanel) and c._role == "assistant"
        ]
        assert len(assistant_panels) >= 1

        assistant_panel = assistant_panels[-1]
        lines = assistant_panel.render(width=80)
        rendered_text = "".join(lines)

        # All chunks should be present
        msg = f"Streaming content incomplete. Got: {rendered_text[:200]}"
        assert "Hello world!" in rendered_text, msg

    @pytest.mark.asyncio
    async def test_assistant_message_renders_with_markdown(self, mock_alfred, mock_terminal):
        """Verify assistant messages render markdown correctly."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        # Stream content with markdown
        async def markdown_stream(*args, **kwargs):
            yield "**Bold** and *italic* text"

        mock_alfred.chat_stream = markdown_stream
        mock_alfred.config.use_markdown_rendering = True
        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        await tui._send_message("Test markdown")

        from alfred.interfaces.pypitui.message_panel import MessagePanel
        assistant_panels = [
            c for c in tui.conversation.children
            if isinstance(c, MessagePanel) and c._role == "assistant"
        ]
        assert len(assistant_panels) >= 1

        assistant_panel = assistant_panels[-1]

        # Content should exist and have content blocks
        assert len(assistant_panel._content_blocks) >= 1, "Should have content blocks"

        # Render and check
        lines = assistant_panel.render(width=80)
        rendered_text = "".join(lines)

        # Should have content (markdown may add ANSI codes, so check for the text)
        assert "Bold" in rendered_text or "**Bold**" in rendered_text, \
            f"Markdown content not rendered. Got: {rendered_text[:200]}"

    @pytest.mark.asyncio
    async def test_assistant_message_empty_content_handling(self, mock_alfred, mock_terminal):
        """Verify assistant messages handle empty content gracefully."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        # Stream that yields nothing initially, then content
        call_count = 0
        async def delayed_stream(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            yield ""  # Empty first
            yield "Now I have content"

        mock_alfred.chat_stream = delayed_stream
        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        await tui._send_message("Test")

        from alfred.interfaces.pypitui.message_panel import MessagePanel
        assistant_panels = [
            c for c in tui.conversation.children
            if isinstance(c, MessagePanel) and c._role == "assistant"
        ]
        assert len(assistant_panels) >= 1

        assistant_panel = assistant_panels[-1]
        lines = assistant_panel.render(width=80)
        rendered_text = "".join(lines)

        # Should have the actual content
        assert "Now I have content" in rendered_text, \
            f"Empty content not handled. Got: {rendered_text[:200]}"


class TestAssistantMessageWithToolCalls:
    """Tests for assistant messages with tool calls."""

    @pytest.mark.asyncio
    async def test_assistant_message_with_tool_call_renders_both(self, mock_alfred, mock_terminal):
        """Verify assistant messages with tool calls render both text and tool."""
        from alfred.agent import ToolStart
        from alfred.interfaces.pypitui.message_panel import MessagePanel
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Set up current assistant message
        assistant_msg = MessagePanel(role="assistant", content="Let me search...")
        tui._current_assistant_msg = assistant_msg
        tui.conversation.add_child(assistant_msg)

        # Add tool call
        tui._tool_callback(ToolStart(
            tool_call_id="call-1",
            tool_name="search_memories",
            arguments={"query": "test"}
        ))

        # Add more content after tool
        assistant_msg.set_content("Let me search... Found it!")

        # Render
        lines = assistant_msg.render(width=80)
        rendered_text = "".join(lines)

        # Both text and tool should be visible
        assert "search_memories" in rendered_text, "Tool call not rendered"
        assert "Found it" in rendered_text, "Post-tool content not rendered"

    @pytest.mark.asyncio
    async def test_tool_call_before_text_arrives(self, mock_alfred, mock_terminal):
        """Verify tool calls render correctly when added before text content."""
        from alfred.agent import ToolStart
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Tool callback creates the assistant message
        event = ToolStart(tool_call_id="call-1", tool_name="bash", arguments={"command": "ls"})
        tui._tool_callback(event)

        # Now add text content
        assert tui._current_assistant_msg is not None
        tui._current_assistant_msg.set_content("Running command...")

        # Render
        lines = tui._current_assistant_msg.render(width=80)
        rendered_text = "".join(lines)

        # Both should be visible
        assert "bash" in rendered_text, "Tool not in render"
        assert "Running command" in rendered_text, "Text not in render"


class TestMessagePanelContentBlocks:
    """Tests for MessagePanel content block architecture."""

    def test_content_blocks_created_for_simple_text(self):
        """Verify content blocks are created for simple text."""
        from alfred.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(role="assistant", content="Hello world")

        # Should have content blocks
        assert len(panel._content_blocks) >= 1, "Should have at least one content block"

        # First block should be text
        first_block = panel._content_blocks[0]
        assert first_block.type == "text", f"Expected text block, got {first_block.type}"
        assert "Hello" in first_block.content, "Content not in block"

    def test_content_blocks_with_tool_call(self):
        """Verify content blocks include tool calls."""
        from alfred.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(role="assistant", content="Before tool")
        panel.add_tool_call("remember", "call-1")
        panel.set_content("Before tool After tool")

        # Should have multiple blocks
        assert len(panel._content_blocks) >= 2, "Should have text + tool blocks"

        # Check types
        types = [b.type for b in panel._content_blocks]
        assert "text" in types, "Should have text block"
        assert "tool" in types, "Should have tool block"

    def test_rendered_output_contains_all_content(self):
        """Verify render() output contains all content blocks."""
        from alfred.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(role="assistant", content="First part ")
        panel.add_tool_call("search", "call-1")
        panel.set_content("First part Second part")

        lines = panel.render(width=80)
        rendered = "".join(lines)

        # All content should appear
        assert "First part" in rendered, "First part not in render"
        assert "Second part" in rendered, "Second part not in render"
        assert "search" in rendered, "Tool name not in render"


class TestRegressionMessagePanelEmptyRender:
    """Regression tests for empty render issues."""

    def test_message_panel_empty_content_renders_border_only(self):
        """Verify empty content still renders border structure."""
        from alfred.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(role="assistant", content="")
        lines = panel.render(width=40)

        # Should have at least top border, title area, bottom border
        assert len(lines) >= 3, "Should render border structure even with empty content"

        # Should have Alfred title
        assert any("Alfred" in line for line in lines), "Should have title"

    def test_set_content_updates_render(self):
        """Verify set_content() updates rendered output."""
        from alfred.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(role="assistant", content="Initial")

        # Initial render
        lines1 = panel.render(width=40)
        text1 = "".join(lines1)
        assert "Initial" in text1

        # Update content
        panel.set_content("Updated content here")

        # New render
        lines2 = panel.render(width=40)
        text2 = "".join(lines2)

        assert "Updated" in text2, "Updated content not in render"
        assert "Initial" not in text2, "Old content still in render"

    def test_content_blocks_rebuilt_on_set_content(self):
        """Verify content blocks are rebuilt when content changes."""
        from alfred.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(role="assistant", content="First")

        panel.set_content("Second message with more content")

        # Should still have blocks
        assert len(panel._content_blocks) >= 1, "Content blocks should exist after set_content"

        # Content should be updated
        if panel._content_blocks:
            assert "Second" in panel._content_blocks[0].content, "Block content not updated"


class TestMockTerminalIntegration:
    """Integration tests using MockTerminal."""

    @pytest.mark.asyncio
    async def test_full_conversation_render_via_mock_terminal(self, mock_alfred, mock_terminal):
        """Verify full conversation renders correctly through MockTerminal."""
        from alfred.interfaces.pypitui.tui import AlfredTUI

        tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

        # Simulate user message
        tui._on_submit("Hello Alfred")

        # Send and get response
        await tui._send_message("Hello Alfred")

        # Render the TUI
        tui.tui.render_frame()

        # Check conversation has content
        from alfred.interfaces.pypitui.message_panel import MessagePanel
        panels = [c for c in tui.conversation.children if isinstance(c, MessagePanel)]

        assert len(panels) >= 2, "Should have user + assistant panels"

        # Check each panel renders with content
        for panel in panels:
            lines = panel.render(width=80)
            rendered = "".join(lines)
            # Should have some content (not just empty borders)
            assert len(rendered) > 20, f"Panel render seems empty: {rendered}"

    def test_message_panel_different_widths(self, mock_terminal):
        """Verify MessagePanel renders correctly at different widths."""
        from alfred.interfaces.pypitui.message_panel import MessagePanel

        content = "This is a test message that might wrap at narrow widths."
        panel = MessagePanel(role="assistant", content=content)

        # Test various widths
        for width in [40, 60, 80, 100]:
            lines = panel.render(width=width)
            rendered = "".join(lines)

            # Should always have Alfred title
            assert "Alfred" in rendered, f"No title at width {width}"

            # Content should be present (might be wrapped)
            assert "test" in rendered or "This" in rendered, \
                f"Content missing at width {width}: {rendered[:100]}"

    def test_streaming_content_accumulation(self, mock_terminal):
        """Verify content accumulates correctly during simulated streaming."""
        from alfred.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(role="assistant", content="")

        # Simulate streaming chunks
        chunks = ["First", " ", "second", " ", "third."]
        accumulated = ""

        for chunk in chunks:
            accumulated += chunk
            panel.set_content(accumulated)

            # Verify render at each step
            lines = panel.render(width=80)
            rendered = "".join(lines)

            assert accumulated in rendered or chunk in rendered, \
                f"Chunk '{chunk}' not in render. Accumulated: {accumulated}"


class TestEdgeCases:
    """Edge case tests for message rendering."""

    def test_very_long_content_renders(self):
        """Verify very long content doesn't break rendering."""
        from alfred.interfaces.pypitui.message_panel import MessagePanel

        long_content = "Word " * 500  # Very long content
        panel = MessagePanel(role="assistant", content=long_content)

        lines = panel.render(width=80)

        # Should render many lines
        assert len(lines) > 10, "Long content should produce many lines"

        # All content should be present
        rendered = "".join(lines)
        assert "Word" in rendered, "Long content not rendered"

    def test_unicode_content_renders(self):
        """Verify unicode content renders correctly."""
        from alfred.interfaces.pypitui.message_panel import MessagePanel

        unicode_content = "Hello 世界 🌍 émojis"
        panel = MessagePanel(role="assistant", content=unicode_content)

        lines = panel.render(width=80)
        rendered = "".join(lines)

        # Content should be present
        assert "Hello" in rendered, "ASCII part not rendered"
        assert "世界" in rendered, "Unicode not rendered"

    def test_multiple_consecutive_set_content_calls(self):
        """Verify multiple set_content calls work correctly."""
        from alfred.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(role="assistant", content="Start")

        # Multiple rapid updates (simulating streaming)
        for i in range(10):
            panel.set_content(f"Message {i}")

        # Final render should have last message
        lines = panel.render(width=80)
        rendered = "".join(lines)

        assert "Message 9" in rendered, "Final message not in render"
