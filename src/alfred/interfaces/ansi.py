"""ANSI escape codes for terminal colors and styles.

The agent can use placeholder syntax in responses:
    {cyan}colored text{reset} or {bold}bold text{reset}

Placeholders are replaced with actual ANSI codes before display.

Available placeholders:
  Colors: {black}, {red}, {green}, {yellow}, {blue}, {magenta}, {cyan}, {white}
  Bright: {bright_black}, {bright_red}, {bright_green}, {bright_yellow},
          {bright_blue}, {bright_magenta}, {bright_cyan}, {bright_white}
  Backgrounds: {on_red}, {on_green}, etc. (prefix color with 'on_')
  Styles: {bold}, {dim}, {italic}, {underline}, {blink}, {reverse}, {strike}
  Reset: {reset} - always use this to end coloring!

Example:
    "{cyan}command{reset} executed {bold}{green}successfully{reset}"
"""

from __future__ import annotations

# ANSI escape codes
_CODES = {
    # Reset
    "reset": "\033[0m",
    # Styles
    "bold": "\033[1m",
    "dim": "\033[2m",
    "italic": "\033[3m",
    "underline": "\033[4m",
    "blink": "\033[5m",
    "reverse": "\033[7m",
    "strike": "\033[9m",
    # Foreground colors
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    # Bright foreground
    "bright_black": "\033[90m",
    "bright_red": "\033[91m",
    "bright_green": "\033[92m",
    "bright_yellow": "\033[93m",
    "bright_blue": "\033[94m",
    "bright_magenta": "\033[95m",
    "bright_cyan": "\033[96m",
    "bright_white": "\033[97m",
    # Background colors
    "on_black": "\033[40m",
    "on_red": "\033[41m",
    "on_green": "\033[42m",
    "on_yellow": "\033[43m",
    "on_blue": "\033[44m",
    "on_magenta": "\033[45m",
    "on_cyan": "\033[46m",
    "on_white": "\033[47m",
    # Bright backgrounds
    "on_bright_black": "\033[100m",
    "on_bright_red": "\033[101m",
    "on_bright_green": "\033[102m",
    "on_bright_yellow": "\033[103m",
    "on_bright_blue": "\033[104m",
    "on_bright_magenta": "\033[105m",
    "on_bright_cyan": "\033[106m",
    "on_bright_white": "\033[107m",
}

# Also export raw codes for programmatic use
RESET = _CODES["reset"]
BOLD = _CODES["bold"]
DIM = _CODES["dim"]
ITALIC = _CODES["italic"]
UNDERLINE = _CODES["underline"]
BLINK = _CODES["blink"]
REVERSE = _CODES["reverse"]
STRIKE = _CODES["strike"]
BLACK = _CODES["black"]
RED = _CODES["red"]
GREEN = _CODES["green"]
YELLOW = _CODES["yellow"]
BLUE = _CODES["blue"]
MAGENTA = _CODES["magenta"]
CYAN = _CODES["cyan"]
WHITE = _CODES["white"]
BRIGHT_BLACK = _CODES["bright_black"]
BRIGHT_RED = _CODES["bright_red"]
BRIGHT_GREEN = _CODES["bright_green"]
BRIGHT_YELLOW = _CODES["bright_yellow"]
BRIGHT_BLUE = _CODES["bright_blue"]
BRIGHT_MAGENTA = _CODES["bright_magenta"]
BRIGHT_CYAN = _CODES["bright_cyan"]
BRIGHT_WHITE = _CODES["bright_white"]
ON_BLACK = _CODES["on_black"]
ON_RED = _CODES["on_red"]
ON_GREEN = _CODES["on_green"]
ON_YELLOW = _CODES["on_yellow"]
ON_BLUE = _CODES["on_blue"]
ON_MAGENTA = _CODES["on_magenta"]
ON_CYAN = _CODES["on_cyan"]
ON_WHITE = _CODES["on_white"]
ON_BRIGHT_BLACK = _CODES["on_bright_black"]
ON_BRIGHT_RED = _CODES["on_bright_red"]
ON_BRIGHT_GREEN = _CODES["on_bright_green"]
ON_BRIGHT_YELLOW = _CODES["on_bright_yellow"]
ON_BRIGHT_BLUE = _CODES["on_bright_blue"]
ON_BRIGHT_MAGENTA = _CODES["on_bright_magenta"]
ON_BRIGHT_CYAN = _CODES["on_bright_cyan"]
ON_BRIGHT_WHITE = _CODES["on_bright_white"]


def apply_ansi(text: str) -> str:
    """Replace {placeholder} syntax with ANSI escape codes.

    Args:
        text: String with {color} or {style} placeholders

    Returns:
        String with ANSI escape codes

    Example:
        >>> apply_ansi("{cyan}hello{reset}")
        '\x1b[36mhello\x1b[0m'
    """
    result = text
    for placeholder, code in _CODES.items():
        result = result.replace(f"{{{placeholder}}}", code)
    return result
