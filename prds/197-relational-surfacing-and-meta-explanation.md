# PRD: Relational Surfacing and Meta-Explanation

**Architecture Doc**: [docs/architecture/semantic-runtime-engine.md](../docs/architecture/semantic-runtime-engine.md)
**Parent PRD**: [#192 Relational Projection Work on the Semantic Runtime Engine](./192-relational-runtime-semantics-and-stance-adjudication.md)
**GitHub Issue**: [#197](https://github.com/jeremysball/alfred/issues/197)
**Priority**: High
**Status**: Draft
**Created**: 2026-04-09
**Author**: Agent

---

## 1. Problem Statement

Alfred still lacks a principled seam for deciding when to explain his relational stance, when to keep it implicit, and how to talk about a stance shift without dumping internal jargon.

Today:
- the runtime can shape tone implicitly through values and prompts
- reflection guidance focuses on pattern surfacing rather than relational explanation
- the user can still ask direct relational questions that Alfred should answer better

That creates five problems:

1. **The relational layer stays too hidden or too hand-wavy**
   - Alfred often should keep the stance implicit.
   - But when the user asks or trust is at stake, he needs a better explanation path.

2. **There is no bounded surfacing rule for relational stance**
   - The runtime lacks a narrow seam for deciding whether to say nothing, give a compact explanation, or give a richer relational explanation.

3. **Meta-explanation risks either oversharing or evasiveness**
   - Too much explanation makes Alfred sound mechanical.
   - Too little explanation makes stance shifts feel mysterious or arbitrary.

4. **The support-runtime surfacing taste has not yet been applied here**
   - PRD #190 sharpens pattern surfacing through shortlist-plus-adjudication.
   - The relational layer needs an equivalent design for stance explanation.

5. **The user needs a better answer to relational why-questions**
   - Questions like “why are you being more direct right now?” or “why are you coming in above me?” deserve a bounded, truth-preserving runtime answer.

This PRD applies the shared **candidate adjudication** primitive to relational surfacing and meta-explanation choices.

---

## 2. Goals

1. Add shared candidate adjudication for whether relational stance should stay implicit or be explained.
2. Keep implicit behavior as the default.
3. Allow compact or richer explanation when the user asks, when correction is needed, or when trust requires it.
4. Prevent the runtime from dumping internal labels, scores, or policy metadata by default.
5. Make relational explanations traceable and inspectable without making normal conversation mechanical.

---

## 3. Non-Goals

- Turning every turn into a self-explaining relational monologue.
- Replacing pattern surfacing or broader reflection guidance.
- Letting the model invent reasons not grounded in runtime state.
- Exposing internal score names, prompt metadata, or hidden registries by default.
- Owning stance selection itself. That belongs to PRD #195.

---

## 4. Proposed Solution

### 4.1 Use the shared candidate-adjudication primitive for relational surfacing

The adjudicator should answer a narrow question:

> should Alfred keep the current relational stance implicit, give a compact explanation, or give a richer explanation right now?

Recommended top-level outputs:
- `implicit`
- `compact`
- `rich`

Optional fields:
- `reason_refs[]`
- grounded quote when the user explicitly asked or challenged the stance
- confidence

### 4.2 Use explicit reason refs rather than freeform explanation plans

The model should not invent arbitrary explanation categories.

Recommended candidate reason refs:
- `user_asked`
- `boundary_acknowledgment`
- `repair_after_misattunement`
- `major_directness_shift`
- `major_authority_shift`
- `major_pressure_shift`
- `explicit_preference_match`
- `calibration_requires_explanation`

The adjudicator may select from only the provided reason refs.

This keeps the seam candidate-bound and inspectable.

### 4.3 Forward rich symbolic context

The surfacing prompt should receive:
- current user message
- previous assistant reply when relevant
- whether the user explicitly asked about Alfred's stance
- current effective relational values
- current baseline-to-effective stance delta when present
- active relational observations or boundaries when relevant
- current response mode and support need when relevant
- explicit candidate reason refs and hard output constraints

### 4.4 Keep implicit behavior as the default

Default rule:
- most turns should remain `implicit`

The relational layer should be felt more often than narrated.

Good candidates for `compact` or `rich` explanation include:
- the user explicitly asks why Alfred is showing up this way
- a boundary or rupture needs acknowledgment
- the runtime made a substantial stance shift that materially affects trust
- Alfred needs to clarify that he is honoring a known relational preference

### 4.5 Keep the explanation truthful but natural

If explanation is surfaced:
- Alfred should explain the move naturally
- he should not dump internal labels, registry names, scores, or raw contract metadata unless the user asks more explicitly

For example:
- “I’m being more direct because you asked for less hedging here.”
- “I’m backing off the pressure because this sounds more tender than action-ready.”
- “I’m trying to stay beside you rather than come in above you.”

Not:
- raw score dumps
- registry-name narration
- internal policy jargon by default

### 4.6 Keep validation and fallback strict

Required safeguards:
- explanation mode must be one of `implicit`, `compact`, `rich`
- selected `reason_refs` must come from the provided candidate set
- quotes must be grounded if present
- malformed output falls back to `implicit`

Safe fallback:
- `implicit`

### 4.7 Make the seam inspectable without overexposing it

Support traces should be able to show:
- what explanation mode was selected
- what reason refs were selected
- whether the user explicitly asked
- whether the runtime fell back to `implicit`

Normal conversation should not expose that machinery unless the selected mode calls for it.

### 4.8 Keep relation to PRD #190 clear

PRD #190 owns whether to surface support patterns and reflection guidance.

This PRD owns whether to surface relational stance explanation.

They may share:
- the adjudication envelope from PRD #185
- observability and fallback helpers
- some inspection or trace infrastructure

They should not collapse into one mixed seam.

---

## 5. User Experience Requirements

Users should experience Alfred as:
- more capable of explaining relational shifts when they matter
- less mysterious when the stance changes noticeably
- still natural and non-mechanical most of the time
- better at acknowledging boundaries and repairs explicitly when needed

Representative experiences:
- “Why are you being more direct right now?”
- “You’re coming in above me. Don’t do that.”
- “Why are you being gentler than usual?”
- “Are you doing this because I asked for less pressure?”
- “This is landing wrong. What are you trying to do here?”

---

## 6. Success Criteria

- [ ] The relational runtime can choose `implicit`, `compact`, or `rich` explanation through a bounded seam.
- [ ] Implicit behavior remains the default.
- [ ] Explanation is candidate-bound and grounded in real runtime state.
- [ ] Invalid output falls back safely to `implicit`.
- [ ] Alfred can answer relational why-questions more truthfully without dumping internal metadata by default.

---

## 7. Milestones

### Milestone 1: Define the surfacing contract
Define explanation modes, reason refs, validation rules, and fallback behavior.

Validation: the contract supports bounded explanation choices and candidate-bound reason selection.

### Milestone 2: Implement the adjudication path
Use the relational-surfacing adjudicator after effective stance is known.

Validation: runtime can choose implicit or explanation modes safely.

### Milestone 3: Connect explanation output to response assembly and traces
Feed accepted explanation mode into response guidance and trace storage.

Validation: Alfred can explain stance shifts when warranted and remain implicit otherwise.

### Milestone 4: Add targeted tests and observability
Cover explicit asks, boundary acknowledgments, repair cases, invalid outputs, and fallback behavior.

Validation: tests prove bounded explanation behavior and safe fallback.

### Milestone 5: Align docs and inspection text
Update docs and any inspection surfaces that describe relational explanation behavior.

Validation: docs and runtime behavior match.

---

## 8. Likely File Changes

```text
prds/197-relational-surfacing-and-meta-explanation.md
src/alfred/support_reflection.py
src/alfred/support_policy.py
src/alfred/alfred.py
tests/test_support_policy.py
tests/test_core_observability.py
docs/relational-support-model.md
docs/how-alfred-helps.md
docs/self-model.md
templates/SYSTEM.md
templates/prompts/voice.md
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Alfred starts over-explaining his relational choices | High | keep `implicit` as the default and require explicit bounded triggers for explanation |
| Explanations become internal-jargon dumps | High | restrict the seam to candidate-bound reason refs and natural-language realization |
| The user still cannot tell why a stance shifted | Medium | allow compact or rich explanation when asked, repairing, or honoring a visible boundary |
| This duplicates pattern surfacing work badly | Medium | keep ownership separate from PRD #190 and share only infrastructure |

---

## 10. Validation Strategy

This PRD will likely require Python runtime changes and docs alignment.

Validation should focus on:
- bounded explanation-mode selection
- candidate-bound reason-ref validation
- grounded quote handling when present
- safe fallback to `implicit`
- response-assembly behavior that stays natural and non-jargony

---

## 11. Related PRDs

- PRD #185: Generalized Semantic Runtime Substrate Contract and Ontology Projection Envelope
- PRD #190: Semantic Pattern Surfacing and Reflection Guidance
- PRD #192: Relational Projection Work on the Semantic Runtime Engine
- PRD #195: Semantic Relational Stance Adjudication
- PRD #196: Natural-Language Relational Preference and Boundary Extraction

---

## 12. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-09 | Add a dedicated relational-surfacing and meta-explanation seam | Relational why-questions and repairs need a bounded runtime answer |
| 2026-04-09 | Keep implicit behavior as the default | Alfred should feel natural rather than mechanically narrated |
| 2026-04-09 | Use candidate-bound reason refs instead of freeform explanation planning | This keeps the seam inspectable and less likely to drift into prompt theater |
| 2026-04-09 | Fallback safely to `implicit` on invalid output | Safe silence is better than a bad meta-explanation |
