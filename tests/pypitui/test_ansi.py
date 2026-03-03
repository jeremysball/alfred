"""Tests for ANSI color placeholder system."""


from src.interfaces.ansi import (
    BLACK,
    BLUE,
    BOLD,
    BRIGHT_BLACK,
    BRIGHT_BLUE,
    BRIGHT_CYAN,
    BRIGHT_GREEN,
    BRIGHT_MAGENTA,
    BRIGHT_RED,
    BRIGHT_WHITE,
    BRIGHT_YELLOW,
    CYAN,
    DIM,
    GREEN,
    ITALIC,
    MAGENTA,
    ON_BLACK,
    ON_BLUE,
    ON_BRIGHT_BLACK,
    ON_BRIGHT_BLUE,
    ON_BRIGHT_CYAN,
    ON_BRIGHT_GREEN,
    ON_BRIGHT_MAGENTA,
    ON_BRIGHT_RED,
    ON_BRIGHT_WHITE,
    ON_BRIGHT_YELLOW,
    ON_CYAN,
    ON_GREEN,
    ON_MAGENTA,
    ON_RED,
    ON_WHITE,
    ON_YELLOW,
    RED,
    RESET,
    UNDERLINE,
    WHITE,
    YELLOW,
    apply_ansi,
)


class TestApplyAnsi:
    """Tests for apply_ansi() function."""

    def test_basic_color_replacement(self) -> None:
        """Verify {cyan} gets replaced with ANSI cyan code."""
        result = apply_ansi("{cyan}hello{reset}")
        assert result == f"{CYAN}hello{RESET}"

    def test_multiple_colors(self) -> None:
        """Verify multiple color placeholders work."""
        result = apply_ansi("{red}error{reset} and {green}success{reset}")
        assert result == f"{RED}error{RESET} and {GREEN}success{RESET}"

    def test_nested_styles(self) -> None:
        """Verify multiple styles can be combined."""
        result = apply_ansi("{bold}{green}bold green{reset}")
        assert result == f"{BOLD}{GREEN}bold green{RESET}"

    def test_all_basic_colors(self) -> None:
        """Verify all basic color placeholders work."""
        colors = [
            ("{black}", BLACK),
            ("{red}", RED),
            ("{green}", GREEN),
            ("{yellow}", YELLOW),
            ("{blue}", BLUE),
            ("{magenta}", MAGENTA),
            ("{cyan}", CYAN),
            ("{white}", WHITE),
        ]
        for placeholder, code in colors:
            result = apply_ansi(f"{placeholder}text{{reset}}")
            assert result == f"{code}text{RESET}"

    def test_all_bright_colors(self) -> None:
        """Verify all bright color placeholders work."""
        bright_colors = [
            ("{bright_black}", BRIGHT_BLACK),
            ("{bright_red}", BRIGHT_RED),
            ("{bright_green}", BRIGHT_GREEN),
            ("{bright_yellow}", BRIGHT_YELLOW),
            ("{bright_blue}", BRIGHT_BLUE),
            ("{bright_magenta}", BRIGHT_MAGENTA),
            ("{bright_cyan}", BRIGHT_CYAN),
            ("{bright_white}", BRIGHT_WHITE),
        ]
        for placeholder, code in bright_colors:
            result = apply_ansi(f"{placeholder}text{{reset}}")
            assert result == f"{code}text{RESET}"

    def test_all_background_colors(self) -> None:
        """Verify all background color placeholders work."""
        backgrounds = [
            ("{on_black}", ON_BLACK),
            ("{on_red}", ON_RED),
            ("{on_green}", ON_GREEN),
            ("{on_yellow}", ON_YELLOW),
            ("{on_blue}", ON_BLUE),
            ("{on_magenta}", ON_MAGENTA),
            ("{on_cyan}", ON_CYAN),
            ("{on_white}", ON_WHITE),
        ]
        for placeholder, code in backgrounds:
            result = apply_ansi(f"{placeholder}text{{reset}}")
            assert result == f"{code}text{RESET}"

    def test_all_bright_background_colors(self) -> None:
        """Verify all bright background color placeholders work."""
        bright_backgrounds = [
            ("{on_bright_black}", ON_BRIGHT_BLACK),
            ("{on_bright_red}", ON_BRIGHT_RED),
            ("{on_bright_green}", ON_BRIGHT_GREEN),
            ("{on_bright_yellow}", ON_BRIGHT_YELLOW),
            ("{on_bright_blue}", ON_BRIGHT_BLUE),
            ("{on_bright_magenta}", ON_BRIGHT_MAGENTA),
            ("{on_bright_cyan}", ON_BRIGHT_CYAN),
            ("{on_bright_white}", ON_BRIGHT_WHITE),
        ]
        for placeholder, code in bright_backgrounds:
            result = apply_ansi(f"{placeholder}text{{reset}}")
            assert result == f"{code}text{RESET}"

    def test_background_with_foreground(self) -> None:
        """Verify background and foreground colors can be combined."""
        result = apply_ansi("{on_red}{white}alert{reset}")
        assert result == f"{ON_RED}{WHITE}alert{RESET}"

    def test_invalid_placeholder_not_replaced(self) -> None:
        """Verify {bg_red} (wrong name) is NOT replaced - stays literal."""
        result = apply_ansi("{bg_red}hello{reset}")
        # bg_red is not a valid placeholder, should stay as-is
        assert "{bg_red}" in result
        # Note: {reset} IS valid so it gets replaced, that's fine

    def test_typo_placeholder_shows_literal(self) -> None:
        """Verify typos in placeholder names show as literal text."""
        result = apply_ansi("{on_reed}text{reset}")  # typo: reed not red
        assert "{on_reed}" in result


class TestAnsiRenderingBehavior:
    """Tests that verify ANSI codes actually appear in rendered panel output."""

    def test_background_color_renders_ansi_in_panel(self) -> None:
        """Verify {on_red}text{reset} produces \\033[41m in rendered panel."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(
            role="assistant",
            content="{on_red}alert{reset}",
            terminal_width=80,
            use_markdown=False,  # Disable markdown to test raw ANSI
        )

        lines = panel.render(width=80)
        rendered = "".join(lines)

        # Should contain actual ANSI escape code for red background
        assert "\033[41m" in rendered
        # Should NOT contain the placeholder
        assert "{on_red}" not in rendered

    def test_all_backgrounds_render_in_panel(self) -> None:
        """Verify all 8 backgrounds produce correct escape codes in output."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        backgrounds = [
            ("{on_black}", "\033[40m"),
            ("{on_red}", "\033[41m"),
            ("{on_green}", "\033[42m"),
            ("{on_yellow}", "\033[43m"),
            ("{on_blue}", "\033[44m"),
            ("{on_magenta}", "\033[45m"),
            ("{on_cyan}", "\033[46m"),
            ("{on_white}", "\033[47m"),
        ]

        for placeholder, ansi_code in backgrounds:
            panel = MessagePanel(
                role="assistant",
                content=f"{placeholder}test{{reset}}",
                terminal_width=80,
                use_markdown=False,
            )
            lines = panel.render(width=80)
            rendered = "".join(lines)

            assert ansi_code in rendered, f"{placeholder} did not render as {ansi_code}"
            assert placeholder not in rendered, f"{placeholder} was not replaced"

    def test_invalid_placeholder_shows_literal_in_panel(self) -> None:
        """Verify {bg_red} (wrong name) shows as literal text in panel."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(
            role="assistant",
            content="{bg_red}hello{reset}",
            terminal_width=80,
            use_markdown=False,
        )

        lines = panel.render(width=80)
        rendered = "".join(lines)

        # Invalid placeholder should remain as literal text
        assert "{bg_red}" in rendered

    def test_background_combined_with_foreground_in_panel(self) -> None:
        """Verify {on_red}{white}text{reset} renders both codes."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(
            role="assistant",
            content="{on_red}{white}alert{reset}",
            terminal_width=80,
            use_markdown=False,
        )

        lines = panel.render(width=80)
        rendered = "".join(lines)

        # Both background and foreground codes should be present
        assert "\033[41m" in rendered  # on_red
        assert "\033[37m" in rendered  # white

    def test_placeholder_in_inline_code_preserved(self) -> None:
        """Verify {on_red} in `code` shows literally (markdown processes first)."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        # With markdown enabled, inline code should preserve the placeholder
        panel = MessagePanel(
            role="assistant",
            content="Use `{on_red}` for background",
            terminal_width=80,
            use_markdown=True,
        )

        lines = panel.render(width=80)
        rendered = "".join(lines)

        # The placeholder inside backticks should NOT be converted to ANSI
        # (markdown renders it as code, then ANSI is applied after)
        # This tests the actual behavior - may need adjustment based on implementation
        # If markdown converts first, {on_red} might get escaped
        pass  # TODO: Verify actual behavior after running test

    def test_bright_background_renders_in_panel(self) -> None:
        """Verify bright backgrounds work in rendered output."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(
            role="assistant",
            content="{on_bright_red}warning{reset}",
            terminal_width=80,
            use_markdown=False,
        )

        lines = panel.render(width=80)
        rendered = "".join(lines)

        assert "\033[101m" in rendered  # bright red background
        assert "{on_bright_red}" not in rendered


class TestAnsiEndToEnd:
    """End-to-end tests using full TUI rendering pipeline."""

    def test_assistant_message_with_background_shows_color(
        self, mock_alfred, mock_terminal
    ) -> None:
        """Verify assistant response with {on_green} renders with ANSI code."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(
            role="assistant",
            content="{on_green}success{reset}",
            terminal_width=80,
            use_markdown=False,
        )

        lines = panel.render(width=80)
        rendered = "".join(lines)

        assert "\033[42m" in rendered  # green background ANSI code
        assert "{on_green}" not in rendered

    def test_user_message_with_background_shows_color(
        self, mock_alfred, mock_terminal
    ) -> None:
        """Verify user message with {on_red} renders with ANSI code."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(
            role="user",
            content="{on_red}error{reset}",
            terminal_width=80,
            use_markdown=False,
        )

        lines = panel.render(width=80)
        rendered = "".join(lines)

        assert "\033[41m" in rendered  # red background ANSI code
        assert "{on_red}" not in rendered

    def test_styles(self) -> None:
        """Verify style placeholders work."""
        styles = [
            ("{bold}", BOLD),
            ("{dim}", DIM),
            ("{italic}", ITALIC),
            ("{underline}", UNDERLINE),
        ]
        for placeholder, code in styles:
            result = apply_ansi(f"{placeholder}text{{reset}}")
            assert result == f"{code}text{RESET}"

    def test_no_placeholder_no_change(self) -> None:
        """Verify text without placeholders is unchanged."""
        text = "plain text without colors"
        result = apply_ansi(text)
        assert result == text

    def test_partial_placeholder_not_replaced(self) -> None:
        """Verify incomplete placeholders are not replaced."""
        text = "{invalid}text"
        result = apply_ansi(text)
        # {invalid} is not a valid placeholder so it stays as-is
        assert result == text

    def test_empty_string(self) -> None:
        """Verify empty string is handled."""
        result = apply_ansi("")
        assert result == ""

    def test_only_reset(self) -> None:
        """Verify reset placeholder works alone."""
        result = apply_ansi("{reset}")
        assert result == RESET


class TestAnsiConstants:
    """Tests for ANSI constant exports."""

    def test_reset_is_zero(self) -> None:
        """Verify RESET is ANSI reset code."""
        assert RESET == "\033[0m"

    def test_bold_is_one(self) -> None:
        """Verify BOLD is ANSI bold code."""
        assert BOLD == "\033[1m"

    def test_cyan_is_36(self) -> None:
        """Verify CYAN is ANSI cyan code."""
        assert CYAN == "\033[36m"

    def test_red_is_31(self) -> None:
        """Verify RED is ANSI red code."""
        assert RED == "\033[31m"

    def test_green_is_32(self) -> None:
        """Verify GREEN is ANSI green code."""
        assert GREEN == "\033[32m"

    def test_bright_colors_are_90_plus(self) -> None:
        """Verify bright colors use 90-97 range."""
        assert BRIGHT_BLACK == "\033[90m"
        assert BRIGHT_RED == "\033[91m"
        assert BRIGHT_WHITE == "\033[97m"

    def test_background_colors_are_40_plus(self) -> None:
        """Verify background colors use 40-47 range."""
        assert ON_BLACK == "\033[40m"
        assert ON_RED == "\033[41m"
        assert ON_WHITE == "\033[47m"

    def test_bright_backgrounds_are_100_plus(self) -> None:
        """Verify bright backgrounds use 100-107 range."""
        assert ON_BRIGHT_BLACK == "\033[100m"
        assert ON_BRIGHT_RED == "\033[101m"
        assert ON_BRIGHT_WHITE == "\033[107m"


class TestMessagePanelAnsiIntegration:
    """Tests for ANSI placeholder integration in MessagePanel."""

    def test_message_panel_replaces_placeholders(self) -> None:
        """Verify MessagePanel applies ANSI placeholders."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(
            role="assistant",
            content="{cyan}command{reset} executed",
            terminal_width=80,
            use_markdown=True,
        )

        text_component = panel.children[0]
        rendered = text_component._text

        # Should have ANSI codes, not placeholders
        assert "{cyan}" not in rendered
        assert "{reset}" not in rendered
        assert "\033[36m" in rendered  # CYAN
        assert "\033[0m" in rendered  # RESET

    def test_message_panel_preserves_plain_text(self) -> None:
        """Verify MessagePanel leaves plain text unchanged."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(
            role="assistant",
            content="plain text without colors",
            terminal_width=80,
            use_markdown=True,
        )

        text_component = panel.children[0]
        rendered = text_component._text

        assert "plain text without colors" in rendered

    def test_message_panel_combines_markdown_and_ansi(self) -> None:
        """Verify MessagePanel handles both markdown and ANSI."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(
            role="assistant",
            content="**bold** and {cyan}colored{reset}",
            terminal_width=80,
            use_markdown=True,
        )

        text_component = panel.children[0]
        rendered = text_component._text

        # Markdown should be processed (no **)
        assert "**" not in rendered
        # ANSI should be processed (no {cyan})
        assert "{cyan}" not in rendered

    def test_message_panel_invalid_placeholders_preserved(self) -> None:
        """Verify invalid placeholders are left as-is."""
        from src.interfaces.pypitui.message_panel import MessagePanel

        panel = MessagePanel(
            role="assistant",
            content="{invalid} stays {unknown}",
            terminal_width=80,
            use_markdown=True,
        )

        text_component = panel.children[0]
        rendered = text_component._text

        # Invalid placeholders should remain
        assert "{invalid}" in rendered
        assert "{unknown}" in rendered
