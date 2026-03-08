"""Alfred CLI entry point with Typer.

Uses lazy imports for fast shell completion. Heavy modules are only
imported when commands actually run, not during completion.
"""

import asyncio
import logging
import os
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

import typer
from rich.console import Console

if TYPE_CHECKING:
    from alfred.alfred import Alfred
    from alfred.cron.socket_protocol import (
        JobCompletedMessage,
        JobFailedMessage,
        JobStartedMessage,
        NotifyMessage,
    )
    from alfred.interfaces.pypitui.toast import ToastManager

app = typer.Typer(
    name="alfred",
    help="Alfred - Persistent memory-augmented LLM assistant",
    no_args_is_help=False,
    add_completion=False,
)
console = Console()

# Global state for callback
_run_telegram = False
_log_level: str | None = None


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    telegram: bool = typer.Option(
        False,
        "--telegram",
        "-t",
        help="Run as Telegram bot (default: run as CLI)",
    ),
    log: str | None = typer.Option(
        None,
        "--log",
        "-l",
        help="Set log level: 'info' or 'debug'. Default: warnings only",
    ),
    install_completions: bool = typer.Option(
        False,
        "--install-completions",
        help="Install fast static shell completions",
    ),
) -> None:
    """Alfred - Persistent memory-augmented LLM assistant.

    Run without arguments to start interactive chat.
    Use 'alfred cron' for cron job management.
    """
    # Skip during shell completion
    if os.environ.get("_TYPER_COMPLETE") or os.environ.get("_ALFRED_COMPLETE"):
        return

    if install_completions:
        from alfred.cli.install_completions import install

        install()
        raise typer.Exit()

    global _run_telegram, _log_level
    _run_telegram = telegram
    _log_level = log

    # If no subcommand, run interactive chat
    if ctx.invoked_subcommand is None:
        asyncio.run(_run_interactive())


# ============================================================================
# Cron subcommands - lazy-loaded proxies
# ============================================================================

cron_app = typer.Typer(name="cron", help="Manage cron jobs")


@cron_app.callback()
def cron_callback() -> None:
    """Cron job management."""
    pass


@cron_app.command(name="list")
def cron_list(
    status: str = typer.Option(
        "all",
        "--status",
        "-s",
        help="Filter by status: all, pending, active, paused",
    ),
) -> None:
    """List all cron jobs."""
    from alfred.cli.cron import list_jobs

    list_jobs(status)


@cron_app.command(name="submit")
def cron_submit(
    name: str = typer.Argument(..., help="Job name"),
    cron: str = typer.Argument(..., help="Cron expression (e.g., '0 9 * * *' for 9am daily)"),
    code: str | None = typer.Option(None, "--code", "-c", help="Python code for the job"),
) -> None:
    """Submit a new cron job for approval."""
    from alfred.cli.cron import submit_job

    submit_job(name, cron, code)


@cron_app.command(name="review")
def cron_review(
    job_id: str = typer.Argument(..., help="Job ID or name"),
) -> None:
    """Review a pending job's details."""
    from alfred.cli.cron import review_job

    review_job(job_id)


@cron_app.command(name="approve")
def cron_approve(
    job_id: str = typer.Argument(..., help="Job ID or name"),
) -> None:
    """Approve a pending job."""
    from alfred.cli.cron import approve_job

    approve_job(job_id)


@cron_app.command(name="reject")
def cron_reject(
    job_id: str = typer.Argument(..., help="Job ID or name"),
) -> None:
    """Reject and delete a pending job."""
    from alfred.cli.cron import reject_job

    reject_job(job_id)


@cron_app.command(name="history")
def cron_history(
    job_id: str | None = typer.Option(None, "--job-id", "-j", help="Filter by job ID"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum records to show"),
) -> None:
    """Show job execution history."""
    from alfred.cli.cron import show_history

    show_history(job_id, limit)


@cron_app.command(name="start")
def cron_start() -> None:
    """Start the cron daemon."""
    from alfred.cli.cron import start_daemon

    start_daemon()


@cron_app.command(name="stop")
def cron_stop() -> None:
    """Stop the cron daemon."""
    from alfred.cli.cron import stop_daemon

    stop_daemon()


@cron_app.command(name="status")
def cron_status() -> None:
    """Check daemon status."""
    from alfred.cli.cron import daemon_status

    daemon_status()


@cron_app.command(name="reload")
def cron_reload() -> None:
    """Reload daemon jobs (send SIGHUP)."""
    from alfred.cli.cron import reload_daemon

    reload_daemon()


@app.command("daemon")
def run_daemon():
    """Run AlfredDaemon in foreground (blocks until Ctrl+C)."""
    from alfred.cron.daemon_runner import main
    main()


app.add_typer(cron_app)


# ============================================================================
# Memory subcommands - lazy-loaded proxies
# ============================================================================

memory_app = typer.Typer(name="memory", help="Manage memory system")


@memory_app.callback()
def memory_callback() -> None:
    """Memory system management."""
    pass


@memory_app.command(name="migrate")
def memory_migrate(
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help="Show what would be migrated without making changes",
    ),
) -> None:
    """Migrate memories from JSONL to FAISS."""
    from alfred.cli.memory import migrate_command

    migrate_command()


@memory_app.command(name="status")
def memory_status() -> None:
    """Show memory system status."""
    from alfred.cli.memory import status_command

    status_command()


@memory_app.command(name="prune")
def memory_prune(
    days: int = typer.Option(
        90,
        "--days",
        "-d",
        help="Remove memories older than this many days",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help="Show what would be deleted without deleting",
    ),
) -> None:
    """Prune expired memories."""
    from alfred.cli.memory import prune_command

    prune_command(ttl_days=days, dry_run=dry_run)


app.add_typer(memory_app)


# ============================================================================
# Interactive mode
# ============================================================================


async def _run_interactive() -> None:
    """Run interactive CLI or Telegram bot."""
    # Lazy imports - these only run when interactive mode is invoked
    from alfred.alfred import Alfred
    from alfred.config import load_config
    from alfred.data_manager import init_xdg_directories
    from alfred.interfaces.pypitui.toast import ToastManager

    toast_manager: ToastManager | None = None
    if not _run_telegram:
        toast_manager = ToastManager()

    init_xdg_directories()
    config = load_config()
    _setup_logging(toast_manager)

    alfred = Alfred(config, telegram_mode=_run_telegram)

    try:
        if _run_telegram:
            await _run_telegram_bot(alfred)
        else:
            await _run_chat(alfred, toast_manager)
    except KeyboardInterrupt:
        pass
    finally:
        await alfred.stop()


async def _run_chat(alfred: "Alfred", toast_manager: "ToastManager | None") -> None:
    """Run interactive CLI chat."""
    from alfred.cron.socket_server import SocketServer
    from alfred.interfaces.pypitui_cli import AlfredTUI

    socket_server = SocketServer(
        on_notify=lambda msg: _handle_notify(toast_manager, msg),
        on_job_started=lambda msg: _handle_job_started(toast_manager, msg),
        on_job_completed=lambda msg: _handle_job_completed(toast_manager, msg),
        on_job_failed=lambda msg: _handle_job_failed(toast_manager, msg),
    )

    await socket_server.start()

    try:
        interface = AlfredTUI(alfred, toast_manager=toast_manager)
        await alfred.start()
        await interface.run()
    finally:
        await socket_server.stop()


def _handle_notify(toast_manager: "ToastManager | None", msg: "NotifyMessage") -> None:
    if toast_manager:
        toast_manager.add(msg.message, msg.level)


def _handle_job_started(toast_manager: "ToastManager | None", msg: "JobStartedMessage") -> None:
    if toast_manager:
        toast_manager.add(f"Cron job started: {msg.job_name}", "info")


def _handle_job_completed(toast_manager: "ToastManager | None", msg: "JobCompletedMessage") -> None:
    if toast_manager:
        toast_manager.add(f"Cron job completed: {msg.job_name} ({msg.duration_ms}ms)", "info")


def _handle_job_failed(toast_manager: "ToastManager | None", msg: "JobFailedMessage") -> None:
    if toast_manager:
        toast_manager.add(f"Cron job failed: {msg.job_name} - {msg.error}", "error")


async def _run_telegram_bot(alfred: "Alfred") -> None:
    """Run Telegram bot."""
    from alfred.interfaces.telegram import TelegramInterface

    data_dir = alfred.config.data_dir
    interface = TelegramInterface(alfred.config, alfred, data_dir)
    await alfred.start()
    await interface.run()


def _setup_logging(toast_manager: "ToastManager | None" = None) -> None:
    """Configure logging to file."""
    if _log_level == "debug":
        level = logging.DEBUG
    elif _log_level == "info":
        level = logging.INFO
    else:
        level = logging.WARNING

    from alfred.data_manager import get_log_file

    log_file = get_log_file()
    log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s:%(name)s:%(message)s"))

    handlers: list[logging.Handler] = [file_handler]

    if toast_manager is not None:
        from alfred.interfaces.pypitui.toast import ToastHandler

        toast_handler = ToastHandler(toast_manager)
        toast_handler.setLevel(logging.WARNING)
        handlers.append(toast_handler)

    logging.basicConfig(level=level, handlers=handlers)

    # Capture Python warnings (e.g., RuntimeWarning) and route through logging
    logging.captureWarnings(True)

    for logger_name in ["markdown_it", "httpcore", "httpx", "urllib3", "asyncio"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def run_async(coro_factory: Callable[[], Coroutine[Any, Any, None]]) -> None:
    asyncio.run(coro_factory())


if __name__ == "__main__":
    app()
