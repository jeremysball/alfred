---
name: git-switch-commit
description: Stash changes, switch to main, commit, push, then return to your branch and restore stashed changes. Perfect for quickly committing fixes to main while working on a feature branch.
---

# 🔄 Git Switch Commit

Quickly commit changes to main while working on a feature branch without losing your work-in-progress.

## ✨ What It Does

```
Your Branch ──► Stash ──► Main ──► Commit ──► Push ──► Your Branch ──► Pop
```

This skill automates the tedious git workflow of temporarily switching branches to commit something to main, then returning to your work.

## 🚀 Usage

```bash
cd /workspace/alfred-prd/.pi/skills/git-switch-commit

# Commit current directory's changes to main
python3 src/git_switch_commit.py

# Commit specific files to main
python3 src/git_switch_commit.py --files "src/fix.py,tests/test_fix.py"

# Use custom commit message
python3 src/git_switch_commit.py --message "fix: urgent bug fix"

# Push to different remote
python3 src/git_switch_commit.py --remote upstream

# Dry run (see what would happen without doing it)
python3 src/git_switch_commit.py --dry-run
```

## 📋 Requirements

- Must be in a git repository
- Must have a clean git state or uncommitted changes to stash
- Must have `main` branch (configurable with `--branch`)

## 🔧 How It Works

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `git stash push` | Save your current changes |
| 2 | `git checkout main` | Switch to main branch |
| 3 | `git add <files>` | Stage specified files (or all) |
| 4 | `git commit -m "..."` | Commit with provided message |
| 5 | `git push origin main` | Push to remote |
| 6 | `git checkout <branch>` | Return to your branch |
| 7 | `git stash pop` | Restore your stashed changes |

## 🎯 Example Scenarios

### Scenario 1: Quick Fix to Main
You're working on `feature/big-refactor` and notice a critical bug in `config.py`:

```bash
# Edit config.py to fix the bug
vim config.py

# Commit just that fix to main without losing your refactor work
python3 src/git_switch_commit.py --files "config.py" --message "fix: correct database timeout"

# Continue your refactor where you left off
```

### Scenario 2: Update README While Coding
You're deep in feature development and want to update the README with new info:

```bash
# Edit README.md
vim README.md

# Commit to main and get right back to coding
python3 src/git_switch_commit.py --files "README.md" --message "docs: update API examples"
```

### Scenario 3: Emergency Hotfix
Production is broken and you need to push a fix NOW:

```bash
# Your feature branch has weeks of messy work
# But you have a clean fix ready

python3 src/git_switch_commit.py --files "src/critical_fix.py" \
  --message "hotfix: prevent data loss in edge case"

# Done. Back to your feature branch in seconds.
```

## ⚙️ Options

| Flag | Description | Default |
|------|-------------|---------|
| `--files` | Comma-separated list of files to commit | All changes |
| `--message`, `-m` | Commit message | "chore: quick update from <branch>" |
| `--branch` | Target branch to commit to | `main` |
| `--remote` | Remote to push to | `origin` |
| `--dry-run` | Show commands without executing | `false` |
| `--keep-stash` | Don't pop stash at end (leave for manual) | `false` |

## 🛡️ Safety Features

- **Stash conflict detection**: Warns if stash pop fails
- **Branch protection**: Refuses to run if already on target branch
- **Dry-run mode**: Preview all commands before executing
- **Clean return**: Always attempts to return to original branch even on failure

## 📝 Output Example

```
🔄 Git Switch Commit
═══════════════════════════════════════════════════════

📦 Stashing current changes...
✅ Stashed: WIP on feature-branch: a1b2c3d Work in progress

🔄 Switching to main...
✅ On branch main

📋 Staging files...
✅ Added: src/fix.py

💾 Committing...
✅ Committed: fix: correct database timeout
   3fd30b2 fix: correct database timeout

🚀 Pushing to origin/main...
✅ Pushed: main → origin/main

🔄 Returning to feature-branch...
✅ Switched to branch 'feature-branch'

📦 Restoring stashed changes...
✅ Stash popped: Dropped refs/stash@{0}

═══════════════════════════════════════════════════════
✨ Done! Your changes are on main and you're back to work.
```

## 🔗 Related Workflows

This skill pairs well with:
- **token-burn**: After pushing, check your token usage
- **prd-done**: Complete PRD workflow after committing

## License

MIT © 2025 Git Switch Commit
