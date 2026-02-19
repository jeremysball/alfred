# Alfred

![Memory Moth Banner](docs/assets/memory-moth-banner.png)

**The assistant that remembers what you forget.**

Alfred pays attention. Not just to what you say, but to how you work. The patterns you miss. The details you meant to follow up on. The thing you were worried about three weeks ago that suddenly matters again.

He runs on your machine. Your data never leaves. And he gets smarter the more you use him.

---

## The Difference

Other assistants start fresh every conversation. Alfred builds a relationship with you. He notices things.

```
You: Review this function?

Alfred: Looks solid. One pattern I'm noticing—you tend to skip 
error handling when you're in flow state. Last three refactors 
you did were all adding try/catch blocks after the fact.

This one has the same shape. Want me to suggest where the 
edge cases might bite you?
```

That's not search. That's understanding.

Or this:

```
You: I'm stuck on this API design.

Alfred: You're circling the same structure you debated for the 
webhook system last month. You went with flat over nested then, 
but said "might regret it for complex payloads."

Want me to pull up that conversation? You sketched an alternative 
that might work here.
```

Weeks later. Different project. He remembers not just what you did, but what you were thinking.

---

## What Makes Alfred Different

### He Actually Pays Attention

Every conversation is stored with meaning, not just text. Alfred searches by concept. Ask "what was that thing I was worried about?" and he'll find it.

### Two Kinds of Memory

- **Message-level**: Specific facts, commands, decisions
- **Session-level**: Narrative arcs, project phases, how your thinking evolved

Search either. Alfred picks the right one based on what you're asking.

### No Slash Commands

Just talk. "Find that thing about Postgres" works. So does "what did we decide?" and "remind me why I chose this approach." Alfred figures out what you mean.

### He Uses Tools

Read your files. Run your tests. Check your git history. Alfred doesn't just remember—he investigates.

```
You: Did I fix that bug?

Alfred: [checking git log]

You committed a fix yesterday (a3f7d2e) but the test you added 
is failing on main. Want me to run it and see what's up?
```

### Scheduled Actions

Alfred doesn't just respond—he acts on his own. Schedule Python code that runs with access to his memory and tools.

```
You: Every morning, check my calendar and remind me of any 
     deadlines mentioned in my notes.

Alfred: [creates scheduled job]

I'll run this each morning with access to your memories.
```

Jobs run with **configurable context**. You decide what they can access:
- Full context: Search memories, save insights, use any tool
- Sandboxed: Memory operations only, no file system or network
- System jobs: Pre-vetted code that runs automatically
- User jobs: Require approval before execution

You control the attack surface for every job.

### Your Data, Your Machine

JSONL files. Markdown templates. Human-readable, portable, yours. No cloud lock-in, no proprietary formats. If you want to leave, you take everything with you.

---

## Why Alfred Works This Way

Three principles shape every decision:

**1. Model-Driven Intelligence**

When Alfred decides what to remember, how to respond, or which tool to use—the LLM decides. We prompt instead of programming. This makes Alfred flexible and genuinely intelligent, not a rigid workflow engine.

**2. Zero-Command Interface**

Natural language is the interface. No `/remember` or `/search` to memorize. Just talk to him like a person who happens to have perfect memory.

**3. Fail Fast**

Errors surface immediately. Silent failures hide bugs. If something's wrong, you'll know. If Alfred's uncertain, he'll say so.

---

## Getting Started

```bash
pip install alfred-ai

export KIMI_API_KEY=your_key
export OPENAI_API_KEY=your_key

alfred
```

Then just start talking.

**Prefer Telegram?**

```bash
export TELEGRAM_BOT_TOKEN=your_token
alfred --telegram
```

Alfred works in both places with the same memory, same personality, same understanding.

---

## How It Works

```
┌─────────┐     message      ┌─────────┐
│   You   │ ───────────────> │ Alfred  │
└─────────┘                  └────┬────┘
     ^                            │
     │                            │ embed & store
     │                            ▼
     │                     ┌─────────────┐
     │                     │Dual Memory  │
     │                     │  System     │
     │                     │             │
     │                     │• Messages   │
     │                     │• Sessions   │
     │                     └──────┬──────┘
     │                            │
     │                            │ semantic search
     │                            │
     │     ┌─────────┐     ┌──────┴──────┐
     └──── │ Response│ <── │   Context   │
           │         │     │   Assembly  │
           └─────────┘     └─────────────┘
```

Every message gets embedded. Every session gets summarized. When you talk, Alfred searches by meaning, pulls relevant context, and prompts the LLM with your history, your preferences, and your current situation.

Over time, he learns what matters. Which details are important. How you think.

---

## For Developers

Alfred is built for people who care about:

- **Simplicity**: File-based storage, clear abstractions, minimal magic
- **Observability**: You can read every memory, every prompt, every decision
- **Extensibility**: Add tools by writing Python classes. The LLM learns them automatically.
- **Reliability**: Idempotent operations, clear error messages, no silent failures

```python
# Adding a tool is this simple
from alfred.tools import Tool

class DeployTool(Tool):
    name = "deploy"
    description = "Deploy the application"
    
    async def run(self, environment: str) -> str:
        # Your logic here
        return f"Deployed to {environment}"
```

The LLM sees the schema, understands the purpose, and uses it when relevant. No registration code, no routing logic.

---

## What's Next

Alfred is young but useful. We're building:

- **Learning system**: Automatic updates to your preference profile
- **Rich CLI output**: Streaming markdown rendering
- **Advanced session features**: On-demand summarization, context management
- **Extended tool library**: More built-in tools for common workflows

See [ROADMAP.md](docs/ROADMAP.md) for the full plan.

---

## Contributing

If Alfred's approach resonates:

- Improve how he spots patterns in your work
- Make the learning system smarter about what matters
- Add tools for workflows you care about
- Write tests, fix bugs, improve docs

Check [AGENTS.md](AGENTS.md) for how we work. Issues and PRs welcome.

---

## License

MIT

---

**Alfred doesn't just remember. He understands.**

The more you use him, the more useful he becomes. Not because of complex configuration or fine-tuning, but because he's actually paying attention.

Start a conversation. See what he notices.
