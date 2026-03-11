"""Daemon CLI commands - manage the background daemon process."""

import subprocess
import sys
import time

import typer
from rich.console import Console

from alfred.cron.daemon import DaemonManager

console = Console()


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


def daemon_status() -> None:
    """Check daemon status."""
    daemon = DaemonManager()

    if daemon.is_running():
        pid = daemon.read_pid()
        console.print(f"[green]●[/green] Daemon running (PID {pid})")
    else:
        console.print("[dim]○[/dim] Daemon not running")


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
