---
name: git-switch-commit
description: Interactively commit specific files to main (or another branch) while working on a dirty feature branch. Preserves all other uncommitted changes.
---

# 🔄 Git Switch Commit

Commit selected files to another branch without losing work-in-progress on your current branch.

## 🎯 When to Use

- Working on a feature branch with dirty work tree
- Another agent or process is editing files
- Need to commit a specific file or two to main quickly
- Don't want to lose or disturb other uncommitted changes

## 📋 Interactive Workflow

Execute these steps in order:

### Step 1: List Dirty Files

```bash
git status --short
```

Present the list to the user and ask: **"Which files should be committed to the target branch?"**

Wait for user to select files (by number, path, or glob).

### Step 2: Stash All Changes

```bash
git stash push -m "switch-commit-temp" -u
```

This captures ALL uncommitted changes (including untracked files) into a named stash.

### Step 3: Switch to Target Branch

```bash
git checkout main  # or user-specified branch
```

Default is `main`. Ask user if they want a different branch.

### Step 4: Extract Only Selected Files from Stash

```bash
git checkout stash@{0} -- <file1> <file2> ...
```

**Important**: Use `checkout` not `pop` - this extracts specific files without removing the stash.

### Step 5: Infer Commit Message and Confirm

Read the diffs of the selected files:

```bash
git diff --cached <files>  # if staged
git diff <files>           # if unstaged
```

Generate a conventional commit message based on the changes. Present to user:

> **Inferred commit message:**
> ```
> fix: update authentication timeout handling
> ```
>
> Use this message? **[Y/n/edit]**

- **Y** (default): Proceed with this message
- **n**: Prompt user to enter a custom message
- **edit**: Let user type a modified message

### Step 6: Commit and Push

```bash
git add <files>
git commit -m "<message>"
git push origin <branch>
```

### Step 7: Switch Back to Original Branch

```bash
git checkout <original-branch>
```

### Step 8: Pop Stash

```bash
git stash pop
```

This restores all your work-in-progress.

### Step 9: Cleanup (if needed)

If the stash wasn't fully popped (conflict or partial extraction):

```bash
git stash drop stash@{0}
```

## 🛡️ Safety Rules

| Situation | Action |
|-----------|--------|
| Stash pop conflict | **Abort immediately**. Notify user with file paths. Do not force resolution. |
| Push rejected (non-fast-forward) | Abort. Notify user to pull first. |
| File not in stash | Skip file, warn user, continue with remaining files. |
| User cancels at any step | Restore original state: switch back, pop stash. |

## 📝 Example Session

```
Agent: I see these dirty files:
       1. src/auth.py
       2. src/utils.py
       3. tests/test_auth.py
       4. README.md

       Which files should be committed to main?

User:   1 and 4

Agent: Switching to main with src/auth.py and README.md...
       [stashes, switches, extracts files]

       Inferred commit message:
       "fix: update auth timeout and docs"

       Use this message? [Y/n/edit]

User:   Y

Agent: [commits, pushes, switches back, pops stash]
       Done! Committed to main, all other changes restored on feature branch.
```

## 🔧 Quick Reference

| Command | Purpose |
|---------|---------|
| `git status --short` | List dirty files concisely |
| `git stash push -m "name" -u` | Stash all changes (including untracked) |
| `git checkout stash@{0} -- <files>` | Extract specific files from stash |
| `git stash pop` | Restore all stashed changes |
| `git stash list` | Show all stashes |
| `git stash drop stash@{0}` | Remove a stash |
