"""ANSI color codes and constants for PyPiTUI components."""

# ANSI color codes for borders
CYAN = "\x1b[36m"
GREEN = "\x1b[32m"
RED = "\x1b[31m"
YELLOW = "\x1b[33m"
RESET = "\x1b[0m"
DIM = "\x1b[2m"
BOLD = "\x1b[1m"

# Dim border colors for tool panels (less prominent than messages)
DIM_BLUE = "\x1b[34;2m"
DIM_GREEN = "\x1b[32;2m"
DIM_RED = "\x1b[31;2m"

# Tool call settings
MAX_TOOL_OUTPUT = 500

# Markdown rendering settings
USE_MARKDOWN_RENDERING = True
