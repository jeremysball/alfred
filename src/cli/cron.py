"""Cron job management commands."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from src.config import load_config

if TYPE_CHECKING:
    from src.cron.models import Job
    from src.cron.scheduler import CronScheduler
    from src.cron.store import CronStore

app = typer.Typer(help="Manage cron jobs")
console = Console()


def get_store() -> CronStore:
    """Get CronStore instance."""
    from src.cron.store import CronStore

    config = load_config()
    data_dir = getattr(config, "data_dir", Path("data"))
    return CronStore(data_dir)


def get_scheduler() -> CronScheduler:
    """Get CronScheduler instance."""
    from src.cron.scheduler import CronScheduler
    from src.cron.store import CronStore

    config = load_config()
    data_dir = getattr(config, "data_dir", Path("data"))
    store = CronStore(data_dir)
    return CronScheduler(store=store, data_dir=data_dir)


@app.command("list")
def list_jobs(
    status: str = typer.Option(
        "all",
        "--status",
        "-s",
        help="Filter by status: all, pending, active, paused",
    ),
) -> None:
    """List all cron jobs.

    Examples:
        alfred cron list
        alfred cron list --status pending
        alfred cron list -s active
    """
    asyncio.run(_list_jobs_async(status))


async def _list_jobs_async(status: str) -> None:
    """Async implementation of list_jobs."""
    store = get_store()
    jobs = await store.load_jobs()

    # Normalize filter
    status_filter = status.lower().strip()
    valid_filters = ["all", "pending", "active", "paused"]

    if status_filter not in valid_filters:
        valid_list = ", ".join(valid_filters)
        console.print(f"[red]Error: Invalid status '{status}'. Use: {valid_list}[/red]")
        raise typer.Exit(1)

    # Filter by status
    if status_filter != "all":
        jobs = [j for j in jobs if j.status == status_filter]

    if not jobs:
        if status_filter == "all":
            console.print("[yellow]No jobs found.[/yellow]")
        else:
            console.print(f"[yellow]No {status_filter} jobs found.[/yellow]")
        return

    # Create table
    table = Table(title=f"Cron Jobs ({status_filter})" if status_filter != "all" else "Cron Jobs")
    table.add_column("ID", style="dim", width=8)
    table.add_column("Name", style="bold")
    table.add_column("Status", width=10)
    table.add_column("Schedule")
    table.add_column("Last Run")

    status_colors = {
        "pending": "yellow",
        "active": "green",
        "paused": "dim",
    }

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
def submit_job(
    name: str = typer.Argument(..., help="Job name"),
    cron: str = typer.Argument(..., help="Cron expression or natural language"),
    code: str | None = typer.Option(
        None,
        "--code",
        "-c",
        help="Python code for the job (opens editor if not provided)",
    ),
) -> None:
    """Submit a new cron job for approval.

    Examples:
        alfred cron submit "Daily Report" "0 9 * * *"
        alfred cron submit "Weekly cleanup" "Sundays at 7pm" --code "print('hello')"
    """
    asyncio.run(_submit_job_async(name, cron, code))


async def _submit_job_async(name: str, cron: str, code: str | None) -> None:
    """Async implementation of submit_job."""
    from src.cron import parser
    from src.cron.nlp_parser import NaturalLanguageCronParser

    # Try to parse cron expression
    nlp_parser = NaturalLanguageCronParser()
    parsed = nlp_parser.parse(cron)

    if parsed is None:
        # Not valid natural language, try strict cron
        if not parser.is_valid(cron):
            console.print(f"[red]Error: Invalid cron expression '{cron}'[/red]")
            console.print("\nTry natural language:")
            console.print("  'every morning at 8am'")
            console.print("  'Sundays at 7pm'")
            console.print("  'every 15 minutes'")
            console.print("\nOr cron format: '0 9 * * *' for 9am daily")
            raise typer.Exit(1)
        cron_expression = cron
        schedule_desc = cron
    elif parsed.confidence < 0.7:
        console.print(f"[yellow]Warning: Low confidence parsing '{cron}'[/yellow]")
        console.print(f"Parsed as: {parsed.cron_expression}")
        cron_expression = parsed.cron_expression
        schedule_desc = parsed.description
    else:
        cron_expression = parsed.cron_expression
        schedule_desc = parsed.description

    # Generate code if not provided
    if code is None:
        code = _generate_default_code(name)

    try:
        compile(code, "<string>", "exec")
    except SyntaxError as e:
        console.print(f"[red]Error: Invalid Python code - {e}[/red]")
        raise typer.Exit(1) from None

    # Submit job
    scheduler = get_scheduler()
    job_id = await scheduler.submit_user_job(
        name=name,
        expression=cron_expression,
        code=code,
    )

    console.print(Panel(
        f"[green]✓[/green] Job '[bold]{name}[/bold]' submitted for approval\n\n"
        f"[dim]Schedule:[/dim] {schedule_desc}\n"
        f"[dim]Cron:[/dim] {cron_expression}\n"
        f"[dim]Job ID:[/dim] {job_id}\n\n"
        f"[yellow]This job requires approval before it will run.[/yellow]\n"
        f"Run: [bold]alfred cron approve {job_id[:8]}[/bold]",
        title="Job Submitted",
        border_style="green",
    ))


def _generate_default_code(name: str) -> str:
    """Generate default job code template."""
    return f'''"""Job: {name}"""

async def run():
    """Execute the job."""
    # TODO: Implement job logic
    print("Running: {name}")
    pass
'''


@app.command("review")
def review_job(
    job_id: str = typer.Argument(..., help="Job ID or name"),
) -> None:
    """Review a pending job's details.

    Shows the job code, schedule, and status for review before approval.

    Examples:
        alfred cron review abc12345
        alfred cron review "Daily Report"
    """
    asyncio.run(_review_job_async(job_id))


async def _review_job_async(job_id: str) -> None:
    """Async implementation of review_job."""
    store = get_store()
    jobs = await store.load_jobs()

    # Find job by ID or name
    job = _find_job(jobs, job_id)

    if job is None:
        console.print(f"[red]Error: Job '{job_id}' not found[/red]")
        raise typer.Exit(1)

    # Display job details
    console.print(Panel(
        f"[bold]{job.name}[/bold]\n"
        f"[dim]ID:[/dim] {job.job_id}\n"
        f"[dim]Status:[/dim] {job.status}\n"
        f"[dim]Schedule:[/dim] {job.expression}\n"
        f"[dim]Created:[/dim] {job.created_at.strftime('%Y-%m-%d %H:%M')}",
        title="Job Details",
        border_style="blue",
    ))

    # Display code with syntax highlighting
    console.print("\n[bold]Code:[/bold]")
    syntax = Syntax(job.code, "python", theme="monokai", line_numbers=True)
    console.print(syntax)

    # Show resource limits
    console.print("\n[bold]Resource Limits:[/bold]")
    console.print(f"  Timeout: {job.resource_limits.timeout_seconds}s")
    console.print(f"  Max Memory: {job.resource_limits.max_memory_mb}MB")
    console.print(f"  Network: {'Allowed' if job.resource_limits.allow_network else 'Blocked'}")

    if job.status == "pending":
        console.print("\n[yellow]This job is pending approval.[/yellow]")
        console.print(f"To approve: [bold]alfred cron approve {job.job_id[:8]}[/bold]")
        console.print(f"To reject: [bold]alfred cron reject {job.job_id[:8]}[/bold]")


@app.command("approve")
def approve_job(
    job_id: str = typer.Argument(..., help="Job ID or name"),
) -> None:
    """Approve a pending job.

    Once approved, the job will run on its schedule.

    Examples:
        alfred cron approve abc12345
        alfred cron approve "Daily Report"
    """
    asyncio.run(_approve_job_async(job_id))


async def _approve_job_async(job_id: str) -> None:
    """Async implementation of approve_job."""
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

    console.print(Panel(
        f"[green]✓[/green] Approved '[bold]{job.name}[/bold]'\n"
        f"The job is now active and will run on schedule.",
        title="Job Approved",
        border_style="green",
    ))


@app.command("reject")
def reject_job(
    job_id: str = typer.Argument(..., help="Job ID or name"),
) -> None:
    """Reject and delete a pending job.

    Examples:
        alfred cron reject abc12345
        alfred cron reject "Daily Report"
    """
    asyncio.run(_reject_job_async(job_id))


async def _reject_job_async(job_id: str) -> None:
    """Async implementation of reject_job."""
    store = get_store()
    jobs = await store.load_jobs()

    job = _find_job(jobs, job_id)

    if job is None:
        console.print(f"[red]Error: Job '{job_id}' not found[/red]")
        raise typer.Exit(1)

    job_name = job.name
    await store.delete_job(job.job_id)

    console.print(Panel(
        f"[green]✓[/green] Deleted '[bold]{job_name}[/bold]'\n"
        f"The job has been removed.",
        title="Job Rejected",
        border_style="yellow",
    ))


@app.command("history")
def show_history(
    job_id: str | None = typer.Option(
        None,
        "--job-id",
        "-j",
        help="Filter by job ID",
    ),
    limit: int = typer.Option(
        20,
        "--limit",
        "-l",
        help="Maximum number of records to show",
    ),
) -> None:
    """Show job execution history.

    Examples:
        alfred cron history
        alfred cron history --job-id abc12345
        alfred cron history -j abc12345 -l 50
    """
    asyncio.run(_show_history_async(job_id, limit))


async def _show_history_async(job_id: str | None, limit: int) -> None:
    """Async implementation of show_history."""
    store = get_store()

    # Load all history
    history_path = store.history_path
    if not history_path.exists():
        console.print("[yellow]No execution history found.[/yellow]")
        return

    from src.cron.models import ExecutionRecord

    records = []
    content = await _read_file_async(history_path)

    for line in content.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            import json
            data = json.loads(line)
            records.append(ExecutionRecord.from_dict(data))
        except (json.JSONDecodeError, KeyError):
            continue

    # Filter by job_id if provided
    if job_id:
        # Also support partial ID matching
        records = [r for r in records if r.job_id.startswith(job_id) or job_id in r.job_id]

    # Sort by started_at descending
    records.sort(key=lambda r: r.started_at, reverse=True)

    # Apply limit
    records = records[:limit]

    if not records:
        if job_id:
            console.print(f"[yellow]No history found for job '{job_id}'.[/yellow]")
        else:
            console.print("[yellow]No execution history found.[/yellow]")
        return

    # Create table
    table = Table(title="Execution History")
    table.add_column("Time", width=16)
    table.add_column("Job ID", width=8)
    table.add_column("Status", width=10)
    table.add_column("Duration", width=10)
    table.add_column("Memory", width=10)

    status_colors = {
        "success": "green",
        "failed": "red",
        "timeout": "yellow",
    }

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

    if records:
        console.print(f"\n[dim]Showing {len(records)} record(s)[/dim]")

        # Show error details for failed jobs
        failed = [r for r in records if r.status.value in ("failed", "timeout")]
        if failed:
            console.print("\n[bold red]Failed Executions:[/bold red]")
            for record in failed[:3]:  # Show first 3 failures
                console.print(f"\n[dim]{record.started_at.strftime('%Y-%m-%d %H:%M')}[/dim]")
                if record.error_message:
                    console.print(f"[red]{record.error_message}[/red]")


async def _read_file_async(path: Path) -> str:
    """Read file asynchronously."""
    import aiofiles

    async with aiofiles.open(path) as f:
        return await f.read()


def _find_job(jobs: list[Job], identifier: str) -> Job | None:
    """Find job by ID or fuzzy name match.

    Args:
        jobs: List of jobs to search
        identifier: Job ID or name to match

    Returns:
        Matching job or None
    """
    identifier_lower = identifier.lower()

    # Try exact ID match first
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
    if len(matches) == 1:
        return matches[0]

    return None
