# PRD: Generalized Semantic Runtime Substrate Contract and Ontology Projection Envelope

**Architecture Doc**: [docs/architecture/semantic-runtime-engine.md](../docs/architecture/semantic-runtime-engine.md)
**Related PRDs**: [#184 Support projection work on the semantic runtime engine](./184-semantic-adjudication-runtime-for-support-routing-and-learning.md), [#192 Relational projection work on the semantic runtime engine](./192-relational-runtime-semantics-and-stance-adjudication.md)
**GitHub Issue**: [#185](https://github.com/jeremysball/alfred/issues/185)
**Priority**: High
**Status**: Draft
**Created**: 2026-04-07
**Author**: Agent

---

## 1. Problem Statement

Alfred needs one shared semantic-runtime substrate contract.
Without it, every projection will invent its own perception envelope, validation rules, fallback behavior, and observability.

The repo currently has two opposing risks:

1. **support-shaped implementation could harden into architecture**
   - current support-domain artifacts are real, but they are not the generic substrate contract
   - if we let them define the shared model, future projections inherit one domain's nouns

2. **projection-specific seams could drift apart**
   - support and relational work already need similar model-facing perception primitives
   - if each projection rolls its own envelope and validators, the runtime will fork into mini-systems

3. **shared mechanics are still under-specified**
   - candidate adjudication and grounded observation extraction need one reusable contract
   - projection-specific meaning should plug into that contract rather than replace it

4. **observability and fallback need one truth**
   - runtime traces should be able to say what request ran, what projection participated, why output was accepted or rejected, and what fallback happened

This PRD defines the generic substrate contract that projection PRDs should reuse.
It is a downstream implementation/planning doc for the architecture, not the architecture itself.

---

## 2. Goals

1. Define one shared perception envelope for semantic-runtime calls.
2. Define one reusable ontology-projection contract.
3. Preserve the two shared model-facing primitives:
   - candidate adjudication
   - grounded observation extraction
4. Define one bounded deferred synthesis envelope for Pattern and ScopedValue proposals.
5. Make the execution split explicit: deterministic envelope assembly -> bounded semantic perception -> deferred synthesis when warranted -> deterministic policy application.
6. Centralize deterministic validation, fallback, and observability.
7. Keep the shared contract ontology-agnostic.
8. Let support, relational, and future projections plug into the same substrate cleanly.

---

## 3. Non-Goals

- Defining support or relational product semantics themselves.
- Choosing the final generalized durable schema for all future evidence/state records.
- Replacing current projection-specific stores in this PRD.
- Owning activation policy for a specific domain.
- Building one giant prompt that answers every semantic question at once.

---

## 4. Proposed Solution

### 4.1 Define one ontology-projection contract

Each projection should be able to register its semantics with the substrate through a bounded contract.

A projection contract should define at least:
- `projection_id`
- supported `request_kinds`
- candidate kinds or closed enums it may expose to candidate adjudication
- observation kinds it may expose to grounded extraction
- allowed pattern kinds
- allowed `ScopedValue` registries or dimensions
- allowed targets or registries
- projection-specific validation rules beyond shared validation
- deterministic interpretation rules after validation
- inspection/surfacing affordances that matter for that projection

Important rule:
- the substrate should not need support-specific or relational-specific nouns in order to run

### 4.2 Define one shared semantic perception envelope

Every semantic-runtime request should receive a structured envelope with only the fields it needs.
The envelope should support one **bounded perception pass** that can return candidate choices, grounded observations, or abstentions without requiring a separate call per seam.

Recommended top-level sections:
- `request_kind`
- `projection_ids`
- `message_context`
  - current user message
  - previous assistant reply when relevant
  - message ids when available
- `session_context`
  - fresh-session flag
  - session id when relevant
  - response mode when known
- `runtime_facts`
  - active operational context
  - effective projected state already loaded for the turn
  - retrieved evidence or history summaries when relevant
  - explicit user controls or confirmed truths when relevant
- `projection_inputs`
  - projection-specific state fragments or summaries
- `candidate_sets`
  - explicit ids or closed enums the model may choose from when candidate-based
- `allowed_observation_kinds`
  - projection-scoped observation kinds the model may emit
- `constraints`
  - max selections
  - abstain allowed
  - grounding required or optional
  - confidence required or optional
  - scope or target rules when relevant
  - inline vs deferred hint when relevant

The exact class names can change.
The contract shape should not depend on support-specific artifact names.

### 4.3 Use a perception-first execution split

The shared contract should assume four stages:
1. **deterministic envelope assembly**
   - code activates projections, bounds candidate sets and evidence, chooses validators, and precommits fallback
2. **bounded semantic perception pass**
   - the model acts as first-pass semantic perception over the bounded envelope
   - it may return candidate choices, grounded observations, and abstentions
3. **bounded deferred synthesis when warranted**
   - over validated bundles, the model may propose Pattern candidates, ScopedValue candidates, contradiction notes, and reflection proposals
4. **deterministic policy application**
   - code validates, activates, defers, persists, confirms Patterns, promotes ScopedValues, surfaces, or rejects the model output

This split keeps the model responsible for perception and bounded synthesis, not policy.

### 4.3A Define one concrete perception-result envelope

To avoid a mushy mixed payload, one bounded perception pass should return one structured result envelope with three top-level lanes:
- `candidate_decisions[]`
- `observations[]`
- `abstentions[]`

Important rule:
- semantic outcome signals belong inside `observations[]` as typed observation kinds
- they should not create a third freeform semantic lane

Recommended shared fields:
- every result item includes `request_kind`
- every result item includes `projection_id`

Recommended `candidate_decisions[]` fields:
- `decision_kind`
- `selected_ids` or closed-enum `decision`
- `ranked_alternatives` when allowed
- `confidence`
- optional `grounding_quotes`

Recommended `observations[]` fields:
- `kind`
- `target` when applicable
- `value` or `direction` when applicable
- `quote` or `quotes`
- `confidence`
- optional `scope`
- optional `source_refs`

Recommended `abstentions[]` fields:
- `abstain_reason`
- optional `blocked_on` such as `missing_candidates`, `weak_evidence`, `ambiguous_text`, or `out_of_scope`

Contract rules:
- empty arrays are allowed, but abstention should be explicit when the model considered a registered request kind and declined to decide
- semantic outcome signals must validate through the same observation validators as other grounded observations
- deterministic policy may accept, reject, defer, or ignore any returned item after validation

### 4.3B Define one deferred synthesis envelope

Per-turn perception is not the only model mode.
The shared contract should also support one bounded **deferred synthesis envelope** for introspection and reflection over validated bundles.

A deferred synthesis envelope may ask the model to return typed proposal objects in separate lanes:
- `pattern_candidates[]`
- `scoped_value_candidates[]`
- `reflection_candidates[]`
- `abstentions[]`

Here, `typed` means **schema-typed** proposal kinds, not a required implementation-specific class hierarchy.
The contract-level proposal kinds are:
- `PatternCandidate`
- `ScopedValueCandidate`
- `ReflectionCandidate`
- `Abstention`

Recommended `pattern_candidates[]` fields:
- `projection_id`
- `pattern_kind`
- `scope`
- `claim_summary`
- `supporting_evidence_refs`
- optional `contradicting_evidence_refs`
- optional `implied_scoped_values[]`
- `confidence`

Recommended `scoped_value_candidates[]` fields:
- `projection_id`
- `registry` or `dimension`
- `scope`
- proposed `value`
- `rationale_summary`
- `supporting_evidence_refs`
- optional `supporting_pattern_refs`
- `confidence`

Recommended `reflection_candidates[]` fields:
- `projection_id`
- `reflection_kind`
- `target_ref`
- `summary`
- `supporting_evidence_refs`
- `confidence`

Contract rules:
- deferred synthesis only runs on validated, bounded bundles
- typed proposal objects should stay in their own lanes rather than collapsing into one generic proposal blob
- each proposal kind should have a closed field set, projection-aware validators, and a deterministic lifecycle handler
- Pattern and ScopedValue proposals are never self-activating
- deterministic policy decides whether a Pattern becomes `candidate` or `confirmed`, and whether a ScopedValue becomes candidate, shadow, active, confirmed, rejected, or retired
- multiple bounded synthesis questions may share one deferred call when they use the same evidence packet and trust boundary

Implementation note:
- the repo may later represent these proposal kinds with dataclasses, Pydantic models, `TypedDict`s, or validated dictionaries
- this PRD cares about the closed contract shape, not the Python representation

### 4.4 Primitive A: candidate adjudication

Use this primitive when the runtime needs a bounded choice, ranking, or abstain over candidates.
A single bounded perception pass may emit candidate-adjudication results alongside grounded observations when the envelope explicitly allows both.

Examples:
- routing
- support need selection
- subject resolution
- pattern surfacing
- live relational-state selection
- stance delta selection
- explanation mode selection

Common output shape inside `candidate_decisions[]`:
- `decision` or typed enum
- `selected_ids` or typed refs when applicable
- `ranked_alternatives` when applicable
- `confidence`
- optional grounding refs or quotes when applicable

Abstention for candidate adjudication should be represented in `abstentions[]`, not as an ad hoc shape unique to this primitive.

Required conventions:
- enums must be closed
- ids must come from the supplied candidate set
- counts must respect the supplied max
- confidence must be numeric and bounded if present

### 4.5 Primitive B: grounded observation extraction

Use this primitive when the runtime needs zero or more typed observations from language or other bounded evidence.
A single bounded perception pass may emit grounded observations alongside candidate-adjudication results when the envelope explicitly allows both.

Examples:
- support preferences
- corrections
- interpretation rejection
- semantic outcome signals such as helpfulness, misunderstanding, repair, progress, or friction expressed in language
- relational preferences
- relational boundaries
- rupture signals
- future projection-specific signals

Common output shape inside `observations[]`:
- each observation may include:
  - `kind`
  - `target` when applicable
  - `value` or `direction` when applicable
  - `quote` or `quotes`
  - `confidence`
  - `scope` when applicable
  - source refs when applicable

Semantic outcome signals should use this same observation shape with closed observation kinds rather than a separate freeform payload.

Required conventions:
- observation kinds must be closed per projection
- targets must be valid when present
- quotes must be exact substrings of the source text when quote grounding is required
- confidence must be numeric and bounded if present

### 4.5A Keep deterministic outcomes separate from semantic outcome signals

The shared contract should preserve two outcome lanes:
- **deterministic outcomes** from structured system seams such as work-state transitions, explicit controls, and persisted state changes
- **semantic outcome signals** from language, extracted as grounded observations

The perception pass may emit semantic outcome signals.
It should not invent or overwrite deterministic outcomes already available from structured state.
Deterministic policy may combine both lanes later when deciding persistence, activation, surfacing, Pattern confirmation, or ScopedValue promotion.

### 4.5B Keep Pattern and ScopedValue first class, but distinct

The target architecture keeps both `Pattern` and `ScopedValue` as first-class durable runtime inputs.
They should not be collapsed into one artifact.

`Pattern` owns:
- recurring claims about what tends to happen
- candidate vs confirmed lifecycle
- support and contradiction tracking
- direct runtime influence once confirmed, plus explanation value

`ScopedValue` owns:
- actionable runtime parameters or constraints
- explicit scope such as global, context, or arc
- direct participation in effective runtime compilation

The shared contract should allow:
- deferred synthesis to propose both Pattern and ScopedValue candidates
- deterministic policy to confirm Patterns and promote ScopedValues independently
- one to support the other without forcing them to be identical

### 4.5C Define the Pattern lifecycle explicitly

Patterns should move through deterministic lifecycle steps.
At minimum, the shared contract should support:
- proposal from deferred synthesis
- promotion to `candidate`
- confirmation to `confirmed`
- rejection to `rejected`
- later retirement to `retired` when a once-useful pattern no longer applies

Promotion to `candidate` should require at least:
- valid pattern kind
- valid scope
- real supporting evidence refs
- dedupe or conflict checks against existing tracked patterns

Confirmation to `confirmed` may consider:
- explicit user confirmation
- repeated support across bounded bundles
- scope consistency
- support from semantic outcome signals and deterministic outcomes when relevant
- low contradiction rate
- successful review-surface confirmation

Once a Pattern is `confirmed`, deterministic runtime compilation should be able to use it as a real runtime input.

The model may propose a Pattern.
Only deterministic policy may store, confirm, reject, or retire it.

### 4.5D Define the ScopedValue promotion boundary explicitly

ScopedValues may be proposed from:
- repeated grounded observations
- explicit user corrections or controls
- deferred synthesis output
- confirmed Patterns that imply an actionable setting or constraint

The model may propose a ScopedValue candidate.
Only deterministic policy may decide whether it becomes candidate, shadow, active, confirmed, rejected, or retired.

### 4.6 Centralize deterministic validation

Validation should be code-owned and reusable across projections.

At minimum, shared validators should cover:
- enum membership
- candidate-id membership
- target validity
- max selected count
- quote grounding
- required field presence
- confidence range
- duplicate elimination
- fallback conversion when output is invalid

Projection-specific validators may add stricter checks.
They should not replace the shared base validators.

### 4.7 Define fallback policy explicitly

Every semantic-runtime request should define a safe fallback that does not require trusting malformed model output.

Examples:
- routing fallback: `none`
- need fallback: `unknown`
- subject fallback: empty selection
- observation fallback: zero observations
- pattern-surfacing fallback: surface nothing
- explanation fallback: `implicit`

Fallback must be deterministic and traceable.

### 4.8 Keep activation and persistence out of the primitives

The shared contract must preserve the repo-wide split:
- the model may perceive bounded candidate choices and grounded observations
- deterministic code validates, activates, persists, updates status, and surfaces state

This PRD does **not** own:
- domain semantics
- final activation rules
- precedence between explicit controls and inference
- durable schema choices for every future record type
- user-facing policy text

### 4.9 Add shared observability

Observability should record:
- request kind
- primitive kind
- projection ids
- model used
- request size and candidate counts
- validation result
- whether output was accepted, abstained, rejected, or fell back
- fallback path used when relevant

Optional debug traces may include sanitized request and raw response payloads when safe.

### 4.10 Provide a reusable test harness

The shared contract should make it easy to test projection seams with explicit fake model outputs.

The test harness should support:
- valid output acceptance
- invalid enum rejection
- invalid id rejection
- invalid target rejection
- bad quote rejection
- over-selection trimming or rejection
- fallback behavior
- observability assertions
- projection-specific validator assertions

---

## 5. User Experience Requirements

Even though this is infrastructure, the user-facing outcome matters.

The runtime should feel:
- more consistent across projections
- more semantically capable without being mushier
- safer when the model emits malformed or overreaching output
- easier to inspect when something falls back or gets rejected

Users should not experience each projection as a totally different semantic system.

---

## 6. Success Criteria

- [ ] A shared structured perception envelope exists for semantic-runtime requests.
- [ ] Projections can register candidate kinds, observation kinds, and validators without changing the substrate shape.
- [ ] Candidate-bound ids, target validation, quote grounding, and fallback behavior are standardized.
- [ ] The contract supports one bounded perception pass that returns a concrete result envelope with `candidate_decisions[]`, `observations[]`, and `abstentions[]` without one call per seam.
- [ ] The contract supports one bounded deferred synthesis pass that returns typed proposal objects in `pattern_candidates[]`, `scoped_value_candidates[]`, `reflection_candidates[]`, and `abstentions[]` over validated bundles.
- [ ] Semantic outcome signals are represented as typed observation kinds inside `observations[]`, not as a separate mushy payload.
- [ ] Deterministic outcomes from structured seams stay distinct from semantic outcome signals extracted from language.
- [ ] Patterns and ScopedValues remain first-class but distinct runtime inputs.
- [ ] Pattern promotion to `candidate` and confirmation to `confirmed` are deterministic policy steps, not model-owned actions.
- [ ] The shared contract stays ontology-agnostic.
- [ ] Tests can validate semantic-runtime seams without real model calls.
- [ ] Observability can explain accepted, rejected, abstained, and fallback outcomes.
- [ ] Support-specific implementation artifacts are not treated as the generic substrate contract.

---

## 7. Milestones

### Milestone 1: Define the projection contract and shared perception + synthesis envelopes
Define the substrate-facing types, sections, and projection registration hooks.
Make the deterministic-envelope / bounded-perception / bounded-synthesis / deterministic-policy split explicit.

Validation: support and relational PRDs can reference one substrate contract without re-explaining it, and the shared result envelopes are concrete enough to test without inventing projection-specific ad hoc payloads.

### Milestone 2: Implement shared validators, fallback helpers, and lifecycle gates
Build the reusable deterministic validation, fallback, Pattern-confirmation, and ScopedValue-promotion boundary layer.

Validation: projection seams can reject malformed output through shared helpers, and lifecycle transitions remain code-owned.

### Milestone 3: Add shared observability and test harness support
Make semantic-runtime calls traceable and testable across projections.

Validation: tests can assert acceptance, rejection, abstain, and fallback behavior without real model calls.

### Milestone 4: Align projection PRDs and docs
Update projection PRDs and architecture-adjacent docs so they reference this substrate contract correctly.

Validation: projection PRDs stop acting like parallel substrate docs.

---

## 8. Likely File Changes

```text
prds/185-shared-semantic-adjudication-contract-and-symbolic-runtime-inputs.md
docs/architecture/semantic-runtime-engine.md
docs/ARCHITECTURE.md
prds/184-semantic-adjudication-runtime-for-support-routing-and-learning.md
prds/192-relational-runtime-semantics-and-stance-adjudication.md
src/alfred/support_policy.py
src/alfred/support_reflection.py
src/alfred/interfaces/webui/server.py
tests/test_core_observability.py
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| The substrate contract becomes too generic to implement | High | make the projection contract explicit and keep envelope and result shapes closed |
| Projection PRDs keep re-inventing shared rules | High | keep validation, fallback, observability, and lifecycle rules centralized here |
| Current support-shaped implementation keeps leaking upward | High | treat support-specific artifacts as migration constraints, not substrate architecture |
| Patterns and ScopedValues blur together into one mushy artifact | Medium | keep their roles explicit: recurring claim vs actionable scoped parameter |
| Shared traces become noisy or unsafe | Medium | keep observability structured and sanitize optional debug payloads |

---

## 10. Open Questions

1. When should mixed turns use one bounded multi-projection perception pass versus several narrower requests?
2. When should one deferred synthesis pass cover both Pattern and ScopedValue proposals versus splitting them apart?
3. What is the smallest durable generalized record model that can replace or wrap today's projection-specific artifacts later?
4. How much projection-specific summary prose actually helps the model compared with structured fields alone?
