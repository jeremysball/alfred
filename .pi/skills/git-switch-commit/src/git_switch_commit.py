#!/usr/bin/env python3
"""
git-switch-commit: Stash, switch to main, commit, push, return, and pop.

Automates the workflow of quickly committing changes to main while
working on a feature branch, without losing work-in-progress.
"""

import argparse
import subprocess
import sys
from typing import Optional, Tuple


def run_cmd(cmd: list[str], check: bool = True, capture: bool = True) -> Tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=False
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def get_current_branch() -> str:
    """Get the name of the current git branch."""
    _, stdout, _ = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return stdout


def has_changes() -> bool:
    """Check if there are uncommitted changes."""
    returncode, _, _ = run_cmd(["git", "diff", "--quiet", "--cached"], check=False)
    if returncode != 0:
        return True
    returncode, _, _ = run_cmd(["git", "diff", "--quiet"], check=False)
    return returncode != 0


def stash_changes(message: Optional[str] = None) -> str:
    """Stash current changes and return stash ref."""
    cmd = ["git", "stash", "push"]
    if message:
        cmd.extend(["-m", message])
    
    _, stdout, _ = run_cmd(cmd)
    
    # Get the stash ref (e.g., "stash@{0}")
    _, stash_list, _ = run_cmd(["git", "stash", "list"])
    if stash_list:
        first_line = stash_list.split('\n')[0]
        stash_ref = first_line.split(':')[0]
        return stash_ref
    return "stash@{0}"


def switch_branch(branch: str) -> None:
    """Switch to specified branch."""
    run_cmd(["git", "checkout", branch])


def stage_files(files: Optional[list[str]] = None) -> None:
    """Stage files for commit. If no files specified, stage all."""
    if files:
        run_cmd(["git", "add"] + files)
    else:
        run_cmd(["git", "add", "-A"])


def commit_changes(message: str) -> str:
    """Commit staged changes and return commit hash."""
    run_cmd(["git", "commit", "-m", message])
    _, stdout, _ = run_cmd(["git", "rev-parse", "--short", "HEAD"])
    return stdout


def push_to_remote(branch: str, remote: str = "origin") -> None:
    """Push current branch to remote."""
    run_cmd(["git", "push", remote, branch])


def pop_stash(stash_ref: Optional[str] = None) -> None:
    """Pop the most recent stash or specified stash."""
    cmd = ["git", "stash", "pop"]
    if stash_ref:
        cmd.append(stash_ref)
    run_cmd(cmd)


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n🔄 {text}")
    print("═" * 55)


def print_step(emoji: str, text: str) -> None:
    """Print a step in the process."""
    print(f"\n{emoji} {text}")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"✅ {text}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"❌ {text}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="🔄 Stash, switch to main, commit, push, return, and pop",
        epilog="Example: git_switch_commit.py --files 'fix.py' -m 'fix: urgent bug'"
    )
    
    parser.add_argument(
        "--files", "-f",
        help="Comma-separated list of files to commit (default: all changes)"
    )
    parser.add_argument(
        "--message", "-m",
        help="Commit message (default: auto-generated)"
    )
    parser.add_argument(
        "--branch", "-b",
        default="main",
        help="Target branch to commit to (default: main)"
    )
    parser.add_argument(
        "--remote", "-r",
        default="origin",
        help="Remote to push to (default: origin)"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show commands without executing"
    )
    parser.add_argument(
        "--keep-stash", "-k",
        action="store_true",
        help="Don't pop stash at end (leave for manual)"
    )
    
    args = parser.parse_args()
    
    # Determine files to stage
    files_to_stage = None
    if args.files:
        files_to_stage = [f.strip() for f in args.files.split(",")]
    
    # Get current state
    original_branch = get_current_branch()
    
    # Don't run if already on target branch
    if original_branch == args.branch:
        print_error(f"Already on {args.branch}. No need to switch.")
        print("   Use 'git commit' and 'git push' directly.")
        sys.exit(1)
    
    # Generate commit message if not provided
    commit_msg = args.message
    if not commit_msg:
        commit_msg = f"chore: quick update from {original_branch}"
    
    if args.dry_run:
        print_header("DRY RUN - Commands that would execute:")
        print(f"  git stash push -m 'WIP on {original_branch}'")
        print(f"  git checkout {args.branch}")
        if files_to_stage:
            print(f"  git add {', '.join(files_to_stage)}")
        else:
            print("  git add -A")
        print(f"  git commit -m '{commit_msg}'")
        print(f"  git push {args.remote} {args.branch}")
        print(f"  git checkout {original_branch}")
        if not args.keep_stash:
            print("  git stash pop")
        else:
            print("  [stash left in place -- use 'git stash pop' manually]")
        sys.exit(0)
    
    print_header("Git Switch Commit")
    
    try:
        # Step 1: Stash current changes
        print_step("📦", "Stashing current changes...")
        stash_ref = stash_changes(f"WIP on {original_branch}")
        print_success(f"Stashed: {stash_ref}")
        
        # Step 2: Switch to target branch
        print_step("🔄", f"Switching to {args.branch}...")
        switch_branch(args.branch)
        print_success(f"On branch {args.branch}")
        
        # Step 3: Stage files
        print_step("📋", "Staging files...")
        stage_files(files_to_stage)
        if files_to_stage:
            print_success(f"Added: {', '.join(files_to_stage)}")
        else:
            print_success("Added all changes")
        
        # Step 4: Commit
        print_step("💾", "Committing...")
        commit_hash = commit_changes(commit_msg)
        print_success(f"Committed: {commit_msg}")
        print(f"   {commit_hash} {commit_msg[:50]}")
        
        # Step 5: Push
        print_step("🚀", f"Pushing to {args.remote}/{args.branch}...")
        push_to_remote(args.branch, args.remote)
        print_success(f"Pushed: {args.branch} → {args.remote}/{args.branch}")
        
        # Step 6: Return to original branch
        print_step("🔄", f"Returning to {original_branch}...")
        switch_branch(original_branch)
        print_success(f"Switched to branch '{original_branch}'")
        
        # Step 7: Pop stash (unless --keep-stash)
        if not args.keep_stash:
            print_step("📦", "Restoring stashed changes...")
            try:
                pop_stash()
                print_success("Stash popped: Changes restored")
            except RuntimeError as e:
                print_error(f"Stash pop failed: {e}")
                print("   Your changes are still in the stash.")
                print("   Run 'git stash pop' manually after resolving.")
        else:
            print_step("📦", "Keeping stash in place...")
            print_success("Stash preserved: Run 'git stash pop' when ready")
        
        print("\n" + "═" * 55)
        print("✨ Done! Your changes are on main and you're back to work.")
        
    except RuntimeError as e:
        print_error(f"Workflow failed: {e}")
        print(f"\n⚠️  Attempting to return to {original_branch}...")
        try:
            switch_branch(original_branch)
            print_success(f"Returned to {original_branch}")
            print("   Check 'git stash list' for your stashed changes.")
        except RuntimeError:
            print_error(f"Could not return to {original_branch}")
            print("   Manual intervention required!")
        sys.exit(1)


if __name__ == "__main__":
    main()
