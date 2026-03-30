# PRD: Adaptive Support Profile and Intervention Learning

**GitHub Issue**: [#168](https://github.com/jeremysball/alfred/issues/168)  
**Priority**: High  
**Status**: Draft  
**Created**: 2026-03-30

---

## 1. Problem Statement

Even with better memory of content, Alfred still lacks a durable model of **how to help**.

Today, support behavior depends too much on:
- prompt wording
- model interpretation
- transient conversation context

That creates four problems:

1. **Support style is too implicit**
   - Alfred can sound helpful without actually learning which interventions work.
   - Personalization is brittle because it lives mostly in prompts and recent context.

2. **There is no structured user model for support behavior**
   - Alfred may remember facts about the user, but not reliable, scoped defaults for planning depth, option count, recovery style, or time scaffolding.

3. **Adaptation is hard to audit**
   - If Alfred becomes more directive or more reflective over time, there is no durable, inspectable log of why that changed.

4. **The system risks mode explosion**
   - A diagnosis-specific toggle such as "ADHD mode" would be too blunt.
   - Alfred needs a general-purpose support model that adapts by context and evidence.

---

## 2. Goals

1. Create a **fixed, versioned support-dimension taxonomy** for runtime personalization.
2. Store per-user support values by **global**, **context**, and **project** scope.
3. Log interventions and outcomes so Alfred can learn what support works.
4. Allow bounded **auto-adaptation** with evidence-backed updates.
5. Keep adaptation general-purpose rather than tied to diagnosis-specific modes.
6. Make support learning inspectable, reversible, and testable.
7. Treat **documentation and managed prompt/template updates** as part of feature completion so Alfred's runtime instructions reflect the support-profile model instead of leaving it implicit in code.

---

## 3. Non-Goals

- Diagnosing conditions or inferring psychiatric states.
- Letting the LLM invent new production support dimensions at runtime.
- Building the weekly reflection UX itself.
- Implementing unlimited or aggressive proactive behavior.
- Replacing explicit user preferences with opaque model inference.

---

## 4. Proposed Solution

### 4.1 Add a fixed support-dimension registry

Alfred should use a closed, versioned taxonomy of support dimensions.

For v1, the registry should include:
- `planning_granularity`
- `option_bandwidth`
- `prompt_shape`
- `time_scaffolding`
- `proactivity_level`
- `recovery_style`
- `accountability_style`
- `reflection_depth`

The registry defines:
- allowed values
- defaults
- valid scopes
- the runtime behaviors each dimension controls

The registry is product-owned and schema-versioned.

### 4.2 Learn runtime values, not runtime taxonomies

Alfred may learn a value for a known dimension.

It may not invent a new dimension during normal runtime.

That means:
- **compile-time / schema-time**: dimension keys and allowed values are fixed
- **runtime**: Alfred can update per-user values, confidence, evidence, and scope

### 4.3 Scope support values

Support values should support at least three scopes:

1. **Global**
   - broad defaults for the user
2. **Context**
   - defaults for interaction types such as `admin_task`, `planning`, `review`, `strategy_discussion`
3. **Project**
   - overrides for a specific active project or loop

This keeps Alfred adaptive without forcing one mode across every situation.

### 4.4 Add an intervention log

Every meaningful support attempt should be logged.

Minimum v1 intervention fields:
- `intervention_id`
- `timestamp`
- `scope`
- `context`
- `project_id` when applicable
- `intervention_type`
- `support_dimensions_applied`
- `prompt_variant` or structured action summary
- `user_response_signal`
- `outcome_signal`
- `evidence_refs`

Example:

```json
{
  "intervention_id": "int_55",
  "context": "admin_task",
  "project_id": "taxes_2026",
  "intervention_type": "first_physical_step",
  "support_dimensions_applied": {
    "planning_granularity": "micro",
    "option_bandwidth": "single",
    "time_scaffolding": "light"
  },
  "user_response_signal": "accepted",
  "outcome_signal": "started_in_session",
  "evidence_refs": ["msg_445", "obs_812"]
}
```

### 4.5 Add support-profile records

Each learned support value should include:
- dimension
- scope
- value
- status (`observed`, `candidate`, `confirmed`)
- confidence
- source (`explicit`, `auto_adapted`, `imported`)
- evidence refs
- timestamps

Example:

```json
{
  "dimension": "planning_granularity",
  "scope": {"type": "context", "id": "admin_task"},
  "value": "micro",
  "status": "observed",
  "confidence": 0.87,
  "source": "auto_adapted",
  "evidence_refs": ["int_55", "int_61", "int_64"]
}
```

### 4.6 Bounded auto-adaptation

Auto-adaptation is allowed, but must be constrained.

Recommended rules:
- **project-scoped** values can adapt fastest
- **context-scoped** values require more evidence
- **global** values require the strongest evidence and should be surfaced to the user
- every automatic change creates a durable update event with evidence and rationale
- all support-profile changes must be reversible

Example update event:

```json
{
  "event_type": "support_profile_update",
  "dimension": "option_bandwidth",
  "scope": {"type": "context", "id": "admin_task"},
  "old_value": "few",
  "new_value": "single",
  "reason": "single-option prompts produced higher acceptance and completion signals",
  "confidence": 0.84
}
```

### 4.7 Runtime application

At runtime, Alfred should:
1. infer the current context
2. load relevant project/context/global support values
3. apply the most specific relevant values first
4. constrain response generation and intervention options accordingly
5. log the intervention and resulting signals

This turns support memory into an explicit control plane rather than a prompt-only behavior.

### 4.8 Shadow observations are allowed for future taxonomy design

The LLM may emit freeform candidate observations for product review, but those do not become production support dimensions automatically.

This creates a safe distinction between:
- **runtime production schema**
- **future taxonomy research inputs**

---

## 5. User Experience Requirements

Users should experience Alfred as a system that:
- adapts how it helps, not just what it remembers
- behaves differently across contexts when that improves outcomes
- can explain why its support style changed
- does not require an explicit ADHD or executive-function mode toggle

Examples:
- use one-step plans for admin work
- use richer analysis in strategy conversations
- default to clean resets after drift
- reduce options when multi-choice prompts perform poorly

---

## 6. Success Criteria

- [ ] Alfred stores support-profile values using a fixed, versioned dimension taxonomy.
- [ ] Support-profile values can be scoped globally, by context, and by project.
- [ ] Alfred logs interventions and outcome signals durably.
- [ ] Alfred can auto-adapt low-risk scoped values and log every change.
- [ ] Global support-profile changes require stronger evidence and are surfaced for user review.
- [ ] Runtime support behavior is driven by structured support state rather than prompt wording alone.

---

## 7. Milestones

### Milestone 1: Define the support-dimension registry
Implement the versioned support-dimension schema, allowed values, defaults, and scope rules.

Validation: targeted tests prove invalid dimensions or values are rejected and valid scoped records are accepted.

### Milestone 2: Add support-profile storage and retrieval
Implement durable storage for scoped support values, confidence, status, source, and evidence refs.

Validation: targeted tests prove Alfred can read the correct effective support values across global, context, and project scopes.

### Milestone 3: Add intervention logging
Implement structured logging for interventions, response signals, and outcome signals tied back to context and evidence.

Validation: targeted tests prove intervention events are stored consistently and can be queried by project and context.

### Milestone 4: Implement bounded auto-adaptation
Add rules for automatic scoped updates, update-event logging, and stronger thresholds for global changes.

Validation: targeted tests prove project/context values can auto-update with evidence while global changes remain gated.

### Milestone 5: Drive runtime support behavior from the support profile
Update runtime orchestration so support dimensions actively constrain next-step generation, option count, recovery behavior, and other supported intervention choices.

Validation: targeted tests prove the runtime applies the right scoped values in representative contexts.

### Milestone 6: Regression coverage, documentation, and prompt/template updates
Add or update tests, architecture docs, and managed prompt/template content for the support-profile model, intervention log, and adaptation contract.

Validation: relevant Python validation passes, docs explain the runtime learning model clearly, and managed prompt/template content reflects the support dimensions, adaptation boundaries, and explanation surfaces consistently.

---

## 8. Likely File Changes

```text
src/alfred/memory/...                  # support-profile and intervention-log storage
src/alfred/context.py or orchestration # runtime application of support values
src/alfred/session.py                  # intervention and outcome signal capture

docs/MEMORY.md
docs/ARCHITECTURE.md
templates/SYSTEM.md
templates/AGENTS.md
templates/prompts/agents/memory-system.md
templates/prompts/boundaries.md
templates/prompts/voice.md
prds/168-adaptive-support-profile-and-intervention-learning.md
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| The taxonomy is too large or too abstract | Medium | start with a small registry of behavior-changing dimensions only |
| The LLM starts inventing unsupported traits | High | keep production dimensions fixed and versioned |
| Auto-adaptation becomes hard to trust | High | log every update with evidence, confidence, and reversibility |
| Context-specific adaptation leaks into all situations | Medium | support explicit scopes and test precedence rules |

---

## 10. Validation Strategy

This is a Python-led change.

Required validation:

```bash
uv run ruff check src/
uv run mypy --strict src/
uv run pytest <targeted tests for touched memory, orchestration, and support-profile surfaces>
```

Docs and prompt/template updates should cover:
- support-dimension registry
- scope precedence
- intervention logging
- auto-adaptation rules
- how managed instructions describe support adaptation, logging, and user-visible explanation of support changes

---

## 11. Related PRDs

- PRD #167: Support Memory Foundation
- PRD #169: Reflection Reviews and Support Controls

---

## 12. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-30 | Use a fixed, versioned support-dimension taxonomy | Runtime support behavior must stay structured and testable |
| 2026-03-30 | Learn dimension values at runtime, not new taxonomies | Alfred should adapt without letting the ontology drift |
| 2026-03-30 | Scope support values globally, by context, and by project | One user can need different support styles in different situations |
| 2026-03-30 | Log interventions and support-profile updates durably | Adaptation must be explainable and auditable |
| 2026-03-30 | Allow bounded auto-adaptation with stronger gates for global changes | Alfred should improve automatically without becoming opaque |
