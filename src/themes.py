"""Predefined themes for Alfred CLI.

Usage:
    # In your shell config or before running alfred:
    export RICH_STYLE=default  # Use rich's default theme

    # Or use Alfred's built-in themes:
    export ALFRED_THEME=dark   # Use dark theme
    export ALFRED_THEME=light  # Use light theme
"""

from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True)
class ThemeConfig:
    """Complete theme configuration for Alfred.

    All colors should be valid rich style names or color values.
    """

    # Primary accent colors
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

    # Role-based message styling
    role_user: str = "color(23)"
    role_assistant: str = "color(24)"

    # Panel styling for tool calls
    tool_normal: str = "dim blue"
    tool_error: str = "red"

    @classmethod
    def dark(cls) -> Self:
        """Dark theme optimized for terminal use (default)."""
        return cls()

    @classmethod
    def light(cls) -> Self:
        """Light theme for light terminal backgrounds."""
        return cls(
            # Primary accent colors - darker for light backgrounds
            primary="dark_blue",
            secondary="blue",
            accent="dark_green",

            # Semantic status colors - adjusted for contrast
            success="dark_green",
            warning="dark_orange",
            error="dark_red",
            info="dark_blue",

            # UI element colors
            border_primary="dark_blue",
            border_secondary="blue",
            border_success="dark_green",
            border_warning="dark_orange",
            border_error="dark_red",

            # Text styling - dark text on light background
            text_primary="black",
            text_secondary="dim",
            text_muted="dim",
            text_highlight="bold",

            # Data visualization colors
            metric_input="dark_blue",
            metric_output="dark_green",
            metric_cache="dark_orange",
            metric_reasoning="dark_magenta",
            metric_context="black",

            # Memory/session indicators
            memory="dark_orange",
            session="dark_blue",
            prompt_section="dark_green",

            # Interactive elements
            spinner="dark_blue",
            prompt="dark_green",
            cursor="reverse",
            selection="bold dark_blue",

            # Role-based message styling - using darker variants
            role_user="color(17)",  # Darker slate blue
            role_assistant="color(18)",  # Darker teal

            # Panel styling for tool calls
            tool_normal="dim blue",
            tool_error="dark_red",
        )

    @classmethod
    def high_contrast(cls) -> Self:
        """High contrast theme for accessibility."""
        return cls(
            # Primary accent colors - bold and distinct
            primary="bright_blue",
            secondary="bright_cyan",
            accent="bright_green",

            # Semantic status colors - very distinct
            success="bright_green",
            warning="bright_yellow",
            error="bright_red",
            info="bright_cyan",

            # UI element colors - bold variants
            border_primary="bright_blue",
            border_secondary="bright_cyan",
            border_success="bright_green",
            border_warning="bright_yellow",
            border_error="bright_red",

            # Text styling
            text_primary="bright_white",
            text_secondary="white",
            text_muted="white",
            text_highlight="bold bright_white",

            # Data visualization colors - all bright
            metric_input="bright_cyan",
            metric_output="bright_green",
            metric_cache="bright_yellow",
            metric_reasoning="bright_magenta",
            metric_context="bright_white",

            # Memory/session indicators
            memory="bright_yellow",
            session="bright_cyan",
            prompt_section="bright_green",

            # Interactive elements
            spinner="bright_cyan",
            prompt="bright_green",
            cursor="reverse",
            selection="bold bright_cyan",

            # Role-based message styling - bright variants
            role_user="color(33)",  # Bright slate blue
            role_assistant="color(34)",  # Bright teal

            # Panel styling for tool calls
            tool_normal="bright_blue",
            tool_error="bright_red",
        )

    @classmethod
    def minimal(cls) -> Self:
        """Minimal theme using only black, white, and grays."""
        return cls(
            # Primary accent colors - all neutral
            primary="white",
            secondary="dim",
            accent="white",

            # Semantic status colors - use symbols/text instead
            success="white",
            warning="white",
            error="white",
            info="white",

            # UI element colors - all neutral
            border_primary="dim",
            border_secondary="dim",
            border_success="dim",
            border_warning="dim",
            border_error="dim",

            # Text styling
            text_primary="white",
            text_secondary="dim",
            text_muted="dim",
            text_highlight="bold",

            # Data visualization colors - all neutral
            metric_input="white",
            metric_output="white",
            metric_cache="dim",
            metric_reasoning="dim",
            metric_context="white",

            # Memory/session indicators
            memory="dim",
            session="white",
            prompt_section="white",

            # Interactive elements
            spinner="white",
            prompt="white",
            cursor="reverse",
            selection="bold",

            # Role-based message styling - subtle grayscale
            role_user="color(240)",  # Dark gray
            role_assistant="color(245)",  # Medium gray

            # Panel styling for tool calls
            tool_normal="dim",
            tool_error="white",
        )

    @classmethod
    def solarized_dark(cls) -> Self:
        """Solarized Dark theme using standard 16-color palette."""
        return cls(
            primary="cyan",
            secondary="blue",
            accent="green",
            success="green",
            warning="yellow",
            error="red",
            info="blue",
            border_primary="cyan",
            border_secondary="blue",
            border_success="green",
            border_warning="yellow",
            border_error="red",
            text_primary="white",
            text_secondary="bright_black",
            text_muted="bright_black",
            text_highlight="bold",
            metric_input="cyan",
            metric_output="green",
            metric_cache="yellow",
            metric_reasoning="magenta",
            metric_context="white",
            memory="yellow",
            session="cyan",
            prompt_section="green",
            spinner="cyan",
            prompt="green",
            cursor="reverse",
            selection="bold cyan",
            role_user="color(23)",
            role_assistant="color(24)",
            tool_normal="dim blue",
            tool_error="red",
        )

    @classmethod
    def solarized_light(cls) -> Self:
        """Solarized Light theme using standard 16-color palette."""
        return cls(
            primary="dark_blue",
            secondary="blue",
            accent="dark_green",
            success="dark_green",
            warning="dark_orange",
            error="dark_red",
            info="blue",
            border_primary="dark_blue",
            border_secondary="blue",
            border_success="dark_green",
            border_warning="dark_orange",
            border_error="dark_red",
            text_primary="black",
            text_secondary="dim",
            text_muted="dim",
            text_highlight="bold",
            metric_input="dark_blue",
            metric_output="dark_green",
            metric_cache="dark_orange",
            metric_reasoning="dark_magenta",
            metric_context="black",
            memory="dark_orange",
            session="dark_blue",
            prompt_section="dark_green",
            spinner="dark_blue",
            prompt="dark_green",
            cursor="reverse",
            selection="bold dark_blue",
            role_user="color(17)",
            role_assistant="color(18)",
            tool_normal="dim blue",
            tool_error="dark_red",
        )


# Predefined theme presets
THEMES: dict[str, ThemeConfig] = {
    "dark": ThemeConfig.dark(),
    "light": ThemeConfig.light(),
    "high_contrast": ThemeConfig.high_contrast(),
    "minimal": ThemeConfig.minimal(),
    "solarized_dark": ThemeConfig.solarized_dark(),
    "solarized_light": ThemeConfig.solarized_light(),
}


def get_theme(name: str | None = None) -> ThemeConfig:
    """Get a theme by name.

    Args:
        name: Theme name (dark, light, high_contrast, minimal, solarized_dark,
              solarized_light). If None, checks ALFRED_THEME env var,
              otherwise returns dark theme.

    Returns:
        ThemeConfig instance

    Examples:
        >>> theme = get_theme("light")
        >>> theme = get_theme()  # From ALFRED_THEME env var or default dark
    """
    import os

    if name is None:
        name = os.environ.get("ALFRED_THEME", "dark")

    return THEMES.get(name.lower(), ThemeConfig.dark())


def list_themes() -> list[str]:
    """List available theme names.

    Returns:
        List of theme names
    """
    return list(THEMES.keys())


def apply_theme(theme_config: ThemeConfig) -> None:
    """Apply a theme configuration to the global Theme.

    This updates the Theme class attributes to use the values
    from the provided theme configuration.

    Args:
        theme_config: ThemeConfig instance to apply
    """
    from src.theme import Theme

    Theme.primary = theme_config.primary
    Theme.secondary = theme_config.secondary
    Theme.accent = theme_config.accent
    Theme.success = theme_config.success
    Theme.warning = theme_config.warning
    Theme.error = theme_config.error
    Theme.info = theme_config.info
    Theme.border_primary = theme_config.border_primary
    Theme.border_secondary = theme_config.border_secondary
    Theme.border_success = theme_config.border_success
    Theme.border_warning = theme_config.border_warning
    Theme.border_error = theme_config.border_error
    Theme.text_primary = theme_config.text_primary
    Theme.text_secondary = theme_config.text_secondary
    Theme.text_muted = theme_config.text_muted
    Theme.text_highlight = theme_config.text_highlight
    Theme.metric_input = theme_config.metric_input
    Theme.metric_output = theme_config.metric_output
    Theme.metric_cache = theme_config.metric_cache
    Theme.metric_reasoning = theme_config.metric_reasoning
    Theme.metric_context = theme_config.metric_context
    Theme.memory = theme_config.memory
    Theme.session = theme_config.session
    Theme.prompt_section = theme_config.prompt_section
    Theme.spinner = theme_config.spinner
    Theme.prompt = theme_config.prompt
    Theme.cursor = theme_config.cursor
    Theme.selection = theme_config.selection
    Theme.role_user = theme_config.role_user
    Theme.role_assistant = theme_config.role_assistant
    Theme.tool_normal = theme_config.tool_normal
    Theme.tool_error = theme_config.tool_error
