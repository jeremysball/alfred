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

### Milestone 1: Config Infrastructure (TDD)

#### 1.1 TOML Parsing Setup
- [x] Test: `test_toml_import_works()` - verify tomli import works
- [x] Implement: Add `import tomli` in `config.py`
- [x] Commit

#### 1.2 XDG Config Path
- [ ] Test: `test_get_config_toml_path_returns_xdg_location()` - verify path is `$XDG_CONFIG_HOME/alfred/config.toml`
- [ ] Implement: Add `get_config_toml_path()` to `data_manager.py`
- [ ] Test: `test_get_config_toml_path_fallback_to_home()` - verify fallback when `XDG_CONFIG_HOME` unset
- [ ] Implement: Fallback to `~/.config/alfred/config.toml`
- [ ] Commit

#### 1.3 Config Template Creation
- [ ] Test: `test_config_template_exists()` - verify `templates/config.toml` exists with required sections
- [ ] Implement: Create `templates/config.toml` with `[provider]`, `[embeddings]`, `[memory]`, `[search]`, `[ui.status_line]` sections
- [ ] Commit

#### 1.4 Template Copy on Init
- [ ] Test: `test_init_xdg_directories_copies_config_toml()` - verify config.toml copied when missing
- [ ] Implement: Update `init_xdg_directories()` to copy `templates/config.toml` to XDG config dir
- [ ] Test: `test_init_xdg_preserves_existing_config_toml()` - verify existing file not overwritten
- [ ] Implement: Check existence before copy
- [ ] Commit

#### 1.5 Config Class TOML Loading
- [ ] Test: `test_load_config_reads_toml()` - verify `load_config()` parses TOML file
- [ ] Implement: Replace JSON loading with TOML parsing in `load_config()`
- [ ] Test: `test_config_default_llm_provider_from_toml()` - verify nested `[provider]` section loads
- [ ] Implement: Update `Config` class to read nested TOML sections
- [ ] Commit

#### 1.6 Memory Budget Field
- [ ] Test: `test_config_has_memory_budget_field()` - verify `Config.memory_budget` exists
- [ ] Implement: Add `memory_budget: int = 32000` to `Config` class
- [ ] Test: `test_memory_budget_loads_from_toml()` - verify `[memory]` section `budget` key loads
- [ ] Implement: Map `memory.budget` TOML key to `memory_budget` field
- [ ] Commit

#### 1.7 Backward Compatibility
- [ ] Test: `test_load_config_falls_back_to_json()` - verify `config.json` read when `config.toml` missing
- [ ] Implement: Check for TOML first, fallback to JSON if not found
- [ ] Test: `test_load_config_prefers_toml_over_json()` - verify TOML takes precedence when both exist
- [ ] Implement: TOML priority logic
- [ ] Commit

**Success Criteria:**
- Config loads from TOML file in XDG config directory
- All existing functionality works with new config system
- Missing config file generates sensible defaults from template
- Backward compatibility with config.json maintained

---

### Milestone 2: Context Budget Refactoring (TDD)

#### 2.1 Rename token_budget to memory_budget
- [ ] Test: `test_context_builder_has_memory_budget_parameter()` - verify `ContextBuilder.__init__` accepts `memory_budget`
- [ ] Implement: Rename parameter in `ContextBuilder.__init__`
- [ ] Test: `test_context_builder_uses_memory_budget_attribute()` - verify internal usage updated
- [ ] Implement: Rename `self.token_budget` → `self.memory_budget`
- [ ] Commit

#### 2.2 Update Default Budget
- [ ] Test: `test_context_builder_default_memory_budget_is_32k()` - verify default is 32000
- [ ] Implement: Change default from 8000 to 32000 in `ContextBuilder`
- [ ] Test: `test_context_builder_accepts_custom_memory_budget()` - verify custom value passes through
- [ ] Implement: Ensure parameter properly sets the attribute
- [ ] Commit

#### 2.3 Wire Config to ContextBuilder
- [ ] Test: `test_context_loader_passes_memory_budget_to_builder()` - verify `ContextLoader` passes config value
- [ ] Implement: Update `ContextLoader` to pass `config.memory_budget` to `ContextBuilder`
- [ ] Test: `test_context_assembly_uses_configured_budget()` - verify end-to-end budget application
- [ ] Implement: Integration between config and context building
- [ ] Commit

**Success Criteria:**
- Variable names clearly distinguish memory budget from model context
- Default budget increased to 32k
- Config value flows through to `ContextBuilder`

---

### Milestone 3: Responsive Status Line (TDD)

#### 3.1 Model Name Truncation
- [ ] Test: `test_truncate_model_at_full_width()` - verify 25 char limit at 80+ width
- [ ] Implement: `_truncate_model()` logic for full width tier
- [ ] Test: `test_truncate_model_at_medium_width()` - verify 15 char limit at 50-79 width
- [ ] Implement: Medium width truncation
- [ ] Test: `test_truncate_model_at_compact_width()` - verify 10 char limit at <50 width
- [ ] Implement: Compact width truncation
- [ ] Commit

#### 3.2 Prevent Wrapping
- [ ] Test: `test_status_line_never_exceeds_width()` - verify render output fits within specified width
- [ ] Implement: Fix width calculation to account for all separators and padding
- [ ] Test: `test_status_line_single_element_returned()` - verify always returns single string
- [ ] Implement: Ensure no line breaks in output
- [ ] Commit

#### 3.3 Responsive Tier Display
- [ ] Test: `test_full_tier_shows_cached_reasoning()` - verify cached/reasoning tokens shown at 80+
- [ ] Test: `test_medium_tier_hides_cached_reasoning()` - verify cached/reasoning hidden at 50-79
- [ ] Test: `test_compact_tier_shows_minimal()` - verify only model + in/out at <50
- [ ] Implement: Tiered display logic in `_render_full()`, `_render_medium()`, `_render_compact()`
- [ ] Commit

#### 3.4 Queued Indicator Conditional
- [ ] Test: `test_queued_shows_when_positive()` - verify queued appears when > 0
- [ ] Test: `test_queued_hidden_when_zero()` - verify queued omitted when 0
- [ ] Implement: Conditional queued display
- [ ] Commit

**Success Criteria:**
- Status line never wraps to multiple lines
- Responsive tiers display correctly at each width threshold
- Model name truncates appropriately per tier
- Queued only shows when non-zero

---

### Milestone 4: Tool Call Formatting (TDD)

#### 4.1 ANSI Constants for Tool Titles
- [ ] Test: `test_tool_title_uses_ansi_bold()` - verify `BOLD`/`RESET` constants in title
- [ ] Implement: Replace `f"[bold]{name}[/bold]"` with `f"{BOLD}{name}{RESET}"` in `message_panel.py`
- [ ] Test: `test_tool_title_no_rich_markup()` - verify no `[bold]` in output
- [ ] Implement: Remove Rich markup entirely
- [ ] Commit

#### 4.2 Tool Output Truncation Direction
- [ ] Test: `test_tool_output_shows_beginning_not_end()` - verify `[:200]` not `[-200:]`
- [ ] Implement: Change slice direction in `_build_content_with_tools()`
- [ ] Test: `test_tool_output_truncates_at_200_chars()` - verify truncation still happens at 200
- [ ] Implement: Preserve truncation limit, just change direction
- [ ] Commit

#### 4.3 Box Utils ANSI Handling
- [ ] Test: `test_build_bordered_box_preserves_ansi_in_title()` - verify ANSI codes not counted in width
- [ ] Implement: Update `box_utils.py` to handle ANSI in title parameter
- [ ] Commit

**Success Criteria:**
- Tool titles use ANSI constants (no Rich markup)
- Tool output shows beginning (not end) of output
- Box drawing handles ANSI codes correctly

---

### Milestone 5: Migration and Cleanup (TDD)

#### 5.1 Remove config.json from Repo
- [ ] Test: `test_config_json_not_in_repo()` - verify `config.json` removed
- [ ] Implement: Delete `config.json`, move to `templates/config.json` if backward compat needed
- [ ] Commit

#### 5.2 Update .gitignore
- [ ] Test: `test_gitignore_ignores_config_files()` - verify patterns exist
- [ ] Implement: Add `config.toml` and `config.json` to `.gitignore`
- [ ] Commit

#### 5.3 Documentation Updates
- [ ] Test: `test_readme_mentions_toml_config()` - verify README references new config location
- [ ] Implement: Update README.md configuration section
- [ ] Test: `test_roadmap_marks_prd_complete()` - verify ROADMAP updated
- [ ] Implement: Mark PRD #100 items complete in ROADMAP.md
- [ ] Commit

#### 5.4 Full Test Suite
- [ ] Run: `uv run pytest` - verify all tests pass
- [ ] Run: `uv run ruff check src/` - verify no lint errors
- [ ] Run: `uv run mypy src/` - verify type checking passes
- [ ] Fix any issues
- [ ] Commit

**Success Criteria:**
- Old config.json no longer in repository
- Documentation reflects new configuration approach
- All tests pass
- Code quality checks pass

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
