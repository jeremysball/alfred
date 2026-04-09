# PRD: Shared Semantic Adjudication Contract and Symbolic Runtime Inputs

**Parent PRD**: [#184 Semantic Adjudication Runtime for Support Routing and Learning](./184-semantic-adjudication-runtime-for-support-routing-and-learning.md)  
**GitHub Issue**: [#185](https://github.com/jeremysball/alfred/issues/185)  
**Priority**: High  
**Status**: Draft  
**Created**: 2026-04-07  
**Author**: Agent

---

## 1. Problem Statement

Alfred now has several support-runtime seams that should move from heuristics to bounded LLM adjudication.

That shift will fail if each seam invents its own prompt format, drops useful symbolic context, or relies on loose parsing of model output.

Four problems matter here:

1. **There is no shared adjudication contract**
   - Session-start routing, need adjudication, subject adjudication, observation extraction, and pattern surfacing should not all invent different prompt and validation rules.

2. **Rich symbolic state could be flattened away**
   - Alfred already tracks arcs, domains, situations, support values, relational values, patterns, and ids.
   - If those become ad hoc prose blobs, the model gets less useful structure and the runtime gets harder to reason about.

3. **Validation rules are not centralized**
   - Candidate-bound ids, quote grounding, abstain behavior, max-selection rules, and fallback policy should be common.
   - If each seam validates differently, the runtime will drift.

4. **Observability could become patchy**
   - LLM adjudication needs explicit traces for raw outputs, validation failures, abstains, and fallbacks.
   - Without shared observability, debugging will be guesswork.

This PRD defines the common contract the child PRDs should reuse.

---

## 2. Goals

1. Define one shared input envelope for semantic adjudication.
2. Preserve Alfred's symbolic runtime state in structured form.
3. Define common output-schema rules across adjudicators.
4. Centralize deterministic validation and fallback behavior.
5. Define shared observability for adjudication requests, outputs, and failures.
6. Make child PRDs smaller by moving common infrastructure here.

---

## 3. Non-Goals

- Implementing every adjudicator in this PRD.
- Owning the business rules for session routing, need classification, or pattern surfacing themselves.
- Replacing storage schemas from PRD #183.
- Making adjudication traces user-visible by default.
- Building one giant generic prompt that tries to answer every support question at once.

---

## 4. Proposed Solution

### 4.1 Define one symbolic adjudication envelope

Every support-runtime adjudicator should receive a shared structured envelope with only the fields it needs.

Recommended envelope sections:
- `request_kind`
- `message_context`
  - current user message
  - previous assistant reply when relevant
  - message ids when available
- `session_state`
  - fresh-session flag
  - session id when relevant
  - active response mode when known
- `operational_state`
  - active arc id
  - candidate arcs with stable ids and compact summaries
  - candidate domains with stable ids and compact summaries
  - global situation / arc situation summaries when relevant
- `support_state`
  - effective support values
  - effective relational values
  - relevant runtime patterns when relevant
- `candidate_set`
  - explicit ids or enums the model may choose from
- `constraints`
  - max selections
  - abstain allowed
  - quote required or optional
  - confidence required or optional

The exact class names can change. The contract should not.

### 4.2 Keep symbolic data structured, not collapsed

The LLM should see symbolic state as structured objects, not only prose summaries.

Required rule:
- do not replace stable ids, typed scopes, active values, and candidate lists with prompt-only narration

Permitted additions:
- compact natural-language summaries alongside the structured data when that improves readability for the model

### 4.3 Define common output patterns

Each adjudicator may have a different payload, but all outputs should follow the same safety conventions.

Common fields:
- `decision` or typed result enum
- `selected_ids` or typed refs when applicable
- `quote` or `quotes` when grounding is useful
- `confidence`
- `abstain_reason` when abstaining

Required conventions:
- enums must be closed
- ids must come from the supplied candidate set
- counts must respect the supplied max
- quotes must be exact substrings of the user message or provided text source
- confidence must be numeric and bounded if present

### 4.4 Centralize deterministic validation

Validation should be code-owned and reusable.

At minimum, shared validators should cover:
- enum membership
- candidate-id membership
- max selected count
- quote grounding
- required field presence
- confidence range
- duplicate elimination
- fallback conversion when output is invalid

### 4.5 Define fallback policy explicitly

Every adjudicator should define a safe fallback that does not require trusting malformed model output.

Examples:
- routing fallback: `none`
- need fallback: `unknown`
- subject fallback: empty subject list
- observation fallback: zero observations
- pattern-surfacing fallback: surface nothing

### 4.6 Add shared observability

Observability should record:
- adjudicator kind
- model used
- request size and candidate counts
- validation result
- whether output was accepted, abstained, or rejected
- fallback path used when relevant

Optional debug traces may include sanitized request and raw response payloads when safe.

### 4.7 Provide a reusable test harness

The shared contract should make it easy to test adjudicators with explicit fake model outputs.

The test harness should support:
- valid output acceptance
- invalid enum rejection
- invalid id rejection
- bad quote rejection
- over-selection trimming or rejection
- fallback behavior
- observability assertions

---

## 5. User Experience Requirements

Even though this is mostly infrastructure, the user-facing outcome matters.

The runtime should feel:
- more semantically capable
- more consistent across support surfaces
- no more opaque than before
- safer when the model emits malformed or overreaching output

The user should not experience different support seams behaving like unrelated mini-systems.

---

## 6. Success Criteria

- [ ] A shared structured envelope exists for support-runtime adjudicators.
- [ ] Child PRDs can reuse one validation and fallback model.
- [ ] Candidate-bound ids, quote grounding, and abstain behavior are standardized.
- [ ] Symbolic runtime information is preserved in structured form across adjudicators.
- [ ] Tests can validate adjudicators without real model calls.
- [ ] Observability can explain accepted, rejected, and fallback adjudication outcomes.

---

## 7. Milestones

### Milestone 1: Define the shared request and response contract
Document the common envelope, common safety conventions, and per-adjudicator extension points.

Validation: child PRDs can reference one shared contract instead of redefining it.

### Milestone 2: Implement shared validators and fallback helpers
Create reusable validators and fallback utilities.

Validation: invalid ids, invalid enums, bad quotes, and over-selection are rejected predictably.

### Milestone 3: Add observability and test harness support
Add logging and fake-model test scaffolding for adjudicators.

Validation: tests can cover success, abstain, rejection, and fallback paths without network calls.

### Milestone 4: Align the child PRDs
Update the child PRDs so they inherit this contract instead of inventing parallel ones.

Validation: PRDs #186 through #190 describe compatible input/output and safety rules.

---

## 8. Likely File Changes

```text
prds/185-shared-semantic-adjudication-contract-and-symbolic-runtime-inputs.md
src/alfred/support_policy.py
src/alfred/support_reflection.py
src/alfred/memory/support_context.py
src/alfred/observability.py
tests/test_support_policy.py
tests/test_support_learning.py
tests/test_core_observability.py
docs/relational-support-model.md
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| The shared contract becomes too generic to be useful | Medium | keep the common layer small and let child PRDs define only seam-specific fields |
| Structured symbolic packets become too large | Medium | use compact summaries and explicit field budgets per adjudicator |
| Validation logic gets duplicated anyway | High | make shared validators part of the acceptance criteria for child PRDs |
| Observability leaks too much prompt detail | Medium | log metadata by default and keep raw traces opt-in or sanitized |

---

## 10. Open Questions

1. Should the shared envelope be represented as dataclasses, Pydantic models, or plain typed dicts?
2. Which pieces of symbolic context should always be included versus added only per adjudicator?
3. How much raw text history should be allowed before prompt bloat outweighs value?
4. Which adjudication traces belong only in logs versus future `/support trace` inspection surfaces?
