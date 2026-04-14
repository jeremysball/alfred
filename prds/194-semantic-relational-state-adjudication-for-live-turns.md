# PRD: Semantic Relational-State Adjudication for Live Turns

**Architecture Doc**: [docs/architecture/semantic-runtime-engine.md](../docs/architecture/semantic-runtime-engine.md)  
**Parent PRD**: [#192 Relational Runtime Semantics and Stance Adjudication](./192-relational-runtime-semantics-and-stance-adjudication.md)  
**GitHub Issue**: [#194](https://github.com/jeremysball/alfred/issues/194)  
**Priority**: High  
**Status**: Draft  
**Created**: 2026-04-09  
**Author**: Agent

---

## 1. Problem Statement

Alfred still lacks a principled semantic layer for the live relational moment.

Today, relational behavior is influenced through:
- fixed defaults by need and response mode
- thin transient flags such as overwhelm or shame risk
- scoped learned values and patterns
- prompt-level judgment not explicitly represented in runtime state

That creates five problems:

1. **The transient relational layer is too thin**
   - The runtime needs to judge more than generic urgency or overwhelm.
   - It needs a bounded read on the live relational conditions of the moment.

2. **Important live-turn judgments are still implicit**
   - Alfred needs to know whether the user is inviting directness, needing steadiness, reacting against authority, or at risk of rupture.
   - Right now those judgments are mostly left to prompt instinct.

3. **The current flags are too heuristic and too narrow**
   - A small boolean set does not capture the relational shape of a conversation well enough.
   - The result is mushy runtime behavior.

4. **Live relational state is different from durable learned preference**
   - A user may usually like directness and still need more gentleness right now.
   - The runtime needs a clean transient seam that does not pretend every moment is durable preference.

5. **The relational runtime still lacks the adjudication taste introduced in recent PRDs**
   - PRDs #184 through #190 move support-runtime semantic judgments into bounded adjudicators over symbolic state.
   - The relational layer needs the same treatment.

This PRD applies the shared **candidate adjudication** primitive to the live relational conditions of one turn or reply window.

---

## 2. Goals

1. Replace thin heuristic transient flags with shared candidate adjudication over a closed live-state ontology.
2. Keep the live-state ontology small, closed, and inspectable.
3. Separate transient relational conditions from durable learned values and patterns.
4. Feed bounded live-state outputs into stance adjudication and compiler behavior.
5. Preserve deterministic validation, fallback, and observability through the shared contract in PRD #185.

---

## 3. Non-Goals

- Persisting live-state outputs directly as durable truth.
- Replacing the shared learning model from PRD #183.
- Letting the model invent arbitrary emotional or diagnostic narratives.
- Owning final stance selection. That belongs to PRD #195.
- Creating an unbounded psychological profile of the user.

---

## 4. Proposed Solution

### 4.1 Use the shared candidate-adjudication primitive for live relational state

The runtime should add one narrow adjudicator for the live relational moment.

The adjudicator should return a closed structured result, not prose.

Recommended initial fields:
- `directness_invitation`
  - `low`, `medium`, `high`
- `steadiness_need`
  - `low`, `medium`, `high`
- `emotional_tenderness`
  - `low`, `medium`, `high`
- `challenge_tolerance`
  - `low`, `medium`, `high`
- `rupture_risk`
  - `low`, `medium`, `high`
- optional grounded quote(s)
- optional confidence

This is intentionally small.

### 4.2 Define what each live-state field means

#### `directness_invitation`
How much the user is inviting or permitting bluntness, plain naming, or sharper contradiction.

#### `steadiness_need`
How much the moment calls for calm, steadiness, and reduced push rather than escalation or energetic pressure.

#### `emotional_tenderness`
How emotionally delicate the moment is and how much explicit care or softness the move may need.

#### `challenge_tolerance`
How much the moment can tolerate being pressed, tested, or confronted.

#### `rupture_risk`
How likely a stronger move is to feel relationally misattuned, alienating, or trust-damaging if mishandled.

### 4.3 Forward structured symbolic inputs

The adjudicator should receive only the fields it needs from the shared envelope in PRD #185.

Recommended inputs:
- current user message
- previous assistant reply when relevant
- current session state
  - fresh-session flag
  - session id when available
- resolved support state when already known
  - need
  - response mode
  - subjects
- active relational values
- active relational patterns when relevant
- compact recent correction / boundary context when relevant
- explicit candidate-set constraints for allowed outputs

Important rule:
- the model should see structured runtime state, not only prose

### 4.4 Keep the ontology small and non-diagnostic

The adjudicator should answer only bounded runtime questions.

It should not infer:
- psychiatric labels
- deep identity claims
- hidden motives
- durable truths from one turn

Safe rule:
- when the evidence is weak or mixed, the adjudicator should stay near neutral and allow confidence to stay limited

### 4.5 Keep validation and fallback strict

Required safeguards:
- each field must be in its closed enum
- quotes must be grounded if present
- confidence must be numeric and bounded if present
- malformed output falls back to neutral defaults

Recommended neutral fallback:
- `directness_invitation = medium`
- `steadiness_need = medium`
- `emotional_tenderness = medium`
- `challenge_tolerance = medium`
- `rupture_risk = medium`

### 4.6 Keep live-state transient

Important rule:
- live relational-state outputs influence the current move
- they do **not** become durable state on their own

If repeated turns or observations show a durable pattern, that should be learned through:
- observation extraction
- attempts and cases
- the shared learning model in PRD #183

### 4.7 Make the output useful to stance adjudication

The live-state result should become one of the main inputs to PRD #195.

Examples:
- `directness_invitation=high` may allow a bounded increase in `candor`
- `steadiness_need=high` may suppress `momentum_pressure`
- `emotional_tenderness=high` may increase `warmth` or `emotional_attunement`
- `challenge_tolerance=low` and `rupture_risk=high` may cap `challenge`

The exact mapping should remain deterministic in code after validation.

### 4.8 Keep the seam inspectable

This output does not need to be user-visible by default.

But it should be inspectable through traces or observability so developers can answer:
- what live relational conditions did the runtime think were present?
- what output was accepted?
- did it fall back?
- how did that affect the final stance?

---

## 5. User Experience Requirements

Users should experience Alfred as:
- more sensitive to whether the moment can handle directness or challenge
- better at staying steady when the moment is tender or unstable
- less likely to push in the wrong way at the wrong time
- still bounded and believable rather than mystical

Representative experiences:
- “Just be blunt with me.”
- “I need you to be steadier here.”
- “Don’t push me right now.”
- “You’re coming in too hard.”
- “Stop softening this and tell me the truth.”

---

## 6. Success Criteria

- [ ] The relational runtime has a bounded live-state adjudication seam.
- [ ] The live-state ontology stays small, typed, and non-diagnostic.
- [ ] The adjudicator uses structured symbolic inputs instead of thin prompt prose.
- [ ] Malformed output falls back safely to neutral values.
- [ ] Live-state outputs inform stance selection without becoming durable truth automatically.

---

## 7. Milestones

### Milestone 1: Define the live-state ontology and contract
Define allowed fields, meanings, and validation rules.

Validation: the ontology is small, clear, and sufficient for the first stance-adjudication slice.

### Milestone 2: Implement the adjudication path
Run the live-state adjudicator on relevant turns using the shared PRD #185 contract.

Validation: the runtime can produce accepted or fallback-safe live-state outputs.

### Milestone 3: Connect live-state outputs to stance selection
Feed validated live-state outputs into the bounded stance-adjudication path.

Validation: live-state judgments can materially shape stance without bypassing deterministic control.

### Milestone 4: Add tests and observability
Cover valid outputs, weak evidence, malformed outputs, and fallback behavior.

Validation: traces can explain accepted versus fallback behavior.

### Milestone 5: Align docs and inspection language
Update docs and any relevant inspection surfaces so they describe the live-state seam truthfully.

Validation: docs and runtime behavior match.

---

## 8. Likely File Changes

```text
prds/194-semantic-relational-state-adjudication-for-live-turns.md
src/alfred/support_policy.py
src/alfred/support_reflection.py
src/alfred/alfred.py
tests/test_support_policy.py
tests/test_core_observability.py
docs/relational-support-model.md
docs/how-alfred-helps.md
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| The ontology becomes too sprawling or therapist-like | High | keep the field set small and explicitly non-diagnostic |
| The runtime starts treating live state as durable truth | High | keep persistence out of scope and route durable learning through PRD #183 |
| The adjudicator overreads weak evidence | High | allow neutral outputs and bounded confidence |
| The seam duplicates support need or subject adjudication badly | Medium | keep the scope relational and focused on the live stance conditions |

---

## 10. Validation Strategy

This PRD will likely require Python implementation and docs alignment.

Validation should focus on:
- closed-schema acceptance and rejection behavior
- grounded quotes when returned
- neutral fallback safety
- clear separation between transient output and durable learning
- observability for accepted, rejected, and fallback outputs

---

## 11. Related PRDs

- PRD #183: Support Learning V2 - Case-Based Adaptation and Full Inspection
- PRD #185: Shared Semantic Adjudication Contract and Symbolic Runtime Inputs
- PRD #192: Relational Runtime Semantics and Stance Adjudication
- PRD #195: Semantic Relational Stance Adjudication

---

## 12. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-09 | Add a bounded live relational-state adjudicator | The current transient relational layer is too thin and too heuristic |
| 2026-04-09 | Keep the live-state ontology small and non-diagnostic | The runtime needs bounded semantic judgment, not freeform psychologizing |
| 2026-04-09 | Live relational-state outputs remain transient by default | One moment should not silently become durable truth |
| 2026-04-09 | Validated live-state outputs should shape stance adjudication through deterministic mappings | The model should inform the move, but code should keep the trust boundary |
