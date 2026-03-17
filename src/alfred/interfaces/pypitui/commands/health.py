"""/health command - Show system health status."""

import asyncio
from typing import TYPE_CHECKING

from alfred.interfaces.ansi import (
    BOLD,
    BRIGHT_CYAN,
    BRIGHT_YELLOW,
    CYAN,
    DIM,
    GREEN,
    RED,
    RESET,
    YELLOW,
)
from alfred.interfaces.pypitui.commands.base import Command

if TYPE_CHECKING:
    from alfred.interfaces.pypitui.tui import AlfredTUI


def _status_ok(text: str) -> str:
    """Format status as OK (green)."""
    return f"{GREEN}[OK]{RESET} {text}"


def _status_pending(text: str) -> str:
    """Format status as PENDING (yellow)."""
    return f"{YELLOW}[PENDING]{RESET} {text}"


def _status_active(text: str) -> str:
    """Format status as ACTIVE (cyan)."""
    return f"{CYAN}[ACTIVE]{RESET} {text}"


def _status_warning(text: str) -> str:
    """Format status as WARNING (bright yellow)."""
    return f"{BRIGHT_YELLOW}[WARNING]{RESET} {text}"


def _status_error(text: str) -> str:
    """Format status as ERROR (red)."""
    return f"{RED}[ERROR]{RESET} {text}"


def _section_header(title: str) -> str:
    """Format a section header."""
    return f"{BOLD}{title}{RESET}"


def _divider(width: int = 50) -> str:
    """Create a divider line."""
    return DIM + "-" * width + RESET


class HealthCommand(Command):
    """Show system health status for session and memory systems."""

    name = "health"
    description = "Show system health status"

    def execute(self, tui: "AlfredTUI", arg: str | None) -> bool:
        """Show health status of Alfred's systems."""

        async def _fetch_and_display() -> None:
            """Async helper to fetch stats and display health info."""
            lines: list[str] = []

            # Header
            lines.append("")
            lines.append(f"{BRIGHT_CYAN}╔{'═' * 48}╗{RESET}")
            lines.append(f"{BRIGHT_CYAN}║{RESET}  {_section_header('SYSTEM HEALTH CHECK'):<46}{BRIGHT_CYAN}║{RESET}")
            lines.append(f"{BRIGHT_CYAN}╚{'═' * 48}╝{RESET}")
            lines.append("")

            # Session System
            lines.append(_section_header("SESSION SYSTEM"))
            lines.append(_divider())

            try:
                session_manager = tui.alfred.core.session_manager
                if session_manager.has_active_session():
                    session = await session_manager.get_current_cli_session_async()
                    if session:
                        lines.append(_status_active(f"Current Session: {session.meta.session_id[:8]}..."))
                    else:
                        lines.append(_status_pending("Current Session: Loading..."))
                else:
                    lines.append(_status_ok("Current Session: No active session"))

                # Count total sessions
                all_sessions = session_manager.list_sessions()
                lines.append(f"  Total Sessions: {len(all_sessions)}")
            except Exception as e:
                lines.append(_status_error(f"Session system error: {e}"))

            lines.append("")

            # Memory System
            lines.append(_section_header("MEMORY SYSTEM"))
            lines.append(_divider())

            try:
                memory_store = tui.alfred.core.memory_store
                if hasattr(memory_store, 'count_memories'):
                    count = await memory_store.count_memories()
                    if count > 0:
                        lines.append(_status_ok(f"Stored Memories: {count}"))
                    else:
                        lines.append(_status_ok("Stored Memories: 0"))
                else:
                    lines.append(_status_pending("Memory store not available"))
            except Exception as e:
                lines.append(_status_error(f"Memory system error: {e}"))

            lines.append("")

            # Embedding System
            lines.append(_section_header("EMBEDDING SYSTEM"))
            lines.append(_divider())

            try:
                embedding_provider = tui.alfred.core.embedder
                if embedding_provider:
                    provider_name = embedding_provider.__class__.__name__
                    lines.append(_status_active(f"Provider: {provider_name}"))
                    lines.append(_status_ok("Status: Ready"))

                    # Show in-flight count if available
                    if hasattr(embedding_provider, 'in_flight_items'):
                        in_flight = len(embedding_provider.in_flight_items)
                        if in_flight > 0:
                            lines.append(_status_pending(f"In-flight: {in_flight} items"))
                        else:
                            lines.append(_status_ok(f"In-flight: {in_flight} items"))
                else:
                    lines.append(_status_error("No embedding provider configured"))
            except Exception as e:
                lines.append(_status_error(f"Embedding system error: {e}"))

            lines.append("")
            lines.append(f"{DIM}{'═' * 50}{RESET}")
            lines.append("")

            # Add the message to the TUI
            tui._add_system_message("\n".join(lines))

        # Schedule async work
        try:
            asyncio.get_running_loop()
            asyncio.create_task(_fetch_and_display())
        except RuntimeError:
            tui._add_system_message("Error: No event loop available")

        return True
