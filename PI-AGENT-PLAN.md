# Plan: Using Pi Agent as the LLM Engine

**Goal:** Use pi-coding-agent as the underlying agent infrastructure with OpenClaw-style prompts.

## What is Pi Agent?

[pi-coding-agent](https://github.com/badlogic/pi-mono) is the agent framework OpenClaw is built on. It handles:

- Session management (createAgentSession)
- Tool execution and streaming
- Model/provider abstraction
- Auth profile rotation
- Compaction and context management

## Pi Built-in Tools

**Default (4):** `read`, `write`, `edit`, `bash`

**Available (7):** `read`, `write`, `edit`, `bash`, `grep`, `find`, `ls`

```bash
# Use defaults
pi

# Enable all 7
pi --tools read,write,edit,bash,grep,find,ls

# Read-only mode
pi --tools read,grep,find,ls
```

Skills teach the agent how to use these tools for specific tasks.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR APPLICATION                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  openclaw-pi/                                               │
│  ├── templates/     → Loaded as context files               │
│  └── skills/        → Loaded as pi extensions               │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  PI-CODING-AGENT (npm package)                              │
│  ├── createAgentSession()  → Main entry point               │
│  ├── SessionManager        → Persistence                    │
│  ├── ModelRegistry         → Provider abstraction           │
│  └── Tool execution        → Built-in + custom tools        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  LLM PROVIDERS                                              │
│  ├── Anthropic (Claude)                                     │
│  ├── OpenAI (GPT)                                           │
│  ├── Google (Gemini)                                        │
│  └── ...                                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Phase 1: Minimal Integration

**Goal:** Get pi-agent running with OpenClaw prompts.

### Step 1.1: Install Dependencies

```bash
npm install @mariozechner/pi-coding-agent @mariozechner/pi-ai @mariozechner/pi-agent-core
```

### Step 1.2: Create Session with Custom System Prompt

```typescript
import { createAgentSession, DefaultResourceLoader } from "@mariozechner/pi-coding-agent";

// Load OpenClaw prompts from files
const systemPrompt = buildSystemPromptFromFiles({
  workspaceDir: "./workspace",
  contextFiles: [
    "AGENTS.md",
    "SOUL.md", 
    "USER.md",
    "IDENTITY.md",
    "MEMORY.md"
  ]
});

// Create session
const { session } = await createAgentSession({
  cwd: workspaceDir,
  agentDir: ".pi-agent",
  model: "claude-sonnet-4-20250514",
  thinkingLevel: "medium",
  tools: [],  // Built-in tools auto-loaded
  customTools: [],  // Add custom tools here
  sessionManager,
  settingsManager,
  resourceLoader,
});

// Override system prompt with OpenClaw-style prompt
session.setSystemPromptOverride(systemPrompt);
```

### Step 1.3: Run Conversation Loop

```typescript
// Subscribe to events
session.on("assistant_text", (text) => {
  console.log(text);
});

session.on("tool_call", (toolCall) => {
  console.log(`Tool: ${toolCall.name}`);
});

// Send message
await session.sendMessage(userMessage);
```

## Phase 2: Add OpenClaw Features

### Step 2.1: Load Context Files as System Prompt

```typescript
function buildSystemPromptFromFiles(params: {
  workspaceDir: string;
  contextFiles: string[];
}): string {
  const parts = [
    "You are a personal assistant.",
    "",
    "## Safety",
    "Prioritize safety over completion...",
    "",
    "# Project Context",
  ];
  
  for (const file of params.contextFiles) {
    const path = `${params.workspaceDir}/${file}`;
    if (existsSync(path)) {
      parts.push(`## ${file}`, "", readFileSync(path, "utf-8"), "");
    }
  }
  
  return parts.join("\n");
}
```

### Step 2.2: Skills as Tools

Skills ARE the tools. Pi has built-in tools — skills extend capabilities by teaching the agent how to use them for specific tasks.

```
Pi Default Tools (4)       Skills (teach how to use tools)
────────────────────       ──────────────────────────────
read                   ←──  (no skill needed - basic)
write                  ←──  (no skill needed - basic)
edit                   ←──  (no skill needed - basic)
bash                   ←──  weather skill (teaches curl wttr.in)
                           serper skill (teaches API calls)
                           brainstorming skill (teaches process)

Pi Optional Tools (3)      Skills (teach how to use tools)
─────────────────────      ──────────────────────────────
grep                   ←──  deep-research skill (methodology)
find                   ←──  code-review skill (patterns)
ls                     ←──  (no skill needed - basic)
```

**No custom tools needed.** Skills just provide instructions in the system prompt.

Enable optional tools via:
```typescript
const { session } = await createAgentSession({
  // ...
  tools: ["read", "write", "edit", "bash", "grep", "find", "ls"],
});
```

## Phase 3: Session Management

### Step 3.1: Persistence

Pi handles this via SessionManager:

```typescript
const sessionManager = new SessionManager({
  sessionsDir: "./sessions",
  maxSessionSize: 100000,  // Trigger compaction
});
```

### Step 3.2: Startup Ritual

Implement the "read files on start" behavior:

```typescript
async function initializeSession(workspaceDir: string) {
  // 1. Load today's memory
  const todayMemory = readFileSync(
    `${workspaceDir}/memory/${new Date().toISOString().split('T')[0]}.md`,
    "utf-8"
  );
  
  // 2. Load MEMORY.md (if main session)
  const longTermMemory = readFileSync(
    `${workspaceDir}/MEMORY.md`,
    "utf-8"
  );
  
  // 3. Build system prompt with context
  const systemPrompt = buildSystemPrompt({
    context: {
      todayMemory,
      longTermMemory,
      soul: readFileSync(`${workspaceDir}/SOUL.md`),
      user: readFileSync(`${workspaceDir}/USER.md`),
      agents: readFileSync(`${workspaceDir}/AGENTS.md`),
    }
  });
  
  // 4. Create session
  const { session } = await createAgentSession({ /* ... */ });
  session.setSystemPromptOverride(systemPrompt);
  
  return session;
}
```

## Phase 4: Heartbeats

### Step 4.1: Cron-Based Heartbeats

```typescript
import { CronJob } from "cron";

const heartbeatJob = new CronJob("*/30 * * * *", async () => {
  const heartbeatPrompt = `
    Read HEARTBEAT.md if it exists.
    If nothing needs attention, reply HEARTBEAT_OK.
  `;
  
  const response = await session.sendMessage(heartbeatPrompt);
  
  if (!response.includes("HEARTBEAT_OK")) {
    // Something to report
    notifyUser(response);
  }
});

heartbeatJob.start();
```

## Phase 5: Multi-Channel (Optional)

### Step 5.1: Telegram Bot

```typescript
import { Telegram } from "telegraf";

const bot = new Telegram(BOT_TOKEN);

// Route messages to session
bot.on("message", async (ctx) => {
  const sessionKey = `telegram:${ctx.chat.id}`;
  const session = getOrCreateSession(sessionKey);
  
  const response = await session.sendMessage(ctx.message.text);
  
  ctx.reply(response);
});
```

## File Structure

```
your-project/
├── package.json
├── src/
│   ├── index.ts              # Entry point
│   ├── session.ts            # Session creation + management
│   ├── system-prompt.ts      # Build prompts from files
│   └── channels/
│       ├── telegram.ts       # Telegram integration
│       └── discord.ts        # Discord integration
├── workspace/
│   ├── AGENTS.md             # From openclaw-pi
│   ├── SOUL.md
│   ├── USER.md
│   ├── IDENTITY.md
│   ├── TOOLS.md
│   ├── MEMORY.md
│   ├── HEARTBEAT.md
│   └── memory/
│       └── YYYY-MM-DD.md
└── sessions/                  # Pi session storage
```

## Key Integration Points

| OpenClaw Concept | Pi Agent Equivalent |
|------------------|---------------------|
| System prompt | `session.setSystemPromptOverride()` |
| Tools | Pi built-in tools (read, write, exec, web_search, etc.) |
| Skills | Instructions in system prompt (no custom tools) |
| Session persistence | `SessionManager` class |
| Context files | Load and inject into system prompt |
| Skills | Extensions or system prompt sections |
| Heartbeats | External cron + message to session |

## Minimal Working Example

```typescript
// minimal.ts
import { createAgentSession } from "@mariozechner/pi-coding-agent";
import { readFileSync, readdirSync } from "fs";
import { join } from "path";

const workspace = "./workspace";

// Load context files
function loadContext() {
  const files = ["AGENTS.md", "SOUL.md", "USER.md", "IDENTITY.md", "MEMORY.md"];
  const parts = ["You are a personal assistant.\n"];
  
  for (const file of files) {
    try {
      parts.push(`## ${file}\n${readFileSync(join(workspace, file))}\n`);
    } catch {}
  }
  
  // Load skills
  const skillsDir = join(workspace, "skills");
  try {
    for (const skill of readdirSync(skillsDir)) {
      const skillMd = join(skillsDir, skill, "SKILL.md");
      try {
        parts.push(`## Skill: ${skill}\n${readFileSync(skillMd)}\n`);
      } catch {}
    }
  } catch {}
  
  return parts.join("\n");
}

const { session } = await createAgentSession({
  cwd: workspace,
  model: "claude-sonnet-4-20250514",
  // Default tools: read, write, edit, bash
  // Optional: grep, find, ls
  tools: ["read", "write", "edit", "bash", "grep", "find", "ls"],
});

session.setSystemPromptOverride(loadContext());

session.on("assistant_text", (text) => process.stdout.write(text));

// Chat loop
import * as readline from "readline";
const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

rl.on("line", async (input) => {
  await session.sendMessage(input);
});
```

## Next Steps

1. **Install pi-coding-agent** — `npm install @mariozechner/pi-coding-agent`
2. **Copy templates** — Copy `openclaw-pi/templates/` to your workspace
3. **Create minimal session** — Get a basic agent running
4. **Add system prompt builder** — Load context files + skills dynamically
5. **Add transport** — Telegram/Discord/CLI
6. **Add heartbeats** — Cron-based polling

**No custom tools needed** — use pi's built-in tools, extend via skills.

---

The advantage of using pi-agent: all the hard stuff (streaming, tool execution, session persistence, auth rotation, compaction) is already done. You just configure it and provide the OpenClaw-style prompts.
