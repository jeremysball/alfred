"""Cron CLI commands - manage cron jobs.

These commands work both with and without the TUI running:
- When TUI is running: communicate via socket for real-time updates
- When TUI is not running: access database directly
"""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from alfred.config import load_config
from alfred.cron.socket_client import SocketClient
from alfred.cron.store import CronStore

app = typer.Typer(name="cron", help="Manage cron jobs", no_args_is_help=True)
console = Console()

T = TypeVar("T")


def async_command[T](func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """Decorator to run async Typer commands."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        return asyncio.run(func(*args, **kwargs))

    return wrapper


def get_socket_client() -> SocketClient:
    """Get a socket client connected to the TUI."""
    return SocketClient()


def get_store() -> CronStore:
    """Get a direct store connection."""
    config = load_config()
    return CronStore(config.data_dir)


def is_daemon_running() -> bool:
    """Check if the background daemon is running."""
    from alfred.cron.daemon import DaemonManager

    daemon = DaemonManager()
    return daemon.is_running()


def start_daemon_if_needed() -> bool:
    """Start the daemon if it's not already running.

    Returns:
        True if daemon was started or is already running, False on failure
    """
    if is_daemon_running():
        return True

    console.print("[dim]Starting daemon...[/dim]")
    import subprocess
    import sys
    import time

    from alfred.cron.daemon import DaemonManager

    daemon = DaemonManager()

    # Clean up any stale PID file
    if daemon.pid_file.exists():
        daemon.pid_file.unlink()

    # Start the daemon
    process = subprocess.Popen(
        [sys.executable, "-m", "alfred.cli.cron_runner", "--daemon"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait a bit for daemon to initialize
    time.sleep(0.3)

    # Check if process is still running
    ret = process.poll()
    if ret is not None and ret != 0:
        # Process exited with error
        stdout, stderr = process.communicate()
        console.print("[red]Failed to start daemon[/red]")
        if stderr:
            console.print(stderr.decode())
        return False

    # Wait for PID file with timeout
    start = time.monotonic()
    while time.monotonic() - start < 5.0:
        if daemon.is_running():
            console.print("[green]✓[/green] Daemon started")
            return True
        time.sleep(0.1)

    console.print("[red]Daemon failed to start[/red]")
    return False


async def try_socket_first(
    socket_func: Callable[..., Any],
    fallback_func: Callable[..., Any],
    *args: Any,
    autostart: bool = True,
    **kwargs: Any,
) -> Any:
    """Try socket connection first, fall back to direct store access.

    Args:
        socket_func: Async function to call via socket
        fallback_func: Async function to call directly if socket fails
        *args: Positional arguments
        autostart: Whether to try starting the daemon if not running
        **kwargs: Keyword arguments

    Returns:
        Result from socket or fallback function
    """
    # Try autostarting daemon if requested
    if autostart and not is_daemon_running() and start_daemon_if_needed():
        # Wait a moment for socket to be created
        await asyncio.sleep(0.5)

    client = get_socket_client()
    await client.start()

    try:
        if client.is_connected:
            return await socket_func(client, *args, **kwargs)
    except Exception:
        pass
    finally:
        await client.stop()

    # Fall back to direct store access
    return await fallback_func(*args, **kwargs)


@app.command("list")
@async_command
async def list_jobs(
    status: str = typer.Option(
        "all",
        "--status",
        "-s",
        help="Filter by status: all, pending, active, paused",
    ),
) -> None:
    """List all cron jobs."""
    async def _via_socket(client: SocketClient) -> list[dict]:
        response = await client.query_jobs(timeout=5.0)
        if response is None:
            raise ConnectionError("Socket connected but query failed")
        return response.jobs

    async def _via_store() -> list[dict]:
        store = get_store()
        jobs = await store.load_jobs()
        return [
            {
                "job_id": job.job_id,
                "name": job.name,
                "status": job.status,
                "expression": job.expression,
                "last_run": job.last_run.isoformat() if job.last_run else None,
                "created_at": job.created_at.isoformat() if job.created_at else None,
            }
            for job in jobs
        ]

    try:
        jobs = await try_socket_first(_via_socket, _via_store)
    except Exception as e:
        console.print(f"[red]Error loading jobs: {e}[/red]")
        raise typer.Exit(1) from e

    status_filter = status.lower().strip()
    valid_filters = ["all", "pending", "active", "paused"]

    if status_filter not in valid_filters:
        valid_list = ", ".join(valid_filters)
        console.print(f"[red]Error: Invalid status '{status}'. Use: {valid_list}[/red]")
        raise typer.Exit(1)

    if status_filter != "all":
        jobs = [j for j in jobs if j.get("status") == status_filter]

    if not jobs:
        msg = "No jobs found." if status_filter == "all" else f"No {status_filter} jobs found."
        console.print(f"[yellow]{msg}[/yellow]")
        return

    table = Table(
        title=f"Cron Jobs ({status_filter})" if status_filter != "all" else "Cron Jobs"
    )
    table.add_column("ID", style="dim", width=8)
    table.add_column("Name", style="bold")
    table.add_column("Status", width=10)
    table.add_column("Schedule")
    table.add_column("Last Run")

    status_colors = {"pending": "yellow", "active": "green", "paused": "dim"}

    for job in jobs:
        status_color = status_colors.get(job.get("status", ""), "white")
        last_run = job.get("last_run", "—") if job.get("last_run") else "—"
        table.add_row(
            job.get("job_id", "")[:8],
            job.get("name", ""),
            f"[{status_color}]{job.get('status', '')}[/{status_color}]",
            job.get("expression", ""),
            last_run,
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(jobs)} job(s)[/dim]")


@app.command("submit")
@async_command
async def submit_job(
    name: str = typer.Argument(..., help="Job name"),
    schedule: str = typer.Argument(
        ..., help="Schedule expression (e.g., '0 9 * * *' for 9am daily)"
    ),
    code: str | None = typer.Option(None, "--code", "-c", help="Python code for the job"),
) -> None:
    """Submit a new cron job for approval."""
    from alfred.cron import parser
    from alfred.cron.models import Job

    cron = schedule
    if not parser.is_valid(cron):
        console.print(f"[red]Error: Invalid schedule expression '{cron}'[/red]")
        console.print("\nUse schedule format:")
        console.print("  '0 9 * * *' for 9am daily")
        console.print("  '*/15 * * * *' for every 15 minutes")
        console.print("  '0 19 * * 0' for Sundays at 7pm")
        raise typer.Exit(1)

    cron_expression = cron

    if code is None:
        code = f'''"""Job: {name}"""

async def run():
    """Execute the job."""
    # User should replace this with actual job logic
    print("Running: {name}")
    pass
'''

    try:
        compile(code, "<string>", "exec")
    except SyntaxError as e:
        console.print(f"[red]Error: Invalid Python code - {e}[/red]")
        raise typer.Exit(1) from None

    async def _via_socket(client: SocketClient) -> str:
        response = await client.submit_job(
            name=name, expression=cron_expression, code=code, timeout=10.0
        )
        if response is None:
            raise ConnectionError("Socket connected but submit failed")
        if not response.success:
            raise RuntimeError(response.message)
        return response.job_id

    async def _via_store() -> str:
        import uuid
        store = get_store()
        job = Job(
            job_id=str(uuid.uuid4()),
            name=name,
            expression=cron_expression,
            code=code,
            status="pending",
        )
        await store.save_job(job)
        return job.job_id

    try:
        job_id = await try_socket_first(_via_socket, _via_store)
        console.print(
            Panel(
                f"[green]✓[/green] Job '[bold]{name}[/bold]' submitted for approval\n\n"
                f"[dim]Schedule:[/dim] {cron_expression}\n"
                f"[dim]Job ID:[/dim] {job_id}\n\n"
                f"[yellow]This job requires approval before it will run.[/yellow]\n"
                f"Run: [bold]alfred cron approve {job_id[:8]}[/bold]",
                title="Job Submitted",
                border_style="green",
            )
        )
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command("review")
@async_command
async def review_job(job_id: str = typer.Argument(..., help="Job ID or name")) -> None:
    """Review a pending job's details."""
    async def _via_socket(client: SocketClient) -> dict:
        response = await client.query_jobs(timeout=5.0)
        if response is None:
            raise ConnectionError("Socket connected but query failed")
        job = _find_job_dict(response.jobs, job_id)
        if job is None:
            raise ValueError(f"Job '{job_id}' not found")
        return job

    async def _via_store() -> dict:
        store = get_store()
        jobs = await store.load_jobs()
        job = _find_job_model(jobs, job_id)
        if job is None:
            raise ValueError(f"Job '{job_id}' not found")
        return {
            "job_id": job.job_id,
            "name": job.name,
            "status": job.status,
            "expression": job.expression,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "code": job.code,
            "resource_limits": {
                "timeout_seconds": (
                    job.resource_limits.timeout_seconds if job.resource_limits else 60
                ),
                "max_memory_mb": (
                    job.resource_limits.max_memory_mb if job.resource_limits else 128
                ),
                "allow_network": (
                    job.resource_limits.allow_network if job.resource_limits else False
                ),
            },
        }

    try:
        job = await try_socket_first(_via_socket, _via_store)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error loading job: {e}[/red]")
        raise typer.Exit(1) from e

    console.print(
        Panel(
            f"[bold]{job.get('name', '')}[/bold]\n"
            f"[dim]ID:[/dim] {job.get('job_id', '')}\n"
            f"[dim]Status:[/dim] {job.get('status', '')}\n"
            f"[dim]Schedule:[/dim] {job.get('expression', '')}\n"
            f"[dim]Created:[/dim] {job.get('created_at', '')}",
            title="Job Details",
            border_style="blue",
        )
    )

    console.print("\n[bold]Code:[/bold]")
    syntax = Syntax(job.get("code", ""), "python", theme="monokai", line_numbers=True)
    console.print(syntax)

    limits = job.get("resource_limits", {})
    console.print("\n[bold]Resource Limits:[/bold]")
    console.print(f"  Timeout: {limits.get('timeout_seconds', 'N/A')}s")
    console.print(f"  Max Memory: {limits.get('max_memory_mb', 'N/A')}MB")
    network_allowed = limits.get("allow_network", False)
    console.print(f"  Network: {'Allowed' if network_allowed else 'Blocked'}")

    if job.get("status") == "pending":
        console.print("\n[yellow]This job is pending approval.[/yellow]")
        console.print(
            f"To approve: [bold]alfred cron approve {job.get('job_id', '')[:8]}[/bold]"
        )
        console.print(f"To reject: [bold]alfred cron reject {job.get('job_id', '')[:8]}[/bold]")


@app.command("approve")
@async_command
async def approve_job(job_id: str = typer.Argument(..., help="Job ID or name")) -> None:
    """Approve a pending job."""
    from alfred.cron.scheduler import CronScheduler

    async def _via_socket(client: SocketClient) -> tuple[str, str]:
        # First find the job
        response = await client.query_jobs(timeout=5.0)
        if response is None:
            raise ConnectionError("Socket connected but query failed")
        job = _find_job_dict(response.jobs, job_id)
        if job is None:
            raise ValueError(f"Job '{job_id}' not found")
        if job.get("status") == "active":
            return job.get("name", ""), "already_active"
        if job.get("status") != "pending":
            raise ValueError(f"Cannot approve job with status '{job.get('status')}'")

        # Approve via socket
        approve_response = await client.approve_job(
            job_identifier=job.get("job_id", ""), timeout=10.0
        )
        if approve_response is None:
            raise ConnectionError("Failed to send approval")
        if not approve_response.success:
            raise RuntimeError(approve_response.message)
        return approve_response.job_name, "approved"

    async def _via_store() -> tuple[str, str]:
        store = get_store()
        jobs = await store.load_jobs()
        job = _find_job_model(jobs, job_id)
        if job is None:
            raise ValueError(f"Job '{job_id}' not found")
        if job.status == "active":
            return job.name, "already_active"
        if job.status != "pending":
            raise ValueError(f"Cannot approve job with status '{job.status}'")

        # Approve directly via scheduler
        scheduler = CronScheduler(store=store, data_dir=store.data_dir)
        result = await scheduler.approve_job(job.job_id, approved_by="user")
        if not result.get("success"):
            raise RuntimeError(result.get("message", "Unknown error"))
        return job.name, "approved"

    try:
        job_name, status = await try_socket_first(_via_socket, _via_store)
        if status == "already_active":
            console.print(f"[yellow]Job '{job_name}' is already active.[/yellow]")
        else:
            console.print(
                Panel(
                    f"[green]✓[/green] Approved '[bold]{job_name}[/bold]'\n"
                    f"The job is now active and will run on schedule.",
                    title="Job Approved",
                    border_style="green",
                )
            )
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command("reject")
@async_command
async def reject_job(job_id: str = typer.Argument(..., help="Job ID or name")) -> None:
    """Reject and delete a pending job."""
    async def _via_socket(client: SocketClient) -> str:
        response = await client.query_jobs(timeout=5.0)
        if response is None:
            raise ConnectionError("Socket connected but query failed")
        job = _find_job_dict(response.jobs, job_id)
        if job is None:
            raise ValueError(f"Job '{job_id}' not found")

        actual_job_id = job.get("job_id", "")
        reject_response = await client.reject_job(job_identifier=actual_job_id, timeout=10.0)
        if reject_response is None:
            raise ConnectionError("Failed to send reject")
        if not reject_response.success:
            raise RuntimeError(reject_response.message)
        return job.get("name", "")

    async def _via_store() -> str:
        store = get_store()
        jobs = await store.load_jobs()
        job = _find_job_model(jobs, job_id)
        if job is None:
            raise ValueError(f"Job '{job_id}' not found")
        await store.delete_job(job.job_id)
        return job.name

    try:
        job_name = await try_socket_first(_via_socket, _via_store)
        console.print(
            Panel(
                f"[green]✓[/green] Deleted '[bold]{job_name}[/bold]'\n"
                f"The job has been removed.",
                title="Job Rejected",
                border_style="yellow",
            )
        )
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command("history")
@async_command
async def show_history(
    job_id: str | None = typer.Option(None, "--job-id", "-j", help="Filter by job ID"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum records to show"),
) -> None:
    """Show job execution history."""
    # History is only available via socket for now
    client = get_socket_client()
    await client.start()

    try:
        if not client.is_connected:
            console.print(
                "[yellow]Warning: Not connected to TUI. "
                "Execution history is only available when TUI is running.[/yellow]"
            )
            return

        response = await client.query_jobs(timeout=5.0)

        if response is None:
            console.print("[red]Error: Failed to query jobs[/red]")
            raise typer.Exit(1)

        recent_failures = response.recent_failures

        if job_id:
            recent_failures = [
                r
                for r in recent_failures
                if r.get("job_id", "").startswith(job_id) or job_id in r.get("job_id", "")
            ]

        # Sort by started_at (most recent first)
        recent_failures.sort(key=lambda r: r.get("started_at", ""), reverse=True)
        recent_failures = recent_failures[:limit]

        if not recent_failures:
            console.print(
                f"[yellow]No history found{' for job ' + job_id if job_id else ''}.[/yellow]"
            )
            return

        table = Table(title="Execution History")
        table.add_column("Time", width=16)
        table.add_column("Job ID", width=8)
        table.add_column("Status", width=10)
        table.add_column("Duration", width=10)
        table.add_column("Memory", width=10)

        status_colors = {"success": "green", "failed": "red", "timeout": "yellow"}

        for record in recent_failures:
            status = record.get("status", "")
            status_color = status_colors.get(status, "white")
            duration_ms = record.get("duration_ms", 0)
            duration = f"{duration_ms}ms" if duration_ms < 1000 else f"{duration_ms // 1000}s"
            memory = f"{record.get('memory_peak_mb')}MB" if record.get("memory_peak_mb") else "—"
            table.add_row(
                record.get("started_at", "")[:16],  # YYYY-MM-DD HH:MM
                record.get("job_id", "")[:8],
                f"[{status_color}]{status}[/{status_color}]",
                duration,
                memory,
            )

        console.print(table)
        console.print(f"\n[dim]Showing {len(recent_failures)} record(s)[/dim]")

        failed = [r for r in recent_failures if r.get("status") in ("failed", "timeout")]
        if failed:
            console.print("\n[bold red]Failed Executions:[/bold red]")
            for record in failed[:3]:
                console.print(f"\n[dim]{record.get('started_at', '')[:16]}[/dim]")
                error_msg = record.get("error_message", "")
                if error_msg:
                    console.print(f"[red]{error_msg}[/red]")

    finally:
        await client.stop()


def _find_job_dict(jobs: list[dict], identifier: str) -> dict | None:
    """Find job by ID or fuzzy name match."""
    identifier_lower = identifier.lower()

    # Try exact ID match
    for job in jobs:
        if job.get("job_id") == identifier:
            return job

    # Try partial ID match
    for job in jobs:
        if job.get("job_id", "").startswith(identifier):
            return job

    # Try exact name match
    for job in jobs:
        if job.get("name", "").lower() == identifier_lower:
            return job

    # Try substring name match (must be unique)
    matches = [j for j in jobs if identifier_lower in j.get("name", "").lower()]
    return matches[0] if len(matches) == 1 else None


def _find_job_model(jobs: list, identifier: str):
    """Find job model by ID or fuzzy name match."""
    identifier_lower = identifier.lower()

    # Try exact ID match
    for job in jobs:
        if job.job_id == identifier:
            return job

    # Try partial ID match
    for job in jobs:
        if job.job_id.startswith(identifier):
            return job

    # Try exact name match
    for job in jobs:
        if job.name.lower() == identifier_lower:
            return job

    # Try substring name match (must be unique)
    matches = [j for j in jobs if identifier_lower in j.name.lower()]
    return matches[0] if len(matches) == 1 else None
