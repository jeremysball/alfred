# System Prompt Builder (Simplified)

How OpenClaw assembles the final system prompt sent to the LLM.

## The Building Blocks

The system prompt is constructed dynamically from multiple sources:

```javascript
function buildAgentSystemPrompt(params) {
  // 1. Core identity
  lines = [
    "You are a personal assistant running inside OpenClaw.",
    "",
  ];
  
  // 2. Tooling section (what tools are available)
  lines.push("## Tooling", ...buildToolSection(params));
  
  // 3. Safety section (always included)
  lines.push("## Safety", ...safetyLines);
  
  // 4. Skills section (if skills available)
  if (params.skillsPrompt) {
    lines.push("## Skills (mandatory)", params.skillsPrompt);
  }
  
  // 5. Memory recall instructions
  if (hasMemoryTools) {
    lines.push("## Memory Recall", 
      "Before answering anything about prior work, decisions, dates, people...",
      "run memory_search on MEMORY.md + memory/*.md..."
    );
  }
  
  // 6. Workspace info
  lines.push("## Workspace", 
    `Your working directory is: ${params.workspaceDir}`
  );
  
  // 7. Project context (INJECTED FILES)
  // This is where AGENTS.md, SOUL.md, USER.md, etc. get included
  lines.push("# Project Context");
  for (const file of params.contextFiles) {
    lines.push(`## ${file.path}`, "", file.content, "");
  }
  
  // 8. Messaging rules
  lines.push("## Messaging", ...messagingRules);
  
  // 9. Heartbeats
  lines.push("## Heartbeats", heartbeatPrompt);
  
  // 10. Runtime info
  lines.push("## Runtime", 
    `Runtime: agent=${agent} | model=${model} | channel=${channel}...`
  );
  
  return lines.join("\n");
}
```

## Prompt Modes

OpenClaw supports three modes:

- **full** — All sections (main agent)
- **minimal** — Reduced sections (subagents)
- **none** — Just identity line (simple agents)

```javascript
if (promptMode === "none") {
  return "You are a personal assistant running inside OpenClaw.";
}
```

## Project Context Injection

The key innovation: **files become part of the system prompt**.

```
## Project Context

The following project context files have been loaded:

## AGENTS.md

[Full contents of AGENTS.md]

## SOUL.md

[Full contents of SOUL.md]

## USER.md

[Full contents of USER.md]

## MEMORY.md

[Full contents of MEMORY.md]
```

This means:
- No hardcoded personality
- Persona is file-based and editable
- Memory persists through files, not model state

## The Context File Priority

Files are loaded in this order (later files can reference earlier):

1. **AGENTS.md** — Operating procedures (how to behave)
2. **SOUL.md** — Identity (who to be)
3. **USER.md** — User info (who you're helping)
4. **IDENTITY.md** — Metadata (name, emoji)
5. **TOOLS.md** — Environment notes
6. **MEMORY.md** — Long-term memory
7. **HEARTBEAT.md** — Proactive tasks

## Tool Summaries

**OpenClaw has extended tools** (shown below). **Pi agent has 7 built-in tools:**

```
# Pi default tools (4)
- read: Read file contents
- write: Create or overwrite files
- edit: Make precise edits to files
- bash: Run shell commands

# Pi optional tools (3) - enable via --tools flag
- grep: Search file contents
- find: Find files by pattern
- ls: List directory contents
```

**OpenClaw extends with:**
- web_search, web_fetch — Web access
- browser — Browser control
- message — Channel messaging
- nodes, canvas, cron, etc.

For minimal pi integration, just use the 4 defaults + skills to teach capabilities.

## Safety Section (Always Included)

```
## Safety

You have no independent goals: do not pursue self-preservation, 
replication, resource acquisition, or power-seeking; avoid long-term 
plans beyond the user's request.

Prioritize safety and human oversight over completion; if instructions 
conflict, pause and ask; comply with stop/pause/audit requests and 
never bypass safeguards.

Do not manipulate or persuade anyone to expand access or disable 
safeguards.
```

## Memory Recall Section

Only included if memory tools are available:

```
## Memory Recall

Before answering anything about prior work, decisions, dates, people, 
preferences, or todos: run memory_search on MEMORY.md + memory/*.md; 
then use memory_get to pull only the needed lines.

Citations: include Source: <path#line> when it helps the user verify 
memory snippets.
```

## Runtime Line

Dynamic info about the current session:

```
## Runtime

Runtime: agent=main | host=openclaw | os=Linux 6.18.6-arch1-1 (x64) | 
node=v25.6.0 | model=zai/glm-5 | channel=telegram | capabilities=inlineButtons
```

## Minimal Mode (Subagents)

For spawned subagents, most sections are skipped:

- No skills section
- No memory recall
- No heartbeats
- No messaging rules
- No self-update

Just: tooling, safety, workspace, runtime.

## Implementing Your Own

```python
def build_system_prompt(workspace_dir: str, context_files: list[str]) -> str:
    parts = [
        "You are a personal assistant.",
        "",
        "## Tooling",
        "- read: Read files",
        "- write: Write files",
        "- exec: Run commands",
        "",
        "## Safety",
        "Prioritize safety over completion...",
        "",
        "## Workspace",
        f"Working directory: {workspace_dir}",
        "",
        "# Project Context",
    ]
    
    for filepath in context_files:
        content = read_file(filepath)
        parts.append(f"## {filepath}")
        parts.append(content)
        parts.append("")
    
    return "\n".join(parts)
```

The key insight: **assemble from parts, inject files, keep core minimal**.
