## Running the Project

```bash
# Interactive TUI (default)
uv run alfred

# With debug logging
uv run alfred --debug info
uv run alfred --debug debug

# Telegram bot mode
uv run alfred --telegram

# Cron job management
uv run alfred cron list
uv run alfred cron add "daily standup" "every day at 9am"
uv run alfred cron remove <job_id>
```

**Entry point:** `src/cli/main.py`
