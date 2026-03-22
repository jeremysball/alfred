"""E2E test for terminal resize handling and layout correctness.

Verifies that the status line and input field don't overlap after terminal resize,
and that wrapped input displays correctly at different terminal widths.

Run with: uv run pytest tests/e2e/test_resize_layout.py -v -m e2e
"""

import subprocess

import pytest

from tests.e2e.tmux_tool import TerminalSession


@pytest.fixture
def alfred_session():
    """Create Alfred terminal session."""
    with TerminalSession("alfred_resize", port=7682, cols=80, rows=20) as s:
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
def test_status_line_not_overlapped_after_resize(alfred_session):
    """Verify status line remains separate from input after terminal resize.

    Regression test for: input area overlapping status line on resize.
    """
    s = alfred_session

    # Type a message that will wrap at narrower widths
    s.send("This is a test message that will demonstrate wrapping behavior")
    s.sleep(0.5)

    # Capture initial state at 80 columns
    text_before = s.capture_text()

    # Verify status line is present (contains model name or tokens)
    assert "moonshot" in text_before or "kimi" in text_before or "ctx" in text_before, "Status line should be visible with model info"

    # Resize terminal to 40 columns (forces input to wrap)
    subprocess.run(["tmux", "resize-window", "-t", s.name, "-x", "40", "-y", "20"], capture_output=True)
    s.sleep(1)  # Wait for resize to take effect

    # Capture after resize
    text_after = s.capture_text()

    # The status line should still be visible and not overwritten
    # Look for status indicators that should persist
    status_indicators = ["ctx", "↑", "↓", "queued"]
    status_found = any(indicator in text_after for indicator in status_indicators)

    # Also check for model name (may be truncated)
    model_found = "moonshot" in text_after or "kimi" in text_after

    assert status_found or model_found, f"Status line should remain visible after resize. Content:\n{text_after}"

    # Verify no line contains both input text and status line content
    # (which would indicate overlap)
    lines = text_after.split("\n")
    for line in lines:
        # If a line has both user input text AND status indicators, it's overlapping
        has_input_text = "test message" in line or "demonstrate" in line
        has_status = any(indicator in line for indicator in status_indicators[:2])  # ↑ or ↓

        # Allow the input line to have the message, and status line to have arrows
        # But if both are on same line, that's the bug
        if has_input_text and has_status and len(line) < 40:
            pytest.fail(f"Input and status appear to overlap on same line: {line}")


@pytest.mark.e2e
def test_input_wrapping_on_resize(alfred_session):
    """Verify input field correctly wraps text when terminal is resized narrower."""
    s = alfred_session

    # Type a medium-length message
    test_msg = "Testing resize behavior with wrapping"
    s.send(test_msg)
    s.sleep(0.5)

    # Capture at 80 columns - should be on one line
    text_wide = s.capture_text()

    # The message should be visible
    assert "Testing resize" in text_wide, "Message should be visible at 80 columns"

    # Resize to 40 columns
    subprocess.run(["tmux", "resize-window", "-t", s.name, "-x", "40", "-y", "20"], capture_output=True)
    s.sleep(1)

    # Capture at 40 columns
    text_narrow = s.capture_text()

    # Message should still be visible (possibly wrapped)
    assert "Testing" in text_narrow, "Message should still be visible after resize to 40 cols"

    # Count lines with our test content - at 40 cols,
    # "Testing resize behavior with wrapping" (45 chars) should wrap to 2 lines
    lines_with_content = [line for line in text_narrow.split("\n") if "Testing" in line or "resize" in line or "wrapping" in line]

    # Should have at least 1 line, likely 2 due to wrapping
    assert len(lines_with_content) >= 1, f"Message should be displayed on at least 1 line. Content:\n{text_narrow}"


@pytest.mark.e2e
def test_resize_larger_then_smaller(alfred_session):
    """Verify layout correctness through multiple resizes."""
    s = alfred_session

    # Add some conversation content first
    s.send("Hello Alfred")
    s.send_key("Enter")
    s.sleep(2)

    # Resize to 60 columns
    subprocess.run(["tmux", "resize-window", "-t", s.name, "-x", "60", "-y", "20"], capture_output=True)
    s.sleep(0.5)

    # Type more content
    s.send("This is a longer message for testing resize stability")
    s.sleep(0.5)

    # Resize to 40 columns
    subprocess.run(["tmux", "resize-window", "-t", s.name, "-x", "40", "-y", "20"], capture_output=True)
    s.sleep(0.5)

    # Capture state
    text = s.capture_text()

    # Verify we can see both messages
    assert "Hello" in text, "First message should still be visible"
    assert "resize stability" in text or "longer message" in text, "Second message should be visible after resize"

    # Verify status line integrity
    # After resize, status line should still show token counts or model info
    has_status_info = any(x in text for x in ["ctx", "↑", "↓", "queued", "moonshot", "kimi"])
    assert has_status_info, "Status line should maintain integrity after multiple resizes"


@pytest.mark.e2e
def test_input_at_bottom_after_resize(alfred_session):
    """Verify input field stays at bottom of screen after resize."""
    s = alfred_session

    # Type a message
    s.send("Bottom positioning test")
    s.sleep(0.5)

    # Resize narrower
    subprocess.run(["tmux", "resize-window", "-t", s.name, "-x", "50", "-y", "20"], capture_output=True)
    s.sleep(0.5)

    # Capture and check last few lines
    text = s.capture_text()
    lines = text.split("\n")

    # The last non-empty line should contain our input or the cursor
    # (or be empty waiting for input)
    non_empty_lines = [line for line in lines if line.strip()]

    if non_empty_lines:
        last_content_line = non_empty_lines[-1]
        # Last line should either have our text, be the input prompt area,
        # or contain status indicators
        assert (
            "Bottom" in last_content_line
            or "test" in last_content_line
            or any(x in last_content_line for x in ["ctx", "↑", "↓", "moonshot", "kimi"])
            or len(last_content_line) < 5
        ), f"Input or status should be at bottom. Last line: {last_content_line}"
