# PRD: Alfred Self-Model and Personality

**GitHub Issue**: [#147](https://github.com/jeremysball/alfred/issues/147)  
**Status**: Draft  
**Priority**: Medium  
**Created**: 2026-03-22

---

## 1. Problem Statement

Alfred is functional, but he still feels too generic.

He knows how to assemble context, call tools, and stream responses, but he does not yet maintain a strong enough internal model of:
- who he is as a system
- what surfaces and tools he has available
- what world state he is operating in
- how he should speak when he is being himself

That leaves two gaps:
1. **Personality gap** — Alfred sounds helpful, but not distinctly Alfred. He needs a sharper voice: more opinionated, more witty, more playful, without becoming noisy or fake.
2. **Self-model gap** — Alfred should understand his own runtime shape well enough to reason about himself as a system and describe his own constraints, tools, and environment accurately.

The goal is not to make Alfred theatrical. The goal is to make him feel like a coherent agent with an identity, a point of view, and a current state.

---

## 2. Goals & Success Criteria

### Goals

1. Give Alfred a stronger personality that is opinionated, witty, playful, and direct.
2. Teach Alfred a clearer internal self-model covering identity, capabilities, runtime mode, and environment.
3. Keep the self-model internal for now so it informs reasoning without becoming a separate user-facing surface.
4. Make `/context` able to show a compact note about Alfred’s current self state when asked.
5. Keep the model grounded in facts about Alfred’s actual runtime and architecture.

### Success Criteria

- Alfred speaks with a noticeably more distinct voice while still staying useful.
- Alfred can answer questions about his own system, tool access, and operating mode without sounding generic or self-contradictory.
- The self-model is available during context assembly and changes when runtime state changes.
- The self-model does not leak as a noisy block into ordinary user responses.
- `/context` can show a concise self-status summary for debugging and introspection.
- CLI and WebUI behavior stay consistent.
- Telegram remains deprecated and out of scope.

---

## 3. Proposed Solution

### 3.1 Strengthen the personality layer

Update Alfred’s personality guidance so the model is expected to sound more like a real character and less like a neutral assistant.

Desired traits:
- opinionated, but not contrarian for sport
- witty, but not quippy every turn
- playful, but not unserious when the situation is serious
- direct and low-friction
- self-aware without becoming corny about it

This should reshape how Alfred speaks, but not replace the existing behavioral rules that keep him grounded and honest.

### 3.2 Add an internal runtime self-model

Introduce a runtime self-model that describes Alfred’s current state and operating world.

The self-model should include facts such as:
- Alfred’s identity and role
- active interface or surface
- runtime mode and daemon state
- available tools and capabilities
- current session and context pressure
- memory/search availability
- template sync or startup issues
- other significant state Alfred should know about himself

This self-model should be assembled dynamically from runtime data rather than stored as a static personality paragraph.

### 3.3 Keep the self-model internal by default

The self-model should inform prompt assembly and reasoning, but it should not become a new default user-facing panel.

If surfaced at all, it should appear only as a compact diagnostic note in `/context` and similar inspection paths.

### 3.4 Make the self-model factual and fail-closed

The model should never be left guessing about its own state.

If runtime facts are missing:
- omit them
- mark them unknown
- do not invent a flattering story

The goal is grounded self-awareness, not hallucinated self-confidence.

### 3.5 Keep the character usable under stress

A more expressive personality should not get in the way of:
- clarity during debugging
- directness during failures
- concise answers when the user wants them
- safe behavior when the system is degraded

Personality should be an amplifier, not an obstruction.

---

## 4. Technical Implementation

### Likely file changes

```text
templates/SOUL.md                    # stronger personality guidance and voice rules
src/alfred/context.py                # inject runtime self-model into context assembly
src/alfred/context_display.py        # compact /context summary of self status
src/alfred/alfred.py                 # gather runtime facts used by the self-model
src/alfred/cli/main.py               # wire /context or related inspection behavior, if needed
src/alfred/interfaces/webui/server.py# share the same introspection data in WebUI context views, if needed

tests/test_context_integration.py
tests/test_system_md_integration.py
tests/test_templates.py
tests/webui/test_*.py
```

### Implementation notes

- The self-model should be built from real runtime state, not from a copied paragraph in a prompt file.
- The personality rewrite should be explicit enough that the model reliably changes tone.
- The runtime self-model should stay cheap to compute and easy to update.
- The user should not need to manually manage this feature.
- If the self-model cannot be built, Alfred should still run with a reduced but safe fallback.

---

## 5. Milestones

### Milestone 1: Define the self-model contract
Lock down the runtime facts Alfred should know about himself and the shape of the internal self-status block.

Validation: the contract is documented and stable enough to drive prompt assembly.

**Status**: ✅ Complete
- [x] Created `src/alfred/self_model.py` with Pydantic models
- [x] Implemented `build_runtime_self_model()` builder function
- [x] Added fail-closed handling with safe defaults
- [x] Added tests for schema, builder, and fallback behavior

### Milestone 2: Rewrite SOUL.md for a stronger voice
Update the personality guidance so Alfred reads as more opinionated, witty, playful, and self-possessed.

Validation: the new voice guidance is present in the template and reflected in behavior tests.

**Status**: ✅ Complete
- [x] Rewrote `templates/SOUL.md` with lean, essential personality guidance (~80 lines)
- [x] Sections: Who I Am, How I Speak, What I Do, My Self-Model, Personality Rules
- [x] Added `TestSOULmdPersonality` test validating structure

### Milestone 3: Build runtime self-state assembly
Collect runtime facts from the app, interface, session, tool, and context layers into a single self-model snapshot.

Validation: the snapshot is populated from actual runtime state and updates as state changes.

**Status**: ✅ Complete
- [x] Added `build_self_model()` method to Alfred class
- [x] Method imports and uses `build_runtime_self_model()` from self_model module
- [x] Added tests verifying method exists and returns correct type
- [x] Added test simulating build_self_model() usage with fake Alfred

### Milestone 4: Inject the self-model into context assembly
Feed the self-model into the prompt pipeline as an internal-only block.

Validation: Alfred has access to the self-model every turn without exposing a noisy block to the user.

**Status**: ✅ Complete
- [x] Extended `AssembledContext` model with `self_model: RuntimeSelfModel | None` field
- [x] Added `to_prompt_section()` method to `RuntimeSelfModel` for markdown serialization
- [x] Added `assemble_with_self_model(alfred)` method to `ContextLoader`
- [x] Updated `assemble_with_search()` to accept optional `alfred` parameter for self-model inclusion
- [x] Updated Alfred to use new assembly methods in both message processing paths
- [x] Added tests for prompt section serialization, daemon mode display, and tool list truncation

### Milestone 5: Surface a compact `/context` summary
Add a terse self-status note to the context inspection path so the user can inspect Alfred’s internal state when needed.

Validation: `/context` shows the self-model summary clearly and concisely.

### Milestone 6: Add safety and regression tests
Verify personality tone, internal-only behavior, and fail-closed self-model handling.

Validation: tests cover the prompt behavior and the inspection output.

### Milestone 7: Update documentation and examples
Document what Alfred now knows about himself and how to inspect that state.

Validation: docs explain the personality shift and the self-model boundary.

---

## 6. Validation Strategy

### Required checks
- `uv run pytest tests/test_templates.py tests/test_context_integration.py tests/test_system_md_integration.py -q`
- `uv run pytest tests/webui/test_integration.py tests/webui/test_server.py -q`
- `uv run pytest tests/test_context_observability.py tests/test_observability.py -q` if the new introspection path touches observability helpers
- `uv run ruff check src/ tests/`
- `uv run mypy --strict src/`
- `uv run pytest`
- `uv run alfred`
- `uv run alfred webui`

### What success looks like
- Alfred sounds more like a distinct character.
- Alfred can reason about his own runtime state without sounding vague.
- The self-model is present when needed and invisible when it should be.
- `/context` provides enough introspection to be useful without overwhelming the user.

---

## 7. Risks & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Personality becomes forced or annoying | Medium | Medium | keep the voice playful but not performative; avoid constant jokes |
| Self-model leaks into ordinary responses | Medium | Medium | keep the block internal and only expose a compact `/context` summary |
| Runtime facts become stale | Medium | Medium | rebuild the self-model from current state, not cached assumptions |
| The model starts roleplaying instead of reasoning | High | Medium | keep grounding rules strong and prefer facts over flourish |
| The feature expands into a broad redesign of all prompts | Medium | Low | limit scope to SOUL.md and the internal self-model pipeline |

---

## 8. Non-Goals

- a public self-dashboard or agent control panel
- changing Telegram behavior beyond its deprecation status
- adding a new user-facing personality mode selector
- exposing full internal runtime dumps in ordinary responses
- turning Alfred into a mascot instead of a system

---

## 9. Future Direction

If this lands well, the self-model can later be expanded to cover richer runtime context such as:
- better daemon awareness
- stronger world-state summaries
- selective introspection during debugging
- more nuanced self-description in `/context`

That future work should build on a stable internal contract rather than re-litigating the personality layer again.

---

## 10. Resolved Design Decisions

1. **Alfred should sound more opinionated, witty, and playful.**
2. **The runtime self-model is internal-only for now.**
3. **A compact `/context` summary is allowed.**
4. **The self-model must be grounded in real runtime state.**
5. **Telegram is deprecated and out of scope.**

---

## 11. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-22 | Make Alfred’s voice more opinionated, witty, and playful | The current voice is too generic for a system that is meant to feel distinct |
| 2026-03-22 | Add an internal runtime self-model | Alfred should know more about himself as a system and about his world |
| 2026-03-22 | Keep the self-model internal for now | Preserve a clean boundary between internal reasoning and user-facing output |
| 2026-03-22 | Surface only a compact note in `/context` | Introspection should be available without creating a new UI surface |
