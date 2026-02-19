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

## 🚀 Instructions

When the user asks to use this skill, execute the following steps:

1. **Remember current branch**: `git branch --show-current`
2. **Stash changes**: `git stash push -m "WIP: git-switch-commit"`
3. **Switch to main**: `git checkout main`
4. **Stage files**: `git add <files>` (use specified files or `.` for all)
5. **Commit**: `git commit -m "<message>"` (use provided message or generate appropriate one)
6. **Push**: `git push origin main`
7. **Return to branch**: `git checkout <original-branch>`
8. **Restore stash**: `git stash pop`

## 🛡️ Safety Checks

- **Don't run if already on main** - warn user they're already on target branch
- **Handle stash pop conflicts** - if pop fails, inform user their changes are in `git stash list`
- **Always try to return** - even if commit/push fails, attempt to return to original branch

## 📋 Required from User

- **Files to commit** (optional - defaults to all staged/modified files)
- **Commit message** (optional - will generate conventional commit message)

## 🎯 Example

User: "Use git-switch-commit to commit the README changes"

```
CURRENT=$(git branch --show-current)
git stash push -m "WIP: git-switch-commit"
git checkout main
git add README.md
git commit -m "docs: update README"
git push origin main
git checkout $CURRENT
git stash pop
```
