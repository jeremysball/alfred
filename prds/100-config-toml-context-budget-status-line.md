# PRD: Config TOML Migration, Context Budget Clarity, and Responsive Status Line

**GitHub Issue**: #100  
**Priority**: High  
**Status**: Planning

---

## 1. Problem Statement

### 1.1 Configuration Fragmentation
Alfred's configuration is currently split awkwardly between:
- `config.json` (3 runtime settings: default_llm_provider, embedding_model, chat_model)
- Environment variables/.env (secrets: API keys, tokens)
- Hardcoded values scattered in source code

This makes it difficult to:
- Discover available configuration options
- Understand which settings exist and their defaults
- Manage configuration across different environments

### 1.2 Context Budget Confusion
There are two different "context" concepts that are currently conflated:

| Concept | Current Value | Purpose |
|---------|---------------|---------|
| **Memory Context Budget** | 8000 tokens (hardcoded) | How many tokens of memories to include in the prompt |
| **Model Context Window** | 128k tokens (model capability) | Maximum tokens the model can process total |

The 8000 token limit in `ContextBuilder` is arbitrary and confusingly small compared to the model's actual 128k capacity. Users may incorrectly assume Alfred can't use the full model context.

### 1.3 Status Line Display Issues
The status line has several UX problems:
- Content wraps to multiple lines at narrow terminal widths
- No clear responsive behavior defining what shows/hides at different widths
- Rich formatting (`[bold]`) used in tool call titles instead of ANSI constants
- Tool output shows the last 200 characters instead of the first 200

---

## 2. Solution Overview

### 2.1 Migrate to XDG Config Directory with TOML
Move configuration to `$XDG_CONFIG_HOME/alfred/config.toml` (fallback to `~/.config/alfred/config.toml`) using TOML format for better readability and organization.

### 2.2 Clarify Context Budget vs Model Context
- Rename `token_budget` to `memory_budget` for clarity
- Increase default to 32k tokens (25% of 128k model context)
- Add documentation explaining the distinction
- Consider making this user-configurable

### 2.3 Responsive Status Line
Implement a clearly defined responsive behavior:
- **Full (80+ chars)**: Model | ctx N ↑in/cached⚡ ↓out/reasoningρ | queued N
- **Medium (50-79 chars)**: Model | ctx | in/out | queued
- **Compact (<50 chars)**: Model | in/out only

Also fix:
- Replace Rich `[bold]` markup with ANSI constants
- Show first 200 chars of tool output (not last 200)

---

## 3. Detailed Requirements

### 3.1 Configuration Migration

**New Config Location:**
```
$XDG_CONFIG_HOME/alfred/config.toml
└── ~/.config/alfred/config.toml (fallback)
```

**New Config Structure:**
```toml
[provider]
default = "kimi"
chat_model = "kimi-k2-5"

[embeddings]
model = "text-embedding-3-small"

[memory]
# Token budget for memory search context (not model context window)
# This is how many tokens of memories to include in the prompt
budget = 32000  # 25% of 128k model context

[search]
min_similarity = 0.3
recency_half_life_days = 30

[ui.status_line]
# Width thresholds for responsive layout
compact_threshold = 50
full_threshold = 80
```

**Secrets (remain in .env):**
- `TELEGRAM_BOT_TOKEN`
- `OPENAI_API_KEY`
- `KIMI_API_KEY`
- `KIMI_BASE_URL`

### 3.2 Context Budget Clarification

**Current (confusing):**
```python
class ContextBuilder:
    def __init__(self, searcher: MemorySearcher, token_budget: int = 8000):
        self.token_budget = token_budget  # Is this the model limit?
```

**New (clear):**
```python
class ContextBuilder:
    def __init__(self, searcher: MemorySearcher, memory_budget: int = 32000):
        self.memory_budget = memory_budget  # Tokens allocated for memories in prompt
```

**Documentation addition:**
```python
# Memory budget determines how many tokens of relevant memories
# to include in the prompt context. This is separate from the
# model's total context window (128k for kimi-k2-5).
#
# Example with 32k memory budget:
# - ~8k for system prompt (AGENTS, SOUL, USER, TOOLS)
# - ~32k for retrieved memories
# - ~88k remaining for conversation history
```

### 3.3 Responsive Status Line Specification

**Width Tiers:**

| Tier | Width | Display Format |
|------|-------|----------------|
| Compact | <50 | `{model} ↑{in} ↓{out}` |
| Medium | 50-79 | `{model} \| ctx {ctx} \| ↑{in} ↓{out} \| queued {n}` |
| Full | 80+ | `{model} \| ctx {ctx} \| ↑{in}/cached⚡ ↓{out}/reasoningρ \| queued {n}` |

**Responsive Rules:**
1. Never wrap - truncate with ellipsis if needed
2. Model name truncates first (max 25 → 15 → 10 chars)
3. Context token count abbreviates (32K instead of 32000)
4. Queued indicator only shows when > 0
5. Cached/reasoning tokens only show when > 0

### 3.4 Tool Call Formatting Fixes

**Tool title (line 275 in message_panel.py):**
```python
# Current (Rich markup):
fancy_title = f"[bold]{tc.tool_name}[/bold]"

# New (ANSI constants):
fancy_title = f"{BOLD}{tc.tool_name}{RESET}"
```

**Tool output truncation (line 200 in message_panel.py):**
```python
# Current (shows end):
display_output = tc.output[-200:] if len(tc.output) > 200 else tc.output

# New (shows beginning):
display_output = tc.output[:200] if len(tc.output) > 200 else tc.output
```

---

## 4. Implementation Milestones

### Milestone 1: Config Infrastructure
- [ ] Add TOML parsing dependency (`tomli` for Python <3.11, builtin for 3.11+)
- [ ] Create `Config` class that loads from `XDG_CONFIG_HOME/alfred/config.toml`
- [ ] Add `memory_budget` field (default 32000)
- [ ] Add `xdg_config_dir` to `data_manager.py`
- [ ] Create default config file generation if missing
- [ ] Update `load_config()` to use TOML instead of JSON
- [ ] Add backward compatibility: read `config.json` if `config.toml` doesn't exist

**Success Criteria:**
- Config loads from TOML file in XDG config directory
- All existing functionality works with new config system
- Missing config file generates sensible defaults

### Milestone 2: Context Budget Refactoring
- [ ] Rename `token_budget` → `memory_budget` in `ContextBuilder`
- [ ] Update default from 8000 → 32000
- [ ] Pass `memory_budget` from `Config` to `ContextBuilder`
- [ ] Update `search.py` docstrings to clarify memory_budget vs model context
- [ ] Verify context assembly respects the new budget

**Success Criteria:**
- Variable names clearly distinguish memory budget from model context
- Default budget increased to 32k
- Documentation explains the distinction

### Milestone 3: Responsive Status Line
- [ ] Fix status line width calculation to prevent wrapping
- [ ] Implement truncation logic for model names at each tier
- [ ] Verify responsive thresholds work correctly
- [ ] Add unit tests for status line rendering at different widths

**Success Criteria:**
- Status line never wraps to multiple lines
- Responsive tiers display correctly at each width threshold
- Model name truncates appropriately

### Milestone 4: Tool Call Formatting
- [ ] Replace Rich `[bold]` markup with `BOLD`/`RESET` ANSI constants in tool titles
- [ ] Change tool output truncation from `[-200:]` to `[:200]`
- [ ] Update `box_utils.py` to handle ANSI in titles correctly
- [ ] Verify tool call boxes render correctly

**Success Criteria:**
- Tool titles use ANSI constants (no Rich markup)
- Tool output shows beginning (not end) of output
- Visual appearance unchanged or improved

### Milestone 5: Migration and Cleanup
- [ ] Remove `config.json` from repository
- [ ] Update `.gitignore` to exclude config files
- [ ] Update documentation (README, ROADMAP)
- [ ] Create migration note for existing users
- [ ] Run full test suite

**Success Criteria:**
- Old config.json no longer used
- Documentation reflects new configuration approach
- All tests pass

---

## 5. File Changes

### Modified Files
| File | Changes |
|------|---------|
| `src/config.py` | Rewrite to load TOML from XDG config dir |
| `src/data_manager.py` | Add XDG config directory helper |
| `src/search.py` | Rename token_budget → memory_budget, update default |
| `src/context.py` | Pass memory_budget from config |
| `src/interfaces/pypitui/status_line.py` | Fix wrapping, improve truncation |
| `src/interfaces/pypitui/message_panel.py` | ANSI constants, output truncation fix |
| `src/interfaces/pypitui/box_utils.py` | Handle ANSI in box titles |

### New Files
| File | Purpose |
|------|---------|
| `~/.config/alfred/config.toml` | User configuration (generated) |

### Removed Files
| File | Reason |
|------|----------|
| `config.json` | Replaced by TOML in XDG config dir |

---

## 6. User Impact

### For New Users
- Configuration lives in standard XDG location
- Clear TOML format with comments
- Better defaults (32k memory budget)

### For Existing Users
- Migration needed: copy `config.json` values to `~/.config/alfred/config.toml`
- Environment variables continue to work unchanged
- Backward compatibility: old config.json will be read if TOML missing

---

## 7. Testing Strategy

### Unit Tests
- Config loading from TOML
- Default value generation
- XDG directory resolution
- Status line rendering at various widths
- Context builder with different budgets

### Integration Tests
- Full config load → context assembly flow
- Status line in TUI at different terminal sizes

### Manual Verification
- Start Alfred with new config
- Verify status line at different terminal widths
- Trigger tool calls to verify formatting
- Test with both compact and wide terminals

---

## 8. Documentation Updates

### README.md
- Update configuration section
- Add XDG_CONFIG_HOME reference
- Document memory_budget setting

### ROADMAP.md
- Mark "Config TOML Migration" complete
- Update related milestones

### New Documentation
- Config reference (all available options)
- Migration guide for existing users
