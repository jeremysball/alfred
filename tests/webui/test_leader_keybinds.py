"""Tests for leader key bindings functionality."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from playwright.async_api import expect


@pytest.mark.asyncio
async def test_leader_search_messages(websocket_server, page_helper):
    """Test Leader > S > M opens search overlay."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    await page.focus("#message-input")
    await page.keyboard.press("Control+s")

    which_key = page.locator(".which-key")
    await expect(which_key).to_be_visible()

    await page.keyboard.press("S")
    await expect(which_key).to_contain_text("Leader + S")

    await page.keyboard.press("M")
    await expect(page.locator(".search-overlay")).to_be_visible()

    await page.keyboard.press("Escape")
    await expect(page.locator(".search-overlay")).not_to_be_visible()


@pytest.mark.asyncio
async def test_leader_dispatch_tracks_registry_path_updates(websocket_server, page_helper):
    """Test leader dispatch follows live registry path updates."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    original_binding = await page.evaluate("() => window.KeymapManager.getBinding('search.open')")

    try:
        await page.evaluate(
            """
            () => window.KeymapManager.setBinding('search.open', {
              leader: {
                path: [
                  { key: 's', label: 'Search', description: 'Search and navigation' },
                  { key: 'z', label: 'Messages', description: 'Search in conversation' },
                ],
              },
            })
            """,
        )

        await page.focus("#message-input")
        await page.keyboard.press("Control+s")

        which_key = page.locator(".which-key")
        await expect(which_key).to_be_visible()

        await page.keyboard.press("S")
        await expect(which_key).to_contain_text("Leader + S")

        keys = await which_key.locator(".which-key-key").all_text_contents()
        assert "Z" in keys
        assert "M" not in keys

        await page.keyboard.press("Z")
        await expect(page.locator(".search-overlay")).to_be_visible()
    finally:
        await page.evaluate(
            """
            (binding) => window.KeymapManager.setBinding('search.open', binding)
            """,
            original_binding,
        )


@pytest.mark.asyncio
async def test_invalid_leader_key_exits_mode_without_dispatching(websocket_server, page_helper):
    """Test invalid leader chords close the overlay without dispatching."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    await page.focus("#message-input")
    await page.keyboard.press("Control+s")

    which_key = page.locator(".which-key")
    await expect(which_key).to_be_visible()

    await page.keyboard.press("Z")
    await expect(which_key).not_to_be_visible()


@pytest.mark.asyncio
async def test_leader_quick_switcher(websocket_server, page_helper):
    """Test Leader > S > Q opens quick switcher."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    await page.focus("#message-input")
    await page.keyboard.press("Control+s")

    which_key = page.locator(".which-key")
    await expect(which_key).to_be_visible()

    await page.keyboard.press("S")
    await expect(which_key).to_contain_text("Leader + S")

    await page.keyboard.press("Q")
    await page.wait_for_timeout(100)  # Small delay for action to execute
    await expect(page.locator("#quick-switcher")).not_to_have_class("hidden")

    await page.keyboard.press("Escape")
    await expect(page.locator("#quick-switcher")).to_have_class("search-overlay hidden")


@pytest.mark.asyncio
async def test_leader_chat_focus_composer(websocket_server, page_helper):
    """Test Leader > C > F focuses composer."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    # Click elsewhere to defocus
    await page.click("#message-list")

    await page.keyboard.press("Control+s")

    which_key = page.locator(".which-key")
    await expect(which_key).to_be_visible()

    await page.keyboard.press("C")
    await expect(which_key).to_contain_text("Leader + C")

    await page.keyboard.press("F")

    # Verify composer is focused
    composer = page.locator("#message-input")
    await expect(composer).to_be_focused()


@pytest.mark.asyncio
async def test_leader_palette_command_palette(websocket_server, page_helper):
    """Test Leader > P > P opens command palette."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    await page.focus("#message-input")
    await page.keyboard.press("Control+s")

    which_key = page.locator(".which-key")
    await expect(which_key).to_be_visible()

    await page.keyboard.press("P")
    await expect(which_key).to_contain_text("Leader + P")

    await page.keyboard.press("P")
    await expect(page.locator(".command-palette")).to_be_visible()

    await page.keyboard.press("Escape")
    await expect(page.locator(".command-palette")).not_to_be_visible()


@pytest.mark.asyncio
async def test_command_palette_searches_session_commands(websocket_server, page_helper):
    """Command palette search should match both session commands."""
    page = page_helper

    await page.wait_for_function(
        "() => window.alfredCommandPalette?.open !== undefined",
        timeout=5000,
    )

    await page.evaluate("() => window.alfredCommandPalette.open()")
    palette_input = page.locator(".command-palette-input")
    await expect(palette_input).to_be_visible()

    await palette_input.fill("session")
    await page.wait_for_timeout(100)
    session_titles = await page.locator(".command-palette-result-title").all_text_contents()
    assert any("Show Current Session" in title for title in session_titles)
    assert any("View Sessions" in title for title in session_titles)

    await palette_input.fill("sessions")
    await page.wait_for_timeout(100)
    session_titles = await page.locator(".command-palette-result-title").all_text_contents()
    assert any("View Sessions" in title for title in session_titles)


@pytest.mark.asyncio
async def test_session_viewer_uses_the_shared_sheet_surface(websocket_server, page_helper):
    """/session should render in the same structured sheet language as /context."""
    page = page_helper

    summary_created_at = datetime.now(UTC) - timedelta(hours=1, minutes=12)
    summary = SimpleNamespace(
        summary_id="summary-2",
        text="Refined session summary",
        created_at=summary_created_at,
        message_count=2,
        version=2,
    )

    websocket_server.alfred.core = SimpleNamespace(
        session_manager=websocket_server.alfred.core.session_manager,
        summarizer=SimpleNamespace(load_summary=AsyncMock(return_value=summary)),
    )

    await page.wait_for_function(
        "() => window.alfredWebSocketClient?.isConnected === true",
        timeout=5000,
    )

    await page.evaluate("() => window.alfredWebSocketClient.sendCommand('/session')")

    session_viewer = page.locator("session-viewer")
    await expect(session_viewer).to_be_visible()
    await expect(session_viewer).to_contain_text("Current Session")
    await expect(session_viewer).to_contain_text("Session Overview")
    await expect(session_viewer).to_contain_text("Latest Summary")
    await expect(session_viewer).to_contain_text("Refined session summary")
    await expect(session_viewer).to_contain_text("Last Summary:")
    await expect(session_viewer).to_contain_text("Age:")
    await expect(session_viewer).to_contain_text("Delta:")


@pytest.mark.asyncio
async def test_leader_help_keyboard_help(websocket_server, page_helper):
    """Test Leader > H > H opens keyboard help."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    await page.focus("#message-input")
    await page.keyboard.press("Control+s")

    which_key = page.locator(".which-key")
    await expect(which_key).to_be_visible()

    await page.keyboard.press("H")
    await expect(which_key).to_contain_text("Leader + H")

    await page.keyboard.press("H")
    await page.wait_for_function(
        "() => window.alfredHelpSheet?.sheet?.isOpen === true",
        timeout=5000,
    )


@pytest.mark.asyncio
async def test_help_sheet_lists_the_same_chord_paths_as_which_key(websocket_server, page_helper):
    """Test keyboard help and WhichKey use the same leader-path vocabulary."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    original_binding = await page.evaluate("() => window.KeymapManager.getBinding('search.open')")
    original_path_text = await page.evaluate(
        """
        () => {
          const binding = window.KeymapManager.getBinding('search.open');
          return window.KeymapManager.formatLeaderBreadcrumb(binding.leader.path);
        }
        """,
    )
    original_prefix_text = await page.evaluate(
        """
        () => {
          const binding = window.KeymapManager.getBinding('search.open');
          return window.KeymapManager.formatLeaderBreadcrumb(binding.leader.path.slice(0, 1));
        }
        """,
    )

    try:
        await page.focus("#message-input")
        await page.keyboard.press("Control+s")
        which_key = page.locator(".which-key")
        await expect(which_key).to_be_visible()
        await page.keyboard.press("S")
        await expect(which_key.locator(".which-key-header")).to_contain_text(original_prefix_text)
        await page.keyboard.press("Escape")
        await expect(which_key).not_to_be_visible()

        await page.evaluate(
            """
            () => {
              window.alfredHelpSheet = window.alfredHelpSheet ?? new window.HelpSheet();
              window.alfredHelpSheet.show();
            }
            """,
        )
        await page.wait_for_function(
            "() => window.alfredHelpSheet?.sheet?.isOpen === true",
            timeout=5000,
        )

        help_sheet = page.locator(".keyboard-help-content")
        await expect(help_sheet).to_contain_text(original_path_text)
        updated_path_text = await page.evaluate(
            """
            () => {
              window.KeymapManager.setBinding('search.open', {
                leader: {
                  path: [
                    { key: 's', label: 'Search', description: 'Search and navigation' },
                    { key: 'z', label: 'Messages', description: 'Search in conversation' },
                  ],
                },
              });
              const binding = window.KeymapManager.getBinding('search.open');
              return window.KeymapManager.formatLeaderBreadcrumb(binding.leader.path);
            }
            """,
        )

        await expect(help_sheet).to_contain_text(updated_path_text)
        await expect(help_sheet).not_to_contain_text(original_path_text)
    finally:
        await page.evaluate(
            """
            (binding) => window.KeymapManager.setBinding('search.open', binding)
            """,
            original_binding,
        )


@pytest.mark.asyncio
async def test_leader_cancel_streaming(websocket_server, page_helper):
    """Test Leader > X > C calls cancel streaming."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    # Set up a mock cancel handler
    await page.evaluate("window.handleStopGenerating = () => { window.__testCancelCalled = true; }")

    await page.focus("#message-input")
    await page.keyboard.press("Control+s")

    which_key = page.locator(".which-key")
    await expect(which_key).to_be_visible()

    await page.keyboard.press("X")
    await expect(which_key).to_contain_text("Leader + X")

    await page.keyboard.press("C")

    # Verify cancel was called
    result = await page.evaluate("window.__testCancelCalled === true")
    assert result is True


@pytest.mark.asyncio
async def test_leader_clear_queue(websocket_server, page_helper):
    """Test Leader > X > Q clears message queue."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    # Set up a mock queue state
    await page.evaluate("window.__testQueueCleared = false; window.clearQueue = () => { window.__testQueueCleared = true; }")

    await page.focus("#message-input")
    await page.keyboard.press("Control+s")

    which_key = page.locator(".which-key")
    await expect(which_key).to_be_visible()

    await page.keyboard.press("X")
    await expect(which_key).to_contain_text("Leader + X")

    await page.keyboard.press("Q")

    # Verify clearQueue was called
    result = await page.evaluate("window.__testQueueCleared === true")
    assert result is True


@pytest.mark.asyncio
async def test_leader_escape_exits_leader_mode(websocket_server, page_helper):
    """Test Escape exits leader mode without timeout."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    await page.focus("#message-input")
    await page.keyboard.press("Control+s")

    which_key = page.locator(".which-key")
    await expect(which_key).to_be_visible()

    # Press Escape to exit
    await page.keyboard.press("Escape")
    await expect(which_key).not_to_be_visible()


@pytest.mark.asyncio
async def test_leader_does_not_auto_timeout(websocket_server, page_helper):
    """Test leader mode does NOT auto-timeout after 3 seconds."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    await page.focus("#message-input")
    await page.keyboard.press("Control+s")

    which_key = page.locator(".which-key")
    await expect(which_key).to_be_visible()

    # Wait 4 seconds (longer than the old 3s timeout)
    await page.wait_for_timeout(4000)

    # Leader mode should still be visible
    await expect(which_key).to_be_visible()

    # Clean up
    await page.keyboard.press("Escape")
