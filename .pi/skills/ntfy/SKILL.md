---
name: ntfy
description: Send push notifications via ntfy.sh for long-running jobs, PRD input requests, and attention-worthy events. Always loaded at conversation start.
---

# 📱 ntfy Push Notifications

Send instant push notifications to your phone or desktop via ntfy.sh. Perfect for:
- Long-running tasks completing
- User input required
- Errors or alerts needing attention
- Workflow milestones

## 🚀 Quick Start

```bash
# Simple message
curl -s -d "Task complete" ntfy.sh/pi-agent-prometheus

# With title and priority
curl -s \
  -H "Title: Deployment Complete" \
  -H "Priority: high" \
  -d "Production deploy successful" \
  ntfy.sh/pi-agent-prometheus

# With tags and actions
curl -s \
  -H "Title: PR Ready for Review" \
  -H "Tags: github,pull-request" \
  -H "Priority: default" \
  -d "Please review PR #123" \
  ntfy.sh/pi-agent-prometheus
```

## 📝 Usage in Code

### Basic Notification
```python
import subprocess

def notify(message: str) -> None:
    """Send a push notification."""
    subprocess.run(
        ["curl", "-s", "-d", message, "ntfy.sh/pi-agent-prometheus"],
        capture_output=True
    )

# Usage
notify("Tests passed")
notify("Need input: Which approach do you prefer?")
```

### With Priority and Tags
```python
import subprocess

def notify_high(message: str, title: str = "Alert") -> None:
    """Send high-priority notification."""
    subprocess.run([
        "curl", "-s",
        "-H", f"Title: {title}",
        "-H", "Priority: high",
        "-d", message,
        "ntfy.sh/pi-agent-prometheus"
    ], capture_output=True)

# Usage
notify_high("Build failed", "CI/CD Alert")
```

## 🎯 Notification Guidelines

| Scenario | Priority | Example |
|----------|----------|---------|
| Task completes | `default` | `"Branches cleaned"` |
| User input required | `high` | `"Need input: Which design?"` |
| Error/alert | `high` | `"Tests failed"` |
| Long job done | `default` | `"PR created and merged"` |

### When to Notify

**Always notify:**
- Multi-step tasks finish
- Tests pass/fail
- PRs created/merged
- User decision needed

**Don't notify:**
- Simple reads
- Intermediate steps
- Acknowledgments

## 🔧 Advanced Options

| Header | Values | Description |
|--------|--------|-------------|
| `Title` | Any text | Notification title |
| `Priority` | `min`, `low`, `default`, `high`, `urgent` | Notification priority |
| `Tags` | Comma-separated | Emojis/tags (e.g., `warning,github`) |
| `Click` | URL | Open URL on click |

### Example with All Options
```bash
curl -s \
  -H "Title: Deploy Failed" \
  -H "Priority: urgent" \
  -H "Tags: warning,x" \
  -H "Click: https://github.com/org/repo/actions" \
  -d "Build #456 failed - check logs" \
  ntfy.sh/pi-agent-prometheus
```

## 🔗 Resources

- **Topic**: `pi-agent-prometheus` (shared)
- **Docs**: https://docs.ntfy.sh
- **Web**: https://ntfy.sh/app

## 📋 One-Liners

```bash
# Success
curl -s -d "✅ Task done" ntfy.sh/pi-agent-prometheus

# Failure
curl -s -H "Priority: high" -d "❌ Task failed" ntfy.sh/pi-agent-prometheus

# Question
curl -s -H "Priority: high" -d "❓ Input needed" ntfy.sh/pi-agent-prometheus
```