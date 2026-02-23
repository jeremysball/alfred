"""Theme system for deriving colors from rich styles.

All colors in the application should use semantic names from this module
instead of hardcoded color values. This ensures colors adapt when users
change their rich console theme.

Usage:
    from src.theme import Theme

    # Use semantic styles
    text.append("Hello", style=Theme.accent)
    panel = Panel(content, border_style=Theme.border_primary)

Environment Variables:
    ALFRED_THEME: Set to "dark", "light", "high_contrast", "minimal",
                  "solarized_dark", or "solarized_light" to select a theme.

    RICH_STYLE: Set to a rich style name to customize the underlying
                rich console theme.
"""


class Theme:
    """Semantic color names that derive from rich's style system.

    These styles will automatically adapt when the user changes their
    rich console theme (via RICH_STYLE environment variable or
    custom console configuration).
    """

    # Primary accent colors - used for highlights and emphasis
    primary: str = "cyan"
    secondary: str = "blue"
    accent: str = "green"

    # Semantic status colors
    success: str = "green"
    warning: str = "yellow"
    error: str = "red"
    info: str = "blue"

    # UI element colors
    border_primary: str = "cyan"
    border_secondary: str = "blue"
    border_success: str = "green"
    border_warning: str = "yellow"
    border_error: str = "red"

    # Text styling
    text_primary: str = "white"
    text_secondary: str = "dim"
    text_muted: str = "dim"
    text_highlight: str = "bold"

    # Data visualization colors
    metric_input: str = "cyan"
    metric_output: str = "green"
    metric_cache: str = "yellow"
    metric_reasoning: str = "magenta"
    metric_context: str = "white"

    # Memory/session indicators
    memory: str = "yellow"
    session: str = "cyan"
    prompt_section: str = "green"

    # Interactive elements
    spinner: str = "cyan"
    prompt: str = "green"
    cursor: str = "reverse"
    selection: str = "bold cyan"

    # Role-based message styling (using color indices for distinctness)
    # These use 256-color palette for consistent distinct appearance
    role_user: str = "color(23)"      # Dark slate blue
    role_assistant: str = "color(24)" # Dark teal

    # Panel styling for tool calls
    tool_normal: str = "dim blue"
    tool_error: str = "red"


def get_style(name: str) -> str:
    """Get a style by name from the Theme.

    Args:
        name: The attribute name from Theme class

    Returns:
        The style string, or empty string if not found
    """
    return getattr(Theme, name, "")


def style_exists(name: str) -> bool:
    """Check if a theme style exists.

    Args:
        name: The attribute name to check

    Returns:
        True if the style exists in Theme
    """
    return hasattr(Theme, name)
