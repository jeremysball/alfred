#!/usr/bin/env python3
"""Simple test to diagnose overlapping borders using MockTerminal."""

from pypitui import Container, MockTerminal
from src.interfaces.pypitui.message_panel import MessagePanel
from src.interfaces.pypitui.patched_tui import PatchedTUI


def main():
    # Small terminal to force scrollback quickly
    terminal = MockTerminal(cols=60, rows=10)
    tui = PatchedTUI(terminal, anchor_top=False)

    conversation = Container()
    tui.add_child(conversation)

    tui.start()

    print("=== Frame 1: Adding Alfred message ===")
    msg1 = MessagePanel(role="assistant", content="Hello! I'm Alfred.", terminal_width=60)
    conversation.add_child(msg1)
    tui.render_frame()

    output1 = terminal.get_output()
    print(f"Output length: {len(output1)}")
    print(f"Newlines emitted: {output1.count(chr(10))}")
    print(f"Emitted scrollback: {tui._emitted_scrollback_lines}")
    print(f"Previous lines count: {len(tui._previous_lines)}")
    print()

    terminal.clear_buffer()

    print("=== Frame 2: Adding User message ===")
    msg2 = MessagePanel(role="user", content="How can I make you more human?", terminal_width=60)
    conversation.add_child(msg2)
    tui.render_frame()

    output2 = terminal.get_output()
    print(f"Output length: {len(output2)}")
    print(f"Newlines emitted: {output2.count(chr(10))}")
    print(f"Emitted scrollback: {tui._emitted_scrollback_lines}")
    print(f"Previous lines count: {len(tui._previous_lines)}")
    print()

    # Show the actual rendered lines
    print("=== Rendered lines (last 15) ===")
    for i, line in enumerate(tui._previous_lines[-15:]):
        # Strip ANSI for readability
        import re
        clean = re.sub(r'\x1b\[[0-9;]*m', '', line)
        print(f"  {i}: {clean[:50]}")

    terminal.clear_buffer()

    print("\n=== Frame 3: Adding another Alfred message ===")
    msg3 = MessagePanel(role="assistant", content="That's an interesting question! I could work on being more conversational and less formal.", terminal_width=60)
    conversation.add_child(msg3)
    tui.render_frame()

    output3 = terminal.get_output()
    print(f"Output length: {len(output3)}")
    print(f"Newlines emitted: {output3.count(chr(10))}")
    print(f"Emitted scrollback: {tui._emitted_scrollback_lines}")
    print(f"Previous lines count: {len(tui._previous_lines)}")
    print()

    print("=== Rendered lines (last 20) ===")
    for i, line in enumerate(tui._previous_lines[-20:]):
        import re
        clean = re.sub(r'\x1b\[[0-9;]*m', '', line)
        print(f"  {i}: {clean[:50]}")

    tui.stop()

    print("\n\n=== Checking for border issues ===")
    # Look for patterns that suggest overlapping
    prev_lines = tui._previous_lines
    for i in range(len(prev_lines) - 1):
        curr = prev_lines[i]
        next_line = prev_lines[i + 1]

        # Check if current line ends with bottom border and next starts with top border
        # (This would indicate overlap)
        curr_clean = re.sub(r'\x1b\[[0-9;]*m', '', curr).strip()
        next_clean = re.sub(r'\x1b\[[0-9;]*m', '', next_line).strip()

        # Check for ┌ immediately after ┘ or └
        if (curr_clean.endswith(('┘', '└')) and
            next_clean.startswith('┌')):
            print(f"POTENTIAL OVERLAP at line {i}:")
            print(f"  Line {i}: {curr_clean[:40]}")
            print(f"  Line {i+1}: {next_clean[:40]}")


if __name__ == "__main__":
    import re
    main()
