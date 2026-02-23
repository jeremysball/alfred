---
name: plan-mode
description: Read-only planning mode for exploring features and producing structured implementation plans. Use before prd-create for better requirements, or before prd-next for deeper task analysis.
invocation: /plan [feature-description]
---

# Plan Mode - Read-Only Planning

## Overview

Plan mode constrains the agent to **read-only exploration** while producing a structured implementation plan. Use this to:
- Explore a codebase before creating a PRD
- Analyze implementation approaches before starting work
- Deep-dive into a specific task before `/prd-next`

**Key Principle**: Read, explore, ask questions, plan — but never write production code.

---

## ⛔ READ-ONLY CONSTRAINT

**While in plan mode, you MUST NOT:**
- Edit, create, or delete source files
- Modify configuration files
- Run state-changing commands (git commit, npm install, etc.)
- Execute code that writes to disk

**You MAY:**
- Read any file in the repository
- Execute read-only commands (ls, grep, find, git log, etc.)
- Write the plan output to `plans/` directory (explicit user choice at end)
- Use search tools (Serper) to research approaches

**If you find yourself about to write code, STOP. You're in plan mode.**

---

## Invocation

```
/plan [feature-description]
```

Examples:
- `/plan authentication refactor`
- `/plan add caching layer to API`
- `/plan migrate from PostgreSQL to SQLite`

---

## Interaction Flow (Hybrid Model)

### Phase 1: Initial Question (30 seconds)

Ask **one** clarifying question to understand intent:

```markdown
Before I explore, let me understand the goal:

[1-2 targeted questions about scope, constraints, or user impact]

This helps me focus the exploration on relevant areas.
```

**Good questions:**
- "Is this a refactor of existing code or new functionality alongside it?"
- "What's the main pain point you're trying to solve?"
- "Are there specific constraints I should know about (performance, compatibility, etc.)?"

**Avoid:**
- Long questionnaires
- Questions you can answer by reading code

---

### Phase 2: Read-Only Exploration (5-10 minutes)

Explore the codebase to understand:
- Current architecture and patterns
- Related files and modules
- Existing implementations of similar features
- Test coverage and documentation

**Exploration tools:**
- `read` - Examine specific files
- `grep` - Find patterns and references
- `find` - Locate relevant files
- `ls` - Understand directory structure
- `bash git log --oneline -n 20` - Recent changes context

**Output your findings as you go:**
```markdown
🔍 **Exploring [area]...**

Found: [key discoveries]
Relevant files: [list with brief notes]
Current approach: [how it works now]
```

---

### Phase 2b: Manual Verification with tmux-tape (Optional)

**When the feature involves a CLI/TUI application**, use tmux-tape to visually verify current behavior before planning changes.

**Use tmux-tape for:**
- CLI applications with interactive prompts
- TUI frameworks (Textual, Rich Live, ncurses)
- Asyncio apps (servers, bots, agents)
- Any terminal output with visual elements (colors, box-drawing, layouts)

**Verification workflow:**
```bash
# 1. Create session directory
SESSION_DIR="/tmp/pi-tmux/$(date +%Y-%m-%d_%H-%M-%S)"
mkdir -p "$SESSION_DIR"
cp .pi/skills/tmux-tape/tmux_tool.py "$SESSION_DIR/"
cd "$SESSION_DIR"

# 2. Write verification script
# 3. Run with uv run python script.py
```

**Example verification script:**
```python
#!/usr/bin/env python3
from tmux_tool import TerminalSession

with TerminalSession("verify", port=7681) as s:
    # Start the CLI/app
    s.send("cd /workspace/project && ./run-cli")
    s.send_key("Enter")
    s.sleep(2)
    
    # Capture current behavior
    result = s.capture("current-behavior.png", upload=True)
    print("Current output:")
    print(result["text"])
    print(f"\nScreenshot: {result['url']}")
    
    # Clean exit
    s.send_key("C-c")
    s.send("exit")
    s.send_key("Enter")
```

**What to verify:**
- Current output format and structure
- Interactive prompts and their flow
- Error messages and edge case handling
- Visual layout (box-drawing, colors, alignment)

**Include in plan:**
```markdown
## Manual Verification

**Current behavior captured:** [screenshot URL]

**Observations:**
- [What the current CLI does]
- [Notable output patterns]
- [Edge cases observed]
```

**Important:** This is read-only verification — do not make changes, just document current behavior.

---

### Phase 3: Deeper Questions (2-5 minutes)

Based on exploration, ask targeted questions:

```markdown
Based on what I found, I have some design questions:

1. [Specific question about approach A vs B]
2. [Question about scope/boundary]
3. [Question about integration with existing code]

These will help me recommend the best path forward.
```

**Question principles:**
- Ground questions in what you discovered
- Offer options with tradeoffs
- Let the user decide

---

### Phase 4: Structured Plan

Produce a plan in this format:

```markdown
# Plan: [Feature Name]

## Problem Statement
[1-2 sentences describing what problem this solves]

## Recommended Approach
[High-level approach with rationale]

### Key Decisions
| Decision | Choice | Rationale |
|----------|--------|-----------|
| [Decision 1] | [Option chosen] | [Why] |
| [Decision 2] | [Option chosen] | [Why] |

## Files & Areas

### To Modify
- `path/to/file.py` - [what changes]
- `path/to/other.py` - [what changes]

### To Create
- `path/to/new_file.py` - [purpose]

### To Review (context only)
- `path/to/existing.py` - [why relevant]

## Implementation Steps

### Phase 1: [Foundation/Setup]
1. [Step with clear outcome]
2. [Step with clear outcome]

### Phase 2: [Core Implementation]
1. [Step with clear outcome]
2. [Step with clear outcome]

### Phase 3: [Integration/Testing]
1. [Step with clear outcome]
2. [Step with clear outcome]

## Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk 1] | H/M/L | H/M/L | [How to address] |

## Verification Artifacts (Optional)
If manual verification was performed:
- **Screenshots:** [URLs to captured images]
- **Current behavior:** [Summary of observed behavior]
- **Edge cases noted:** [Any edge cases discovered during verification]

## Open Questions
- [ ] [Question needing resolution before/during implementation]
- [ ] [Question needing resolution before/during implementation]

## PRD-Ready Milestones (Optional)
If proceeding to `/prd-create`, these milestones can be used directly:
1. [ ] [Milestone 1 - meaningful progress marker]
2. [ ] [Milestone 2]
3. [ ] [Milestone 3]
```

---

## End-of-Plan Options

After presenting the plan, offer:

```markdown
---

**What would you like to do with this plan?**

**1. Save to file**
   Creates `plans/[feature-name].md` for future reference

**2. Create PRD from this plan**
   Proceeds to `/prd-create` with plan as foundation

**3. Start working now**
   Exits plan mode, hands off to `/prd-start` or `/prd-next`

**4. Discard**
   Plan stays in chat only, no file created

Please enter 1-4:
```

### Option 1: Save to File

```bash
mkdir -p plans
# Write plan to plans/[feature-name].md
```

Confirm: `✅ Plan saved to plans/[feature-name].md`

### Option 2: Create PRD

Transition to `/prd-create` workflow, using:
- Problem Statement → PRD Problem section
- PRD-Ready Milestones → PRD milestones
- Key Decisions → Initial decision log
- Open Questions → Discussion points

### Option 3: Start Working

If PRD already exists:
```
To start implementation, run: /prd-start [issue-id]
```

If no PRD:
```
This feature doesn't have a PRD yet. Would you like to create one first? (recommended)
```

### Option 4: Discard

Acknowledge and end:
```
Plan discarded. It remains in this conversation for reference.
```

---

## Integration with PRD Workflow

### Before `/prd-create`
Run `/plan` first to:
- Explore the codebase and understand constraints
- Identify affected files and systems
- Produce PRD-ready milestones
- Ask design questions early

Result: Better PRD with grounded requirements

### Before `/prd-next`
Run `/plan [specific-task]` to:
- Deep-dive into a single task
- Explore implementation options
- Produce step-by-step approach
- Identify risks specific to that task

Result: Clearer implementation path for the recommended task

### Plan File Naming

If saved, plans use this convention:
```
plans/
├── auth-refactor.md
├── caching-layer.md
├── sqlite-migration.md
└── ...
```

Plans are **working documents** — they can be deleted after PRD creation or kept for reference.

---

## Quality Checklist

Before finalizing the plan, verify:

- [ ] Problem statement is clear and user-focused
- [ ] Approach recommendation has rationale
- [ ] Files to modify/create are specific, not vague
- [ ] Steps are ordered logically with clear outcomes
- [ ] Risks include mitigations, not just problems
- [ ] Open questions are actionable
- [ ] Milestones represent meaningful progress (not micro-tasks)
- [ ] If CLI/TUI: manual verification performed or noted as needed

---

## Example Session

```
User: /plan add rate limiting to API

Agent: Before I explore, let me understand the goal:
       Is this for all endpoints or specific high-traffic ones?
       What's the primary concern — abuse prevention or load management?

User: All endpoints, mainly for abuse prevention.

Agent: 🔍 Exploring API structure...
       Found: FastAPI app in src/api/, 12 endpoints, no current rate limiting
       Relevant: src/middleware/ exists, could add there

       Based on exploration, I have design questions:
       1. Fixed rate per IP or per API key?
       2. Redis-backed for distributed or in-memory for single instance?

User: Per API key, in-memory is fine for now.

Agent: [Produces structured plan with approach, files, steps, risks]

       What would you like to do?
       1. Save to file
       2. Create PRD from this plan
       3. Start working now
       4. Discard
```

### Example with Manual Verification (CLI/TUI)

```
User: /plan improve Alfred's status line display

Agent: Before I explore, let me understand the goal:
       What's the main issue — missing information, layout, or visual clarity?

User: Visual clarity — the token count gets lost in the output.

Agent: 🔍 Exploring Alfred CLI structure...
       Found: src/interfaces/cli.py uses Rich Live for display
       Relevant: src/agent.py tracks token usage, status line in cli.py

       📸 Running manual verification to capture current behavior...

       [Uses tmux-tape to capture current CLI output]
       Screenshot: https://0x0.st/abc123.png

       Observations:
       - Status line shows tokens but blends with tool output
       - No visual separation between sections
       - Color scheme makes token count hard to see

       Based on this, I have design questions:
       1. Should status be a fixed panel at bottom, or inline with output?
       2. Do you want collapsible sections for tool calls?

User: Fixed panel at bottom, collapsible tool calls sounds great.

Agent: [Produces structured plan with verification artifacts included]

       What would you like to do?
       1. Save to file
       2. Create PRD from this plan
       3. Start working now
       4. Discard
```

---

## Anti-Patterns to Avoid

❌ **Skipping exploration**: Don't produce a plan without reading code
❌ **Vague steps**: "Implement the feature" is not a step
❌ **No alternatives**: Always consider multiple approaches
❌ **Forgetting tests**: Include testing in the plan
❌ **Ignoring existing patterns**: Follow project conventions
❌ **Writing code**: You're in read-only mode — plan, don't implement
