---
name: git-switch-commit
description: Stash changes, switch to main, commit, push, then return to your branch and restore stashed changes. Perfect for quickly committing fixes to main while working on a feature branch.
---

# 🔄 Git Switch Commit

Quickly commit changes to main while working on a feature branch without losing your work-in-progress.

## ✨ What It Does

```
Feature Branch ──► Stash ──► Main ──► Edit/Apply ──► Commit ──► Push ──► Feature Branch ──► Pop
```

## 🚨 Key Insight

**Git stash is global** - stashes are not per-branch. After stashing on feature branch and switching to main, the stash is still accessible. Pop it on main to bring the changes with you.

## 🎯 Two Scenarios

### Scenario A: Transfer Files from Feature to Main

You have uncommitted changes on feature branch and want to commit some of them to main.

**Two-Stash Approach** (handles partial files cleanly):

```bash
# 1. Stage only the files you want to transfer
git add <files-to-transfer>

# 2. Stash staged files (named for clarity)
git stash push -m "transfer-to-main" --staged

# 3. Stash remaining changes
git stash push -m "wip-feature" -u

# 4. Switch to main
git checkout main

# 5. Pop the transfer stash (stash@{1} because "wip-feature" is now stash@{0})
git stash pop stash@{1}

# 6. Commit and push
git commit -m "fix: something urgent"
git push origin main

# 7. Return to feature branch
git checkout feature/my-branch

# 8. Restore remaining work
git stash pop
```

**Stash Order After Step 3:**
- `stash@{0}` = "wip-feature" (most recent)
- `stash@{1}` = "transfer-to-main"

### Scenario B: Edit Files Directly on Main

You want to edit a file on main (not transfer from feature branch).

```bash
# 1. Stash all feature branch work
git stash push -m "wip-feature" -u

# 2. Switch to main
git checkout main

# 3. Make your edits
# (use edit tool, vim, etc.)

# 4. Commit and push
git add <files>
git commit -m "chore: update todo"
git push origin main

# 5. Return to feature branch
git checkout feature/my-branch

# 6. Restore your work
git stash pop
```

## 📋 Commands Reference

| Command | Purpose |
|---------|---------|
| `git stash push -m "name" -u` | Stash all changes (including untracked) with name |
| `git stash push -m "name" --staged` | Stash only staged files |
| `git stash list` | Show all stashes with names |
| `git stash pop stash@{N}` | Pop specific stash by index |
| `git stash drop stash@{N}` | Drop specific stash |

## 🛡️ Safety

- Use named stashes (`-m "description"`) for clarity
- Verify stash index before popping - order changes after each push
- Clean up leftover stashes with `git stash drop`
