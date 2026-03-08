#!/usr/bin/env python3
"""Generate static shell completions for alfred.

Supports Bash, Fish, and Zsh.
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
COMPLETIONS_DIR = PROJECT_ROOT / "completions"


def discover_commands():
    """Discover commands from the Typer app using Click introspection."""
    # Import here to avoid issues during module load
    import click
    from typer.main import get_group

    from alfred.cli.main import app

    completions = {"": []}  # "" = top-level commands

    # Get the underlying Click group
    group = get_group(app)

    # Get top-level commands and groups (filter out options/flags)
    for name, cmd in group.commands.items():
        # Skip flags/options that were incorrectly added as commands
        if name.startswith("-"):
            continue
        completions[""].append(name)
        if isinstance(cmd, click.Group):
            # This is a subcommand group (like cron, memory)
            completions[name] = list(cmd.commands.keys())

    return completions


def generate_bash(completions: dict) -> str:
    script = """#!/bin/bash
# Static bash completion for alfred
# Generated automatically - do not edit manually

_alfred_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Build command path (e.g., "cron list")
    local cmd_path=""
    for ((i=1; i<COMP_CWORD; i++)); do
        if [[ -n "${COMP_WORDS[i]}" && ! "${COMP_WORDS[i]}" =~ ^- ]]; then
            cmd_path="${cmd_path}${COMP_WORDS[i]} "
        fi
    done
    cmd_path="${cmd_path% }"

    case "$cmd_path" in
"""
    for path, opts in sorted(completions.items()):
        if not opts and path != "":
            continue

        # Add flags to top-level
        if path == "":
            opts.extend(
                ["--telegram", "-t", "--log", "-l", "--install-completions", "--help"]
            )

        opts_str = " ".join(sorted(set(opts)))
        case_path = path if path else '""'
        script += (
            f'        {case_path})\n            opts="{opts_str}"\n            ;;\n'
        )

    script += """        *)
            opts=""
            ;;
    esac

    if [[ -n "$opts" ]]; then
        COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
    fi

    return 0
}

complete -F _alfred_completion alfred
"""
    return script


def generate_fish(completions: dict) -> str:
    """Generate fish completions with descriptions and grouped output."""
    # Descriptions for top-level commands
    command_descriptions = {
        "cron": "Manage scheduled cron jobs",
        "daemon": "Manage the background daemon process",
        "jobs": "Manage pending jobs",
        "memory": "Memory system management",
    }

    # Descriptions for subcommands
    subcommand_descriptions = {
        "cron": {
            "list": "List all scheduled jobs",
            "submit": "Submit a new job for review",
            "review": "Review pending jobs",
            "approve": "Approve a pending job",
            "reject": "Reject a pending job",
            "history": "Show job execution history",
            "start": "Start a job immediately",
            "stop": "Stop a running job",
            "status": "Show job status",
            "reload": "Reload cron configuration",
        },
        "daemon": {
            "stop": "Stop the background daemon",
            "status": "Check daemon status",
            "reload": "Reload daemon configuration",
            "logs": "Open log file in $PAGER or $EDITOR",
        },
        "jobs": {
            "list": "List pending jobs",
            "submit": "Submit a new job",
            "review": "Review job details",
            "approve": "Approve job execution",
            "reject": "Reject job",
            "history": "Show job history",
        },
        "memory": {
            "migrate": "Migrate memory storage",
            "prune": "Prune expired memories",
            "status": "Show memory status",
        },
    }

    script = """# Alfred shell completions for fish
# Generated automatically - do not edit manually

# Disable file completions by default
complete -c alfred -f

# Global flags (available at top-level only, not in subcommands)
complete -c alfred -n "__fish_use_subcommand" -s t -l telegram -d "Run as Telegram bot"
complete -c alfred -n "__fish_use_subcommand" -s l -l log -d "Set log level" -a "info debug"
complete -c alfred -n "__fish_use_subcommand" -l install-completions -d "Install shell completions"
complete -c alfred -l help -d "Show help"

# Top-level commands with descriptions
"""

    top_level = completions.get("", [])

    # Main commands
    for cmd in top_level:
        desc = command_descriptions.get(cmd, cmd)
        script += f'complete -c alfred -n "__fish_use_subcommand" -a "{cmd}" -d "{desc}"\n'

    # Subcommand completions
    script += "\n# Subcommand completions\n"
    for path, opts in sorted(completions.items()):
        if not path or not opts:
            continue

        parts = path.split()
        if len(parts) == 1:
            desc_map = subcommand_descriptions.get(parts[0], {})
            for sub in opts:
                desc = desc_map.get(sub, sub)
                fish_cond = f'"__fish_seen_subcommand_from {parts[0]}"'
                script += f'complete -c alfred -n {fish_cond} -a "{sub}" -d "{desc}"\n'

    # Command-specific options (only after the command is typed)
    script += "\n# Command-specific options\n"
    script += (
        'complete -c alfred -n "__fish_seen_subcommand_from daemon; '
        'and not __fish_seen_subcommand_from stop status reload logs" '
        '-l bg -d "Run in background (daemonize)"\n'
    )

    return script


def generate_zsh(completions: dict) -> str:
    # Minimal Zsh completion wrapper
    script = """#compdef alfred
# Generated automatically - do not edit manually

_alfred() {
    local line
    _arguments -C \\
        '(-t --telegram)'{-t,--telegram}'[Run as Telegram bot]' \\
        '(-l --log)'{-l,--log}'[Set log level]:level:(info debug)' \\
        '--install-completions[Install shell completions]' \\
        '1: :->cmds' \\
        '*:: :->args'

    case $state in
        cmds)
            _values "alfred commands" \\
"""
    top_level = completions.get("", [])
    for cmd in top_level:
        script += f'                "{cmd}" \\\n'

    script += """            ;;
        args)
            case $line[1] in
"""
    for cmd in top_level:
        subcmds = completions.get(cmd, [])
        if subcmds:
            script += f'                {cmd})\n'
            script += f'                    _values "{cmd} subcommands" \\\n'
            for sub in subcmds:
                script += f'                        "{sub}" \\\n'
            script += "                    ;;\n"

    script += """            esac
            ;;
    esac
}

_alfred "$@"
"""
    return script


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="Check if completions are up to date"
    )
    parser.add_argument(
        "--shell", choices=["bash", "fish", "zsh", "all"], default="all"
    )
    args = parser.parse_args()

    # Discover completions from Typer app
    completions = discover_commands()

    # Validate we found commands
    if not completions.get(""):
        print("Error: No commands discovered from Typer app", file=sys.stderr)
        sys.exit(1)

    print(f"Discovered commands: {completions.get('', [])}", file=sys.stderr)
    for cmd, subcmds in completions.items():
        if cmd:
            print(f"  {cmd} subcommands: {subcmds}", file=sys.stderr)

    # Map shells to functions and filenames
    shell_map = {
        "bash": (generate_bash, "alfred.bash"),
        "fish": (generate_fish, "alfred.fish"),
        "zsh": (generate_zsh, "_alfred"),
    }

    if args.check:
        mismatch = False
        for _, (gen_func, filename) in shell_map.items():
            path = COMPLETIONS_DIR / filename
            if not path.exists():
                print(f"Error: {path} is missing")
                mismatch = True
                continue

            current = path.read_text()
            generated = gen_func(completions)
            if current != generated:
                print(f"Error: {path} is out of date")
                mismatch = True

        if mismatch:
            print(
                "\nRun 'python scripts/generate-static-completions.py' to regenerate."
            )
            sys.exit(1)
        else:
            print("Completions are up to date.")
            sys.exit(0)

    # Generate mode
    COMPLETIONS_DIR.mkdir(exist_ok=True)
    shells_to_gen = shell_map.keys() if args.shell == "all" else [args.shell]

    for shell in shells_to_gen:
        gen_func, filename = shell_map[shell]
        content = gen_func(completions)
        (COMPLETIONS_DIR / filename).write_text(content)
        print(f"Generated {COMPLETIONS_DIR / filename}")


if __name__ == "__main__":
    main()
