# PRD: Relational Projection Work on the Semantic Runtime Engine

**Architecture Doc**: [docs/architecture/semantic-runtime-engine.md](../docs/architecture/semantic-runtime-engine.md)
**Shared Contract PRD**: [#185 Generalized Semantic Runtime Substrate Contract and Ontology Projection Envelope](./185-shared-semantic-adjudication-contract-and-symbolic-runtime-inputs.md)
**GitHub Issue**: [#192](https://github.com/jeremysball/alfred/issues/192)
**Priority**: High
**Status**: Draft
**Created**: 2026-04-09
**Author**: Agent

> This PRD is a projection-planning doc downstream of the architecture doc. It does not own the shared substrate design.

---

## 1. Problem Statement

Alfred's recent support-runtime work sharpened the architecture for bounded semantic judgment, but the relational projection still lags behind that design quality.

Today, important relational behavior still depends too much on:
- prompt voice and template prose
- hand-tuned default tables
- thin transient flags
- raw relational values that do not yet cash out into concrete runtime behavior
- weak or missing seams for relational preference extraction and stance explanation

That creates six problems:

1. **Relational semantics are still too implicit**
   - Alfred has relational dimensions such as `candor`, `companionship`, and `authority`
   - the product does not yet define those dimensions crisply enough as runtime behavior

2. **The live relational moment lacks bounded semantic seams**
   - the runtime needs to judge fragility, invitation for directness, steadiness needs, rupture risk, and openness to challenge
   - thin transient flags and hand-written adjustments are not enough for that job

3. **Relational work can drift into shared-architecture language**
   - relational semantics are an important projection, not a second engine
   - this PRD should describe relational projection behavior, not redefine the substrate

4. **Prompt-only relational interpretation is too mushy**
   - without bounded projection seams, relational behavior drifts into vibe rather than inspectable runtime logic

5. **Current support-domain implementation details are the wrong shared foundation**
   - the repo currently ships support-domain learning and inspection behavior through PRD #183
   - relational work should respect that current reality without treating support-specific nouns as universal architecture

6. **The relational layer should reuse the generalized substrate, not invent another one**
   - relational work should plug into the same substrate as support and future projections
   - it should not become a second semantic runtime

---

## 2. Goals

1. Frame the relational layer as a relational projection on the shared semantic runtime engine.
2. Use bounded candidate adjudication where the job is relational selection, ranking, or delta choice.
3. Use grounded observation extraction where the job is relational preference, boundary, feedback, or rupture extraction.
4. Define product-owned relational semantics that cash out into concrete compiler behavior.
5. Keep embeddings focused on retrieval, shortlist generation, and similar-case recall rather than final relational judgment.
6. Keep docs, prompts, inspection text, and runtime behavior aligned.
7. Keep the relational projection compatible with the current repo without hard-coding itself to today's support-shaped implementation artifacts.

---

## 3. Non-Goals

- Creating separate hard-coded personas for friend, peer, mentor, coach, or analyst.
- Building a second semantic engine for relational behavior.
- Letting the LLM write directly to persistence or status transitions.
- Turning Alfred into an unbounded therapy-theater runtime.
- Treating current support-domain implementation artifacts as the target cross-domain substrate.
- Preserving current heuristic seams long-term when bounded adjudicated seams supersede them.

---

## 4. Proposed Solution

### 4.1 Treat the relational layer as one projection plugged into the shared engine

The relational layer should reuse the same three abstractions described in `docs/architecture/semantic-runtime-engine.md`:

1. **candidate adjudication**
2. **grounded observation extraction**
3. **deterministic activation and surfacing policy**

This PRD owns the relational projection's use of those abstractions.
It does **not** own the shared substrate contract.

### 4.2 Use the same responsibility split as the support projection work

Adopt this split for relational-runtime interpretation work:

- **LLM candidate adjudication**
  - live relational-state judgment
  - bounded stance adjustment
  - bounded surfacing and explanation choice

- **LLM grounded observation extraction**
  - relational preference extraction
  - relational boundary extraction
  - stance feedback extraction
  - rupture and meta-request extraction

- **Embeddings**
  - similar-case retrieval
  - shortlist generation
  - pattern/value recall support
  - optional candidate narrowing

- **Deterministic code**
  - scope precedence
  - active-state loading
  - compiler execution
  - validation and fallback
  - persistence
  - inspection payloads
  - explanation thresholds

### 4.3 Child PRD map

This PRD governs the following relational projection work:

- **PRD #193 — Product-Owned Relational Semantics and Compiler Contract**
  - define what each relational dimension means behaviorally
  - define richer compiler outputs and readable stance summaries

- **PRD #194 — Semantic Relational-State Adjudication for Live Turns**
  - use candidate adjudication to infer the live relational conditions of the moment through bounded semantic judgment

- **PRD #195 — Semantic Relational Stance Adjudication**
  - use candidate adjudication to choose bounded per-turn stance deltas against a deterministic baseline

- **PRD #196 — Natural-Language Relational Preference and Boundary Extraction**
  - use grounded observation extraction for relational preferences, boundaries, stance feedback, and rupture signals

- **PRD #197 — Relational Surfacing and Meta-Explanation**
  - use candidate adjudication to decide when Alfred should keep the stance implicit, give a compact explanation, or explain a larger shift

Boundary rule:
- the architecture doc owns the shared engine design
- PRD #185 owns the shared substrate contract
- this PRD owns relational projection behavior and implementation planning

### 4.4 Keep one relational runtime loop on top of the substrate

The target runtime loop for relational behavior should be:

1. resolve support-side context needed for the turn
2. load active relational state and relevant projection evidence
3. build a deterministic relational baseline for the turn
4. run candidate adjudication when the live relational moment or stance delta needs bounded judgment
5. run grounded observation extraction when the turn contains relational learning signals
6. validate, activate, and surface through deterministic code
7. compile the effective relational contract
8. decide whether the stance should stay implicit or get a compact or richer explanation
9. respond naturally inside that contract
10. persist deterministic traces, evidence, and state updates through runtime code
11. expose effective state through `/context` and deeper traces through inspection surfaces

### 4.5 Keep stance selection bounded

The relational runtime should not ask the model to invent an entire new relational state on every turn.

Preferred architecture:
- deterministic code loads the active baseline
- candidate adjudication may apply **small validated changes** when the moment warrants it
- code validates those changes and compiles the final contract
- later adaptive behavior should flow through the generalized substrate rather than through hidden prompt improvisation

This preserves:
- coherence
- inspectability
- bounded drift
- cleaner learning provenance

### 4.6 Keep most relational machinery implicit

Default user-facing rule:
- Alfred should usually **feel** the stance shift more than he narrates it

But the system must still support explanation when:
- the user asks
- the user reacts negatively to the stance
- a major relational shift materially affects trust
- a correction or boundary needs explicit acknowledgment

### 4.7 Keep the current support-domain implementation in its place

The repo currently ships support-domain learning and inspection behavior through PRD #183.
That is a current implementation constraint, not the generalized substrate design.

Relational work should therefore:
- stay compatible with current repo realities where needed
- avoid treating support-specific record names as universal architecture
- leave room for generalized substrate records later

If temporary adapters or compatibility layers are needed, they should be explicit.

---

## 5. User Experience Requirements

Users should experience Alfred as:
- more coherent in how he shows up relationally
- more capable of shifting tone or posture without becoming random or mode-y
- better at understanding moments that need steadiness, more care, less authority, or more directness
- better at learning relational preferences and boundaries from ordinary language
- able to explain stance shifts when asked without dumping internal jargon
- more adaptive without becoming more mysterious

Representative experiences:
- “Be more direct.”
- “Don’t talk to me like a therapist.”
- “Stay beside me here.”
- “Why are you being more blunt right now?”
- “That helped because you didn’t give me too much softness.”
- “I need less pressure and more steadiness tonight.”

---

## 6. Success Criteria

- [ ] Alfred's relational runtime is described as one projection plugged into the shared semantic runtime engine.
- [ ] Product-owned relational semantics and compiler behavior are specified clearly enough that raw values no longer stand in for behavior.
- [ ] The live relational moment is handled through bounded candidate adjudication rather than only through fixed transient flags.
- [ ] Stance selection is based on bounded deltas against a deterministic baseline rather than unconstrained rewrites.
- [ ] Relational preferences and boundaries can be extracted from ordinary language with grounding and validation.
- [ ] Alfred can decide when to keep stance implicit and when to explain it through a bounded surfacing seam.
- [ ] Embeddings remain focused on retrieval and shortlist roles.
- [ ] This PRD does not treat support-domain implementation artifacts as the shared architecture.

---

## 7. Milestones

### Milestone 1: Align the relational projection with the shared engine
Document the relational projection against the architecture doc and shared substrate contract.

Validation: relational child PRDs inherit one architecture and do not invent a parallel semantic system.

### Milestone 2: Define product-owned semantics and compiler behavior
Ship the semantics and compiler contract in PRD #193.

Validation: relational dimensions cash out into concrete compiler behavior and readable stance summaries.

### Milestone 3: Add relational candidate-adjudication seams
Ship PRDs #194 and #195.

Validation: Alfred can assess the live relational moment and apply bounded stance shifts against a deterministic baseline.

### Milestone 4: Add grounded relational observation extraction
Ship PRD #196.

Validation: ordinary language can produce relational observations without bypassing deterministic runtime rules.

### Milestone 5: Add relational surfacing and explanation behavior
Ship PRD #197.

Validation: Alfred can keep stance implicit by default and explain it when trust or user request requires it.

---

## 8. Likely File Changes

```text
prds/192-relational-runtime-semantics-and-stance-adjudication.md
prds/193-product-owned-relational-semantics-and-compiler-contract.md
prds/194-semantic-relational-state-adjudication-for-live-turns.md
prds/195-semantic-relational-stance-adjudication.md
prds/196-natural-language-relational-preference-and-boundary-extraction.md
prds/197-relational-surfacing-and-meta-explanation.md
docs/architecture/semantic-runtime-engine.md
docs/ARCHITECTURE.md
docs/relational-support-model.md
src/alfred/support_policy.py
src/alfred/support_reflection.py
tests/test_support_policy.py
tests/test_support_reflection.py
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| The relational layer creates a second semantic system parallel to the shared substrate | High | keep the engine contract in the architecture doc and PRD #185 |
| Relational adjudication becomes vague or therapist-like | High | keep the ontology small, outputs closed, and fallbacks explicit |
| Prompt vibe keeps overpowering structured relational semantics | High | define compiler behavior and bounded seams explicitly in the child PRDs |
| Current support-domain implementation details leak upward into relational architecture | Medium | treat them as compatibility constraints, not target design |

---

## 10. Open Questions

1. Which relational moments actually need separate live-state adjudication versus deterministic rules?
2. How should mixed support+relational turns compose multiple projection seams without bloating prompts?
3. What compatibility layer, if any, is needed while the repo still uses support-domain implementation records from PRD #183?
