# PRD: Adaptive Support Profile and Intervention Learning

**GitHub Issue**: [#168](https://github.com/jeremysball/alfred/issues/168)  
**Priority**: High  
**Status**: Draft  
**Created**: 2026-03-30

---

## 1. Problem Statement

Even with better operational memory, Alfred still lacks a durable model of **how to help** and **how to show up**.

Today, support behavior depends too much on:
- prompt wording
- model interpretation
- transient conversation context
- ad hoc tone rather than explicit runtime state

That creates five problems:

1. **Support style is too implicit**
   - Alfred can sound helpful without actually learning which interventions work.
   - Personalization is brittle because it lives mostly in prompts and recent context.

2. **Relational stance is too implicit**
   - Alfred is meant to feel like a friend, peer, and sometimes mentor or coach.
   - Without a structured relational model, those positions drift between turns and models.

3. **There is no clear split between product semantics and model phrasing**
   - Terms like warmth, candor, authority, challenge, or companionship are meaningful product concepts.
   - If the model invents their meaning at runtime, the system becomes inconsistent and hard to test.

4. **Adaptation is hard to audit**
   - If Alfred becomes more direct, more companion-like, or more structured over time, there is no durable, inspectable log of why that changed.

5. **The system risks mode explosion**
   - Diagnosis toggles or separate personas would be too blunt.
   - Alfred needs a general-purpose support system that adapts by context, evidence, and relationship rather than multiplying modes.

---

## 2. Goals

1. Create a **fixed, versioned registry of relational dimensions** for how Alfred shows up.
2. Create a **fixed, versioned registry of support dimensions** for how Alfred structures help.
3. Store effective values by **global**, **context**, and **project** scope.
4. Log interventions, response signals, and outcome signals durably so Alfred can learn what works.
5. Add a **behavior compiler** that converts effective runtime values into a response contract for the model.
6. Allow bounded, evidence-backed adaptation without letting the model invent new production dimensions.
7. Keep adaptation general-purpose rather than tied to diagnosis-specific modes.
8. Make support and relational learning inspectable, reversible, and testable.
9. Treat documentation and managed prompt/template updates as part of feature completion so the model's runtime instructions reflect the support system explicitly.

---

## 3. Non-Goals

- Diagnosing conditions or inferring psychiatric states.
- Letting the LLM invent new production dimensions at runtime.
- Building separate hard-coded friend, peer, mentor, coach, or analyst modes.
- Building the weekly reflection UX itself.
- Allowing unlimited or opaque personality drift.
- Replacing explicit user preferences with unreviewable model inference.

---

## 4. Proposed Solution

### 4.1 Add two fixed runtime registries

The product should distinguish between two registries.

#### Relational registry — how Alfred shows up
Recommended v1 dimensions:
- `warmth`
- `companionship`
- `candor`
- `challenge`
- `authority`
- `emotional_attunement`
- `analytical_depth`
- `momentum_pressure`

#### Support registry — how Alfred structures help
Recommended v1 dimensions:
- `planning_granularity`
- `option_bandwidth`
- `proactivity_level`
- `accountability_style`
- `recovery_style`
- `reflection_depth`
- `pacing`
- `recommendation_forcefulness`

The registries define:
- allowed values
- defaults
- valid scopes
- the behavioral surfaces each dimension controls
- any guardrails or incompatible combinations

The registries are product-owned and schema-versioned.

### 4.2 Product defines semantics; runtime learns values

The model should not be asked to invent the behavioral meaning of dimensions at runtime.

Instead:
- the **product** defines what each dimension means behaviorally
- the **runtime** learns which values work for this user, context, and project
- the **LLM** composes final language and judgment inside that contract

Examples:
- `candor = high` should have defined behavioral implications such as fewer hedges, clearer judgments, and permission to name contradiction
- `companionship = high` should have defined implications such as stronger with-you language, relational continuity, and more explicit presence
- `option_bandwidth = single` should mean Alfred narrows to one recommended path instead of generating a menu

This keeps the system consistent, testable, and portable across models.

### 4.3 Prefer discrete values for v1

V1 should use discrete values such as:
- `low` / `medium` / `high`
- `single` / `few` / `many`
- `light` / `medium` / `deep`

This is easier to explain, inspect, compare, and test than continuous floats.

### 4.4 Scope support and relational values

Values should support at least three scopes:

1. **Global**
   - broad defaults for the user
2. **Context**
   - defaults for contexts such as `plan`, `execute`, `decide`, `review`, `identity_reflect`, `direction_reflect`
3. **Project**
   - overrides for a specific active project, loop, or thread

This keeps Alfred adaptive without forcing one stance or support style across every situation.

### 4.5 Add an intervention log at the episode level

Every meaningful support attempt should be logged against the episode in which it happened.

Minimum v1 intervention fields:
- `intervention_id`
- `episode_id`
- `timestamp`
- `context`
- `project_id` when applicable
- `intervention_type`
- `relational_values_applied`
- `support_values_applied`
- `behavior_contract_summary`
- `user_response_signals`
- `outcome_signals`
- `evidence_refs`

Example:

```json
{
  "intervention_id": "int_55",
  "episode_id": "ep_204",
  "context": "direction_reflect",
  "project_id": "studio_strategy_2026",
  "intervention_type": "name_values_mismatch",
  "relational_values_applied": {
    "companionship": "high",
    "candor": "high",
    "authority": "medium"
  },
  "support_values_applied": {
    "reflection_depth": "deep",
    "option_bandwidth": "few",
    "recommendation_forcefulness": "medium"
  },
  "behavior_contract_summary": "Be clearly companion-like, offer a real point of view, name one likely mismatch, do not force action planning.",
  "user_response_signals": ["resonance", "deepening"],
  "outcome_signals": ["theme_clarified"],
  "evidence_refs": ["msg_445", "msg_448"]
}
```

### 4.6 Add durable support-profile records

Each learned value should include:
- registry type (`relational` or `support`)
- dimension
- scope
- value
- status (`observed`, `candidate`, `confirmed`)
- confidence
- source (`explicit`, `auto_adapted`, `corrected`, `imported`)
- evidence refs
- timestamps

Example:

```json
{
  "registry": "support",
  "dimension": "option_bandwidth",
  "scope": {"type": "context", "id": "execute"},
  "value": "single",
  "status": "observed",
  "confidence": 0.87,
  "source": "auto_adapted",
  "evidence_refs": ["int_55", "int_61", "int_64"]
}
```

### 4.7 Add a stance summary derived from relational values

The system should retain explicit stance labels for explanation and readability:
- friend
- peer
- mentor
- coach
- analyst

However, these should be derived summaries from effective relational values, not top-level settings.

That means the runtime can resolve something like:
- friend/mentor blend in `direction_reflect`
- coach/friend blend in `execute`
- peer/analyst blend in `review`

This gives the user and docs readable language without collapsing back into persona modes.

### 4.8 Add a behavior compiler

The runtime should compile effective relational and support values into a compact response contract for the model.

The contract should state things like:
- how direct Alfred should be
- how many options to give
- whether to recommend or merely frame
- whether to challenge a contradiction if present
- how much emotional presence to bring
- how much action bias to bring
- whether to convert reflection into an immediate next step

Example contract:
- be warm and clearly companion-like
- speak with high candor and medium authority
- name one likely contradiction if present
- give one directional hypothesis and one follow-up question
- do not turn this into a task plan unless the user asks

The model remains responsible for natural expression, tact, and language-level composition inside that contract.

### 4.9 Bound adaptation by scope and truth class

Auto-adaptation is allowed, but must be constrained.

Recommended rules:
- **project-scoped** values can adapt fastest
- **context-scoped** values require more evidence
- **global support values** require the strongest evidence and should be surfaced to the user
- **global relational values** should adapt cautiously and remain reviewable
- **identity and direction themes are not handled here as silent truth updates**; they remain candidate-first and belong in the reflection/control system
- every automatic change creates a durable update event with evidence and rationale
- all support-profile changes must be reversible

Example update event:

```json
{
  "event_type": "support_profile_update",
  "registry": "relational",
  "dimension": "candor",
  "scope": {"type": "context", "id": "direction_reflect"},
  "old_value": "medium",
  "new_value": "high",
  "reason": "Higher-candor direction reflection produced stronger resonance and deepening signals.",
  "confidence": 0.84
}
```

### 4.10 Runtime application

At runtime, Alfred should:
1. infer the current context
2. load relevant project/context/global support values
3. load relevant project/context/global relational values
4. resolve the most specific effective values first
5. derive a stance summary
6. compile a behavior contract
7. constrain intervention and response generation accordingly
8. log interventions and resulting signals

This turns support memory into an explicit control plane rather than a prompt-only behavior.

### 4.11 Shadow observations remain allowed for research

The LLM may emit freeform candidate observations for later product review, but those observations should not become production registries automatically.

This keeps a clean distinction between:
- production runtime schema
- future taxonomy research input

---

## 5. User Experience Requirements

Users should experience Alfred as a system that:
- adapts how it helps, not just what it remembers
- adapts how it shows up, not just what phrasing it happens to use
- behaves differently across contexts when that improves outcomes
- can explain why it is being more direct, more structured, or more companion-like in a given context
- does not require separate friend, mentor, or coach mode toggles

Examples:
- use one-step prompts in `execute`
- use richer tradeoff framing in `decide`
- use deeper, more candid interpretation in `direction_reflect`
- use a more companion-like tone during identity reflection
- reduce options when multi-choice prompts repeatedly underperform

---

## 6. Success Criteria

- [ ] Alfred stores relational and support values using fixed, versioned registries.
- [ ] Runtime values can be scoped globally, by context, and by project.
- [ ] Alfred logs interventions, response signals, and outcome signals durably.
- [ ] Alfred can auto-adapt low-risk scoped values and log every change.
- [ ] Global support and relational changes are surfaced or reviewable.
- [ ] Runtime support behavior is driven by structured state rather than prompt wording alone.
- [ ] The system can explain both what it changed and why.

---

## 7. Milestones

### Milestone 1: Define the relational and support registries
Implement the versioned schemas, allowed values, defaults, and scope rules.

Validation: targeted tests prove invalid dimensions or values are rejected and valid scoped records are accepted.

### Milestone 2: Add profile storage and effective-value retrieval
Implement durable storage for scoped relational/support values, confidence, status, source, and evidence refs.

Validation: targeted tests prove Alfred can resolve correct effective values across global, context, and project scopes.

### Milestone 3: Add episode-level intervention logging
Implement structured logging for interventions, response signals, and outcome signals tied back to context and evidence.

Validation: targeted tests prove intervention events are stored consistently and can be queried by project, context, and dimension.

### Milestone 4: Add the behavior compiler and runtime application
Compile effective values into explicit response contracts and use those contracts at runtime.

Validation: targeted tests prove runtime behavior contracts reflect the correct scoped values in representative contexts.

### Milestone 5: Implement bounded adaptation
Add rules for automatic scoped updates, update-event logging, and stronger thresholds for broad changes.

Validation: targeted tests prove project/context values can auto-update with evidence while broad changes remain surfaced and reversible.

### Milestone 6: Regression coverage, documentation, and prompt/template updates
Add or update tests, docs, and managed prompt/template content for the registries, behavior compiler, and adaptation contract.

Validation: relevant Python validation passes, docs explain the runtime learning model clearly, and managed prompt/template content reflects the same registries and boundaries.

---

## 8. Likely File Changes

```text
src/alfred/memory/...                  # support-profile and intervention-log storage
src/alfred/context.py or orchestration # runtime application of support values
src/alfred/session.py                  # intervention and outcome signal capture

docs/MEMORY.md
docs/ARCHITECTURE.md
docs/relational-support-model.md
templates/SYSTEM.md
templates/SOUL.md
templates/USER.md
prds/168-adaptive-support-profile-and-intervention-learning.md
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| The registries are too large or too abstract | Medium | start with a small set of behavior-changing dimensions only |
| The model starts inventing unsupported meanings for dimensions | High | keep production semantics product-owned and versioned |
| Adaptation becomes hard to trust | High | log every update with evidence, confidence, and reversibility |
| Context-specific adaptation leaks into all situations | Medium | support explicit scopes and test precedence rules |
| Relational richness collapses back into mode toggles | Medium | keep stance labels derived and explanatory rather than primary runtime settings |

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
- relational and support registries
- scope precedence
- behavior compiler semantics
- intervention logging
- auto-adaptation rules
- how managed instructions describe adaptation, explanation, and correction surfaces

---

## 11. Related PRDs

- PRD #167: Support Memory Foundation
- PRD #169: Reflection Reviews and Support Controls
- PRD #179: Relational Support Operating Model

---

## 12. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-30 | Use fixed, versioned relational and support registries | Runtime behavior must stay structured and testable |
| 2026-03-30 | Product defines semantics; runtime learns values; the model expresses them naturally | This keeps the system adaptive without semantic drift |
| 2026-03-30 | Scope runtime values globally, by context, and by project | One user can need different help in different situations |
| 2026-03-30 | Log interventions at the episode level | Support learning needs local, contextual evidence |
| 2026-03-30 | Keep stance labels derived rather than primary runtime modes | Alfred should feel coherent without collapsing into persona switches |
| 2026-03-30 | Broad changes must stay reviewable and reversible | Adaptation should improve Alfred without becoming opaque |
