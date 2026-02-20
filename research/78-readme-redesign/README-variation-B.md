# 🧠 Alfred

> *"I swear we talked about this yesterday..."* — Every LLM ever

<p align="center">
  <img src="https://raw.githubusercontent.com/jeremysball/alfred/main/assets/alfred-hero.png" alt="Alfred - Your AI's Long-Term Memory" width="800">
</p>

<p align="center">
  <strong>The memory layer your AI assistant forgot it needed</strong>
</p>

<p align="center">
  <a href="https://github.com/jeremysball/alfred/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/jeremysball/alfred/ci.yml?branch=main&label=tests&style=for-the-badge&color=black" alt="Tests">
  </a>
  <a href="https://github.com/jeremysball/alfred/releases">
    <img src="https://img.shields.io/github/v/release/jeremysball/alfred?style=for-the-badge&color=black" alt="Version">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-black.svg?style=for-the-badge" alt="License">
  </a>
</p>

---

## Meet Alfred 🎩

**Alfred** is your AI's loyal butler. He remembers every conversation, recalls every detail, and never judges you for asking the same question three times.

While your LLM has the memory of a goldfish, Alfred keeps perfect notes. He stores your chats, indexes them with magic (okay, embeddings), and whispers relevant context to your AI so it actually knows what you're talking about.

**All local. All yours. No cloud nonsense.** ☁️❌

---

## ✨ The Magic

```
You: "What did we decide about the database?"

Alfred: *rummages through memories* 🔍

Alfred: "Ah yes, yesterday at 3pm you said: 
        'Let's go with PostgreSQL because Mongo is 
         too chaotic for this project.'"

You: "Right! Thanks Alfred."

Alfred: *tips hat* 🎩
```

**Behind the scenes:**
- 💾 Every chat saved to `data/memories.jsonl`
- 🔮 Embeddings make search instant
- 🧠 Context auto-injected into prompts
- 🏠 Everything stays on your machine

---

## 🚀 Quick Start

```bash
# Bring Alfred home
pip install alfred-memory

# Teach him your preferences
alfred init

# Start chatting
alfred chat
```

**Or use Telegram:**

```bash
# Set up the bot
alfred telegram setup

# Launch
alfred telegram start
```

Then message [@AlfredMemoryBot](https://t.me/AlfredMemoryBot) 📱

---

## 🎪 Features

| Feature | What It Does | Coolness |
|---------|--------------|----------|
| 💾 **Persistent Memory** | Stores chats in JSONL files you own | No vendor lock-in! |
| 🔮 **Semantic Search** | Finds relevant context instantly | Like Google for your brain |
| 🤖 **Telegram Bot** | Chat via Telegram | Pocket-sized Alfred |
| 💻 **CLI Interface** | Terminal chat with streaming | For the keyboard warriors |
| 📁 **File-Based Config** | `SOUL.md`, `AGENTS.md`, `TOOLS.md` | Human-readable FTW |
| 📂 **Sessions** | Organize by project/topic | Stay organized, finally |
| 🛠️ **Memory Tools** | Search/update programmatically | API for your memories |
| 🔒 **Privacy First** | 100% local, zero cloud | Your data stays yours |

---

## 🎭 Choose Your Interface

| Feature | Telegram 🤖 | CLI 💻 | Library 📦 |
|---------|-------------|--------|------------|
| Chat | ✅ | ✅ | ❌ |
| Search Memories | ✅ | ✅ | ✅ |
| Manage Sessions | ✅ | ✅ | ✅ |
| Execute Tools | ✅ | ✅ | ✅ |
| Stream Responses | ✅ | ✅ | ✅ |

**Telegram**: Chat anywhere, anytime. Like texting a very smart friend.

**CLI**: For the terminal dwellers. Fast, efficient, no mouse required.

**Library**: Build Alfred into your own apps. He plays well with others.

---

## 🎬 See It in Action

```python
from alfred import Alfred

# Wake up Alfred
alfred = Alfred()

# Ask about past conversations
response = await alfred.chat(
    "What did we discuss about my database schema?"
)
# Alfred searches memory and responds with context

# Search memories directly
memories = await alfred.search("database schema", limit=5)
for memory in memories:
    print(f"📝 {memory['timestamp']}: {memory['content']}")
```

---

## 🔍 Where Does Alfred Keep Everything?

**Right here on your machine:**

- 💬 `data/memories.jsonl` — Every word you've shared
- 📋 `data/session_summaries.jsonl` — Conversation TL;DRs
- 🎭 `SOUL.md` — Alfred's personality settings
- 🛠️ `AGENTS.md` — Behavior rules
- ⚙️ `TOOLS.md` — Available tools

**No cloud. No tracking. No "we value your privacy" while selling your data.**

Just files you can read, edit, and delete. Like it should be.

---

## 📚 Documentation

- [Getting Started](docs/getting-started.md) — Your first conversation
- [Configuration](docs/configuration.md) — Teach Alfred your preferences
- [Telegram Setup](docs/telegram.md) — Pocket Alfred activation
- [API Reference](docs/api.md) — Build with Alfred
- [Architecture](docs/architecture.md) — How the magic works

---

## 🏗️ Built With Love Using

- [OpenAI](https://openai.com/) — Embeddings and smarts
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) — Telegram magic
- [Pydantic](https://docs.pydantic.dev/) — Data validation that doesn't hurt
- [aiofiles](https://github.com/Tinche/aiofiles) — Async file ops

---

## 💬 Let's Chat

- [GitHub Discussions](https://github.com/jeremysball/alfred/discussions) — Ideas, questions, show-and-tell
- [GitHub Issues](https://github.com/jeremysball/alfred/issues) — Bugs, feature requests
- [Discord](https://discord.gg/alfred) — Real-time chatter

---

## 🤝 Contributing

Found a bug? Have an idea? Want to add a feature?

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for the how-to.

---

<p align="center">
  <img src="https://raw.githubusercontent.com/jeremysball/alfred/main/assets/alfred-icon.png" alt="Alfred" width="64">
</p>

<p align="center">
  <strong>Made with 🧠, 💾, and a dash of ✨</strong>
</p>

<p align="center">
  <em>"Alfred remembers so you don't have to"</em>
</p>

<p align="center">
  🎩 🧠 💾
</p>
