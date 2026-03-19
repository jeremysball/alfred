"""Alfred CLI entry point with Typer.

Uses lazy imports for fast shell completion. Heavy modules are only
imported when commands actually run, not during completion.
"""

import asyncio
import logging
import os
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer
from rich.console import Console

# Import cron app directly (lightweight, no heavy deps at import time)
from alfred.cli.cron import app as cron_app

if TYPE_CHECKING:
    from alfred.alfred import Alfred
    from alfred.cron.scheduler import CronScheduler
    from alfred.cron.socket_protocol import (
        ApproveJobRequest,
        ApproveJobResponse,
        JobCompletedMessage,
        JobFailedMessage,
        JobStartedMessage,
        NotifyMessage,
        QueryJobsRequest,
        QueryJobsResponse,
        RejectJobRequest,
        RejectJobResponse,
        SubmitJobRequest,
        SubmitJobResponse,
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
    install_completions: str = typer.Option(
        "",
        "--install-completions",
        help="Install shell completions (bash, fish, zsh, or 'auto')",
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

        # 'auto' or empty = detect from $SHELL
        shell_value = None if install_completions in ("auto", "") else install_completions
        install(shell=shell_value)
        raise typer.Exit()

    global _run_telegram, _log_level
    _run_telegram = telegram
    _log_level = log

    # If no subcommand, run interactive chat
    if ctx.invoked_subcommand is None:
        asyncio.run(_run_interactive())


# ============================================================================
# Daemon subcommands - daemon management
# ============================================================================

daemon_app = typer.Typer(name="daemon", help="Manage daemon process", no_args_is_help=True)


@daemon_app.command(name="start")
def daemon_start(
    fg: bool = typer.Option(
        False,
        "--fg",
        help="Run in foreground (don't daemonize)",
    ),
) -> None:
    """Start the daemon."""
    if fg:
        # Run foreground daemon
        from alfred.cron.daemon_runner import main

        main()
    else:
        # Run background daemon (default)
        from alfred.cli.daemon_cli import start_daemon

        start_daemon()


@daemon_app.command(name="stop")
def daemon_stop() -> None:
    """Stop the background daemon."""
    from alfred.cli.daemon_cli import stop_daemon

    stop_daemon()


@daemon_app.command(name="status")
def daemon_status_cmd() -> None:
    """Check background daemon status."""
    from alfred.cli.daemon_cli import daemon_status

    daemon_status()


@daemon_app.command(name="reload")
def daemon_reload_cmd() -> None:
    """Reload background daemon jobs (send SIGHUP)."""
    from alfred.cli.daemon_cli import reload_daemon

    reload_daemon()


@daemon_app.command(name="logs")
def daemon_logs() -> None:
    """Open daemon log file in $PAGER or $EDITOR."""
    import subprocess

    from alfred.data_manager import get_log_file

    log_file = get_log_file()
    if not log_file.exists():
        console.print(f"[yellow]Log file not found: {log_file}[/yellow]")
        raise typer.Exit(1)

    # Try $PAGER first, then $EDITOR, then fallbacks
    pager = os.environ.get("PAGER")
    editor = os.environ.get("EDITOR")

    if pager:
        cmd = [pager, str(log_file)]
    elif editor:
        cmd = [editor, str(log_file)]
    else:
        # Try common fallbacks
        for fallback in ["less", "more", "nano", "vim", "cat"]:
            if subprocess.run(["which", fallback], capture_output=True).returncode == 0:
                cmd = [fallback, str(log_file)]
                break
        else:
            console.print("[red]No pager or editor found. Set $PAGER or $EDITOR.[/red]")
            raise typer.Exit(1) from None

    try:
        subprocess.run(cmd)
    except Exception as e:
        console.print(f"[red]Failed to open log: {e}[/red]")
        raise typer.Exit(1) from e


app.add_typer(daemon_app)
app.add_typer(cron_app)


# ============================================================================
# WebUI subcommands - web interface
# ============================================================================

webui_app = typer.Typer(name="webui", help="Launch web interface", no_args_is_help=False)


@webui_app.callback(invoke_without_command=True)
def webui_callback(
    ctx: typer.Context,
    port: int = typer.Option(
        8080,
        "--port",
        "-p",
        help="Port to run the Web UI server on",
    ),
    open_browser: bool = typer.Option(
        False,
        "--open",
        "-o",
        help="Open browser automatically",
    ),
) -> None:
    """Launch Alfred Web UI server."""
    if ctx.invoked_subcommand is not None:
        return

    import uvicorn

    from alfred.interfaces.webui.server import create_app

    if open_browser:
        import threading
        import time
        import webbrowser

        def open_browser_delayed() -> None:
            time.sleep(1)
            webbrowser.open(f"http://localhost:{port}")

        threading.Thread(target=open_browser_delayed, daemon=True).start()

    uvicorn.run(
        create_app(),
        host="127.0.0.1",
        port=port,
        log_level="info",
    )


app.add_typer(webui_app)


# ============================================================================
# Memory subcommands - lazy-loaded proxies
# ============================================================================

memory_app = typer.Typer(name="memory", help="Manage memory system", no_args_is_help=True)


@memory_app.callback()
def memory_callback() -> None:
    """Memory system management."""
    pass


app.add_typer(memory_app)


# ============================================================================
# Config subcommands - update config files from templates
# ============================================================================

config_app = typer.Typer(name="config", help="Manage configuration files", no_args_is_help=True)


def _get_preserve_set(force: bool) -> set[str]:
    """Determine which files to preserve based on force flag.

    Args:
        force: If True, don't preserve any files. If False, preserve user files.

    Returns:
        Set of filenames to preserve.
    """
    if force:
        return set()
    return {"USER.md", "SOUL.md", "CUSTOM.md"}


def _group_update_results(results: dict[str, Any]) -> dict[str, Any]:
    """Group template update results by status.

    Args:
        results: Dictionary of filename -> result info from update_templates.

    Returns:
        Dictionary with grouped results:
        - updated: List of (name, message) tuples for updated/dry_run files
        - preserved: List of (name, message) tuples for preserved files
        - skipped: List of (name, message) tuples for skipped files
        - errors: List of (name, message) tuples for error files
        - prompts: Dict with prompts status or None
    """
    groups: dict[str, Any] = {
        "updated": [],
        "preserved": [],
        "skipped": [],
        "errors": [],
        "prompts": None,
    }

    for name, info in results.items():
        if name == "prompts/":
            groups["prompts"] = info
            continue

        status = info.get("status", "unknown")
        message = info.get("message", "")
        entry = (name, message)

        if status in ("updated", "dry_run"):
            groups["updated"].append(entry)
        elif status == "preserved":
            groups["preserved"].append(entry)
        elif status == "skipped":
            groups["skipped"].append(entry)
        elif status == "error":
            groups["errors"].append(entry)

    return groups


def _display_update_results(groups: dict[str, Any], dry_run: bool) -> None:
    """Display grouped update results to console.

    Args:
        groups: Grouped results from _group_update_results.
        dry_run: Whether this was a dry run.
    """
    # Header
    if dry_run:
        console.print("[bold]Dry run - no changes made:[/bold]\n")
    else:
        console.print("[bold]Config update results:[/bold]\n")

    # Updated files
    if groups["updated"]:
        console.print("[green]Updated:[/green]")
        for name, msg in groups["updated"]:
            console.print(f"  ✓ {name} - {msg}")
        console.print()

    # Preserved files
    if groups["preserved"]:
        console.print("[yellow]Preserved (not overwritten):[/yellow]")
        for name, msg in groups["preserved"]:
            console.print(f"  ○ {name} - {msg}")
        console.print()

    # Skipped files
    if groups["skipped"]:
        console.print("[dim]Skipped (up to date):[/dim]")
        for name, msg in groups["skipped"]:
            console.print(f"  - {name} - {msg}")
        console.print()

    # Errors
    if groups["errors"]:
        console.print("[red]Errors:[/red]")
        for name, msg in groups["errors"]:
            console.print(f"  ✗ {name} - {msg}")
        console.print()

    # Prompts (special handling)
    prompts = groups["prompts"]
    if prompts:
        status = prompts.get("status", "unknown")
        message = prompts.get("message", "")
        if status == "updated":
            console.print(f"[green]Prompts:[/green] {message}")
        elif status == "skipped":
            console.print(f"[dim]Prompts:[/dim] {message}")
        else:
            console.print(f"Prompts: {message}")


def _display_footer(workspace_dir: Path, force: bool, preserved: list[tuple[str, str]]) -> None:
    """Display footer with workspace info and tips.

    Args:
        workspace_dir: Path to the workspace directory.
        force: Whether --force flag was used.
        preserved: List of preserved files.
    """
    console.print(f"\n[dim]Config files location: {workspace_dir}[/dim]")

    if not force and preserved:
        console.print("\n[dim]Tip: Use --force to also update USER.md and SOUL.md[/dim]")


@config_app.callback()
def config_callback() -> None:
    """Configuration file management."""
    pass


@config_app.command(name="update")
def config_update(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be updated without making changes",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Also overwrite USER.md and SOUL.md (use with caution)",
    ),
) -> None:
    """Update config files from templates.

    Updates SYSTEM.md, AGENTS.md, TOOLS.md, and prompts/ from templates.
    Preserves USER.md, SOUL.md, and CUSTOM.md by default.
    Use --force to override preservation.
    """
    from alfred.data_manager import get_workspace_dir
    from alfred.templates import TemplateManager

    workspace_dir = get_workspace_dir()
    manager = TemplateManager(workspace_dir)
    preserve = _get_preserve_set(force)

    try:
        results = manager.update_templates(preserve=preserve, dry_run=dry_run)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e

    groups = _group_update_results(results)
    _display_update_results(groups, dry_run)
    _display_footer(workspace_dir, force, groups["preserved"])


app.add_typer(config_app)


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
    from alfred.cron.scheduler import CronScheduler

    # Start daemon in background if not running (non-blocking, fire-and-forget)
    from alfred.cron.socket_client import SocketClient
    from alfred.cron.socket_server import SocketServer
    from alfred.cron.store import CronStore
    from alfred.interfaces.pypitui_cli import AlfredTUI

    client = SocketClient()
    await client.start()
    if not client.is_connected:
        # Daemon not running, start it without blocking TUI
        from alfred.cli.cron import start_daemon_if_needed

        start_daemon_if_needed()
    await client.stop()

    # Create scheduler for socket handlers
    scheduler = CronScheduler(
        store=CronStore(alfred.config.data_dir),
        data_dir=alfred.config.data_dir,
    )

    socket_server = SocketServer(
        on_notify=lambda msg: _handle_notify(toast_manager, msg),
        on_job_started=lambda msg: _handle_job_started(toast_manager, msg),
        on_job_completed=lambda msg: _handle_job_completed(toast_manager, msg),
        on_job_failed=lambda msg: _handle_job_failed(toast_manager, msg),
        on_query_jobs=lambda msg: _handle_query_jobs(scheduler, msg),
        on_submit_job=lambda msg: _handle_submit_job(scheduler, msg),
        on_approve_job=lambda msg: _handle_approve_job(scheduler, msg),
        on_reject_job=lambda msg: _handle_reject_job(scheduler, msg),
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


async def _handle_submit_job(
    scheduler: "CronScheduler", msg: "SubmitJobRequest"
) -> "SubmitJobResponse":
    """Handle job submission request from tools.

    Args:
        scheduler: The cron scheduler to submit job to
        msg: Submit job request message

    Returns:
        SubmitJobResponse with result
    """
    from alfred.cron.socket_protocol import SubmitJobResponse

    try:
        job_id = await scheduler.submit_user_job(
            name=msg.name,
            expression=msg.expression,
            code=msg.code,
        )
        return SubmitJobResponse(
            request_id=msg.request_id,
            success=True,
            job_id=job_id,
            message=f"Job '{msg.name}' submitted successfully",
        )
    except Exception as e:
        return SubmitJobResponse(
            request_id=msg.request_id,
            success=False,
            job_id="",
            message=f"Failed to submit job: {e}",
        )


async def _handle_approve_job(
    scheduler: "CronScheduler", msg: "ApproveJobRequest"
) -> "ApproveJobResponse":
    """Handle job approval request from tools.

    Args:
        scheduler: The cron scheduler to approve job through
        msg: Approve job request message

    Returns:
        ApproveJobResponse with result
    """
    from alfred.cron.socket_protocol import ApproveJobResponse

    try:
        # Find job by ID or name
        job_id = await _find_job_id(scheduler, msg.job_identifier)
        if not job_id:
            return ApproveJobResponse(
                request_id=msg.request_id,
                success=False,
                job_id="",
                job_name="",
                message=f"Job not found: {msg.job_identifier}",
            )

        result = await scheduler.approve_job(job_id, approved_by="user")
        if result["success"]:
            return ApproveJobResponse(
                request_id=msg.request_id,
                success=True,
                job_id=job_id,
                job_name=result.get("job_name", ""),
                message=result["message"],
            )
        else:
            return ApproveJobResponse(
                request_id=msg.request_id,
                success=False,
                job_id=job_id,
                job_name=result.get("job_name", ""),
                message=result["message"],
            )
    except Exception as e:
        return ApproveJobResponse(
            request_id=msg.request_id,
            success=False,
            job_id="",
            job_name="",
            message=f"Failed to approve job: {e}",
        )


async def _handle_reject_job(
    scheduler: "CronScheduler", msg: "RejectJobRequest"
) -> "RejectJobResponse":
    """Handle job rejection request from tools.

    Args:
        scheduler: The cron scheduler to reject job through
        msg: Reject job request message

    Returns:
        RejectJobResponse with result
    """
    from alfred.cron.socket_protocol import RejectJobResponse

    try:
        # Find job by ID or name
        job_id = await _find_job_id(scheduler, msg.job_identifier)
        if not job_id:
            return RejectJobResponse(
                request_id=msg.request_id,
                success=False,
                job_id="",
                job_name="",
                message=f"Job not found: {msg.job_identifier}",
            )

        # Get job name before deleting
        jobs = await scheduler._store.load_jobs()
        job_name = ""
        for job in jobs:
            if job.job_id == job_id:
                job_name = job.name
                break

        # Delete the job
        await scheduler._store.delete_job(job_id)

        return RejectJobResponse(
            request_id=msg.request_id,
            success=True,
            job_id=job_id,
            job_name=job_name,
            message=f"Job '{job_name}' deleted",
        )
    except Exception as e:
        return RejectJobResponse(
            request_id=msg.request_id,
            success=False,
            job_id="",
            job_name="",
            message=f"Failed to reject job: {e}",
        )


async def _handle_query_jobs(
    scheduler: "CronScheduler", msg: "QueryJobsRequest"
) -> "QueryJobsResponse":
    """Handle job query request from tools.

    Args:
        scheduler: The cron scheduler to query
        msg: Query jobs request message

    Returns:
        QueryJobsResponse with job list
    """
    from alfred.cron.socket_protocol import QueryJobsResponse

    try:
        jobs = await scheduler._store.load_jobs()
        # Convert jobs to dict format
        job_dicts = []
        for job in jobs:
            job_dicts.append(
                {
                    "job_id": job.job_id,
                    "name": job.name,
                    "expression": job.expression,
                    "code": job.code,
                    "status": job.status,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                }
            )

        return QueryJobsResponse(
            request_id=msg.request_id,
            jobs=job_dicts,
            recent_failures=[],
        )
    except Exception:
        return QueryJobsResponse(
            request_id=msg.request_id,
            jobs=[],
            recent_failures=[],
        )


async def _find_job_id(scheduler: "CronScheduler", identifier: str) -> str | None:
    """Find job ID by identifier (ID or name).

    Args:
        scheduler: The cron scheduler
        identifier: Job ID or name to find

    Returns:
        Job ID if found, None otherwise
    """
    jobs = await scheduler._store.load_jobs()
    identifier_lower = identifier.lower()

    # Try exact ID match first
    for job in jobs:
        if job.job_id == identifier:
            return job.job_id

    # Try exact name match
    for job in jobs:
        if job.name.lower() == identifier_lower:
            return job.job_id

    # Try substring name match (must be unique)
    matches = [j for j in jobs if identifier_lower in j.name.lower()]
    if len(matches) == 1:
        return matches[0].job_id

    return None


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
