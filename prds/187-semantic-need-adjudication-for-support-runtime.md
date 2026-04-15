# PRD: Semantic Need Adjudication for Support Runtime

**Architecture Doc**: [docs/architecture/semantic-runtime-engine.md](../docs/architecture/semantic-runtime-engine.md)
**Parent PRD**: [#184 Support Projection Work on the Semantic Runtime Engine](./184-semantic-adjudication-runtime-for-support-routing-and-learning.md)
**GitHub Issue**: [#187](https://github.com/jeremysball/alfred/issues/187)
**Priority**: High
**Status**: Draft
**Created**: 2026-04-07
**Author**: Agent

---

## 1. Problem Statement

Alfred currently infers support need through embedding similarity to a small hardcoded prototype bank.

That approach is too brittle for a pragmatic judgment like:
- is the user asking to orient?
- resume?
- activate?
- decide?
- reflect?
- calibrate?

Four problems matter now:

1. **Prototype banks are too thin for real pragmatic variation**
   - Users ask for the same kind of help in many ways.
   - A few prototype phrases cannot represent that space well enough.

2. **Need classification is not just semantic similarity**
   - The runtime needs to infer the user's current job, not merely the nearest paraphrase to a canned line.

3. **The current logic underuses rich runtime state**
   - Fresh-session status, recent turn context, active values, and operational context can all matter.
   - The prototype-bank path mostly ignores that richer structure.

4. **Threshold tuning is becoming the product**
   - Similarity margins and prototype hit counts are implementation glue, not a durable product contract.

This PRD applies the shared **candidate adjudication** primitive to support-need selection.

---

## 2. Goals

1. Replace embedding-prototype need classification with shared candidate adjudication over a closed need enum.
2. Keep the allowed need set closed and typed.
3. Preserve deterministic response-mode mapping in code.
4. Forward rich symbolic runtime context into the adjudication request.
5. Keep observability and fallback behavior explicit.

---

## 3. Non-Goals

- Reworking response-mode semantics themselves.
- Replacing embeddings for retrieval elsewhere in the system.
- Combining need and subject adjudication into one unconstrained prompt.
- Letting the model invent new need categories.

---

## 4. Proposed Solution

### 4.1 Use the shared candidate-adjudication primitive for need selection

The adjudicator should classify the turn into exactly one of:
- `orient`
- `resume`
- `activate`
- `decide`
- `reflect`
- `calibrate`
- `unknown`

Optional returned fields:
- grounding quote
- confidence

### 4.2 Forward symbolic context, not only text

The need prompt should be able to see structured inputs such as:
- current user message
- previous assistant reply when relevant
- fresh-session flag
- current response-mode hints when relevant
- active arc or domain context when already known
- effective support and relational values when relevant
- compact operational context when relevant

The aim is to let the model interpret the live turn in context, not compare it to a small phrase bank.

### 4.3 Keep response-mode mapping deterministic

Need adjudication does not own the final response-mode mapping.

Required rule:
- the model selects the need
- code maps need plus session/runtime context into response mode

This keeps the control boundary inspectable.

### 4.4 Keep strict safeguards

Required safeguards:
- need must be in the closed enum
- quote must be grounded if present
- confidence must be numeric if present
- invalid output falls back to `unknown`

### 4.5 Preserve observability

Need adjudication should log:
- selected need
- confidence if present
- whether output passed validation
- whether fallback to `unknown` occurred

---

## 5. User Experience Requirements

Users should be able to say things like:
- “I need one small way in.”
- “Tell me honestly what you think is happening.”
- “Can you help me compare these?”
- “I’m spiraling a bit. What am I actually in the middle of?”
- “Why do I keep doing this?”

And Alfred should classify the need without depending on canned phrasings.

---

## 6. Success Criteria

- [ ] Need adjudication no longer depends on prototype-bank similarity as the primary path.
- [ ] Alfred can classify paraphrased requests into the existing need set.
- [ ] Response-mode mapping remains deterministic in code.
- [ ] Invalid output falls back safely to `unknown`.
- [ ] Tests cover paraphrase, ambiguity, and malformed-model-output cases.

---

## 7. Milestones

### Milestone 1: Define the need-adjudication contract
Define the bounded schema and the symbolic inputs need classification may consume.

Validation: the prompt contract can express every allowed need and `unknown`.

### Milestone 2: Replace prototype-bank need classification
Use the adjudicator in the support-policy path that currently calls the need prototype bank.

Validation: support policy chooses need through the adjudicated path instead of embedding prototypes.

### Milestone 3: Add targeted tests and observability
Cover paraphrase, ambiguity, invalid output, and deterministic response-mode mapping.

Validation: tests prove the new path is bounded and fallback-safe.

### Milestone 4: Align docs
Update support-model documentation so it describes adjudicated need selection truthfully.

Validation: docs and runtime behavior match.

---

## 8. Likely File Changes

```text
prds/187-semantic-need-adjudication-for-support-runtime.md
src/alfred/support_policy.py
tests/test_support_policy.py
tests/test_core_observability.py
docs/relational-support-model.md
docs/how-alfred-helps.md
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Need classification becomes less predictable | Medium | keep the enum closed and preserve deterministic mapping afterward |
| The model overcommits when the turn is ambiguous | High | include `unknown` explicitly and prefer abstention over false confidence |
| Runtime context bloats the prompt | Medium | limit the symbolic packet to fields that materially affect need selection |
| Old prototype-bank logic lingers in parallel | Medium | treat the adjudicated path as the replacement, not an optional side path |

---

## 10. Open Questions

1. Should fresh-session status be mandatory input for need adjudication, or only used when true?
2. Which symbolic fields measurably improve need classification versus just adding tokens?
3. Should confidence drive any runtime branching, or only observability and future inspection?
