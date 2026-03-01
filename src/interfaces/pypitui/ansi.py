"""ANSI escape codes for terminal colors and styles.

Use these constants to add color to TUI output.
Always pair with RESET to avoid color bleeding.

Example:
    from src.interfaces.pypitui.ansi import CYAN, GREEN, RESET

    f"{CYAN}command{RESET} executed {GREEN}successfully{RESET}"
"""

# Reset
RESET = "\033[0m"

# Styles
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
BLINK = "\033[5m"
REVERSE = "\033[7m"
STRIKE = "\033[9m"

# Foreground colors
BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

# Bright foreground colors
BRIGHT_BLACK = "\033[90m"
BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_WHITE = "\033[97m"

# Background colors (prefixed with ON_)
ON_BLACK = "\033[40m"
ON_RED = "\033[41m"
ON_GREEN = "\033[42m"
ON_YELLOW = "\033[43m"
ON_BLUE = "\033[44m"
ON_MAGENTA = "\033[45m"
ON_CYAN = "\033[46m"
ON_WHITE = "\033[47m"

# Bright background colors
ON_BRIGHT_BLACK = "\033[100m"
ON_BRIGHT_RED = "\033[101m"
ON_BRIGHT_GREEN = "\033[102m"
ON_BRIGHT_YELLOW = "\033[103m"
ON_BRIGHT_BLUE = "\033[104m"
ON_BRIGHT_MAGENTA = "\033[105m"
ON_BRIGHT_CYAN = "\033[106m"
ON_BRIGHT_WHITE = "\033[107m"
