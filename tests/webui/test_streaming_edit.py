"""Browser tests for inline message editing."""

from __future__ import annotations

import pytest
from playwright.async_api import Page, expect

pytestmark = [pytest.mark.asyncio, pytest.mark.slow]


async def _wait_for_ui(page: Page) -> None:
    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )


async def _append_message(
    page: Page,
    *,
    role: str,
    content: str,
    message_id: str,
    editable: bool = False,
) -> None:
    await page.evaluate(
        """
        ({ role, content, messageId, editable }) => {
          const messageList = document.getElementById('message-list');
          const message = document.createElement('chat-message');
          message.setAttribute('role', role);
          message.setAttribute('content', content);
          message.setAttribute('message-id', messageId);
          if (editable) {
            message.setAttribute('editable', 'true');
          }
          messageList.appendChild(message);
        }
        """,
        {
            "role": role,
            "content": content,
            "messageId": message_id,
            "editable": editable,
        },
    )


async def test_pencil_button_visible_on_last_user_message(websocket_server, page_helper) -> None:
    """Editable user messages should expose the inline edit control."""
    page = page_helper
    await _wait_for_ui(page)
    await _append_message(
        page,
        role="user",
        content="Test message",
        message_id="test-msg-1",
        editable=True,
    )

    pencil_button = page.locator("chat-message[role='user'] [data-action='edit']")
    await expect(pencil_button).to_be_visible()
    await expect(pencil_button).to_have_attribute("aria-label", "Edit message")


async def test_pencil_button_hidden_when_not_editable(websocket_server, page_helper) -> None:
    """Non-editable user messages should not render the edit control."""
    page = page_helper
    await _wait_for_ui(page)
    await _append_message(
        page,
        role="user",
        content="Test message",
        message_id="test-msg-2",
    )

    pencil_button = page.locator("chat-message[message-id='test-msg-2'] [data-action='edit']")
    await expect(pencil_button).to_have_count(0)


async def test_pencil_button_hidden_on_assistant_messages(websocket_server, page_helper) -> None:
    """Assistant messages should not render the edit control."""
    page = page_helper
    await _wait_for_ui(page)
    await _append_message(
        page,
        role="assistant",
        content="Assistant response",
        message_id="test-msg-3",
    )

    pencil_button = page.locator("chat-message[role='assistant'] [data-action='edit']")
    await expect(pencil_button).to_have_count(0)


async def test_click_pencil_shows_inline_editor(websocket_server, page_helper) -> None:
    """Clicking edit should swap the message body for an inline editor."""
    page = page_helper
    await _wait_for_ui(page)
    await _append_message(
        page,
        role="user",
        content="Message to edit",
        message_id="test-msg-4",
        editable=True,
    )

    await page.click("chat-message[message-id='test-msg-4'] [data-action='edit']")

    textarea = page.locator("chat-message[message-id='test-msg-4'] .inline-edit-textarea")
    await expect(textarea).to_be_visible()
    await expect(textarea).to_have_value("Message to edit")
    await expect(
        page.locator("chat-message[message-id='test-msg-4'] .message.editing-inline"),
    ).to_have_count(1)


async def test_escape_cancels_inline_edit(websocket_server, page_helper) -> None:
    """Escape should close inline edit mode without saving."""
    page = page_helper
    await _wait_for_ui(page)
    await _append_message(
        page,
        role="user",
        content="Cancelable content",
        message_id="test-msg-5",
        editable=True,
    )

    await page.click("chat-message[message-id='test-msg-5'] [data-action='edit']")
    await expect(
        page.locator("chat-message[message-id='test-msg-5'] .inline-edit-textarea"),
    ).to_be_visible()

    await page.keyboard.press("Escape")

    await expect(
        page.locator("chat-message[message-id='test-msg-5'] .inline-edit-textarea"),
    ).to_have_count(0)
    await expect(page.locator("chat-message[message-id='test-msg-5']")).to_have_attribute(
        "content",
        "Cancelable content",
    )


async def test_ctrl_enter_saves_inline_edit_and_dispatches_event(
    websocket_server,
    page_helper,
) -> None:
    """Saving inline edit should emit message-edited with the updated content."""
    page = page_helper
    await _wait_for_ui(page)

    await page.evaluate(
        """
        () => {
          window.__editedEvents = [];
          document.addEventListener('message-edited', (event) => {
            window.__editedEvents.push({
              messageId: event.detail.messageId,
              oldContent: event.detail.oldContent,
              newContent: event.detail.newContent,
            });
          });
        }
        """,
    )

    await _append_message(
        page,
        role="user",
        content="Original content",
        message_id="event-test-msg",
        editable=True,
    )

    await page.click("chat-message[message-id='event-test-msg'] [data-action='edit']")
    textarea = page.locator("chat-message[message-id='event-test-msg'] .inline-edit-textarea")
    await expect(textarea).to_be_visible()
    await textarea.fill("Updated content")
    await textarea.press("Control+Enter")

    await page.wait_for_function("() => (window.__editedEvents || []).length === 1")

    edit_events = await page.evaluate("() => window.__editedEvents")
    assert len(edit_events) == 1
    assert edit_events[0]["messageId"] == "event-test-msg"
    assert edit_events[0]["oldContent"] == "Original content"
    assert edit_events[0]["newContent"] == "Updated content"


async def test_cancel_button_restores_non_editing_view(websocket_server, page_helper) -> None:
    """The inline cancel button should exit edit mode and restore the original content."""
    page = page_helper
    await _wait_for_ui(page)
    await _append_message(
        page,
        role="user",
        content="Keep me",
        message_id="test-msg-6",
        editable=True,
    )

    await page.click("chat-message[message-id='test-msg-6'] [data-action='edit']")
    await page.click("chat-message[message-id='test-msg-6'] [data-action='cancel-edit']")

    await expect(
        page.locator("chat-message[message-id='test-msg-6'] .inline-edit-textarea"),
    ).to_have_count(0)
    await expect(page.locator("chat-message[message-id='test-msg-6']")).to_have_attribute(
        "content",
        "Keep me",
    )
