# PRD: Adaptive Support Profile and Intervention Learning

**GitHub Issue**: [#168](https://github.com/jeremysball/alfred/issues/168)  
**Priority**: High  
**Status**: In Progress  
**Created**: 2026-03-30

---

## 1. Problem Statement

Even with better operational memory, Alfred still lacks a durable model of **how to help** and **how to show up**.

Today, support behavior depends too much on:
- prompt wording
- model interpretation
- transient conversation context
- ad hoc tone rather than explicit runtime state

That creates six problems:

1. **Support style is too implicit**
   - Alfred can sound helpful without actually learning which interventions work.
   - Personalization is brittle because it lives mostly in prompts and recent context.

2. **Relational stance is too implicit**
   - Alfred is meant to feel like a friend, peer, and sometimes mentor or coach.
   - Without a structured relational model, those positions drift between turns and models.

3. **The system risks fake scaffolding**
   - If the runtime gathers context but still lets the LLM freely choose forcefulness, pacing, option count, and stance strength, the architecture becomes decorative.
   - The product needs runtime-owned policy resolution, not only model vibes.

4. **There is no clear split between product semantics and model phrasing**
   - Terms like warmth, candor, authority, challenge, companionship, and recommendation forcefulness are meaningful product concepts.
   - If the model invents their meaning at runtime, the system becomes inconsistent and hard to test.

5. **Adaptation is hard to audit**
   - If Alfred becomes more direct, more companion-like, or more structured over time, there is no durable, inspectable log of why that changed.

6. **The system risks mode explosion**
   - Diagnosis toggles or separate personas would be too blunt.
   - Alfred needs a general-purpose support system that adapts by context, evidence, and relationship rather than multiplying modes.

---

## 2. Goals

1. Create a **fixed, versioned registry of relational dimensions** for how Alfred shows up.
2. Create a **fixed, versioned registry of support dimensions** for how Alfred structures help.
3. Add **runtime policy resolvers** that choose effective values as composites of need, context, target, user state, patterns, and evidence.
4. Add a **behavior compiler** that converts effective runtime values into an explicit response contract for the model.
5. Make clear which parts of the contract are **runtime-owned policy** versus **LLM-owned realization**.
6. Store effective values by **global**, **context**, and **operational-arc** scope.
7. Log interventions, response signals, and outcome signals durably so Alfred can learn what works.
8. Allow bounded, evidence-backed adaptation without letting the model invent new production dimensions.
9. Keep adaptation general-purpose rather than tied to diagnosis-specific modes.
10. Make support and relational learning inspectable, reversible, and testable.
11. Treat documentation and managed prompt/template updates as part of feature completion so the model's runtime instructions reflect the support system explicitly.

---

## 3. Non-Goals

- Diagnosing conditions or inferring psychiatric states.
- Letting the LLM invent new production dimensions at runtime.
- Letting the LLM be the primary chooser of policy values like recommendation forcefulness.
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
- guardrails or incompatible combinations
- human-readable semantics for docs and explanation surfaces

The registries are product-owned and schema-versioned.

### 4.2 Product defines semantics; runtime resolves values; model realizes them

The model should not be asked to invent the behavioral meaning of dimensions at runtime.

Instead:
- the **product** defines what each dimension means behaviorally
- the **runtime** resolves effective values from current support conditions
- the **LLM** composes final language and tact inside that contract

This means:
- `recommendation_forcefulness = high` should already mean something concrete before the model speaks
- `option_bandwidth = single` should already mean Alfred is narrowing to one path rather than a menu
- `candor = high` should already mean fewer hedges and greater permission to name contradiction

Short version:

> runtime owns policy  
> model owns realization

### 4.3 Prefer discrete values for v1

V1 should use discrete values such as:
- `low` / `medium` / `high`
- `single` / `few` / `many`
- `minimal` / `short` / `full`
- `brisk` / `steady` / `slow`
- `light` / `medium` / `deep`

This is easier to explain, inspect, compare, and test than continuous floats.

### 4.4 Scope support and relational values

Values should support at least three scopes using one uniform scope object shape:

```json
{"type": "...", "id": "..."}
```

1. **Global**
   - broad defaults for the user
   - v1 representation: `{"type": "global", "id": "user"}`
2. **Context**
   - defaults for contexts such as `plan`, `execute`, `decide`, `review`, `identity_reflect`, `direction_reflect`
   - v1 should validate against this fixed taxonomy rather than accepting arbitrary strings
3. **Operational arc**
   - overrides for a specific active project, loop, or decision thread
   - `id` should be the concrete arc identifier

This keeps Alfred adaptive without forcing one stance or support style across every situation.

Important Milestone 1 boundary:
- the first milestone should define and validate scope shape and allowed IDs
- it should not yet implement runtime context inference from user messages or conversation state

### 4.5 Resolve effective values as composites

The runtime should choose values as **composites**, not as unconstrained LLM guesses.

Recommended resolver inputs:
- current need (`orient`, `resume`, `activate`, `decide`, `reflect`, `calibrate`)
- current context
- current target type (domain, arc, pattern-focused reflection)
- transient support state
- friction signals
- selected pattern objects
- explicit user ask
- evidence strength
- stakes and reversibility
- scope-specific learned support preferences

Pseudo-shape:

```text
effective_value =
  authored_default_by_need_and_context
+ adjustment_from_scope_specific_learning
+ adjustment_from_transient_state
+ adjustment_from_pattern_match
+ adjustment_from_evidence_strength
- adjustment_from_ambiguity_or_risk
```

Then clamp to the dimension's allowed values.

Important examples:
- `recommendation_forcefulness` should usually increase for activation and option-paralysis situations, but decrease when stakes are high and ambiguity is unresolved
- `option_bandwidth` should usually contract when overwhelm or initiation friction is high
- `candor` should increase when calibration is invited and trust is strong, but soften when the moment requires containment rather than pressure

### 4.6 Add a behavior compiler

The runtime should compile effective values into a compact response contract for the model.

The contract should state things like:
- how direct Alfred should be
- how many options to give
- how much structure to give
- whether to recommend or merely frame
- whether to challenge a contradiction if present
- how much emotional presence to bring
- how much momentum pressure to bring
- whether to surface evidence explicitly

Example contract:
- need: `activate`
- context: `execute`
- option bandwidth: `single`
- recommendation forcefulness: `high`
- planning granularity: `minimal`
- candor: `medium`
- companionship: `high`
- momentum pressure: `medium`
- evidence mode: `light`

The model remains responsible for natural expression, tact, and language-level composition inside that contract.

### 4.7 Behavior compiler policy table

The table below defines the main compiled fields, their default starting values by session-start type, the inputs that can adjust them, and the division of ownership between runtime and model.

Start-type shorthand:
- `op` = scoped operational start
- `orient` = broad orient start
- `reflect` = reflective start
- `cal` = calibration start

| Field | Type | Allowed values | Default by start type | Composite adjustment inputs | Runtime-owned decision | LLM-owned freedom |
|---|---|---|---|---|---|---|
| `planning_granularity` | support | `minimal`, `short`, `full` | `op=minimal; orient=short; reflect=minimal; cal=minimal` | task complexity, clarity, activation, ambiguity, support-preference patterns | choose granularity band | phrase the structure naturally |
| `option_bandwidth` | support | `single`, `few`, `many` | `op=single; orient=few; reflect=few; cal=single` | overwhelm, option paralysis, explicit ask for brainstorming, recurring-blocker patterns | cap how many real options Alfred should give | choose exact wording/order of options |
| `proactivity_level` | support | `low`, `medium`, `high` | `contract=medium; start-type policy deferred in Milestone 1` | task initiation friction, explicit ask for push, user appetite for initiative, support-preference patterns | choose how much initiative Alfred should take without waiting | decide how that initiative is phrased |
| `accountability_style` | support | `light`, `medium`, `firm` | `contract=medium; start-type policy deferred in Milestone 1` | user appetite for challenge, shame risk, commitment strength, correction history | choose how explicitly Alfred should hold the line | phrase accountability without breaking trust |
| `recovery_style` | support | `gentle`, `steady`, `directive` | `contract=steady; start-type policy deferred in Milestone 1` | overload, missed intentions, shame risk, urgency, recovery needs | choose how Alfred should help the user recover after slips or overload | realize recovery in natural language |
| `recommendation_forcefulness` | support | `low`, `medium`, `high` | `op=high; orient=medium; reflect=low; cal=medium` | explicit ask for recommendation, reversibility, stakes, ambiguity, support-preference patterns | decide whether Alfred should softly frame, lean, or clearly recommend | express the recommendation with tact |
| `reflection_depth` | support | `light`, `medium`, `deep` | `op=light; orient=light; reflect=deep; cal=medium` | user appetite, current strain, identity/direction relevance, time pressure | decide how far inward Alfred should go | choose specific reflective phrasing |
| `pacing` | support | `brisk`, `steady`, `slow` | `op=brisk; orient=steady; reflect=slow; cal=steady` | transient load, urgency, recovery needs, resistance, conversation tempo | choose pacing band | sentence cadence, paragraph shape |
| `warmth` | relational | `low`, `medium`, `high` | `op=medium; orient=high; reflect=high; cal=medium` | explicit emotional need, user state, trust, current tenderness of subject | set warmth target | how warmth sounds in language |
| `companionship` | relational | `low`, `medium`, `high` | `op=medium; orient=high; reflect=high; cal=medium` | loneliness/fog, need for steadiness, reflective depth, support-preference patterns | decide how strongly beside-the-user Alfred should feel | with-you wording and tone |
| `candor` | relational | `low`, `medium`, `high` | `op=medium; orient=medium; reflect=high; cal=high` | calibration invitation, contradiction strength, correction history, fragility of moment | decide how directly Alfred may name tensions or contradictions | choose exact bluntness and phrasing |
| `analytical_depth` | relational | `low`, `medium`, `high` | `op=medium; orient=medium; reflect=high; cal=high` | complexity, reflection/cali mode, evidence density, user ask for analysis | choose how much explicit reasoning to show | wording and sequencing of analysis |
| `momentum_pressure` | relational | `low`, `medium`, `high` | `op=medium; orient=low; reflect=low; cal=low` | initiation friction, urgency, shame risk, recovery style, whether motion is actually the goal | decide how much push toward movement is appropriate | how pressure is expressed without breaking rapport |
| `evidence_mode` | compiler-only | `none`, `light`, `explicit`, `structured` | `op=light; orient=light; reflect=light; cal=structured` | calibration relevance, confidence, identity-risk, explicit ask for evidence | decide whether Alfred must show evidence or observation→interpretation→recommendation structure | weave evidence into natural language |
| `intervention_family` | compiler-only | `orient`, `summarize`, `narrow`, `sequence`, `recommend`, `mirror`, `compare`, `challenge`, `reset`, `confirm` | `op=narrow/recommend; orient=orient/summarize; reflect=mirror/compare; cal=compare/challenge` | need, target type, top patterns, friction, outcome history | choose the family of move Alfred should make next | choose exact phrasing and micro-ordering inside the move |

Milestone 1 implementation note:
- the typed support-profile contract stores one neutral `default_value` per dimension for validation and persistence readiness
- start-type-specific defaults remain a later runtime-policy concern and are not yet encoded in the Milestone 1 dataclass registry

Important rule:
- the runtime chooses the band or family
- the model chooses how to **realize** that choice naturally
- the model does **not** freely replace a runtime-chosen `single` with a six-option menu or a runtime-chosen `high` recommendation with total neutrality

### 4.8 Support-preference and blocker patterns should materially shape behavior

Patterns should not just decorate language.

Operationally important pattern kinds should directly affect compiled values.

In operational starts, load priority should favor:
1. `support_preference`
2. `recurring_blocker`
3. `calibration_gap` when contradiction is immediately relevant
4. `identity_theme`
5. `direction_theme`

Examples:
- `support_preference: narrower next steps work better than menus` should usually lower `option_bandwidth`
- `recurring_blocker: ambiguity stalls starts` should usually lower `planning_granularity` and increase preference for `narrow`
- `support_preference: candid peer framing works better than authority-heavy advice` should change stance values, not just copywriting

### 4.9 Add an intervention log at the episode level

Every meaningful support attempt should be logged against the episode in which it happened.

Minimum v1 intervention fields:
- `intervention_id`
- `episode_id`
- `timestamp`
- `context`
- `arc_id` when applicable
- `intervention_type`
- `relational_values_applied`
- `support_values_applied`
- `behavior_contract_summary`
- `user_response_signals`
- `outcome_signals`
- `evidence_refs`

Intervention evidence refs should reuse the support-memory provenance contract rather than untyped string IDs.

Important dependency update:
- Milestone 3 now depends on the PRD #167 transcript-normalization addendum
- same-session transcript provenance should use canonical `(session_id, message_id)` rows
- intervention evidence should point to first-class message-ID spans rather than raw string arrays

Example:

```json
{
  "intervention_id": "int_55",
  "episode_id": "ep_204",
  "context": "execute",
  "arc_id": "webui_cleanup",
  "intervention_type": "narrow_next_step",
  "relational_values_applied": {
    "companionship": "medium",
    "candor": "medium",
    "momentum_pressure": "medium"
  },
  "support_values_applied": {
    "planning_granularity": "minimal",
    "option_bandwidth": "single",
    "recommendation_forcefulness": "high"
  },
  "behavior_contract_summary": "Keep this narrow, recommend one next move, do not open a planning tree.",
  "user_response_signals": ["resonance", "commitment"],
  "outcome_signals": ["next_step_chosen"],
  "evidence_refs": [
    {
      "session_id": "sess_812",
      "message_start_id": "msg_445",
      "message_end_id": "msg_446"
    },
    {
      "session_id": "sess_812",
      "message_start_id": "msg_448",
      "message_end_id": "msg_448"
    }
  ]
}
```

### 4.10 Add durable support-profile records

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
  "schema_version": 1,
  "registry": "support",
  "dimension": "option_bandwidth",
  "scope": {"type": "context", "id": "execute"},
  "value": "single",
  "status": "observed",
  "confidence": 0.87,
  "source": "auto_adapted",
  "created_at": "2026-03-30T10:05:00+00:00",
  "updated_at": "2026-03-30T10:08:00+00:00",
  "evidence_refs": ["int_55", "int_61", "int_64"]
}
```

### 4.11 Add a stance summary derived from relational values

The system should retain explicit stance labels for explanation and readability:
- friend
- peer
- mentor
- coach
- analyst

However, these should be derived summaries from effective relational values, not top-level settings.

That means the runtime can resolve something like:
- peer/coach blend in `execute`
- peer/analyst blend in `review`
- friend/mentor blend in `direction_reflect`

This gives the user and docs readable language without collapsing back into persona modes.

### 4.12 Bound adaptation by scope and truth class

Auto-adaptation is allowed, but must be constrained.

Recommended rules:
- **arc-scoped** values can adapt fastest
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

### 4.13 Runtime application

At runtime, Alfred should:
1. infer the current need and context
2. load relevant domain/arc support values
3. load relevant domain/arc relational values
4. load high-priority patterns that can change the next move
5. resolve the most specific effective values first
6. derive a stance summary
7. compile a behavior contract
8. constrain intervention and response generation accordingly
9. log interventions and resulting signals

This turns support memory into an explicit control plane rather than a prompt-only behavior.

### 4.14 Shadow observations remain allowed for research

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
- does not feel mechanically scripted even though runtime policy is structured underneath

Examples:
- use one-step prompts in `execute`
- use richer tradeoff framing in `decide`
- use deeper, more candid interpretation in `direction_reflect`
- use a more companion-like tone during identity reflection
- use explicit evidence structure when making a stronger calibration claim

---

## 6. Success Criteria

- [x] Alfred stores relational and support values using fixed, versioned registries.
- [x] Runtime values can be scoped globally, by context, and by operational arc.
- [ ] The runtime resolves policy values as composites instead of leaving them to raw LLM choice.
- [ ] Alfred compiles explicit response contracts before generation.
- [x] Alfred logs interventions, response signals, and outcome signals durably.
- [ ] Alfred can auto-adapt low-risk scoped values and log every change.
- [ ] Global support and relational changes are surfaced or reviewable.
- [ ] Runtime support behavior is driven by structured state rather than prompt wording alone.
- [ ] The system can explain both what it changed and why.
- [ ] The model remains free to phrase naturally without becoming the primary owner of policy.

---

## 7. Milestones

### Milestone 1: Define the relational and support registries
Implement the versioned schemas, allowed values, defaults, and scope rules for one uniform scope object.
This milestone defines and validates the contract only; it does not infer contexts yet.

Progress update (2026-03-30): completed in `src/alfred/memory/support_profile.py`, `src/alfred/memory/__init__.py`, `tests/test_support_profile.py`, and `prds/execution-plan-168-milestone1.md`. The delivered contract covers scope validation, the versioned registry catalog, relational and support registry definitions, typed scoped value validation, and public memory re-exports. Broader success criteria remain open until later milestones add storage, runtime resolution, compiler behavior, and adaptation.

Validation: targeted tests prove invalid dimensions, invalid values, invalid scope shapes, and invalid context IDs are rejected, while valid global, context, and arc-scoped records are accepted.

### Milestone 2: Add profile storage and effective-value retrieval
Implement durable storage for scoped relational/support values, confidence, status, source, and evidence refs.

Progress update (2026-03-30): completed in `src/alfred/memory/support_profile.py`, `src/alfred/storage/sqlite.py`, `tests/test_support_profile.py`, `tests/storage/test_support_profile_storage.py`, and `prds/execution-plan-168-milestone2.md`. The delivered storage layer extends `SupportProfileValue` with `schema_version`, `created_at`, `updated_at`, and `to_record()` / `from_record()` helpers, persists scoped values in SQLite with explicit `scope_type` / `scope_id` columns, and resolves the most specific stored value by arc → context → global precedence. Broader success criteria remain open until later milestones add composite policy resolution, behavior compilation, intervention logging, and adaptation.

Validation: targeted tests prove record round-tripping, SQLite round-tripping, and scope-precedence retrieval. `uv run pytest tests/test_support_profile.py tests/storage/test_support_profile_storage.py -v`, `uv run ruff check src/ tests/test_support_profile.py tests/storage/test_support_profile_storage.py`, and `uv run mypy --strict src/` passed.

### Milestone 3: Add episode-level intervention logging
Implement structured logging for interventions, response signals, and outcome signals tied back to context and evidence.

Prerequisite update (2026-03-30): before Milestone 3 begins, the PRD #167 transcript-normalization addendum must land so transcript messages are stored canonically by `(session_id, message_id)` and support-memory `EvidenceRef` spans use `message_start_id` / `message_end_id` instead of message indexes.

Progress update (2026-03-30): completed in `src/alfred/memory/support_memory.py`, `src/alfred/memory/__init__.py`, `src/alfred/storage/sqlite.py`, `tests/test_support_intervention.py`, `tests/storage/test_support_intervention_storage.py`, and `prds/execution-plan-168-milestone3.md`. The delivered intervention layer adds a typed `SupportIntervention` contract, lightweight same-session `SupportInterventionMessageRef` evidence spans, JSON-backed record helpers, SQLite persistence linked to support episodes, and query surfaces by episode, arc, context, and applied dimension. Broader success criteria remain open until later milestones add composite policy resolution, behavior compilation, and bounded adaptation.

Validation: targeted tests prove intervention events are stored consistently and can be queried by arc, context, and dimension. `uv run pytest tests/test_support_intervention.py tests/storage/test_support_intervention_storage.py -v`, `uv run ruff check src/ tests/test_support_intervention.py tests/storage/test_support_intervention_storage.py`, and `uv run mypy --strict src/` passed.

### Milestone 4: Add policy resolvers and the behavior compiler
Compile effective values into explicit response contracts and use those contracts at runtime.

Validation: targeted tests prove the compiled contract reflects the correct need, scope, patterns, and transient-state inputs in representative contexts.

### Milestone 5: Implement bounded adaptation
Add rules for automatic scoped updates, update-event logging, and stronger thresholds for broad changes.

Validation: targeted tests prove arc/context values can auto-update with evidence while broad changes remain surfaced and reversible.

### Milestone 6: Regression coverage, documentation, and prompt/template updates
Add or update tests, docs, and managed prompt/template content for the registries, compiler, and adaptation contract.

Validation: relevant Python validation passes, docs explain the runtime learning model clearly, and managed prompt/template content reflects the same registries and boundaries.

---

## 8. Likely File Changes

```text
src/alfred/memory/...                  # support-profile and intervention-log storage
src/alfred/context.py or orchestration # runtime application of compiled support values
src/alfred/session.py                  # intervention and outcome signal capture
src/alfred/orchestration/...           # policy resolvers and behavior compiler if introduced

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
| The runtime claims structure but still lets the model pick policy ad hoc | High | resolve values before generation and test compiled contracts directly |
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
- policy resolution rules
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
| 2026-03-30 | Product defines semantics; runtime resolves composite values; the model expresses them naturally | This keeps the system adaptive without semantic drift |
| 2026-03-30 | Scope runtime values globally, by context, and by operational arc | One user can need different help in different situations |
| 2026-03-30 | Use one uniform scope object shape and represent global scope as `{"type": "global", "id": "user"}` | This keeps storage, validation, and future UI/debug surfaces consistent without null special-casing |
| 2026-03-30 | Validate context-scoped values against the fixed v1 interaction taxonomy in Milestone 1 | The first milestone should lock the contract before runtime context inference work begins |
| 2026-03-30 | Use frozen dataclasses with `__post_init__` for Milestone 1 support-profile contracts | This matches the existing support-memory model style and keeps the first schema layer lightweight and explicit |
| 2026-03-30 | Log interventions at the episode level | Support learning needs local, contextual evidence |
| 2026-03-30 | Keep stance labels derived rather than primary runtime modes | Alfred should feel coherent without collapsing into persona switches |
| 2026-03-30 | Broad changes must stay reviewable and reversible | Adaptation should improve Alfred without becoming opaque |
| 2026-03-30 | Support-preference and recurring-blocker patterns should directly influence compiled behavior | Patterns should change the next move, not just the wording |
| 2026-03-30 | Use Option B support vocabularies for the missing v1 support dimensions | `proactivity_level` uses `low/medium/high`, `accountability_style` uses `light/medium/firm`, and `recovery_style` uses `gentle/steady/directive` so the support registry stays product-defined and explainable |
| 2026-03-30 | Store one neutral `default_value` per dimension in the Milestone 1 contract and defer start-type defaults to runtime policy | This keeps the dataclass registry lightweight and persistence-ready without prematurely encoding later runtime policy tables |
| 2026-03-30 | Reuse `SupportProfileValue` as the Milestone 2 persisted record contract and extend it with `schema_version`, `created_at`, `updated_at`, and `to_record()` / `from_record()` helpers | This keeps the storage boundary aligned with the typed support-profile model and the existing support-memory persistence style without introducing a second record type |
| 2026-03-30 | Normalize transcript provenance first under a PRD #167 addendum, then build Milestone 3 intervention logging on top of canonical `(session_id, message_id)` transcript rows and message-ID-based `EvidenceRef` spans | Intervention logging needs first-class evidence references and real same-session provenance guarantees rather than raw string IDs or message-index pointers |
| 2026-03-30 | Use lightweight same-session `SupportInterventionMessageRef` spans inside intervention logs instead of embedding full `EvidenceRef` records | Intervention logging needs typed transcript provenance without coupling each intervention record to the heavier promoted-evidence contract |
