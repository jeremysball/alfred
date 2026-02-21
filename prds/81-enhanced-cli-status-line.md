# PRD: Enhanced CLI Status Line & Tool Visibility

## Overview

**Issue**: #81
**Status**: Active
**Priority**: Medium
**Created**: 2026-02-20

## Problem Statement

The current CLI lacks visibility into Alfred's internal state. Users cannot see:
- Which model is processing their request
- How many tokens have been consumed (input, output, cache, reasoning)
- What context is loaded (memories, session history, system prompts)
- When Alfred is actively processing vs idle
- Tool execution details without cluttering the conversation

This opacity makes it difficult to understand costs, debug context issues, and gauge Alfred's activity.

## Solution Overview

Add an enhanced status line using Rich toolkit (already in use) that provides:

1. **Persistent Input Prompt**: Always-visible input field at the bottom
2. **Activity Indicator**: Throbber/spinner showing when Alfred is processing
3. **Model Display**: Full provider name (e.g., `kimi/moonshot-v1-128k`)
4. **Token Dashboard**: Real-time cumulative counts for input, output, cache read, reasoning tokens, plus current context size
5. **Context Summary**: Retrieved memories count, session message count, loaded prompt sections
6. **Collapsible Tool Panels**: Styled background panels for tool calls with toggle keybinding

## User Stories

1. As a user, I want to see token usage so I understand API costs
2. As a user, I want to see what context Alfred has loaded so I can debug retrieval
3. As a user, I want a visual indicator when Alfred is processing so I know to wait
4. As a user, I want to hide/show tool output so I can focus on the conversation
5. As a user, I want to see which model is active so I know what I'm using

## Technical Design

### Status Line Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [Conversation history scrolls here]                                      │
│                                                                          │
│ ┌─ Tool: bash ─────────────────────────────────────────────────────────┐ │
│ │ $ uv run pytest -q                                                    │ │
│ │ 572 passed, 4 skipped                                                 │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│ 🔄 kimi/moonshot-v1-128k │ 📥 12,847 📤 3,291 💾 8,420 🧠 1,200 │ 45/50 │
│ 📚 3 memories │ 💬 28 msgs │ 📋 SOUL,USER,TOOLS                      │
├─────────────────────────────────────────────────────────────────────────┤
│ > _                                                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Components

#### 1. Activity Indicator (Throbber)
- `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏` spinner during streaming
- Static `●` when idle
- Color: cyan when active, green when idle

#### 2. Model Display
- Format: `{provider}/{model_name}`
- Examples: `kimi/moonshot-v1-128k`, `openai/gpt-4o`
- Source: `Alfred.llm_provider` config

#### 3. Token Dashboard
| Field | Source | Color |
|-------|--------|-------|
| 📥 Input | Cumulative `usage.prompt_tokens` across conversation | Blue |
| 📤 Output | Cumulative `usage.completion_tokens` | Green |
| 💾 Cache Read | Cumulative `usage.cache_read_input_tokens` (if available) | Yellow |
| 🧠 Reasoning | Cumulative reasoning tokens (if available) | Magenta |
| Context | Current context window size / max | Default |

#### 4. Context Summary
- **Memories**: Count of retrieved memories from last search
- **Messages**: Current session message count
- **Prompts**: Loaded system prompt sections (SOUL, USER, TOOLS, AGENTS, etc.)

#### 5. Tool Panels
- Bordered panel with tool name in header
- Collapsible via `T` keybinding
- Background color: dim blue/grey
- Shows: tool name, params (truncated), result (truncated)

#### 6. Persistent Input
- `> ` prompt always at bottom
- Input area doesn't scroll away
- Uses Rich `Prompt` or custom input handling with `Live` display

### Keybindings

| Key | Action |
|-----|--------|
| `Ctrl-T` | Toggle tool panel visibility (show/hide all tool output) |
| `Ctrl+C` | Cancel current stream / exit |

### Data Sources

```python
# Token tracking (new state required)
class TokenUsage:
    input_tokens: int = 0      # Cumulative
    output_tokens: int = 0     # Cumulative
    cache_read_tokens: int = 0 # Cumulative
    reasoning_tokens: int = 0  # Cumulative
    context_tokens: int = 0    # Current context size

# Context info (existing sources)
memories_count = len(retrieved_memories)  # From last search
session_messages = len(session.messages)  # From Session
prompt_sections = ["SOUL", "USER", "TOOLS"]  # From Context

# Model info (existing source)
model_display = f"{provider}/{model_name}"  # From LLM config
```

### Implementation Approach

1. **TokenTracker**: New class to accumulate token usage across the conversation
2. **StatusRenderer**: Rich Live display component for status line
3. **ToolPanelManager**: Manages collapsible tool output panels
4. **EnhancedCLI**: Refactor `cli.py` to use Live display with persistent input

## Milestones

- [x] **M1: Token Tracking Infrastructure** — Add TokenTracker class that accumulates usage from LLM responses, integrate with agent loop
- [x] **M2: Status Line Display** — Implement Rich Live status bar showing model, activity, and token counts
- [~] **M3: Context Summary** — DROPPED: User decided not to include context info (memories, messages, prompt sections) in status display
- [x] **M4: Tool Panels with Toggle** — Implement collapsible tool output panels with `Ctrl-T` keybinding. Tool panels appear inline where they occur (not at end). No collapsed indicator shown.
- [x] **M5: Persistent Input Prompt** — Fixed layout with header, scrollable body with scrollbar indicator, and input at bottom. Prompt is `>>> `.
- [ ] **M6: Manual Validation & Polish** — Test all features, verify token accuracy, refine layout

## Success Criteria

- [ ] Token counts accurately reflect cumulative usage for the conversation
- [ ] Activity indicator shows during streaming, hides when idle
- [ ] Model name displays full provider/model format
- [ ] Tool panels toggle with `T` key, state persists across session
- [ ] Input prompt remains visible during streaming
- [ ] Context summary shows accurate counts
- [ ] All existing tests pass, new functionality tested

## Out of Scope

- Per-session token persistence (resets each conversation)
- Token cost estimation (just raw counts)
- Telegram interface changes (CLI only)
- Configuration UI for status line customization

## Dependencies

- `rich` (already in use)
- Token usage data from LLM providers (varies by provider)

## Risks

| Risk | Mitigation |
|------|------------|
| Some providers don't return token counts | Show "N/A" or omit those fields |
| Rich Live + input handling complexity | Test thoroughly, use proven patterns |
| Performance overhead from rendering | Profile, optimize refresh rate |

## Questions Resolved

- **Interface**: CLI only
- **Context visibility**: All (memories, messages, prompt sections)
- **UI style**: Enhanced status line with Rich
- **Model display**: Full provider/model name
- **Tool output**: Collapsible panels with toggle keybinding
