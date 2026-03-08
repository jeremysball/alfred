"""Cron CLI commands - communicate with daemon via socket.

These commands act as a client to the standalone daemon.
They do NOT access the database directly.
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

from alfred.cron.daemon import DaemonManager
from alfred.cron.socket_client import SocketClient

app = typer.Typer(help="Manage cron jobs")
console = Console()

T = TypeVar("T")


def async_command[T](func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """Decorator to run async Typer commands."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        return asyncio.run(func(*args, **kwargs))

    return wrapper


def get_socket_client() -> SocketClient:
    """Get a socket client connected to the daemon."""
    return SocketClient()


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
    client = get_socket_client()
    await client.start()

    try:
        response = await client.query_jobs(timeout=5.0)

        if response is None:
            console.print(
                "[red]Error: Could not connect to daemon. "
                "Is it running? (alfred daemon status)[/red]"
            )
            raise typer.Exit(1)

        jobs = response.jobs

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

    finally:
        await client.stop()


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

    client = get_socket_client()
    await client.start()

    try:
        response = await client.submit_job(
            name=name, expression=cron_expression, code=code, timeout=10.0
        )

        if response is None:
            console.print(
                "[red]Error: Could not connect to daemon. "
                "Is it running? (alfred daemon status)[/red]"
            )
            raise typer.Exit(1)

        if response.success:
            console.print(
                Panel(
                    f"[green]✓[/green] Job '[bold]{name}[/bold]' submitted for approval\n\n"
                    f"[dim]Schedule:[/dim] {cron_expression}\n"
                    f"[dim]Job ID:[/dim] {response.job_id}\n\n"
                    f"[yellow]This job requires approval before it will run.[/yellow]\n"
                    f"Run: [bold]alfred jobs approve {response.job_id[:8]}[/bold]",
                    title="Job Submitted",
                    border_style="green",
                )
            )
        else:
            console.print(f"[red]Error: {response.message}[/red]")
            raise typer.Exit(1)

    finally:
        await client.stop()


@app.command("review")
@async_command
async def review_job(job_id: str = typer.Argument(..., help="Job ID or name")) -> None:
    """Review a pending job's details."""
    client = get_socket_client()
    await client.start()

    try:
        response = await client.query_jobs(timeout=5.0)

        if response is None:
            console.print(
                "[red]Error: Could not connect to daemon. "
                "Is it running? (alfred daemon status)[/red]"
            )
            raise typer.Exit(1)

        jobs = response.jobs
        job = _find_job_dict(jobs, job_id)

        if job is None:
            console.print(f"[red]Error: Job '{job_id}' not found[/red]")
            raise typer.Exit(1)

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

    finally:
        await client.stop()


@app.command("approve")
@async_command
async def approve_job(job_id: str = typer.Argument(..., help="Job ID or name")) -> None:
    """Approve a pending job."""
    client = get_socket_client()
    await client.start()

    try:
        # First get the job details to verify it exists
        response = await client.query_jobs(timeout=5.0)

        if response is None:
            console.print(
                "[red]Error: Could not connect to daemon. "
                "Is it running? (alfred daemon status)[/red]"
            )
            raise typer.Exit(1)

        jobs = response.jobs
        job = _find_job_dict(jobs, job_id)

        if job is None:
            console.print(f"[red]Error: Job '{job_id}' not found[/red]")
            raise typer.Exit(1)

        if job.get("status") == "active":
            console.print(f"[yellow]Job '{job.get('name')}' is already active.[/yellow]")
            return

        if job.get("status") != "pending":
            console.print(f"[red]Error: Cannot approve job with status '{job.get('status')}'[/red]")
            raise typer.Exit(1)

        # Approve via socket
        approve_response = await client.approve_job(
            job_identifier=job.get("job_id", ""), timeout=10.0
        )

        if approve_response is None:
            console.print("[red]Error: Failed to send approval to daemon.[/red]")
            raise typer.Exit(1)

        if approve_response.success:
            console.print(
                Panel(
                    f"[green]✓[/green] Approved '[bold]{approve_response.job_name}[/bold]'\n"
                    f"The job is now active and will run on schedule.",
                    title="Job Approved",
                    border_style="green",
                )
            )
        else:
            console.print(f"[red]Error: {approve_response.message}[/red]")
            raise typer.Exit(1)

    finally:
        await client.stop()


@app.command("reject")
@async_command
async def reject_job(job_id: str = typer.Argument(..., help="Job ID or name")) -> None:
    """Reject and delete a pending job."""
    client = get_socket_client()
    await client.start()

    try:
        # First get the job details
        response = await client.query_jobs(timeout=5.0)

        if response is None:
            console.print(
                "[red]Error: Could not connect to daemon. "
                "Is it running? (alfred daemon status)[/red]"
            )
            raise typer.Exit(1)

        jobs = response.jobs
        job = _find_job_dict(jobs, job_id)

        if job is None:
            console.print(f"[red]Error: Job '{job_id}' not found[/red]")
            raise typer.Exit(1)

        job_name = job.get("name", "")
        actual_job_id = job.get("job_id", "")

        # Reject via socket
        reject_response = await client.reject_job(job_identifier=actual_job_id, timeout=10.0)

        if reject_response is None:
            console.print("[red]Error: Failed to send reject to daemon.[/red]")
            raise typer.Exit(1)

        if reject_response.success:
            console.print(
                Panel(
                    f"[green]✓[/green] Deleted '[bold]{job_name}[/bold]'\n"
                    f"The job has been removed.",
                    title="Job Rejected",
                    border_style="yellow",
                )
            )
        else:
            console.print(f"[red]Error: {reject_response.message}[/red]")
            raise typer.Exit(1)

    finally:
        await client.stop()


@app.command("history")
@async_command
async def show_history(
    job_id: str | None = typer.Option(None, "--job-id", "-j", help="Filter by job ID"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum records to show"),
) -> None:
    """Show job execution history."""
    client = get_socket_client()
    await client.start()

    try:
        response = await client.query_jobs(timeout=5.0)

        if response is None:
            console.print(
                "[red]Error: Could not connect to daemon. "
                "Is it running? (alfred daemon status)[/red]"
            )
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
            if duration_ms < 1000:
                duration = f"{duration_ms}ms"
            else:
                duration = f"{duration_ms // 1000}s"
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


@app.command("start")
def start_daemon() -> None:
    """Start the cron daemon."""
    daemon = DaemonManager()

    # Check if already running
    pid = daemon.read_pid()
    if pid:
        console.print(f"[yellow]Daemon already running (PID {pid})[/yellow]")
        raise typer.Exit(1)

    # Clean up any stale PID file
    if daemon.pid_file.exists():
        daemon.pid_file.unlink()

    # Start the daemon
    console.print("[dim]Starting cron daemon...[/dim]")
    import subprocess
    import sys
    import time

    # Use Popen instead of run so we don't wait for the intermediate parent
    process = subprocess.Popen(
        [sys.executable, "-m", "alfred.cli.cron_runner", "--daemon"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait a bit for daemon to initialize
    time.sleep(0.3)

    # Check if process is still running (it should have exited after forking)
    ret = process.poll()
    if ret is not None and ret != 0:
        # Process exited with error
        stdout, stderr = process.communicate()
        console.print("[red]Failed to start daemon:[/red]")
        if stderr:
            console.print(stderr.decode())
        raise typer.Exit(1)

    # Wait for PID file with timeout
    start = time.monotonic()
    while time.monotonic() - start < 5.0:
        pid = daemon.read_pid()
        if pid:
            console.print(f"[green]✓[/green] Daemon started (PID {pid})")
            return
        time.sleep(0.1)

    console.print("[red]Daemon started but PID file not found[/red]")
    raise typer.Exit(1)


@app.command("stop")
def stop_daemon() -> None:
    """Stop the cron daemon."""
    daemon = DaemonManager()

    if not daemon.is_running():
        console.print("[yellow]Daemon is not running[/yellow]")
        raise typer.Exit(1)

    pid = daemon.read_pid()
    console.print(f"[dim]Stopping daemon (PID {pid})...[/dim]")

    if daemon.stop():
        console.print("[green]✓[/green] Daemon stopped")
    else:
        console.print("[red]Failed to stop daemon[/red]")
        raise typer.Exit(1)


@app.command("status")
def daemon_status() -> None:
    """Check daemon status."""
    daemon = DaemonManager()

    if daemon.is_running():
        pid = daemon.read_pid()
        console.print(f"[green]●[/green] Daemon running (PID {pid})")
    else:
        console.print("[dim]○[/dim] Daemon not running")


@app.command("reload")
def reload_daemon() -> None:
    """Reload daemon jobs (send SIGHUP)."""
    daemon = DaemonManager()

    if not daemon.is_running():
        console.print("[yellow]Daemon is not running[/yellow]")
        raise typer.Exit(1)

    if daemon.reload():
        console.print("[green]✓[/green] Reload signal sent")
    else:
        console.print("[red]Failed to send reload signal[/red]")
        raise typer.Exit(1)


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
