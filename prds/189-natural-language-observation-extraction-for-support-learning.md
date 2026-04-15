# PRD: Natural-Language Observation Extraction for Support Learning

**Architecture Doc**: [docs/architecture/semantic-runtime-engine.md](../docs/architecture/semantic-runtime-engine.md)
**Parent PRD**: [#184 Support Projection Work on the Semantic Runtime Engine](./184-semantic-adjudication-runtime-for-support-routing-and-learning.md)
**Related PRDs**: [#183 Support Learning V2 - Case-Based Adaptation and Full Inspection](./183-support-learning-v2-case-based-adaptation-and-full-inspection.md), [#196 Natural-Language Relational Preference and Boundary Extraction](./196-natural-language-relational-preference-and-boundary-extraction.md)
**GitHub Issue**: [#189](https://github.com/jeremysball/alfred/issues/189)
**Priority**: High
**Status**: Draft
**Created**: 2026-04-07
**Author**: Agent

---

## 1. Problem Statement

Alfred still lacks a principled support-domain path for extracting grounded observations from what the user says.

Today, the system has:
- explicit structured correction flows in `/support`
- deterministic and operational evidence in current support-domain implementation paths
- no strong general path for extracting grounded support observations from ordinary natural language

That creates five problems:

1. **Natural-language learning is underpowered**
   - Users often say important things in ordinary conversation, not in explicit correction commands.
   - Alfred should be able to learn from those signals.

2. **Phrase-family or lexical parsing is not a good solution**
   - Keyword and phrase matching is brittle, easy to overfit, and not trustworthy enough for support learning.

3. **This work should reuse the shared observation-extraction primitive**
   - Support-domain observation extraction should not become its own architecture.
   - It should be one application of the shared semantic runtime engine.

4. **The current support projection needs richer evidence inputs**
   - the current repo already persists support-domain adaptive artifacts and inspection data
   - that implementation needs a grounded conversational evidence source without becoming the architecture

5. **Without deterministic safeguards, extraction would be too risky**
   - Alfred should not silently promote ungrounded claims about the user.
   - The extraction layer needs quotes, typed targets, confidence, and code-owned validation.

---

## 2. Goals

1. Apply the shared grounded observation-extraction primitive to support-domain observations.
2. Keep the support observation ontology small, typed, and inspectable.
3. Require quote grounding and deterministic validation.
4. Feed grounded support observations into the generalized semantic-runtime evidence path, with explicit compatibility for current support-domain implementation seams where needed.
5. Treat language-level helpfulness, misunderstanding, and progress/friction cues as **semantic outcome signals** extracted through this observation lane, not as direct durable outcomes.
6. Preserve explicit `/support` correction commands as a distinct direct-control path.

---

## 3. Non-Goals

- Replacing explicit `/support` actions.
- Letting the model promote values or patterns directly from raw extraction.
- Using phrase families or lexical parsing as the main extraction method.
- Replacing structured operational evidence such as blocker or task changes.
- Flattening relational-specific observations into vague generic labels when PRD #196 needs sharper typed semantics.
- Building the full deterministic promotion or durable-state-update engine here; that remains outside this extractor PRD.

---

## 4. Proposed Solution

### 4.1 Use the shared grounded observation-extraction primitive

For relevant turns, run the shared schema-constrained extraction primitive over inputs such as:
- latest user message
- previous assistant reply when relevant
- active support and relational values when relevant
- current attempt or response context when available
- explicit constraints from PRD #185

The extractor may return zero or more observations.

### 4.2 Keep the ontology small

Initial support observation kinds:
- `correction`
- `preference`
- `feedback`
- `scope`
- `interpretation_rejection`

Each observation should include fields such as:
- `kind`
- `target` when applicable
- `value` when applicable
- `confidence`
- `quote`
- `message_id`
- `attempt_id` when applicable
- `scope` when applicable

These kinds define the broad support-learning lane.
They do not mean every high-value observation should be flattened into only these labels forever.

PRD #196 owns the relational-specific sub-ontology for observations such as:
- relational preferences
- relational boundaries
- stance feedback
- rupture signals
- relational meta-requests

### 4.3 Require deterministic validation

Required safeguards:
- kind must be allowed
- target registry or dimension must be valid when present
- quote must be a real substring of the source message
- referenced ids must exist when supplied
- invalid observations are discarded

### 4.4 Keep promotion and activation out of the extractor

The extractor only emits observations.

It does not decide:
- whether a value becomes active
- whether a pattern is confirmed
- whether a case is promotable
- whether an observation should immediately change runtime behavior

Those decisions stay in deterministic activation and durable-state logic outside the extractor itself, using the shared substrate contract and any current support-domain compatibility seams required by the repo.

### 4.5 Preserve structured operational evidence as a separate lane

Operational changes such as:
- blocker narrowed
- task started
- decision made
- open loop reopened

should still come from structured state and event logic, not NLP extraction.

Language-level outcome cues such as:
- "this helped"
- "no, that's not it"
- "I get it now"
- "this is making it murkier"

may be extracted here as **semantic outcome signals** when they are quote-grounded and schema-valid.

The runtime should combine:
- conversational observations from this PRD, including semantic outcome signals expressed in language
- structured operational evidence from deterministic support-domain state changes

### 4.6 Preserve explicit user control

Explicit `/support` actions remain direct overrides.

They are not merely one more observation with a higher confidence score.

### 4.7 Keep the boundary with PRD #196 explicit

This PRD owns the broader support observation-extraction lane and its shared safeguards for support-domain observations.

That includes:
- when support observation extraction runs
- the shared support observation schema discipline
- quote grounding
- deterministic validation
- handoff into deterministic runtime evidence/update paths, including current support-domain compatibility seams where necessary

PRD #196 owns the relational-specific observation vocabulary and its relational runtime meaning.

Implementation may use either:
- one shared extractor with a generic support ontology plus a relational sub-ontology
- or a shared extractor envelope with separate typed extractors

What matters is that the repo ends with one coherent extraction architecture, not two competing systems.

---

## 5. User Experience Requirements

Users should be able to say things like:
- “Don’t give me options. Just tell me the next step.”
- “No, that’s not what’s going on.”
- “This helped.”
- “This is about work, not health.”
- “Be more direct.”

And Alfred should be able to extract grounded support observations without relying on brittle phrase lists.

---

## 6. Success Criteria

- [ ] Alfred can extract zero or more grounded support observations from ordinary user language.
- [ ] The extractor uses a closed support observation ontology.
- [ ] Quote grounding and deterministic validation reject malformed output.
- [ ] Explicit `/support` actions remain distinct direct-control paths.
- [ ] Deterministic runtime evidence/update paths can consume extracted observations without letting the extractor own promotion decisions.
- [ ] Structured operational outcomes remain deterministic while language-level outcome signals are extracted as grounded observations.
- [ ] The boundary between broad support extraction and relational-specific extraction stays explicit and compatible with PRD #196.

---

## 7. Milestones

### Milestone 1: Define the support observation ontology and schema
Define the support observation kinds, shared fields, targets, validation rules, and the ownership boundary with PRD #196.

Validation: the ontology is small, typed, and sufficient for the first learning slice without collapsing relational-specific observations into generic ones.

### Milestone 2: Implement the extraction pipeline
Run the bounded extractor on relevant turns and validate the outputs.

Validation: valid observations are accepted and malformed ones are dropped.

### Milestone 3: Connect extracted observations to deterministic evidence/update paths
Make extracted observations available to the generalized semantic-runtime evidence/update path or any explicit temporary compatibility boundary required by the current repo.

Validation: observations can be persisted or handed off without bypassing deterministic activation or durable-state rules.

### Milestone 4: Align docs and inspection text
Update docs and support-inspection language so the extraction path is described truthfully.

Validation: docs and runtime behavior match.

---

## 8. Likely File Changes

```text
prds/189-natural-language-observation-extraction-for-support-learning.md
prds/183-support-learning-v2-case-based-adaptation-and-full-inspection.md
docs/architecture/semantic-runtime-engine.md
docs/relational-support-model.md
src/alfred/support_policy.py
src/alfred/support_reflection.py
src/alfred/memory/support_learning.py
tests/test_support_learning.py
tests/test_support_policy.py
docs/self-model.md
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| The extractor overreads ordinary language | High | keep the ontology small, allow zero observations, and require grounded quotes |
| The extractor becomes a hidden promotion engine | High | keep promotion and activation out of scope and under deterministic learning rules |
| Explicit `/support` corrections lose their stronger semantics | Medium | preserve them as a separate direct-control lane |
| Relational extraction splits into two incoherent systems | Medium | keep this PRD as the broad support extraction owner and keep PRD #196 as the relational sub-ontology owner |
| Too much schema complexity creeps in early | Medium | start with five broad support kinds and add relational specificity through PRD #196 |

---

## 10. Open Questions

1. Which turns should trigger support observation extraction by default?
2. Should the extractor always see the last assistant reply, or only when the user is likely reacting to it?
3. Which extracted observations should be visible immediately in `/support` inspection surfaces versus only through later case aggregation?
4. Should the first implementation use one extractor with typed sub-ontologies, or a shared envelope with a separate relational extractor from PRD #196?
