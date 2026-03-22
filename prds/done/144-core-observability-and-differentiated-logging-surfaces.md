# PRD: Core Observability and Differentiated Logging Surfaces

**GitHub Issue**: [#144](https://github.com/jeremysball/alfred/issues/144)
**Status**: Complete
**Priority**: High
**Created**: 2026-03-21
**Last Updated**: 2026-03-21

---

## 1. Summary

Improve Alfred's day-to-day debuggability by doing two things together:

1. add richer **core instrumentation** across turn, context, LLM, tool, and storage lifecycles
2. make different **logging surfaces visually distinct** so it is immediately obvious whether a line came from core Alfred behavior or the Web UI stack

This PRD is intentionally **logs-only**. It does not introduce metrics pipelines, tracing systems, or external observability backends.

The primary user is the local operator/developer running Alfred and trying to answer questions like:
- what is Alfred doing right now?
- where did this log line come from?
- did the slowdown happen in context assembly, the LLM, tool execution, storage, or the Web UI transport?
- why did a long-running or streaming interaction fail?

---

## 2. Problem Statement

Alfred is increasingly multi-surface and long-lived:
- core request/turn handling
- LLM streaming
- tool execution
- storage and session persistence
- Web UI server behavior
- browser-side Web UI behavior

Today, debugging across those boundaries is harder than it should be.

### Current user pain

The current experience has **all of the following problems**:

1. **Hard to debug failures**
   - important lifecycle boundaries are not consistently logged
   - timing data is sparse or missing for many critical paths
   - when something is slow or broken, the logs do not clearly show where the time went

2. **Unclear source of log lines**
   - it is not visually obvious whether a message came from Alfred core, the Web UI server, or the browser client
   - related subsystems such as LLM, tools, and storage do not present a consistent surface identity

3. **Poor long-running visibility**
   - streaming turns, long tool calls, and multi-stage request flows are difficult to follow end-to-end
   - the Web UI has some focused diagnostics, but the core runtime lacks the same level of clarity

4. **Uneven control over logging surfaces**
   - logging controls do not cleanly express "core only" vs "Web UI only" vs "both" in a discoverable way
   - operators need more precise control when narrowing down failures

This is no longer a small ergonomics issue. It is an operational problem that slows down debugging, increases ambiguity, and makes regressions harder to isolate.

---

## 3. Goals & Success Criteria

### Goals

1. Establish a clear logging-surface model for Alfred.
2. Add rich instrumentation to the core runtime.
3. Preserve and align Web UI logging with the same surface model.
4. Make logs visually scannable in live terminal output.
5. Keep file logs unambiguous and grep-friendly.
6. Support separate logging controls for Alfred core and the Web UI.
7. Document how to enable and interpret the new logging surfaces.

### Success Criteria

- Running Alfred with core logging enabled produces meaningful lifecycle logs for:
  - turn start/end/failure/cancellation
  - context assembly and memory/session search
  - LLM request start, first-token, completion, retries, and failures
  - tool start, completion, failure, duration, and output volume
  - storage/persistence boundaries and slow/failing paths
- Web UI logs are clearly distinguishable from core logs at a glance.
- The Web UI browser/client surface remains distinguishable from the Web UI server surface.
- Root and Web UI logging can be enabled independently:
  - `uv run alfred --log debug webui`
  - `uv run alfred webui --log debug`
  - `uv run alfred --log debug webui --log debug`
- The logging system defaults to metadata-oriented diagnostics rather than dumping full user/assistant content.
- README and debugging docs explain how to use the new logging surfaces effectively.

---

## 4. Current-State Audit

The current codebase already contains some logging and some Web UI diagnostics, but the picture is uneven.

### 4.1 Core runtime logging exists, but it is ad hoc

`src/alfred/alfred.py`
- logs high-level events like message processing, memory loading, and agent-loop startup
- does not provide a consistently structured turn lifecycle
- does not clearly distinguish context, LLM, tool, and storage phases for a single turn

`src/alfred/agent.py`
- logs iteration count and some warning conditions
- does not emit explicit agent/turn lifecycle markers with durations
- does not provide strong observability for tool orchestration boundaries

`src/alfred/llm.py`
- logs retries, stream startup, and errors
- does not consistently expose first-token timing, full request duration, or a stable event vocabulary

`src/alfred/context.py`
- logs some context and budget details
- does not provide a full diagnostic story for context assembly stages, timing, and counts

`src/alfred/storage/sqlite.py`
- logs initialization and selected warnings/errors
- does not consistently emit observable timing and boundary events for normal operational flows

### 4.2 Web UI diagnostics are more intentional, but isolated

The Web UI already has debug-focused websocket diagnostics on the server/client side, especially around long streaming turns and disconnect debugging.

That is useful, but it creates a mismatch:
- Web UI transport has focused diagnostics
- Alfred core does not yet have equally rich lifecycle instrumentation
- surface identity is not yet unified across the full stack

### 4.3 Surface identity is inconsistent

Today, operators often infer the source of a log line from the logger name alone. That is not enough in live debugging.

What is missing:
- a stable surface taxonomy
- visually distinct console output
- consistent event naming across subsystems
- explicit guidance about when to use root logging vs Web UI logging

---

## 5. Proposed Solution

### 5.1 Define a logging surface taxonomy

Adopt a first-class surface model for observability.

Initial required surfaces:
- `core`
- `webui-server`
- `webui-client`
- `llm`
- `tools`
- `storage`

Principles:
- every new observability event should be attributable to one primary surface
- console output should make the surface visually obvious
- file logs should make the surface explicit and easy to grep/filter
- the taxonomy should be narrow enough to stay useful, not explode into dozens of tags

### 5.2 Separate core and Web UI logging controls

The CLI should support separate activation of root/core logging and Web UI-specific logging.

Target behavior:
- root `--log` controls Alfred/core logging
- `webui --log` controls Web UI-specific logging and browser-facing Web UI debug mode
- enabling both should be supported and unsurprising

This behavior should be documented as part of the user-facing debugging story.

### 5.3 Add richer core instrumentation

The core runtime should expose meaningful lifecycle visibility for the paths users/operators actually debug.

#### Turn lifecycle
Examples of desired event boundaries:
- turn received / started
- session selected or created
- context assembly started / completed
- agent loop started
- first assistant output observed
- turn completed
- turn failed
- turn cancelled

#### Context and memory/session retrieval
Examples of desired diagnostics:
- time spent assembling context
- memory search count and selected-result count
- session-history retrieval count
- token-budget summary
- overflow/truncation decisions when relevant

#### LLM lifecycle
Examples of desired diagnostics:
- request started
- provider/model used
- first-token latency
- completion latency
- retry attempt and retry reason
- failure category
- usage/tokens when available

#### Tool lifecycle
Examples of desired diagnostics:
- tool start
- tool completion / failure
- tool duration
- output size or chunk count
- tool surface clearly separated from generic core logs

#### Storage lifecycle
Examples of desired diagnostics:
- important persistence boundaries
- session/message writes
- slow query/write warnings
- store failures with enough context to identify the failing area

### 5.4 Visually differentiate surfaces in live console output

The console log experience should make it easy to visually scan a mixed stream of logs.

Desired characteristics:
- surface-prefixed log lines
- visually distinct presentation for at least `core`, `webui-server`, and `webui-client`
- consistent format across the whole runtime
- easy to read during a long streaming interaction

This PRD does not lock the exact colors or styling tokens, but it does require a clear, durable visual distinction rather than relying on logger module paths alone.

### 5.5 Keep file logs explicit and stable

Console output can optimize for readability, but file logs should remain stable and grep-friendly.

Desired characteristics:
- explicit surface identity in each relevant line
- consistent event names
- duration/count fields where relevant
- avoid formatting choices that make downstream inspection harder

### 5.6 Logs only, not metrics/tracing

This PRD intentionally stops at improved logging and instrumentation.

It does **not** include:
- metrics export
- Prometheus/OpenTelemetry integration
- distributed tracing
- external log shipping

The goal is to make Alfred dramatically easier to debug now without turning this into a full telemetry platform project.

### 5.7 Default to metadata over content

Instrumentation should help debugging without unnecessarily logging sensitive or noisy content.

Guidelines:
- prefer identifiers, counts, durations, token totals, output sizes, and categories
- avoid logging full user prompts or full assistant outputs unless the code path already does so intentionally and the use case is justified
- if content snippets are used, keep them short and deliberate

---

## 6. Likely Technical Changes

### Likely file changes

```text
src/alfred/cli/main.py                      # root vs webui logging control and documentation alignment
src/alfred/alfred.py                        # turn lifecycle instrumentation
src/alfred/agent.py                         # agent/tool orchestration instrumentation
src/alfred/llm.py                           # provider/request/stream instrumentation
src/alfred/context.py                       # context and retrieval instrumentation
src/alfred/storage/sqlite.py                # storage boundary and slow-path instrumentation
src/alfred/tools/__init__.py                # tool surface alignment, if needed
src/alfred/interfaces/webui/server.py       # align server logs with surface model
src/alfred/interfaces/webui/static/js/websocket-client.js  # align client debug surface model
src/alfred/interfaces/webui/static/js/main.js              # optional client-side surface plumbing
src/alfred/.../observability*.py            # optional shared helper/formatter module

README.md
/docs/...                                   # focused debugging/observability documentation

tests/test_cli_webui_logging.py
tests/test_*.py
tests/webui/test_*.py
```

### Implementation notes

- A shared logging helper or observability utility is likely preferable to hand-formatting events in every module.
- Surface differentiation should be centralized rather than reimplemented ad hoc in each subsystem.
- The event vocabulary should be stable and descriptive enough to support future extension.
- The implementation should avoid significant runtime overhead when debug logging is disabled.
- Web UI diagnostics should align with the same conceptual surface model used by the core runtime.

---

## 7. Milestones

### Milestone 1: Define the surface model and logging contract
Lock down the logging surface taxonomy, event naming conventions, and console/file formatting expectations.

Validation: surface identities and log contracts are documented and reflected in shared logging helpers.

### Milestone 2: Separate core and Web UI logging controls cleanly
Make root logging and Web UI logging independently configurable and document the behavior.

Validation: `alfred --log ...`, `alfred webui --log ...`, and both together behave as expected.

### Milestone 3: Instrument core turn and context lifecycle
Add meaningful logs around request/turn handling, session boundaries, context assembly, and memory/session retrieval.

Validation: a developer can follow a full turn through context preparation without guessing where time was spent.

### Milestone 4: Instrument LLM request/stream lifecycle
Add provider-level observability for request start, first token, completion, retries, usage, and failure paths.

Validation: a developer can distinguish prompt-build time from provider latency and stream latency.

### Milestone 5: Instrument tool and storage surfaces
Add lifecycle logs for tools and storage/persistence paths, including duration and failure visibility.

Validation: a developer can identify whether a slow/broken turn was caused by a tool or storage boundary.

### Milestone 6: Align Web UI server/client logs with the same surface model
Bring existing Web UI diagnostics under the same surface taxonomy and visual differentiation scheme.

Validation: mixed core/Web UI debugging sessions are visually readable and unambiguous.

### Milestone 7: Add tests and documentation
Add regression coverage for logging controls and representative instrumentation behavior, then document how to use the new system.

Validation: tests cover key logging-control behavior and the docs explain how to enable and interpret the main surfaces.

---

## 8. Validation Strategy

### Required checks
- `uv run pytest tests/test_cli_webui_logging.py -q`
- `uv run pytest tests/webui/test_websocket.py -q`
- `uv run pytest tests/webui/test_keepalive.py -q`
- targeted tests for core instrumentation modules
- `uv run ruff check src/ tests/`
- `uv run mypy --strict src/`
- `uv run pytest -m "not slow"`

### Runtime verification
- `uv run alfred --log debug`
- `uv run alfred webui --log debug`
- `uv run alfred --log debug webui --log debug`

### What success looks like
- A long-running turn can be followed across core and Web UI logs without guessing the source of each line.
- A slow request can be localized to context, LLM, tool, storage, or transport with ordinary debug logs.
- File logs remain understandable and grep-friendly.
- The system is more observable without becoming noisy by default.

---

## 9. Risks & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Logging becomes too noisy to be useful | High | Medium | keep the default focused, reserve rich detail for debug mode, and prefer lifecycle summaries over spammy per-token logs |
| Instrumentation leaks too much user content | High | Medium | default to metadata-oriented logs and avoid full content dumps by default |
| Surface taxonomy becomes inconsistent over time | Medium | Medium | centralize helpers and document required surfaces/event naming |
| Console differentiation is attractive but file logs become harder to parse | Medium | Low | keep file logs explicit and stable even if console logs are more visual |
| Debug instrumentation adds noticeable runtime overhead | Medium | Low | keep expensive formatting behind debug checks and prefer lightweight counters/timers |
| Core and Web UI evolve separate observability conventions again | High | Medium | define one shared surface model and apply it across both layers |

---

## 10. Non-Goals

- building a metrics backend
- adding tracing infrastructure
- integrating with external observability vendors
- redesigning every logger in the codebase in one sweep regardless of value
- creating a fully general telemetry framework before user-visible debugging gets better
- logging full user/assistant conversation content by default

---

## 11. Resolved Design Decisions

1. **This PRD is scope B**: logging UX plus richer core instrumentation.
2. **The feature is logs-only for now**: no metrics or tracing are required.
3. **Primary surfaces to differentiate are** `core`, `webui-server`, `webui-client`, `llm`, `tools`, and `storage`.
4. **The primary user is the local operator/developer** debugging Alfred in real time.
5. **Root and Web UI logging controls should remain separate** so debugging can be narrowed to one surface when needed.
6. **Documentation should include README updates and focused debugging guidance**, not just code changes.
