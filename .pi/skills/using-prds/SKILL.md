---
name: using-prds
description: Master the PRD workflow. Load at the start of every conversation to understand when and how to use PRD skills.
---

# Using PRDs - Product Requirements Document Workflow

## Overview

PRDs (Product Requirements Documents) guide feature development from concept to completion. This skill explains the complete PRD lifecycle and when to use each PRD command.

## PRD Lifecycle

```
Create → Start → Work → Update → Complete/Close
```

## The PRD Skills

### 1. `/prd-create` - Create a New PRD

**When to use:** You have a new feature idea and need to document requirements.

**What it does:**
- Creates a GitHub issue with the "PRD" label
- Creates a detailed PRD file in `prds/[issue-id]-[feature-name].md`
- Defines 5-10 major milestones (not micro-tasks)
- Links the issue to the PRD

**Example:**
```
I want to add a notification system → /prd-create
```

---

### 2. `/prd-start [issue-id]` - Begin Implementation

**When to use:** You are ready to start coding on an existing PRD.

**What it does:**
- Validates the PRD is ready for implementation
- Creates a feature branch: `feature/prd-[issue-id]-[name]`
- Sets up the development environment
- Hands off to `/prd-next` for task identification

**Example:**
```
Ready to work on PRD #12 → /prd-start 12
```

---

### 3. `/prd-next` - Get the Next Task

**When to use:** You want to know what to work on next.

**What it does:**
- Analyzes the current PRD state
- Identifies the single highest-priority task
- Recommends what to work on and why
- Helps design the implementation

**Example:**
```
What should I work on? → /prd-next
```

**Note:** After implementing the task, run `/prd-update-progress`.

---

### 4. `/prd-update-progress` - Record Completed Work

**When to use:** You have completed implementation work and want to update the PRD.

**What it does:**
- Updates PRD checkboxes based on git commits
- Creates a commit with your changes
- Updates GitHub issue with progress
- Optionally pushes to remote

**Example:**
```
Just finished the API endpoint → /prd-update-progress
```

---

### 5. `/prd-update-decisions` - Capture Design Decisions

**When to use:** You made architectural or design decisions during development.

**What it does:**
- Records decisions in the PRD decision log
- Updates requirements affected by the decision
- Captures rationale and impact

**Example:**
```
We decided to use Redis instead of PostgreSQL → /prd-update-decisions
```

---

### 6. `/prd-done` - Complete the PRD

**When to use:** All PRD requirements are implemented and tested.

**What it does:**
- Creates a pull request with all changes
- Merges the PR
- Moves the PRD to `prds/done/`
- Closes the GitHub issue
- Updates ROADMAP.md

**Example:**
```
All tasks complete → /prd-done
```

---

### 7. `/prd-close` - Close Without Implementation

**When to use:** The PRD is no longer needed (already implemented elsewhere, out of scope, duplicate).

**What it does:**
- Updates PRD status to "Closed"
- Moves PRD to `prds/done/`
- Closes the GitHub issue with explanation
- Commits directly to main

**Example:**
```
This was already done in another project → /prd-close 20 "Already implemented"
```

**Do NOT use when:** You just finished implementing the PRD (use `/prd-done` instead).

---

### 8. `/prds-get` - List All PRDs

**When to use:** You want to see all open PRDs and their status.

**What it does:**
- Fetches all GitHub issues with the "PRD" label
- Groups by category (Architecture, UX, Developer Experience, etc.)
- Shows priority and readiness

**Example:**
```
What PRDs do we have? → /prds-get
```

---

## Common Workflows

### Starting a New Feature

```
1. /prd-create                    # Document the feature
2. /prd-start [issue-id]          # Begin implementation
3. /prd-next                      # Get first task
4. [Implement the task]
5. /prd-update-progress           # Record completion
6. Repeat steps 3-5 until done
7. /prd-done                      # Complete and merge
```

### Working on an Existing PRD

```
1. /prds-get                      # See available PRDs
2. /prd-start [issue-id]          # Pick one and start
3. /prd-next                      # Get next task
4. [Implement]
5. /prd-update-progress           # Record work
```

### Quick Reference

| Command | When to Use |
|---------|-------------|
| `/prd-create` | New feature idea |
| `/prd-start` | Ready to code |
| `/prd-next` | What to work on next |
| `/prd-update-progress` | After completing work |
| `/prd-update-decisions` | After design decisions |
| `/prd-done` | PRD fully implemented |
| `/prd-close` | PRD no longer needed |
| `/prds-get` | List all PRDs |

## PRD File Locations

- **Active PRDs:** `prds/[issue-id]-[feature-name].md`
- **Completed PRDs:** `prds/done/[issue-id]-[feature-name].md`
- **ROADMAP:** `docs/ROADMAP.md` (if exists)

## Best Practices

1. **Always create a PRD first** - Document before implementing
2. **Use milestones, not tasks** - 5-10 major milestones per PRD
3. **Update progress regularly** - Run `/prd-update-progress` after each work session
4. **Record decisions** - Use `/prd-update-decisions` for design changes
5. **Close properly** - Use `/prd-done` for completed work, `/prd-close` for abandoned PRDs