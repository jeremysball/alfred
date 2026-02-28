#!/usr/bin/env python3
"""Test to diagnose overlapping borders in chat interface."""

import time
from pypitui import Container, ProcessTerminal, Text
from src.interfaces.pypitui.message_panel import MessagePanel

# Use PatchedTUI from the app
from src.interfaces.pypitui.patched_tui import PatchedTUI


def main():
    terminal = ProcessTerminal()
    tui = PatchedTUI(terminal, anchor_top=False)

    # Main conversation container
    conversation = Container()
    tui.add_child(conversation)

    # Status line
    from src.interfaces.pypitui.status_line import StatusLine
    status = StatusLine()
    status.update(model="test", ctx=0, in_tokens=0, out_tokens=0)
    tui.add_child(status)

    # Input placeholder
    input_placeholder = Text("Message Alfred...", padding_x=1)
    tui.add_child(input_placeholder)

    tui.start()

    try:
        term_width = terminal.get_size()[0]

        # Add first message (Alfred)
        print("Adding Alfred message...")
        msg1 = MessagePanel(role="assistant", content="Hello! I'm Alfred.", terminal_width=term_width)
        conversation.add_child(msg1)
        tui.request_render()
        tui.render_frame()
        time.sleep(1)

        # Add second message (User)
        print("Adding User message...")
        msg2 = MessagePanel(role="user", content="How can I make you more human?", terminal_width=term_width)
        conversation.add_child(msg2)
        tui.request_render()
        tui.render_frame()
        time.sleep(1)

        # Add third message (Alfred)
        print("Adding second Alfred message...")
        msg3 = MessagePanel(role="assistant", content="That's an interesting question!", terminal_width=term_width)
        conversation.add_child(msg3)
        tui.request_render()
        tui.render_frame()
        time.sleep(1)

        # Print debug info
        print(f"\n\n=== Debug Info ===")
        print(f"Total lines rendered: {len(tui._previous_lines)}")
        print(f"Emitted scrollback lines: {tui._emitted_scrollback_lines}")
        print(f"Terminal height: {terminal.get_size()[1]}")
        print(f"Max lines rendered: {tui._max_lines_rendered}")

        # Keep rendering to see if borders get corrupted
        for i in range(5):
            tui.request_render()
            tui.render_frame()
            time.sleep(0.5)

        print("\n\nTest complete. Check if borders overlap.")
        input("Press Enter to exit...")

    finally:
        tui.stop()


if __name__ == "__main__":
    main()
