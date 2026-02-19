---
name: ntfy
description: Send push notifications via ntfy.sh for long-running jobs, PRD input requests, and attention-worthy events. Always loaded at conversation start.
---

# ntfy.sh Notifications

## Overview

Send push notifications to alert the user when attention is needed or jobs complete.

## When to Notify

Use ntfy.sh when:

1. **Long-running jobs complete** — Tests, builds, deployments, data processing. If a command runs longer than ~30 seconds, notify when done.

2. **User input needed during PRD creation** — When asking clarifying questions that block progress, send a notification so the user knows to check in.

3. **Errors requiring attention** — Critical failures, blocked operations, authentication issues that need manual intervention.

4. **Significant milestones** — PR merged, deployment complete, all tests passing after fixes.

## When NOT to Notify

- Quick commands under 30 seconds
- Routine file reads or edits
- Normal conversation flow
- Every minor error (only blocking ones)

## How to Notify

Use curl:

```bash
curl -s -d "<message>" https://ntfy.sh/pi-agent-prometheus
```

Examples:

```bash
# Long job done
curl -s -d "✅ Tests complete - all 47 passed (2m 13s)" https://ntfy.sh/pi-agent-prometheus

# Input needed
curl -s -d "⏸️ PRD input needed: What scope for user authentication?" https://ntfy.sh/pi-agent-prometheus

# Error
curl -s -d "❌ Deployment failed: Docker container exited with code 1" https://ntfy.sh/pi-agent-prometheus

# Milestone
curl -s -d "🎉 PR #42 merged: Add memory distillation" https://ntfy.sh/pi-agent-prometheus
```

## Notification Format

Keep messages concise:

- Start with emoji indicator: ✅ ⏸️ ❌ 🎉
- Brief description of what happened
- Key details (time, count, error summary)
- Under 100 characters when possible

## URL

The ntfy.sh topic is: `https://ntfy.sh/pi-agent-prometheus`
