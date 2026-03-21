# PRD: PyPiTUI v2 Adoption and Alfred Runtime Rewrite

**Status**: Draft
**Priority**: High
**Created**: 2026-03-21
**Issue**: [#140](https://github.com/jeremysball/alfred/issues/140)

---

## Summary

Make **PyPiTUI v2** genuinely usable as a runtime library and test surface, then rewrite Alfred’s interactive CLI to consume that real PyPiTUI API **end-to-end**.

This PRD covers **both codebases**:
- **PyPiTUI** as a tracked subproject dependency for Alfred
- **Alfred** as the application that must consume PyPiTUI directly

The result should be one coherent system:
- PyPiTUI exposes a stable, documented, tested runtime API
- Alfred uses that API directly for its full interactive terminal runtime
- Alfred keeps only **thin, unavoidable application glue**, not a compatibility layer that re-implements the library

---

## Problem

Alfred’s current PyPiTUI integration has drifted away from the real library.

Current problems:
- Alfred imports stale or missing PyPiTUI symbols and behaviors
- PyPiTUI documentation, examples, exports, and implementation are not fully aligned
- test fixtures expect public library utilities that are not consistently exported
- Alfred carries library-shaped code that acts like a compatibility layer instead of consuming the library directly
- this drift is now blocking baseline verification, interactive runtime stability, and future CLI work

This is not just a bugfix. It is an architectural mismatch between the library Alfred wants to use and the library that actually exists.

---

## Goals

1. **Make PyPiTUI usable as a real runtime dependency** for Alfred and for its own test/examples/docs surface
2. **Rewrite Alfred’s interactive CLI runtime to use real PyPiTUI v2 APIs directly**
3. **Eliminate Alfred-side compatibility shims and wrapper-style backfills**
4. Keep only **thin, unavoidable Alfred-specific glue** where behavior is app-specific rather than library infrastructure
5. Restore a clean, verifiable baseline across docs, tests, type checking, and real terminal execution

---

## Non-Goals

- Preserve backward compatibility with stale Alfred or PyPiTUI APIs
- Maintain old examples or docs if they conflict with the actual runtime model
- Introduce a new abstraction layer in Alfred that hides PyPiTUI again
- Design a generic UI framework inside Alfred on top of PyPiTUI
- Delay architectural cleanup in order to preserve old imports or wrappers

Breaking changes are explicitly allowed in both PyPiTUI and Alfred where they improve coherence.

---

## Scope

### In Scope

#### PyPiTUI subproject work
- align public exports, implementation, docs, tests, and examples
- expose and validate the runtime primitives Alfred actually needs
- ensure testing utilities are public and stable enough for downstream consumers
- make the documented render loop, focus model, overlay model, terminal model, and test model internally consistent

#### Alfred work
- rewrite the interactive CLI runtime around the real PyPiTUI v2 API
- remove stale assumptions about the library surface
- remove or collapse Alfred-side PyPiTUI compatibility/wrapper code
- keep Alfred-specific code only where it encodes Alfred behavior, not missing library machinery
- verify that `uv run alfred` launches and works on the rewritten runtime

### Boundary Rule

**No Alfred-side library emulation layer.**

Allowed:
- thin Alfred-specific components or helpers for message formatting, command orchestration, and app behavior

Not allowed:
- Alfred-defined compatibility wrappers that recreate missing PyPiTUI runtime APIs under Alfred’s namespace
- preserving old Alfred code just to mask library drift

---

## Current State

### PyPiTUI
- public documentation and examples describe APIs or patterns that do not fully match the current source tree
- important test/runtime utilities are not consistently exported from the package surface
- downstream consumers cannot rely on the package surface as the source of truth

### Alfred
- the interactive TUI code assumes PyPiTUI APIs that are stale, missing, or changed
- parts of Alfred’s `src/alfred/interfaces/pypitui/` directory act as compensation for missing or mismatched library behavior
- the integration is brittle enough to break imports, tests, and baseline verification

---

## Target State

### PyPiTUI target state
PyPiTUI provides a coherent v2 runtime surface that is:
- documented
- exported publicly
- exercised by its own tests
- suitable for direct downstream use
- reflected accurately in `LLMS.md`, examples, and package exports

### Alfred target state
Alfred’s interactive CLI is a direct PyPiTUI application:
- one real PyPiTUI-driven runtime loop
- one real component tree
- one real focus/overlay/input/render model
- no Alfred-side API shim layer
- thin Alfred-specific logic only for Alfred concepts such as messages, commands, status, and tool-call presentation

### User-visible target state
When users run `uv run alfred`, they get:
- a working interactive PyPiTUI runtime
- native scrollback behavior
- streaming responses
- session commands and completion
- tool-call display
- overlays/toasts where needed
- clean Ctrl-C/exit behavior
- stable rendering and input handling

---

## Product Requirements

### 1. PyPiTUI must become the source of truth
The library must define one coherent public runtime model that Alfred can consume directly.

This includes:
- package exports matching actual supported APIs
- runtime behavior matching documentation
- examples matching real usage
- test utilities available to downstream consumers where needed

### 2. Alfred must use the real PyPiTUI API directly
Alfred must stop coding against stale or invented library behavior.

All interactive runtime responsibilities must be rebuilt around the actual PyPiTUI surface chosen in this effort.

### 3. Thin glue only
If Alfred keeps custom code, it must be clearly Alfred-specific.

Examples of acceptable thin glue:
- message formatting and role styling
- app-specific command dispatch
- token/status formatting
- app-specific tool-call presentation

Examples of unacceptable glue:
- Alfred wrappers that recreate or alias missing PyPiTUI runtime concepts
- Alfred-owned substitutes for library focus, overlay, terminal, or render-loop APIs

### 4. The whole interactive CLI runtime must be rewritten, not partially bridged
This effort targets Alfred’s **interactive terminal runtime as a whole**, not just a single screen.

That includes the runtime path for:
- chat input
- streaming output
- focus handling
- overlays
- completion
- session commands
- tool-call display
- status/toast behavior
- exit/interrupt handling

### 5. Verification must be complete
This work is not done until:
- lint passes
- type checking passes
- full pytest passes
- real terminal launch is verified
- PyPiTUI docs/examples are updated to match the shipped implementation

---

## Technical Requirements

### PyPiTUI Requirements
- define a stable public v2 runtime surface for Alfred’s needs
- export the runtime/testing symbols Alfred and its tests depend on
- make terminal behavior, render behavior, overlays, focus, and test fixtures internally coherent
- update `LLMS.md` and examples so they match the shipped source
- ensure package installation/editable usage reflects the same code Alfred is targeting

### Alfred Requirements
- refactor `src/alfred/interfaces/pypitui/` to consume the real PyPiTUI surface
- remove stale imports and assumptions
- delete wrapper-style code that exists only to compensate for library drift
- preserve Alfred features through direct PyPiTUI composition rather than library emulation
- keep any remaining custom code visibly app-specific and minimal

### Testing Requirements
- PyPiTUI must have unit/integration coverage for the runtime surface Alfred relies on
- Alfred must have tests covering behavior through its public interface
- TUI lifecycle bugs must be covered with behavior tests, not only direct method assertions
- MockTerminal-based tests should remain the default where appropriate
- real terminal verification is required before the work is considered complete

---

## Implementation Milestones

- [ ] **Milestone 1: PyPiTUI public runtime surface is coherent and usable**  
  Define and implement the public API Alfred will target, including exports, testing utilities, and runtime behaviors required for direct downstream use.

- [ ] **Milestone 2: PyPiTUI docs, examples, and tests match the actual v2 runtime**  
  Update `LLMS.md`, examples, and library tests so they describe and verify the same shipped behavior.

- [ ] **Milestone 3: Alfred runtime skeleton is rewritten on direct PyPiTUI APIs**  
  Replace stale assumptions with one direct runtime loop, one component tree, and one real PyPiTUI integration path.

- [ ] **Milestone 4: Alfred chat, streaming, focus, and scrollback behaviors are restored on the new runtime**  
  Ensure the core interaction model works cleanly under direct PyPiTUI usage.

- [ ] **Milestone 5: Alfred interactive features are ported end-to-end with thin app-specific glue only**  
  Port completion, overlays, session commands, tool-call display, status/toast behaviors, and interrupt handling without recreating library infrastructure inside Alfred.

- [ ] **Milestone 6: Legacy Alfred wrapper/compatibility code is deleted and the test baseline is repaired**  
  Remove obsolete files and imports, keep only thin Alfred-specific components, and restore passing verification across the codebase.

- [ ] **Milestone 7: Full verification and developer-facing documentation are complete**  
  Validate both codebases with tests and real terminal runs, and leave the docs/examples in a trustworthy state.

---

## Success Criteria

### Architecture
- [ ] PyPiTUI is the clear runtime source of truth for the Alfred CLI
- [ ] Alfred no longer depends on stale or undocumented PyPiTUI behavior
- [ ] Alfred retains no compatibility layer that emulates missing library APIs
- [ ] Remaining Alfred-specific UI code is thin, obvious, and app-specific

### Functionality
- [ ] `uv run alfred` launches successfully on the rewritten runtime
- [ ] Chat input, streaming, scrollback, overlays, completion, commands, and tool-call rendering work on the direct PyPiTUI integration
- [ ] Ctrl-C and runtime cleanup behave correctly

### Quality
- [ ] `uv run ruff check src/ tests/` passes in Alfred
- [ ] `uv run mypy --strict src/alfred` passes in Alfred
- [ ] `uv run pytest` passes in Alfred
- [ ] PyPiTUI’s own relevant test suite passes for the runtime surface Alfred uses
- [ ] real interactive terminal verification has been run successfully

### Documentation
- [ ] `LLMS.md` matches actual PyPiTUI behavior
- [ ] examples use the real supported runtime model
- [ ] Alfred’s implementation no longer depends on outdated migration guidance

---

## Validation Strategy

### PyPiTUI validation
- unit tests for the selected public runtime surface
- integration tests for render loop, focus, overlays, terminal behavior, and mock terminal behavior
- example/doc validation against the real implementation

### Alfred validation
- unit and integration tests for direct PyPiTUI usage
- behavior tests for lifecycle-sensitive TUI features
- full-project lint, types, and pytest verification
- real launch verification of `uv run alfred`

### Manual verification
- start Alfred in the terminal
- exercise message send/stream behavior
- verify focus and input behavior
- verify overlays/completion/commands
- verify exit and cleanup

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| PyPiTUI API remains ambiguous during rewrite | Alfred rewrite churn | lock one documented runtime surface first, then rewrite Alfred against it |
| Alfred feature regressions during wrapper removal | broken CLI behavior | milestone-by-milestone porting with behavior tests |
| docs drift again after implementation | future breakage | require docs/examples updates in the definition of done |
| editable/package install mismatch | false confidence in test results | verify package surface and downstream import path explicitly |
| interactive lifecycle bugs survive unit-only coverage | hangs/cleanup failures | require behavior tests and real terminal verification |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-21 | PRD covers both PyPiTUI and Alfred | The problem spans both the library and the app; solving only one side leaves the mismatch intact |
| 2026-03-21 | Treat PyPiTUI as a subproject dependency for planning | Alfred is the planning home, but the implementation must coordinate library and app changes together |
| 2026-03-21 | Allow only thin, unavoidable Alfred-specific glue | Alfred may keep app semantics, but must not recreate the library inside the app |
| 2026-03-21 | Breaking changes are allowed | Backward compatibility would preserve the wrong architecture |
| 2026-03-21 | Definition of done includes all verification layers | This rewrite is only valuable if the runtime, tests, and docs all converge |

---

## Related Documents

- `docs/pypitui-migration-guide.md`
- `docs/prds/done/94-migrate-to-pypitui.md`
- `docs/prds/done/95-pypitui-cli.md`
- `prds/137-pypitui-cruft-removal.md`
