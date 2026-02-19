---
name: desktop-notifications
description: Auto-loaded skill that sends phone notifications via ntfy.sh when tasks complete or user input is required. Loaded automatically on every startup.
---

# Phone Notifications via ntfy.sh

## Overview

Pi sends push notifications to your phone via ntfy.sh when work completes or when your input is needed. This skill runs automatically—no action required.

## When to Notify

**ALWAYS send a notification when:**

1. **Task completes** — Any multi-step task finishes (tests pass, files created, PR merged, etc.)
2. **User input required** — You ask a question, present options, or need a decision

**Do NOT notify for:**
- Simple read operations
- Intermediate steps in ongoing work
- Acknowledgments or confirmations

## How to Notify

Use curl to send to ntfy.sh:

```bash
curl -s -d "<message>" ntfy.sh/pi-agent-prometheus
```

Replace `<message>` with a brief summary (2-5 words max).

### Examples

```bash
# Task done
curl -s -d "Tests passed" ntfy.sh/pi-agent-prometheus

# User input needed
curl -s -d "Need decision" ntfy.sh/pi-agent-prometheus

# PR created
curl -s -d "PR ready" ntfy.sh/pi-agent-prometheus

# Question asked
curl -s -d "Question for you" ntfy.sh/pi-agent-prometheus
```

## Message Guidelines

- **Short**: 2-5 words maximum
- **Action-oriented**: "Tests passed", "PR created", "Ready for review"
- **For input**: "Need input", "Question", "Your turn"
- **No punctuation**: Keep it minimal

## Implementation

After completing a task or asking a question, execute:

```
bash: curl -s -d "<message>" ntfy.sh/pi-agent-prometheus
```

Do this as the final step before awaiting user response.
