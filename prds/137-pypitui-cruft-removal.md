# PRD #137: PyPiTUI Cruft Removal and Modernization

## Overview

Replace all custom PyPiTUI implementations with native PyPiTUI components from the newly-built library. Remove 75% of custom code while maintaining feature parity.

## Current State

- **4,252 lines** of custom PyPiTUI code across 18 files
- Custom implementations: Input, Container, Overlays, Focus, Box drawing, Throbbers
- Heavy maintenance burden, inconsistent patterns

## Target State

- **~1,000 lines** (75% reduction)
- **Native PyPiTUI components** exclusively
- **Zero custom component implementations**

## Success Criteria

1. 75% code reduction (4,252 → ~1,000 lines)
2. Zero custom components - All native PyPiTUI
3. Feature parity - All current features work
4. Proper focus management with push_focus()/pop_focus()
5. Native overlay system with show_overlay()/close_overlay()
6. All existing tests pass

## Implementation Phases

### Phase 1: Foundation - Replace Core Components

**Files to Modify:**
- `src/alfred/interfaces/pypitui/tui.py` (876 → ~300 lines)

**Changes:**
- Replace `WrappedInput` (412 lines custom) with native `Input`
- Replace custom focus with `push_focus()`/`pop_focus()`
- Use native `Container` from PyPiTUI

**Delete:**
- `wrapped_input.py` (412 lines)

**Tests:** Verify input submission, focus handling

---

### Phase 2: Overlay System - Replace Custom Overlays

**Files to Modify:**
- `tui.py` - Replace overlay handling

**Changes:**
- Replace `ToastOverlay` with native `Overlay` + `OverlayPosition`
- Replace completion menu overlay with native `show_overlay()`/`close_overlay()`
- Use `z_index` for stacking order

**Delete:**
- `toast_overlay.py` (77 lines)
- `throbber_overlay.py` (160 lines)

**Tests:** Verify toast display, completion menu, overlay closing

---

### Phase 3: Message Display - Simplify MessagePanel

**Files to Modify:**
- `message_panel.py` (534 → ~150 lines)

**Changes:**
- Use `BorderedBox` + `Text` components for messages
- Remove custom rendering logic
- Keep only message formatting/parsing logic

**Tests:** Verify message display, formatting, scrolling

---

### Phase 4: Completion Menu - Use SelectList

**Files to Modify:**
- `completion_menu_component.py` (148 → ~80 lines)

**Changes:**
- Replace custom completion menu with `SelectList`
- Use `SelectItem` for completion items
- Show as `Overlay` with `OverlayPosition`

**Delete:**
- `completion_addon.py` (239 lines)

**Tests:** Verify completion display, selection, navigation

---

### Phase 5: Status & Throbbers - Native Components

**Files to Modify:**
- `status_line.py` (267 → ~100 lines)

**Changes:**
- Use `BorderedBox` + `Text` for status
- Replace custom throbber with simple `Text` in `Overlay`

**Delete:**
- `throbber.py` (444 lines)
- `throbber_overlay.py` (160 lines)

**Tests:** Verify status display, throbber animation

---

### Phase 6: Utilities Cleanup

**Delete:**
- `box_utils.py` (79 lines) - Use `BorderedBox`
- `rich_renderer.py` (92 lines) - Will use pygments/mistune later

**Keep (slimmed):**
- `utils.py` - Token formatting only
- `constants.py` - Color constants
- `fuzzy.py` - Fuzzy matching (business logic)
- `history_cache.py` - History management (business logic)
- `key_bindings.py` - Key handling (business logic)

---

### Phase 7: Commands Modernization

**Files to Modify:** `commands/*.py`

**Changes:**
- Use native component methods for message display
- Use `SelectList` for `/sessions` and `/resume` commands
- Simplify command output

**Tests:** All command tests pass

---

## Final File Structure

### Before (18 files, 4,252 lines):
```
pypitui/
├── __init__.py          # 103 lines
├── box_utils.py         # 79 lines  ❌ DELETE
├── completion_addon.py  # 239 lines ❌ DELETE
├── completion_menu_component.py # 148 lines → 80 lines
├── constants.py         # 8 lines   ✅ KEEP
├── fuzzy.py             # 32 lines  ✅ KEEP
├── history_cache.py     # 292 lines ✅ KEEP
├── key_bindings.py      # 280 lines ✅ KEEP
├── message_panel.py     # 534 lines → 150 lines
├── models.py            # 45 lines  ✅ KEEP
├── rich_renderer.py     # 92 lines  ❌ DELETE
├── status_line.py       # 267 lines → 100 lines
├── throbber.py          # 444 lines ❌ DELETE
├── throbber_overlay.py  # 160 lines ❌ DELETE
├── toast.py             # 148 lines ✅ KEEP
├── toast_overlay.py     # 77 lines  ❌ DELETE
├── tui.py               # 876 lines → 300 lines
├── utils.py             # 16 lines  ✅ KEEP
└── wrapped_input.py     # 412 lines ❌ DELETE
```

### After (~7 files, ~800-1,000 lines):
```
pypitui/
├── __init__.py          # Simplified exports
├── commands/            # ✅ KEEP (business logic)
├── completion_menu.py   # ~80 lines (SelectList wrapper)
├── constants.py         # ✅ KEEP
├── fuzzy.py             # ✅ KEEP
├── history_cache.py     # ✅ KEEP
├── key_bindings.py      # ✅ KEEP
├── message_panel.py     # ~150 lines (formatting only)
├── models.py            # ✅ KEEP
├── status_line.py       # ~100 lines
├── toast.py             # ✅ KEEP (simplified)
├── tui.py               # ~300 lines (orchestrator)
└── utils.py             # ✅ KEEP
```

## Test Strategy

1. **Unit tests** for each phase
2. **Integration tests** for full TUI
3. **Manual verification** of all commands
4. **Regression testing** - All existing tests pass

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 1: Foundation | 4 hours | Input + Focus replaced |
| 2: Overlays | 4 hours | Toast + Completion overlays |
| 3: Messages | 4 hours | MessagePanel simplified |
| 4: Completion | 4 hours | SelectList integration |
| 5: Status | 4 hours | Throbbers removed |
| 6: Cleanup | 4 hours | Delete cruft files |
| 7: Commands | 4 hours | Modernized commands |
| **Total** | **28 hours** | **~4 days** |

## Dependencies

- PyPiTUI >= 1.0.0 (already in pyproject.toml)

## Risks

1. **Regression in commands** - Mitigation: Comprehensive tests
2. **Focus handling edge cases** - Mitigation: Manual testing
3. **Overlay z-index conflicts** - Mitigation: Clear z-index hierarchy

## GitHub Issue

Related to: PRD #136 (Web UI) - This cleanup enables better code sharing between CLI and Web UI
