# Execution Plan: PRD #140 - Milestone 1

## Overview

Stabilize the **PyPiTUI public runtime surface** Alfred will target.

This phase is intentionally limited to the library-side foundation needed to make PyPiTUI usable as a real downstream dependency. It does **not** yet rewrite Alfred’s runtime or update all docs/examples; those belong to later milestones.

For planning purposes, `../pypitui` is treated as a subproject of this work.

---

## Milestone 1: PyPiTUI public runtime surface is coherent and usable

### Component: Package exports

- [ ] **Test**: `test_package_exports_mock_terminal()` — downstream code can `from pypitui import MockTerminal` without reaching into private modules
- [ ] **Implement**: export `MockTerminal` from `../pypitui/src/pypitui/__init__.py` and keep `__all__` aligned with the supported public surface
- [ ] **Run**: `cd ../pypitui && uv run pytest tests/integration/test_terminal_tui.py::TestMockTerminalIntegration -v`

### Component: Terminal size contract

- [ ] **Test**: `test_terminal_get_size_returns_current_dimensions()` — `Terminal` exposes a public size API suitable for downstream runtime code
- [ ] **Implement**: add `get_size()` to `../pypitui/src/pypitui/terminal.py` using the real terminal size contract
- [ ] **Run**: `cd ../pypitui && uv run pytest tests/unit/test_terminal_api.py::test_terminal_get_size_returns_current_dimensions -v`

- [ ] **Test**: `test_mock_terminal_get_size_returns_configured_dimensions()` — `MockTerminal` exposes the same size contract as `Terminal`
- [ ] **Implement**: add `get_size()` to `../pypitui/src/pypitui/mock_terminal.py` and keep the mock aligned with the real terminal API
- [ ] **Run**: `cd ../pypitui && uv run pytest tests/unit/test_terminal_api.py::test_mock_terminal_get_size_returns_configured_dimensions -v`

### Component: Public render loop API

- [ ] **Test**: `test_tui_render_frame_renders_root_component()` — `TUI.render_frame()` exists as a public method and renders the root component without downstream callers reaching into private internals
- [ ] **Implement**: add public `render_frame()` to `../pypitui/src/pypitui/tui.py` using the library’s actual render/composite/diff pipeline
- [ ] **Run**: `cd ../pypitui && uv run pytest tests/unit/test_tui_public_api.py::test_tui_render_frame_renders_root_component -v`

- [ ] **Test**: `test_tui_render_frame_composites_visible_overlays()` — overlays are included in the public render path in their documented order
- [ ] **Implement**: ensure `render_frame()` composites visible overlays using the same public runtime model described in `LLMS.md`
- [ ] **Run**: `cd ../pypitui && uv run pytest tests/unit/test_tui_public_api.py::test_tui_render_frame_composites_visible_overlays -v`

### Component: Downstream Alfred smoke contract

- [ ] **Test**: `test_alfred_can_import_supported_pypitui_runtime_symbols()` — Alfred can import the agreed runtime surface directly from `pypitui`
- [ ] **Implement**: align the exported surface and Alfred-side imports so the smoke contract passes without Alfred compatibility aliases
- [ ] **Run**: `uv run pytest tests/test_pypitui_v2_contract.py::test_alfred_can_import_supported_pypitui_runtime_symbols -v`

- [ ] **Test**: `test_minimal_pypitui_runtime_smoke_for_alfred_use_case()` — a minimal Alfred-shaped runtime can create a TUI, render a frame, and query terminal size using the public API only
- [ ] **Implement**: finish any remaining library-side runtime gaps required for the minimal downstream smoke case
- [ ] **Run**: `uv run pytest tests/test_pypitui_v2_contract.py::test_minimal_pypitui_runtime_smoke_for_alfred_use_case -v`

---

## Files to Modify

### PyPiTUI subproject
1. `../pypitui/src/pypitui/__init__.py` — public exports
2. `../pypitui/src/pypitui/terminal.py` — public terminal size API
3. `../pypitui/src/pypitui/mock_terminal.py` — downstream test terminal contract
4. `../pypitui/src/pypitui/tui.py` — public render loop method
5. `../pypitui/tests/unit/test_terminal_api.py` — new terminal API tests
6. `../pypitui/tests/unit/test_tui_public_api.py` — new public render loop tests

### Alfred
7. `tests/test_pypitui_v2_contract.py` — downstream smoke contract for the supported runtime surface
8. `src/alfred/interfaces/pypitui/tui.py` — import surface adjustment only if needed for the smoke contract

---

## Commit Strategy

Each completed checkbox should be treated as one atomic change with a test-first cycle:
- `test(pypitui): verify mock terminal export`
- `feat(pypitui): add terminal size api`
- `feat(pypitui): add public render_frame`
- `test(alfred): verify pypitui runtime contract`

Do not batch multiple runtime-surface changes into one commit.

---

## Exit Criteria for Milestone 1

- PyPiTUI exposes the minimum supported public runtime surface Alfred needs to target directly
- Alfred can import and exercise that surface without compatibility shims
- No downstream code needs to reach into private PyPiTUI modules for core runtime behavior
- Milestone 2 can proceed with docs/examples alignment on top of the now-stable runtime contract
