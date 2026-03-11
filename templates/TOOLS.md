---
title: "TOOLS.md"
summary: "Local environment and tool configurations"
read_when:
  - Before using any tool
  - When tool behavior seems wrong
---

# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to this setup.

## What Goes Here

Things like:

- LLM provider preferences and API configurations
- Skill-specific settings
- Directory preferences
- Notification preferences
- Anything environment-specific

## Examples

```markdown
### LLM Preferences

- Preferred provider: Kimi
- Fallback provider: Z.AI
- Default model: kimi-k2-5
- Temperature: 0.7 (creative) / 0.3 (precise)

### Skills

- **file_manager:** Prefer `~/workspace` for new projects
- **memory_search:** Return top 10 results by default
- **web_search:** Use Serper, 10 results

### Notifications

- Preferred channel: Telegram
- Quiet hours: 22:00 - 08:00
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes.

---

Add whatever helps you do your job. This is your cheat sheet.
