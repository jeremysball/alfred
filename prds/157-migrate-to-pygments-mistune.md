# PRD: Migrate from Rich to Pygments+Mistune for Markdown Rendering

## Issue Reference

**GitHub Issue**: #157  
**Status**: Draft  
**Priority**: Medium  
**Created**: 2026-03-26

---

## 1. Problem Statement

### Current State
Alfred uses **Rich** for markdown rendering in the TUI (`src/alfred/interfaces/pypitui/rich_renderer.py`). While Rich provides excellent features, it has inherent performance costs:

1. **Console Emulation Overhead**: Rich creates a full Console instance for every render, which includes terminal detection, color system setup, and screen buffer management
2. **Heavyweight Parsing**: Rich's markdown parser is comprehensive but slower than specialized alternatives
3. **Memory Pressure**: StringIO buffer allocation per render adds GC pressure during streaming

### Performance Impact
Even with the incremental rendering fix (PRD #155 follow-up), Rich adds ~5-15ms per chunk for typical responses. For a 4000-token response with 1000 chunks, this is 5-15 seconds of cumulative rendering time.

### Target State
Replace Rich with:
- **Mistune**: Fast, extensible markdown parser (pure Python, minimal overhead)
- **Pygments**: Industry-standard syntax highlighting (already used by many tools)

**Expected Improvement**: 2-5x faster markdown rendering, reduced memory pressure.

---

## 2. Goals and Non-Goals

### Goals
- [ ] Replace `RichRenderer` with `PygmentsMistuneRenderer`
- [ ] Maintain feature parity: markdown parsing, code blocks, inline formatting
- [ ] Improve syntax highlighting quality via Pygments (better language detection, themes)
- [ ] Reduce per-chunk rendering latency
- [ ] Maintain incremental rendering optimization

### Non-Goals
- [ ] Change Web UI rendering (it uses a different stack)
- [ ] Add new markdown features beyond current capabilities
- [ ] Modify Telegram interface rendering
- [ ] Support non-ANSI terminal types

---

## 3. User Stories

**As a CLI user**, I want streaming responses to appear smoothly without stuttering, so I can read along as the model generates.

**As a user reading code-heavy responses**, I want accurate syntax highlighting for all major languages, so I can understand code blocks more easily.

**As a user on resource-constrained systems**, I want Alfred to use fewer CPU cycles for rendering, so my system stays responsive during long conversations.

---

## 4. Technical Requirements

### 4.1 API Compatibility
The new renderer must implement the same interface as `RichRenderer`:

```python
class PygmentsMistuneRenderer:
    def __init__(self, width: int = 80, code_theme: str = "monokai") -> None
    def render_markdown(self, text: str) -> str  # Returns ANSI-colored text
    def render_markup(self, text: str) -> str    # For [dim]foo[/dim] style
    def update_width(self, width: int) -> None
```

### 4.2 Markdown Features to Support
| Feature | Priority | Notes |
|---------|----------|-------|
| Paragraphs | P0 | Basic block separation |
| Code blocks | P0 | Fenced (```) and indented, with syntax highlighting |
| Inline code | P0 | Single backticks |
| Bold/Italic | P0 | **bold**, *italic* |
| Headers | P0 | # ## ### etc. |
| Lists | P1 | Ordered and unordered |
| Links | P1 | [text](url) - render as underlined text |
| Blockquotes | P2 | > quoted text |
| Tables | P2 | Basic support if easy with Mistune |
| Horizontal rules | P2 | ---

### 4.3 ANSI Output Requirements
- True color support (24-bit) when available
- Fallback to 256-color or 16-color as needed
- Proper ANSI reset codes to prevent style bleeding
- Width-aware wrapping (preserve ANSI codes during wrap)

### 4.4 Syntax Highlighting
- Use Pygments with `TerminalFormatter` or `TerminalTrueColorFormatter`
- Support themes: monokai (default), dracula, solarized-dark, github-dark
- Auto-detect language from code block tag (```python)
- Fallback to plain text for unknown languages

---

## 5. Implementation Plan

### Milestone 1: Core Renderer Implementation
- [ ] Create `src/alfred/interfaces/pypitui/pygments_mistune_renderer.py`
- [ ] Implement Mistune renderer subclass for ANSI output
- [ ] Integrate Pygments for code block highlighting
- [ ] Implement `render_markdown()` with feature parity
- [ ] Add width-aware text wrapping with ANSI preservation

**Validation**: Renderer produces output matching current Rich renderer for test inputs.

### Milestone 2: MessagePanel Integration
- [ ] Swap `RichRenderer` for `PygmentsMistuneRenderer` in `MessagePanel`
- [ ] Ensure incremental rendering still works correctly
- [ ] Handle edge cases (tool calls mixed with markdown, errors, etc.)

**Validation**: TUI streaming works with no visual regressions.

### Milestone 3: Theme and Configuration Support
- [ ] Add `code_theme` option to config
- [ ] Support theme switching without restart
- [ ] Document available themes

**Validation**: User can change themes via config file.

### Milestone 4: Testing and Quality Assurance
- [ ] Unit tests for `PygmentsMistuneRenderer`
- [ ] Visual regression tests for common markdown patterns
- [ ] Performance benchmarks comparing old vs new
- [ ] Edge case testing (very long lines, nested formatting, etc.)

**Validation**: All tests pass, benchmarks show 2x+ improvement.

### Milestone 5: Cleanup and Documentation
- [ ] Remove `rich_renderer.py` (or deprecate)
- [ ] Update `pyproject.toml` dependencies (remove rich, add mistune+pygments)
- [ ] Update ROADMAP.md
- [ ] Add changelog entry

**Validation**: No references to Rich in TUI code, dependencies updated.

---

## 6. Migration Strategy

### Phase 1: Parallel Implementation
Keep both renderers, add feature flag to switch between them.

```python
# In config.py
markdown_renderer: Literal["rich", "pygments"] = "rich"  # Default to rich initially
```

### Phase 2: Gradual Rollout
- Test `pygments` renderer in development
- Switch default to `pygments` after validation
- Keep `rich` as fallback for one release

### Phase 3: Cleanup
- Remove `rich_renderer.py`
- Remove config option (always use pygments)

---

## 7. Dependencies

### Remove
- `rich>=13.0` (from TUI rendering, may keep for other uses)

### Add
- `mistune>=3.0` (markdown parser)
- `pygments>=2.16` (syntax highlighting)

Both are lighter than Rich and already widely used in the Python ecosystem.

---

## 8. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Mistune doesn't support some Rich features | Medium | Medium | Audit features first, implement custom renderer methods if needed |
| ANSI output differs from Rich | Medium | Low | Accept minor visual differences; focus on correctness |
| Performance not significantly better | Low | High | Benchmark early in Milestone 1, pivot if needed |
| Breaking existing user themes | Low | Low | Document migration, provide theme mapping |

---

## 9. Success Criteria

- [ ] Rendering latency reduced by 2x or more (measured via benchmarks)
- [ ] Memory usage during streaming reduced (measured via tracemalloc)
- [ ] No visual regressions in common markdown patterns
- [ ] All existing tests pass
- [ ] Code syntax highlighting quality improved (more languages, better accuracy)

---

## 10. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-26 | Use Mistune over CommonMark/mistletoe | Mistune is fastest pure-Python parser, extensible via plugins |
| 2026-03-26 | Keep Pygments (don't use ansi2html-style) | Pygments is standard, theme ecosystem is mature |
| 2026-03-26 | Three-phase migration | Reduces risk, allows rollback if issues found |

---

## 11. Open Questions

1. Should we support ANSI strip mode for testing/log capture?
2. Do we need to support non-UTF-8 terminals?
3. Should inline markup ([dim]foo[/dim]) use a separate mini-parser or be removed?

---

## 12. Related Work

- PRD #155: Interleaved Tool Calls and Thinking Blocks (streaming performance)
- Issue #157: This PRD
- Current implementation: `src/alfred/interfaces/pypitui/rich_renderer.py`
