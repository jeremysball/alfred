# PRD: Natural-Language Relational Preference and Boundary Extraction

**Parent PRD**: [#192 Relational Runtime Semantics and Stance Adjudication](./192-relational-runtime-semantics-and-stance-adjudication.md)  
**GitHub Issue**: [#196](https://github.com/jeremysball/alfred/issues/196)  
**Priority**: High  
**Status**: Draft  
**Created**: 2026-04-09  
**Author**: Agent

---

## 1. Problem Statement

Users express relational preferences and boundaries in ordinary language, but Alfred still lacks a dedicated, grounded path for extracting them.

Today, Alfred can:
- accept explicit correction flows through support controls
- learn some thin support signals
- rely on prompt interpretation when a user says something relationally important in normal conversation

That creates five problems:

1. **Relational learning signals are too easy to miss**
   - Users say things like “be more direct,” “don’t talk to me from above,” or “stay beside me here.”
   - Those are high-value runtime signals.
   - Alfred does not yet extract them through a dedicated lane.

2. **Generic support extraction is not enough**
   - Relational preferences and boundaries have sharper interaction consequences than ordinary help-shape preferences.
   - They deserve a more explicit relational ontology.

3. **Prompt-only interpretation is too mushy**
   - If Alfred only “kind of gets the vibe,” the runtime will drift instead of learning grounded, corrigible preferences.

4. **Relational misattunement needs a first-class correction path**
   - A user saying “that felt too harsh,” “don’t frame me that way,” or “you’re coming in too therapisty” is not noise.
   - It is important relational evidence.

5. **These signals should feed the shared learning model without bypassing it**
   - Relational extraction should create grounded observations.
   - It should not become a hidden direct-promotion engine.

This PRD adds a dedicated extraction seam for relational preferences, boundaries, stance feedback, and rupture signals.

---

## 2. Goals

1. Add a schema-constrained extraction path for relational observations from ordinary language.
2. Keep the relational observation ontology small, typed, and inspectable.
3. Require quote grounding and deterministic validation.
4. Feed validated relational observations into the shared learning model from PRD #183.
5. Preserve explicit support-control commands as stronger direct-control paths.

---

## 3. Non-Goals

- Replacing explicit `/support` actions.
- Promoting values or patterns directly from extracted observations.
- Turning every emotional utterance into a relational observation.
- Replacing the broader support-observation work in PRD #189 with an unrelated system.
- Letting the model invent unsupported claims about the user's relational needs.

---

## 4. Proposed Solution

### 4.1 Add a bounded relational observation extractor

For relevant turns, run one schema-constrained extractor focused on relational signals.

The extractor may return zero or more observations.

Recommended inputs:
- latest user message
- previous assistant reply when relevant
- current effective relational values when relevant
- current attempt or response context when available
- explicit constraints from the shared PRD #185 envelope

### 4.2 Keep the ontology small and relationally specific

Recommended initial observation kinds:
- `relational_preference`
- `relational_boundary`
- `stance_feedback`
- `rupture_signal`
- `meta_request`

#### `relational_preference`
The user expresses a positive preference for how Alfred should show up.

Examples:
- “Be more direct.”
- “Stay more peer-like with me.”
- “I want you to push a little harder on avoidance.”

#### `relational_boundary`
The user expresses a limit, prohibition, or “not like that.”

Examples:
- “Don’t talk to me like a therapist.”
- “Don’t come in above me.”
- “Don’t be that soft with me.”

#### `stance_feedback`
The user evaluates how a prior stance landed.

Examples:
- “That helped because you were blunt.”
- “That felt too harsh.”
- “That was the right tone.”

#### `rupture_signal`
The user signals relational friction, distance, or misattunement.

Examples:
- “You’re talking past me.”
- “That makes me want to pull away.”
- “This is landing wrong.”

#### `meta_request`
The user asks Alfred to explain or adjust the relational mode explicitly.

Examples:
- “Why are you being more direct?”
- “Can you be less coachy?”
- “Stay beside me, not above me.”

### 4.3 Define the structured observation shape

Each extracted observation should include:
- `kind`
- `target`
  - relational dimension, compiled stance field, or bounded interaction target when applicable
- `direction` or `value` when applicable
- `quote`
- `confidence`
- `message_id`
- `attempt_id` when applicable

Important rule:
- the ontology should stay small enough that support inspection remains legible

### 4.4 Keep deterministic validation strict

Required safeguards:
- `kind` must be allowed
- `target` must be valid when present
- target dimensions must come from the relational registry when dimension-based
- quotes must be exact substrings of the source message
- confidence must be numeric and bounded if present
- invalid observations are discarded

### 4.5 Preserve the shared learning boundary

The extractor only emits grounded observations.

It does **not** decide:
- whether a relational value becomes active
- whether a pattern is confirmed
- whether a case is promotable
- whether a stance boundary outranks an existing value

Those decisions remain in deterministic learning and status logic under PRD #183.

### 4.6 Keep explicit support controls stronger

Explicit correction and control commands remain the stronger lane.

If the user uses a direct control surface, that is not merely “one more observation.”
It is a first-class override or correction action.

### 4.7 Stay compatible with PRD #189

This PRD is not meant to create a conflicting parallel system to PRD #189.

Relationship to PRD #189:
- **PRD #189** owns the broader support observation extraction lane
- **this PRD** defines the relational-specific observation sub-ontology and runtime consequences that need sharper treatment

If implementation prefers one shared extractor with typed sub-ontologies, that is acceptable.
The important point is that relational observations stay explicit and not flattened into generic support signals.

### 4.8 Make the observations inspectable

`/support` should be able to show relational observations through cases and traces.

Representative trace questions:
- what did the user actually say?
- what quote grounded the observation?
- was it treated as preference, boundary, feedback, rupture, or meta-request?
- what later value, pattern, or status change did it contribute to?

---

## 5. User Experience Requirements

Users should be able to say things like:
- “Be more direct.”
- “Don’t come in above me.”
- “That was too soft.”
- “That felt good because you stayed beside me.”
- “You’re talking past me.”
- “Why are you being more blunt right now?”

And Alfred should be able to turn those into grounded relational observations rather than vague prompt impressions.

---

## 6. Success Criteria

- [ ] Alfred can extract zero or more grounded relational observations from ordinary language.
- [ ] The relational observation ontology remains small and typed.
- [ ] Quote grounding and deterministic validation reject malformed output.
- [ ] Explicit support-control actions remain stronger than extracted observations.
- [ ] Extracted observations feed the shared learning path without becoming a hidden promotion engine.

---

## 7. Milestones

### Milestone 1: Define the relational observation ontology and schema
Define allowed kinds, targets, fields, and validation rules.

Validation: the ontology is small, relationally specific, and sufficient for the first runtime slice.

### Milestone 2: Implement the extraction path
Run the bounded extractor on relevant turns and validate outputs.

Validation: valid observations are accepted and malformed ones are dropped.

### Milestone 3: Connect observations to the shared learning model
Feed relational observations into attempts, observations, cases, or the interim handoff boundary without bypassing deterministic learning rules.

Validation: relational observations can influence later learning and inspection safely.

### Milestone 4: Add targeted tests and inspection support
Cover preference, boundary, feedback, rupture, and invalid-output cases.

Validation: tests prove grounded extraction and clear traceability.

### Milestone 5: Align docs and support-control language
Update docs and relevant inspection language so the relational extraction path is described truthfully.

Validation: docs and runtime behavior match.

---

## 8. Likely File Changes

```text
prds/196-natural-language-relational-preference-and-boundary-extraction.md
src/alfred/memory/support_learning.py
src/alfred/support_policy.py
src/alfred/support_reflection.py
tests/test_support_learning.py
tests/test_support_policy.py
docs/relational-support-model.md
docs/how-alfred-helps.md
docs/self-model.md
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| The extractor overreads ordinary language | High | keep the ontology small, allow zero observations, and require grounded quotes |
| Relational extraction duplicates PRD #189 incoherently | Medium | keep this PRD focused on relational-specific observations and compatible with shared extraction infrastructure |
| The extractor becomes a hidden control path | High | keep promotion and status mutation outside the extractor |
| Users cannot tell whether a boundary was honored later | Medium | ensure observations are traceable through `/support` cases and update events |

---

## 10. Validation Strategy

This PRD will likely require Python runtime changes and docs alignment.

Validation should focus on:
- quote grounding
- target validation
- zero-observation safety
- separation between extraction and promotion
- inspection traceability through the shared learning model

---

## 11. Related PRDs

- PRD #183: Support Learning V2 - Case-Based Adaptation and Full Inspection
- PRD #189: Natural-Language Observation Extraction for Support Learning
- PRD #192: Relational Runtime Semantics and Stance Adjudication
- PRD #197: Relational Surfacing and Meta-Explanation

---

## 12. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-09 | Create a dedicated relational observation extraction PRD instead of folding everything into the generic support extractor | Relational preferences and boundaries are high-impact enough to deserve an explicit ontology |
| 2026-04-09 | Keep the relational observation ontology small and typed | The runtime needs reliable, inspectable signals rather than broad interpretive freedom |
| 2026-04-09 | Extracted relational observations feed the shared learning model but do not promote directly | The learning and status boundary should remain deterministic |
| 2026-04-09 | Explicit support-control actions remain stronger than extracted observations | Users need a direct correction and override path that outranks inference |
