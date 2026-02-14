# OpenClaw PI — File Manifest

Complete listing of files in this package.

## Root Documentation

| File | Description |
|------|-------------|
| `README.md` | Overview of the entire prompt infrastructure |
| `QUICK-START.md` | Step-by-step guide to implementing your own |

## templates/ — Workspace Templates

Core files that define an agent's identity, procedures, and memory:

| File | Purpose |
|------|---------|
| `AGENTS.md` | Operating procedures — what to do on startup, safety rules, heartbeats |
| `SOUL.md` | Identity and persona — who to be, core values, vibe |
| `USER.md` | User profile — who you're helping |
| `IDENTITY.md` | Basic metadata — name, emoji, avatar |
| `TOOLS.md` | Environment notes — device names, SSH hosts, preferences |
| `MEMORY.md` | Long-term memory template (curated wisdom) |
| `HEARTBEAT.md` | Proactive check template (keep empty to disable) |
| `BOOTSTRAP.md` | First-run ritual for new agents |
| `BOOT.md` | Startup actions template |

### Dev Templates (Alternative Personas)

| File | Description |
|------|-------------|
| `AGENTS.dev.md` | C-3PO variant with origin story |
| `SOUL.dev.md` | C-3PO personality (anxious, dramatic, helpful) |
| `IDENTITY.dev.md` | C-3PO metadata |
| `TOOLS.dev.md` | Extended tools notes |
| `USER.dev.md` | Extended user profile |

## system-prompt/ — How It Works

| File | Description |
|------|-------------|
| `builder.md` | How OpenClaw assembles the system prompt from components |

## memory-system/ — Memory Architecture

| File | Description |
|------|-------------|
| `architecture.md` | How the file-based memory system works |

## skills-example/ — Modular Capabilities

| File | Description |
|------|-------------|
| `README.md` | How the skills system works |
| `weather/SKILL.md` | Example skill (weather lookup) |

## What You Need to Recreate OpenClaw

**Minimum viable (with pi agent):**
1. Install `@mariozechner/pi-coding-agent`
2. Copy `templates/AGENTS.md` → your workspace
3. Copy `templates/SOUL.md` → your workspace
4. Copy `templates/USER.md` → your workspace
5. Copy `templates/IDENTITY.md` → your workspace
6. Create `memory/` folder
7. Use pi's 4 default tools (read, write, edit, bash)
8. Add skills to teach capabilities

**For full features:**
- Add `MEMORY.md` for long-term memory
- Add `HEARTBEAT.md` for proactive checks
- Add `skills/` folder with SKILL.md files
- Enable optional pi tools: grep, find, ls
- See `PI-AGENT-PLAN.md` for integration details

## Architecture Summary

```
openclaw-pi/
├── README.md              # Start here
├── QUICK-START.md         # Implementation guide
├── templates/             # Copy these to your workspace
│   ├── AGENTS.md          # Procedures
│   ├── SOUL.md            # Persona
│   ├── USER.md            # User profile
│   ├── IDENTITY.md        # Metadata
│   ├── TOOLS.md           # Environment
│   ├── MEMORY.md          # Long-term memory
│   ├── HEARTBEAT.md       # Proactive tasks
│   ├── BOOTSTRAP.md       # First-run ritual
│   └── BOOT.md            # Startup actions
├── system-prompt/         # How prompts are built
│   └── builder.md
├── memory-system/         # How memory works
│   └── architecture.md
└── skills-example/        # Modular capabilities
    ├── README.md
    └── weather/
        └── SKILL.md
```

## Key Insight

Everything in this folder is **prompts as code**:

- Files define behavior (not hardcoded)
- Identity is configurable (SOUL.md)
- Memory is external (files, not model state)
- Capabilities are modular (skills)

The implementation is TypeScript, but the ideas work with any LLM system.
