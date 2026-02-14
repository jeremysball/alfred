# Pi Agent README

*Downloaded from: https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/README.md*

---

Pi is a minimal terminal coding harness. Extend it with TypeScript Extensions, Skills, Prompt Templates, and Themes.

## Built-in Tools

**Default tools (4):** `read`, `write`, `edit`, `bash`

**Available tools (7):** `read`, `write`, `edit`, `bash`, `grep`, `find`, `ls`

```bash
# Use defaults
pi

# Specify tools
pi --tools read,bash,edit,write

# Read-only mode
pi --tools read,grep,find,ls

# No tools (extension tools only)
pi --no-tools
```

## Quick Start

```bash
npm install -g @mariozechner/pi-coding-agent
export ANTHROPIC_API_KEY=sk-ant-...
pi
```

## SDK Usage

```typescript
import { 
  AuthStorage, 
  createAgentSession, 
  ModelRegistry, 
  SessionManager 
} from "@mariozechner/pi-coding-agent";

const { session } = await createAgentSession({
  sessionManager: SessionManager.inMemory(),
  authStorage: new AuthStorage(),
  modelRegistry: new ModelRegistry(authStorage),
});

await session.prompt("What files are in the current directory?");
```

## Context Files

Pi loads `AGENTS.md` (or `CLAUDE.md`) from:
- `~/.pi/agent/AGENTS.md` (global)
- Parent directories (walking up from cwd)
- Current directory

Replace system prompt with `.pi/SYSTEM.md`.

## Customization

### Skills
On-demand capability packages. `/skill:name` to invoke.

```markdown
<!-- ~/.pi/agent/skills/my-skill/SKILL.md -->
# My Skill
Use this skill when the user asks about X.

## Steps
1. Do this
2. Then that
```

### Extensions
TypeScript modules for custom tools, commands, UI.

```typescript
export default function (pi: ExtensionAPI) {
  pi.registerTool({ name: "deploy", ... });
  pi.registerCommand("stats", { ... });
  pi.on("tool_call", async (event, ctx) => { ... });
}
```

### Prompt Templates
Reusable prompts as Markdown. `/name` to expand.

```markdown
<!-- ~/.pi/agent/prompts/review.md -->
Review this code for bugs.
Focus on: {{focus}}
```

## Providers

**Subscriptions:** Anthropic Claude Pro/Max, OpenAI ChatGPT Plus/Pro, GitHub Copilot, Google Gemini CLI

**API keys:** Anthropic, OpenAI, Azure, Google, Bedrock, Mistral, Groq, xAI, OpenRouter, etc.

## Philosophy

- **No MCP.** Build CLI tools with READMEs (skills), or add MCP via extension.
- **No sub-agents.** Spawn pi instances via tmux, or build with extensions.
- **No permission popups.** Use containers, or build your own flow.
- **No plan mode.** Write plans to files, or build with extensions.
- **No built-in to-dos.** Use TODO.md, or build with extensions.

---

See full README at: https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/README.md
