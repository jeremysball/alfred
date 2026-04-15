# PRD: Semantic Pattern Surfacing and Reflection Guidance

**Architecture Doc**: [docs/architecture/semantic-runtime-engine.md](../docs/architecture/semantic-runtime-engine.md)
**Parent PRD**: [#184 Support Projection Work on the Semantic Runtime Engine](./184-semantic-adjudication-runtime-for-support-routing-and-learning.md)
**GitHub Issue**: [#190](https://github.com/jeremysball/alfred/issues/190)
**Priority**: High
**Status**: Draft
**Created**: 2026-04-07
**Author**: Agent

---

## 1. Problem Statement

Alfred currently decides whether to surface support patterns through additive heuristic scores in the reflection-guidance path.

That path blends:
- situation similarity
- scope score
- status score
- evidence count
- recency
- move-impact heuristics
- fresh-session heuristics

This is useful as retrieval and prioritization logic, but weak as the final answer to a pragmatic question:

> should Alfred say this now?

Four problems matter now:

1. **Similarity is not the same as surfacing judgment**
   - A relevant pattern is not always a pattern that should be surfaced right now.

2. **The current score stack is hard to reason about**
   - Many local weights interact to decide compact versus rich versus silent behavior.

3. **The system underuses symbolic context**
   - Current response mode, start type, fresh-session state, active values, and candidate pattern metadata all matter.
   - The current path compresses these into a heuristic load score.

4. **The trust boundary should be clearer**
   - Embeddings and similarity should shortlist candidate patterns.
   - The final surfacing judgment should be a bounded semantic decision with strict limits and safe fallback.

This PRD applies the shared **candidate adjudication** primitive to final pattern-surfacing choices after deterministic shortlist generation.

---

## 2. Goals

1. Keep embeddings and scoring for shortlist generation only.
2. Use shared candidate adjudication for the final surfacing decision.
3. Keep surfacing bounded to none, one, or a small number of candidate patterns.
4. Preserve deterministic safety limits and silent fallback behavior.
5. Improve Alfred's judgment about when to surface a pattern and when to stay quiet.

---

## 3. Non-Goals

- Replacing pattern retrieval or search with LLM-only logic.
- Letting the model invent new pattern ids or pattern claims.
- Reworking the full pattern model or support review model.
- Turning reflection guidance into an open-ended essay generator.

---

## 4. Proposed Solution

### 4.1 Keep shortlist retrieval deterministic

The existing retrieval and prioritization path may still compute a candidate shortlist from:
- similarity
- scope
- status
- evidence count
- recency

That shortlist should remain deterministic and bounded.

### 4.2 Use the shared candidate-adjudication primitive for surfacing

Given a shortlist, the model should decide:
- surface none / one / two candidate patterns
- which candidate `pattern_id`s if any
- `surface_level` for each selected pattern:
  - `compact`
  - `rich`

Optional returned fields:
- grounded quote or evidence reference id when applicable
- confidence

### 4.3 Forward rich symbolic context

The surfacing prompt should see structured inputs such as:
- current user turn
- previous assistant reply when relevant
- response mode
- fresh-session flag
- start type when relevant
- effective support and relational values
- shortlisted patterns with:
  - `pattern_id`
  - kind
  - status
  - scope
  - confidence
  - compact why-summary
  - supporting evidence summary or counts

### 4.4 Keep strict constraints and fallback

Required safeguards:
- selected `pattern_id`s must come from the shortlist
- surfaced count must respect a hard maximum
- `surface_level` must be valid
- invalid output falls back to surfacing nothing
- the runtime must never surface invented claims or patterns outside the shortlist

### 4.5 Preserve silent behavior as a first-class valid outcome

The model should be free to choose `none`.

This PRD is not about forcing reflection into every turn.
It is about making the surfacing judgment more semantically aware and less weight-driven.

---

## 5. User Experience Requirements

Alfred should get better at questions like:
- “Should I name this recurring blocker right now?”
- “Should I remind the user of this support preference?”
- “Should I stay quiet and just help with the next move?”

The user-facing effect should be:
- better timing
- fewer awkward or premature pattern mentions
- preserved ability to surface relevant patterns when they would actually help

---

## 6. Success Criteria

- [ ] Pattern retrieval remains deterministic and bounded.
- [ ] Final surfacing is decided through bounded semantic adjudication.
- [ ] The model can surface none, one, or a small bounded number of shortlisted patterns.
- [ ] Invalid output falls back safely to silence.
- [ ] Tests cover compact, rich, silent, and malformed-output cases.

---

## 7. Milestones

### Milestone 1: Define the surfacing input and output contract
Define the shortlist shape, output schema, and fallback rules.

Validation: the contract supports bounded `pattern_id` selection and `surface_level` choice.

### Milestone 2: Replace the heuristic final surfacing decision
Use the adjudicator after deterministic shortlist generation.

Validation: reflection guidance makes the final surface-level decision through the adjudicated path.

### Milestone 3: Add targeted tests and observability
Cover helpful surfacing, deliberate silence, invalid ids, and malformed outputs.

Validation: tests prove bounded selection and safe silent fallback.

### Milestone 4: Align docs
Update support-model and reflection docs to describe the new surfacing behavior truthfully.

Validation: docs and runtime behavior match.

---

## 8. Likely File Changes

```text
prds/190-semantic-pattern-surfacing-and-reflection-guidance.md
src/alfred/support_reflection.py
tests/test_support_learning.py
tests/test_core_observability.py
docs/relational-support-model.md
docs/how-alfred-helps.md
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| The model surfaces too much | High | keep silence as a valid choice and enforce small hard caps |
| The model invents justification beyond the shortlist | High | restrict outputs to shortlisted ids and validated levels only |
| Deterministic retrieval quality regresses while adding adjudication | Medium | keep retrieval and shortlist logic intact; change only the final surfacing judgment |
| Reflection timing becomes harder to debug | Medium | add observability around shortlist inputs, accepted outputs, and fallbacks |

---

## 10. Open Questions

1. Should rich surfacing ever be allowed outside reflective response modes?
2. How many shortlisted patterns should the adjudicator see before timing and prompt quality degrade?
3. Should surfacing confidence affect whether Alfred names a pattern directly versus more tentatively?
