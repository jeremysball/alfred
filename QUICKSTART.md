# OpenClaw Pi - Bash-Only Agent Runner

Run OpenClaw-style agents using pi-coding-agent, no session system required.

## Quick Start

```bash
# 1. Install pi-coding-agent
./setup.sh

# 2. Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# 3. Run interactive agent
./run.sh

# Or one-shot query
./ask.sh "What files are in this project?"
```

## Scripts

| Script | Purpose |
|--------|---------|
| `setup.sh` | Install pi, set up workspace |
| `build-prompt.sh` | Assemble `.pi/SYSTEM.md` from context files |
| `run.sh` | Build prompt + start interactive pi |
| `ask.sh` | One-shot: send message, get response |

## Directory Structure

```
openclaw-pi/
├── workspace/           # Your context files
│   ├── AGENTS.md       # Agent behavior rules
│   ├── SOUL.md         # Persona/identity
│   ├── USER.md         # Who you're helping
│   ├── MEMORY.md       # Long-term memory
│   ├── memory/         # Daily logs (YYYY-MM-DD.md)
│   └── skills/         # Optional skills (SKILL.md each)
├── .pi/
│   └── SYSTEM.md       # Generated system prompt
├── templates/          # Starter templates
└── *.sh                # Scripts
```

## How It Works

1. `build-prompt.sh` reads all context files from `workspace/`
2. Assembles them into `.pi/SYSTEM.md`
3. Pi automatically loads `.pi/SYSTEM.md` when run from workspace

No TypeScript, no session persistence layer. Just bash + pi.

## Customizing

Edit the files in `workspace/`:
- **AGENTS.md** - Change how the agent behaves
- **SOUL.md** - Change personality/tone
- **USER.md** - Add context about yourself
- **MEMORY.md** - Add long-term memories

Then rebuild:
```bash
./build-prompt.sh workspace
```

## Calling from Another Pi Instance

If you want to call this from another pi instance:

```bash
# One-shot query
./ask.sh "Review the code" /path/to/workspace

# Or just build the prompt and call pi yourself
./build-prompt.sh /path/to/workspace
cd /path/to/workspace
pi
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes* | Anthropic API key |
| `OPENAI_API_KEY` | Yes* | OpenAI API key (if using OpenAI) |

*At least one API key required.
