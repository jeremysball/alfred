"""E2E test for CLI scrollback functionality.

Verifies that conversation history flows into terminal scrollback buffer
and can be viewed by scrolling up.

Run with: uv run pytest tests/e2e/test_cli_scrollback.py -v -m e2e
"""

import pytest

from tests.e2e.tmux_tool import TerminalSession


@pytest.fixture
def alfred_session():
    """Create Alfred terminal session."""
    with TerminalSession("alfred_scrollback", port=7681, cols=80, rows=20) as s:
        # Start bash to avoid shell compatibility issues
        s.send("bash")
        s.send_key("Enter")
        s.sleep(0.3)

        # Start Alfred with environment
        s.send("cd /workspace/alfred-prd && export $(grep -v '^#' .env | xargs) && .venv/bin/alfred")
        s.send_key("Enter")
        s.sleep(3)  # Wait for Alfred to start

        yield s

        # Cleanup: exit Alfred and close session
        s.send_key("C-c")
        s.sleep(0.3)
        s.send("exit")
        s.send_key("Enter")
        s.sleep(0.3)


@pytest.mark.e2e
def test_many_messages_visible_in_scrollback(alfred_session):
    """Verify 25+ messages flow into scrollback and early ones are visible."""
    s = alfred_session

    # Send 25 short messages
    for i in range(1, 26):
        s.send(f"msg{i}")
        s.send_key("Enter")
        s.sleep(0.5)  # Brief pause between messages

    # Wait for last message to appear
    s.sleep(1)

    # Capture terminal text
    text = s.capture_text()

    # Verify early messages appear (they would scroll off screen without scrollback)
    # With 25 messages in a 20-row terminal, early ones must be in scrollback
    assert "msg1" in text, "First message should be in terminal buffer (scrollback working)"
    assert "msg5" in text, "Early messages should be in terminal buffer"
    assert "msg25" in text, "Last message should be visible"

    # Verify user role indicators are present (MessagePanel integration)
    assert "You" in text, "User messages should show 'You' title from MessagePanel"


@pytest.mark.e2e
def test_long_response_flows_to_scrollback(alfred_session):
    """Verify long responses (50+ lines) flow into scrollback."""
    s = alfred_session

    # Request a long response
    s.send("Count from 1 to 30, one number per line")
    s.send_key("Enter")

    # Wait for LLM response (needs time to generate)
    s.sleep(15)

    # Capture terminal text
    text = s.capture_text()

    # Verify response content is present
    # The response should contain multiple numbers
    numbers_found = sum(1 for i in range(1, 31) if str(i) in text)
    assert numbers_found >= 10, f"Expected 10+ numbers in output, found {numbers_found}"

    # Verify Alfred title present (MessagePanel integration)
    assert "Alfred" in text, "Assistant messages should show 'Alfred' title from MessagePanel"
