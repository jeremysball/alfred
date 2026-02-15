# User Guide

## Getting Started

### Installation

```bash
# Clone repository
git clone <repository-url>
cd openclaw-pi

# Install Pi coding agent
npm install -g @mariozechner/pi-coding-agent

# Install Python dependencies
uv pip install -e ".[dev]"

# Copy templates to workspace
cp -r templates/* workspace/
```

### Configuration

Create `.env` file:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
LLM_API_KEY=your_llm_api_key
OPENAI_API_KEY=your_openai_key_for_embeddings  # Optional

# Optional settings
LOG_LEVEL=INFO
LLM_PROVIDER=zai
LLM_MODEL=glm-4-flash
```

### Running the Bot

```bash
# Run with CLI
openclaw-pi

# Or as Python module
python -m openclaw_pi
```

## Using the Bot

### Starting a Conversation

1. Start chat with your bot on Telegram
2. Send `/start` to see available commands
3. Start chatting - each thread gets its own context

### Commands

| Command | Description |
|---------|-------------|
| `/start` | Show welcome message and commands |
| `/status` | Show active processes and stored threads |
| `/threads` | List all conversation threads |
| `/kill <id>` | Stop a thread's AI process |
| `/cleanup` | Stop all AI processes |
| `/subagent <task>` | Run task in background |

### Multi-Thread Conversations

- **Direct messages:** Each DM is a separate thread
- **Groups:** Each thread in a group is separate (`<chat_id>_<thread_id>`)
- **Context isolation:** Threads don't share memory

### Background Tasks

Use `/subagent` for long-running tasks:

```
/subagent analyze the codebase and suggest improvements
```

The bot will:
1. Acknowledge the task
2. Process in background
3. Post results when complete

## Workspace Files

### Customizing Your Agent

Edit files in `workspace/`:

| File | Purpose | When to Edit |
|------|---------|--------------|
| `AGENTS.md` | Agent behavior rules | Change how agent responds |
| `SOUL.md` | Personality definition | Change tone/voice |
| `USER.md` | Your preferences | Add personal context |
| `MEMORY.md` | Long-term memory | Curated important info |
| `TOOLS.md` | Tool configuration | Add API keys, settings |

### Memory System

Daily notes are automatically created in `memory/YYYY-MM-DD.md`.

To add a note:
```bash
echo "- Remembered this important thing" >> workspace/memory/2026-02-15.md
```

The agent reads today's and yesterday's notes on startup.

## Troubleshooting

### Bot Not Responding

1. Check bot is running: `ps aux | grep openclaw-pi`
2. Check logs: `tail -f logs/openclaw-pi.log`
3. Verify Telegram token: Test with curl

### Timeout Errors

If you see "⏱️ Timeout":
- LLM API may be slow
- Check `PI_TIMEOUT` in `.env` (default 300s)
- Try again - transient issue

### Empty Responses

If bot returns empty messages:
- Check `LLM_API_KEY` is set correctly
- Verify provider (zai, moonshot, etc.)
- Check `LOG_LEVEL=DEBUG` for details

### Pi Not Found

If error says "Pi executable not found":
```bash
# Install globally
npm install -g @mariozechner/pi-coding-agent

# Or set path in .env
PI_PATH=/path/to/pi
```

## Advanced Usage

### Semantic Memory Search

Enable OpenAI embeddings for semantic search over memories:

1. Set `OPENAI_API_KEY` in `.env`
2. The system will embed memories automatically
3. Search uses cosine similarity

### Custom Skills

Add skills to `workspace/skills/`:

```
workspace/skills/my-skill/
└── SKILL.md
```

Skills are loaded on startup and available to the agent.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | - | **Required.** Bot token |
| `LLM_API_KEY` | - | **Required.** LLM API key |
| `OPENAI_API_KEY` | - | Optional, for embeddings |
| `WORKSPACE_DIR` | ./workspace | User context directory |
| `THREADS_DIR` | ./threads | Thread storage |
| `LOG_LEVEL` | INFO | Logging level |
| `PI_TIMEOUT` | 300 | Subprocess timeout |
| `LLM_PROVIDER` | zai | LLM provider |
| `LLM_MODEL` | - | Model name |

## Tips

1. **Use threads** - Create new threads for different topics
2. **Clean up** - Use `/cleanup` if things get slow
3. **Check MEMORY.md** - Review what agent remembers
4. **Daily notes** - Let agent record important context
5. **Be specific** - Clear prompts get better responses
