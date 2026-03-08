"""Logic for installing fast static shell completions."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from alfred.interfaces.ansi import apply_ansi

SUPPORTED_SHELLS = ["bash", "fish", "zsh"]


def install(shell: str | None = None) -> None:
    """Install fast static completions for the specified shell.

    Args:
        shell: Shell to install completions for (bash, fish, zsh).
               If None, attempts to auto-detect from $SHELL.
    """
    if shell is None:
        shell = _detect_shell()

    if not shell:
        print(
            apply_ansi("{red}Could not detect shell. Currently supporting: bash, fish, zsh{reset}")
        )
        print(apply_ansi("{dim}Use: --install-completions --shell bash|fish|zsh{reset}"))
        return

    shell = shell.lower().strip()
    if shell not in SUPPORTED_SHELLS:
        print(apply_ansi(f"{{red}}Unknown shell: {shell}. Use: bash, fish, or zsh{{reset}}"))
        return

    # 1. Regenerate completions to ensure they are up-to-date
    project_root = Path(__file__).parent.parent.parent.parent
    gen_script = project_root / "scripts" / "generate-static-completions.py"

    print(apply_ansi("{cyan}Regenerating static completions...{reset}"))
    try:
        subprocess.run([sys.executable, str(gen_script)], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(apply_ansi(f"{{red}}Failed to regenerate completions: {e}{{reset}}"))
        return

    # 2. Copy the relevant completion file to the user's config directory
    success = False
    if shell == "bash":
        success = _install_bash(project_root)
    elif shell == "fish":
        success = _install_fish(project_root)
    elif shell == "zsh":
        success = _install_zsh(project_root)

    if success:
        print(apply_ansi(f"{{green}}✓ Static completions installed for {shell}.{{reset}}"))
        print(
            apply_ansi("{dim}Restart your shell or source the completion file to activate.{reset}")
        )


def _detect_shell() -> str | None:
    """Detect the current shell."""
    shell_path = os.environ.get("SHELL", "")
    if "bash" in shell_path:
        return "bash"
    if "fish" in shell_path:
        return "fish"
    if "zsh" in shell_path:
        return "zsh"
    return None


def _install_bash(project_root: Path) -> bool:
    """Install Bash completions."""
    comp_file = project_root / "completions" / "alfred.bash"
    dest_dir = Path.home() / ".local" / "share" / "bash-completion" / "completions"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / "alfred"

    shutil.copy(comp_file, dest_file)
    print(apply_ansi(f"{{dim}}Copied {comp_file.name} to {dest_file}{{reset}}"))
    return True


def _install_fish(project_root: Path) -> bool:
    """Install Fish completions."""
    comp_file = project_root / "completions" / "alfred.fish"
    dest_dir = Path.home() / ".config" / "fish" / "completions"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / "alfred.fish"

    shutil.copy(comp_file, dest_file)
    print(apply_ansi(f"{{dim}}Copied {comp_file.name} to {dest_file}{{reset}}"))
    return True


def _install_zsh(project_root: Path) -> bool:
    """Install Zsh completions."""
    comp_file = project_root / "completions" / "_alfred"
    dest_dir = Path.home() / ".zsh" / "completions"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / "_alfred"

    shutil.copy(comp_file, dest_file)
    print(apply_ansi(f"{{dim}}Copied {comp_file.name} to {dest_file}{{reset}}"))

    # Check if ~/.zshrc contains the completion path
    zshrc = Path.home() / ".zshrc"
    if zshrc.exists():
        content = zshrc.read_text()
        if "~/.zsh/completions" not in content:
            print(apply_ansi("{yellow}Note: Add completion path to ~/.zshrc:{reset}"))
            print(apply_ansi("{dim}  fpath=(~/.zsh/completions $fpath){reset}"))
            print(apply_ansi("{dim}  autoload -Uz compinit && compinit{reset}"))

    return True
