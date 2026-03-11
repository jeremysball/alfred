# PRD: Unified Placeholder System

## 1. Problem Statement
Alfred currently uses disparate, fragmented systems for text templating and formatting placeholders across various domains. For instance, `src/placeholders.py` dictates ANSI color replacements and file includes (`{{file.md}}`), but contexts and interfaces (`src/context_display.py`, `src/interfaces/ansi.py`, `src/context.py`) each interact with them differently. This creates inconsistent styling configuration, blocks users from easily configuring UI elements dynamically via configuration options (e.g. mapping `throbber_color` to `cyan` in `config.toml`), and makes the codebase harder to maintain and extend.

## 2. Solution Overview
Refactor and centralize the placeholder system to be completely generic and unified.
1. Guarantee `src/placeholders.py` acts as the definitive engine for resolving templates application-wide.
2. Refactor the Context Builder and all dependent contexts to route through this singular unified mechanism.
3. Update Alfred's `config.toml` defaults and configuration loading to accept clean style names (like `cyan` or `bright_black` instead of explicit tags like `{cyan}`) for UI elements (Status line, Throbber). The system should automatically wrap user inputs in the placeholder syntax `{}` if missing before resolution. 
4. Implement clear, generic circular reference detection across all placeholder operations to prevent endless evaluation loops.

## 3. Dealing with Circular References
For file inclusion (`{{file.md}}`), the system already possesses a `ResolutionContext` that tracks visited paths in a set alongside recursion depth limits.

For a completely generic string placeholder system, we have two primary approaches to prevent evaluation loops (e.g., if a variable `{foo}` attempts to resolve to `{bar}`, and `{bar}` resolves back to `{foo}`):

1. **Max Recursion Depth (Recommended)**: Pass a `ResolutionContext` with a max depth (e.g., 5-10 iterations) on the overall resolution loop. If the resolver executes string substitutions across the text more times than the limit, it throws a safe fallback error or returns the raw remaining text. This is fast, stateless, and incredibly easy to maintain.
2. **Key Visit Sets**: Expand `ResolutionContext` to track specific evaluated string tokens (`{"foo", "bar"}`). If `{foo}` is substituted, add it to a visited `set()`. If the resolver encounters `{foo}` again during processing, it aborts or returns a literal token. This provides stricter tracing but requires more complex regex tracking on what tokens were triggered.

**Decision**: We will lean primarily on extending `ResolutionContext` utilizing the **Context Object Pattern** (specifically as a Parameter Object) with an overall pass/depth limit for generic variables to remain simple, fast, and robust across both files and strings. This pattern naturally bundles environmental state without polluting method signatures and isolates resolution state effectively.

## 4. Success Criteria
- [ ] No hardcoded ANSI string injections in component `__init__` functions that bypass formatting utilities.
- [ ] UI Component styles can be specified directly via `.toml` configuration properties using raw strings (e.g., `bright_black`, `cyan`).
- [ ] The generic resolver enforces circular dependency checks for all nested variables, not just file includes.
- [ ] The context builder outputs successfully utilize the updated generic placeholder resolver.
- [ ] Test coverage written/updated to verify circular dependency tracking and nested resolution capabilities.

## 5. Milestones & Implementation Plan
- [ ] **Milestone 1: Generic Resolver Validation & Circular Tracking** - Audit and ensure `src/placeholders.py` is capable of generic injection. Expand the `ResolutionContext` to support arbitrary nested string variable recursion limits.
- [ ] **Milestone 2: Context System Refactor** - Update `src/context.py` and `src/context_display.py` to route entirely through the centralized unified resolver.
- [ ] **Milestone 3: UI Configuration Support** - Extend `src/config.py` to expose UI style properties (`status_text_color`, `throbber_color`) expecting standard strings (`cyan`).
- [ ] **Milestone 4: Component Integration** - Modify components like `StatusLine` and `Throbber` to ingest config colors, automatically formatting them into `{color}` format and parsing via the unified module.
- [ ] **Milestone 5: Testing and Polish** - Refactor failing unit tests and ensure E2E placeholder resolution across all layers functions correctly.
