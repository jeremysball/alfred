"""Memory management CLI commands."""

import typer
from rich.console import Console

from src.data_manager import get_memory_dir

app = typer.Typer(
    name="memory",
    help="Manage Alfred's memory system",
)
console = Console()


@app.command("status")
def status_command() -> None:
    """Show memory system status.

    Displays information about the current memory store:
    - JSONL entry count
    - Disk usage
    """
    memory_dir = get_memory_dir()

    console.print("[bold]Memory System Status[/]\n")

    jsonl_path = memory_dir / "memories.jsonl"
    if jsonl_path.exists():
        console.print(
            f"JSONL store: [green]✓[/] ({jsonl_path.stat().st_size / 1024:.1f} KB)"
        )
        with open(jsonl_path) as f:
            count = sum(1 for line in f if line.strip())
        console.print(f"JSONL entries: [cyan]{count}[/]")
    else:
        console.print("JSONL store: [yellow]missing[/]")


@app.command("prune")
def prune_command(
    ttl_days: int = typer.Option(  # noqa: B008
        90,
        "--ttl",
        "-t",
        help="Remove memories older than this many days",
    ),
    dry_run: bool = typer.Option(  # noqa: B008
        True,
        "--dry-run/--no-dry-run",
        help="Show what would be deleted without deleting",
    ),
) -> None:
    """Prune expired memories.

    Removes non-permanent memories older than TTL days.
    Use --dry-run to see what would be deleted first.
    """
    console.print("[bold]Pruning expired memories...[/]\n")

    if dry_run:
        console.print("[yellow]Dry run mode - no changes will be made[/]\n")

    # This would integrate with the memory store's prune functionality
    console.print("Pruning is not yet implemented.")
