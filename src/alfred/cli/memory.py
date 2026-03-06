"""Memory management CLI commands."""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="memory",
    help="Manage Alfred's memory system",
)
console = Console()


@app.command("migrate")
def migrate_command(
    provider: str = typer.Option(  # noqa: B008
        "local",
        "--provider",
        "-p",
        help="Embedding provider: 'local' (BGE) or 'openai'",
    ),
    backup: bool = typer.Option(  # noqa: B008
        True,
        "--backup/--no-backup",
        help="Create backup of JSONL file",
    ),
    jsonl_path: Path | None = typer.Option(  # noqa: B008
        None,
        "--jsonl-path",
        help="Path to memories.jsonl (default: XDG data dir)",
    ),
    faiss_path: Path | None = typer.Option(  # noqa: B008
        None,
        "--faiss-path",
        help="Path for FAISS index (default: XDG data dir /faiss)",
    ),
) -> None:
    """Migrate memories from JSONL to FAISS.

    This command converts your existing JSONL memory store to a FAISS-backed
    store for 5,400x faster semantic search. A backup of the original file
    is created by default.

    Examples:
        alfred memory migrate
        alfred memory migrate --provider openai
        alfred memory migrate --no-backup
    """
    from alfred.memory.migrate import migrate_command as migrate_async

    console.print("[bold blue]Migrating memories from JSONL to FAISS...[/]")

    async def run_migration() -> None:
        stats = await migrate_async(
            jsonl_path=jsonl_path,
            faiss_path=faiss_path,
            provider_type=provider,
            backup=backup,
        )

        # Display results
        table = Table(title="Migration Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Migrated", str(stats["migrated"]))
        table.add_row("Failed", str(stats["failed"]))
        table.add_row("Skipped", str(stats["skipped"]))
        table.add_row("Duration", f"{stats['duration_seconds']}s")

        console.print(table)

        if stats["migrated"] > 0:
            console.print("\n[bold green]✓[/] Migration complete!")
            console.print("Update your config.toml to use FAISS:")
            console.print("  [memory]")
            console.print('  store = "faiss"')
        elif stats.get("error"):
            console.print(f"\n[bold red]✗[/] Error: {stats['error']}")
        else:
            console.print("\n[yellow]No memories found to migrate.[/]")

    asyncio.run(run_migration())


@app.command("status")
def status_command() -> None:
    """Show memory system status.

    Displays information about the current memory store:
    - Store type (JSONL or FAISS)
    - Number of memories
    - Index type (if FAISS)
    - Disk usage
    """
    from alfred.config import load_config
    from alfred.data_manager import get_memory_dir

    config = load_config()
    memory_dir = get_memory_dir()

    console.print("[bold]Memory System Status[/]\n")

    # Store type
    store_type = getattr(config, "memory_store", "jsonl")
    console.print(f"Store type: [cyan]{store_type}[/]")

    # Check for files
    jsonl_path = memory_dir / "memories.jsonl"
    faiss_path = memory_dir / "faiss"

    if store_type == "faiss" or faiss_path.exists():
        index_file = faiss_path / "index.faiss"
        metadata_file = faiss_path / "metadata.json"

        if index_file.exists():
            console.print(f"FAISS index: [green]✓[/] ({index_file.stat().st_size / 1024:.1f} KB)")

            if metadata_file.exists():
                import json

                with open(metadata_file) as f:
                    meta = json.load(f)
                console.print(f"Entries: [cyan]{len(meta.get('entries', []))}[/]")
                console.print(f"Index type: [cyan]{meta.get('index_type', 'flat')}[/]")

    if jsonl_path.exists():
        console.print(f"JSONL backup: [green]✓[/] ({jsonl_path.stat().st_size / 1024:.1f} KB)")

        # Count entries
        with open(jsonl_path) as f:
            count = sum(1 for line in f if line.strip())
        console.print(f"JSONL entries: [cyan]{count}[/]")

    # Config settings
    console.print("\n[bold]Configuration[/]")
    provider = getattr(config, "embedding_provider", "openai")
    local_model = getattr(config, "local_embedding_model", "bge-base")
    ttl_days = getattr(config, "memory_ttl_days", 90)
    warning = getattr(config, "memory_warning_threshold", 1000)
    console.print(f"Embedding provider: [cyan]{provider}[/]")
    console.print(f"Local model: [cyan]{local_model}[/]")
    console.print(f"TTL days: [cyan]{ttl_days}[/]")
    console.print(f"Warning threshold: [cyan]{warning}[/]")


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
    console.print("Pruning is not yet implemented for FAISS stores.")
    console.print("Use the existing JSONL prune functionality or wait for integration.")
