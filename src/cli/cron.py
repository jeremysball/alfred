from __future__ import annotations

import asyncio
import functools
import json
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING

import aiofiles
import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from src.config import load_config
from src.cron.daemon import DaemonManager

if TYPE_CHECKING:
    from src.cron.models import Job
    from src.cron.scheduler import CronScheduler
    from src.cron.store import CronStore

app = typer.Typer(help="Manage cron jobs")
console = Console()

def async_command[**P, T](func: Callable[P, Coroutine[object, object, T]]) -> Callable[P, T]:
    """Decorator to run async Typer commands."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return asyncio.run(func(*args, **kwargs))

    return wrapper


def get_store() -> CronStore:
    """Get CronStore instance."""
    from src.cron.store import CronStore

    config = load_config()
    return CronStore(config.data_dir)


def get_scheduler() -> CronScheduler:
    """Get CronScheduler instance."""
    from src.cron.scheduler import CronScheduler
    from src.cron.store import CronStore

    config = load_config()
    store = CronStore(config.data_dir)
    return CronScheduler(store=store, data_dir=config.data_dir, config=config)


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
    store = get_store()
    jobs = await store.load_jobs()

    status_filter = status.lower().strip()
    valid_filters = ["all", "pending", "active", "paused"]

    if status_filter not in valid_filters:
        valid_list = ", ".join(valid_filters)
        console.print(f"[red]Error: Invalid status '{status}'. Use: {valid_list}[/red]")
        raise typer.Exit(1)

    if status_filter != "all":
        jobs = [j for j in jobs if j.status == status_filter]

    if not jobs:
        msg = "No jobs found." if status_filter == "all" else f"No {status_filter} jobs found."
        console.print(f"[yellow]{msg}[/yellow]")
        return

    table = Table(title=f"Cron Jobs ({status_filter})" if status_filter != "all" else "Cron Jobs")
    table.add_column("ID", style="dim", width=8)
    table.add_column("Name", style="bold")
    table.add_column("Status", width=10)
    table.add_column("Schedule")
    table.add_column("Last Run")

    status_colors = {"pending": "yellow", "active": "green", "paused": "dim"}

    for job in jobs:
        status_color = status_colors.get(job.status, "white")
        last_run = job.last_run.strftime("%Y-%m-%d %H:%M") if job.last_run else "—"
        table.add_row(
            job.job_id[:8],
            job.name,
            f"[{status_color}]{job.status}[/{status_color}]",
            job.expression,
            last_run,
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(jobs)} job(s)[/dim]")


@app.command("submit")
@async_command
async def submit_job(
    name: str = typer.Argument(..., help="Job name"),
    cron: str = typer.Argument(..., help="Cron expression (e.g., '0 9 * * *' for 9am daily)"),
    code: str | None = typer.Option(None, "--code", "-c", help="Python code for the job"),
) -> None:
    """Submit a new cron job for approval."""
    from src.cron import parser

    if not parser.is_valid(cron):
        console.print(f"[red]Error: Invalid cron expression '{cron}'[/red]")
        console.print("\nUse cron format:")
        console.print("  '0 9 * * *' for 9am daily")
        console.print("  '*/15 * * * *' for every 15 minutes")
        console.print("  '0 19 * * 0' for Sundays at 7pm")
        raise typer.Exit(1)

    cron_expression = cron

    if code is None:
        code = f'''"""Job: {name}"""

async def run():
    """Execute the job."""
    # TODO: Implement job logic
    print("Running: {name}")
    pass
'''

    try:
        compile(code, "<string>", "exec")
    except SyntaxError as e:
        console.print(f"[red]Error: Invalid Python code - {e}[/red]")
        raise typer.Exit(1) from None

    scheduler = get_scheduler()
    job_id = await scheduler.submit_user_job(
        name=name,
        expression=cron_expression,
        code=code,
    )

    console.print(
        Panel(
            f"[green]✓[/green] Job '[bold]{name}[/bold]' submitted for approval\n\n"
            f"[dim]Cron:[/dim] {cron_expression}\n"
            f"[dim]Job ID:[/dim] {job_id}\n\n"
            f"[yellow]This job requires approval before it will run.[/yellow]\n"
            f"Run: [bold]alfred cron approve {job_id[:8]}[/bold]",
            title="Job Submitted",
            border_style="green",
        )
    )


@app.command("review")
@async_command
async def review_job(job_id: str = typer.Argument(..., help="Job ID or name")) -> None:
    """Review a pending job's details."""
    store = get_store()
    jobs = await store.load_jobs()
    job = _find_job(jobs, job_id)

    if job is None:
        console.print(f"[red]Error: Job '{job_id}' not found[/red]")
        raise typer.Exit(1)

    console.print(
        Panel(
            f"[bold]{job.name}[/bold]\n"
            f"[dim]ID:[/dim] {job.job_id}\n"
            f"[dim]Status:[/dim] {job.status}\n"
            f"[dim]Schedule:[/dim] {job.expression}\n"
            f"[dim]Created:[/dim] {job.created_at.strftime('%Y-%m-%d %H:%M')}",
            title="Job Details",
            border_style="blue",
        )
    )

    console.print("\n[bold]Code:[/bold]")
    syntax = Syntax(job.code, "python", theme="monokai", line_numbers=True)
    console.print(syntax)

    console.print("\n[bold]Resource Limits:[/bold]")
    console.print(f"  Timeout: {job.resource_limits.timeout_seconds}s")
    console.print(f"  Max Memory: {job.resource_limits.max_memory_mb}MB")
    console.print(f"  Network: {'Allowed' if job.resource_limits.allow_network else 'Blocked'}")

    if job.status == "pending":
        console.print("\n[yellow]This job is pending approval.[/yellow]")
        console.print(f"To approve: [bold]alfred cron approve {job.job_id[:8]}[/bold]")
        console.print(f"To reject: [bold]alfred cron reject {job.job_id[:8]}[/bold]")


@app.command("approve")
@async_command
async def approve_job(job_id: str = typer.Argument(..., help="Job ID or name")) -> None:
    """Approve a pending job."""
    store = get_store()
    scheduler = get_scheduler()
    jobs = await store.load_jobs()
    job = _find_job(jobs, job_id)

    if job is None:
        console.print(f"[red]Error: Job '{job_id}' not found[/red]")
        raise typer.Exit(1)

    if job.status == "active":
        console.print(f"[yellow]Job '{job.name}' is already active.[/yellow]")
        return

    if job.status != "pending":
        console.print(f"[red]Error: Cannot approve job with status '{job.status}'[/red]")
        raise typer.Exit(1)

    await scheduler.approve_job(job.job_id, "cli")

    console.print(
        Panel(
            f"[green]✓[/green] Approved '[bold]{job.name}[/bold]'\n"
            f"The job is now active and will run on schedule.",
            title="Job Approved",
            border_style="green",
        )
    )


@app.command("reject")
@async_command
async def reject_job(job_id: str = typer.Argument(..., help="Job ID or name")) -> None:
    """Reject and delete a pending job."""
    store = get_store()
    jobs = await store.load_jobs()
    job = _find_job(jobs, job_id)

    if job is None:
        console.print(f"[red]Error: Job '{job_id}' not found[/red]")
        raise typer.Exit(1)

    job_name = job.name
    await store.delete_job(job.job_id)

    console.print(
        Panel(
            f"[green]✓[/green] Deleted '[bold]{job_name}[/bold]'\nThe job has been removed.",
            title="Job Rejected",
            border_style="yellow",
        )
    )


@app.command("history")
@async_command
async def show_history(
    job_id: str | None = typer.Option(None, "--job-id", "-j", help="Filter by job ID"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum records to show"),
) -> None:
    """Show job execution history."""
    from src.cron.models import ExecutionRecord

    store = get_store()
    history_path = store.history_path

    if not history_path.exists():
        console.print("[yellow]No execution history found.[/yellow]")
        return

    async with aiofiles.open(history_path) as f:
        content = await f.read()

    records = []
    for line in content.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(ExecutionRecord.from_dict(json.loads(line)))
        except (json.JSONDecodeError, KeyError):
            continue

    if job_id:
        records = [r for r in records if r.job_id.startswith(job_id) or job_id in r.job_id]

    records.sort(key=lambda r: r.started_at, reverse=True)
    records = records[:limit]

    if not records:
        console.print(f"[yellow]No history found{' for job ' + job_id if job_id else ''}.[/yellow]")
        return

    table = Table(title="Execution History")
    table.add_column("Time", width=16)
    table.add_column("Job ID", width=8)
    table.add_column("Status", width=10)
    table.add_column("Duration", width=10)
    table.add_column("Memory", width=10)

    status_colors = {"success": "green", "failed": "red", "timeout": "yellow"}

    for record in records:
        status_color = status_colors.get(record.status.value, "white")
        if record.duration_ms < 1000:
            duration = f"{record.duration_ms}ms"
        else:
            duration = f"{record.duration_ms // 1000}s"
        memory = f"{record.memory_peak_mb}MB" if record.memory_peak_mb else "—"
        table.add_row(
            record.started_at.strftime("%Y-%m-%d %H:%M"),
            record.job_id[:8],
            f"[{status_color}]{record.status.value}[/{status_color}]",
            duration,
            memory,
        )

    console.print(table)
    console.print(f"\n[dim]Showing {len(records)} record(s)[/dim]")

    failed = [r for r in records if r.status.value in ("failed", "timeout")]
    if failed:
        console.print("\n[bold red]Failed Executions:[/bold red]")
        for record in failed[:3]:
            console.print(f"\n[dim]{record.started_at.strftime('%Y-%m-%d %H:%M')}[/dim]")
            if record.error_message:
                console.print(f"[red]{record.error_message}[/red]")


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
        [sys.executable, "-m", "src.cli.cron_runner", "--daemon"],
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


def _find_job(jobs: list[Job], identifier: str) -> Job | None:
    """Find job by ID or fuzzy name match."""
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
