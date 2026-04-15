# PRD: Support Projection Work on the Semantic Runtime Engine

**Architecture Doc**: [docs/architecture/semantic-runtime-engine.md](../docs/architecture/semantic-runtime-engine.md)
**Shared Contract PRD**: [#185 Generalized Semantic Runtime Substrate Contract and Ontology Projection Envelope](./185-shared-semantic-adjudication-contract-and-symbolic-runtime-inputs.md)
**GitHub Issue**: [#184](https://github.com/jeremysball/alfred/issues/184)
**Priority**: High
**Status**: Draft
**Created**: 2026-04-07
**Author**: Agent

> This PRD is a projection-planning doc downstream of the architecture doc. It does not own the shared substrate design.

---

## 1. Problem Statement

Alfred's support runtime still depends on several seams that are more hand-tuned than principled.

Today, important support decisions are still made through a mix of:
- lexical phrase checks
- normalized substring matching
- alias and token-overlap scoring
- small embedding prototype banks
- additive heuristic score stacks

That creates five problems:

1. **Support semantics are still implemented too heuristically**
   - session-start routing, support-need classification, subject resolution, and pattern surfacing are pragmatic judgments
   - those are not a great fit for phrase families, cue maps, or local scoring stacks

2. **The support projection underuses structured runtime facts**
   - Alfred already has operational state, situations, values, patterns, and explicit control signals
   - current seams often flatten that structure too early

3. **Support work can drift into shared-architecture language**
   - support is an important projection, but it is not the semantic runtime engine itself
   - this PRD should describe support projection behavior, not redefine the shared substrate

4. **Embeddings are doing work they are not best suited for**
   - embeddings are strong for retrieval and shortlist generation
   - they are weaker as the final authority for bounded pragmatic judgments

5. **Current support-domain implementation details could be mistaken for cross-domain architecture**
   - today's support-specific learning records and ledgers are real implementation constraints
   - they should not define the support projection's long-term architecture contract

---

## 2. Goals

1. Apply the shared semantic-runtime architecture to the support projection.
2. Replace heuristic support seams with bounded candidate adjudication or grounded observation extraction where appropriate.
3. Preserve rich support-domain symbolic state instead of flattening it into thin prompts.
4. Keep support activation, persistence, precedence, and surfacing deterministic in code.
5. Keep embeddings responsible for retrieval, shortlist generation, clustering, and similarity search rather than final pragmatic judgments.
6. Keep support projection work compatible with the current repo while avoiding support-specific substrate assumptions.
7. Break support projection work into smaller child PRDs without turning this PRD into an architecture doc.

---

## 3. Non-Goals

- Replacing retrieval, vector search, or clustering with LLM-only search.
- Letting the model write directly to storage without deterministic validation.
- Turning support routing into an unconstrained freeform reasoning loop.
- Treating current support-domain implementation artifacts as the permanent shared substrate.
- Flattening curated memory, support projection state, and explicit durable truth into one lane.

---

## 4. Proposed Solution

### 4.1 Treat support as one ontology projection of the shared engine

The support projection should plug into the architecture from `docs/architecture/semantic-runtime-engine.md`.

This means support work should reuse the three shared abstractions:
1. **candidate adjudication**
2. **grounded observation extraction**
3. **deterministic activation and surfacing policy**

This PRD owns the support projection's use of those abstractions.
It does **not** own the shared substrate contract.

### 4.2 Use candidate adjudication for bounded support choices

For support-runtime seams that are fundamentally pragmatic choices, Alfred should use bounded model judgment over structured runtime facts and candidate sets.

Target support-domain candidate-adjudication seams:
- session-start routing
- support-need adjudication
- subject adjudication
- pattern surfacing and reflection guidance

Each adjudicator should answer a narrow question with a closed schema.

### 4.3 Use grounded observation extraction for support-language signals

For seams where the runtime needs typed support observations from natural language, Alfred should use bounded extraction rather than phrase hacks.

Target support-domain observation-extraction seams:
- corrections
- support preferences
- feedback
- scope updates
- interpretation rejection

The extractor may emit zero or more observations.
It does not activate, promote, or persist values by itself.

### 4.4 Preserve support-domain symbolic information

The point is not to replace Alfred's support model with prompt vibes.
The point is to let the model reason over support-domain symbolic state Alfred already has.

That means support-domain requests should carry structured data such as:
- current user turn
- previous assistant reply when relevant
- candidate arcs and domains with stable ids and compact summaries
- global and arc situations
- active support and relational values when relevant
- recent support-domain evidence or patterns when relevant
- explicit control or scope refs when relevant

### 4.5 Keep deterministic safeguards as the trust boundary

Every support-domain adjudicator or extractor must be wrapped in code-owned safeguards from the shared substrate contract.

Required safeguards:
- closed enums for allowed decisions
- candidate ids must come from the provided candidate set
- quote grounding when quotes are returned
- max selection counts enforced in code
- explicit abstain / none outputs allowed
- invalid model output falls back to deterministic safe behavior
- persistence and status mutation happen only after validation

### 4.6 Keep the current support-domain implementation in its place

The repo already ships support-domain learning and inspection behavior through PRD #183.
That is a real constraint.

But this PRD should treat PRD #183 as:
- current support-domain implementation
- inspection/control reality to stay compatible with for now
- not the definition of the support projection's shared architecture

If later substrate work replaces today's support-shaped records, the support projection should survive that migration without changing its product meaning.

### 4.7 Child PRD structure

This PRD governs support projection work such as:
- **PRD #186** — semantic session-start routing for resume and orientation
- **PRD #187** — semantic need adjudication for the support projection
- **PRD #188** — semantic subject adjudication for the support projection
- **PRD #189** — natural-language support observation extraction
- **PRD #190** — semantic pattern surfacing and reflection guidance

Boundary rule:
- the architecture doc owns the shared engine design
- PRD #185 owns the shared substrate contract
- this PRD owns support projection behavior and implementation planning

---

## 5. User Experience Requirements

Users should experience Alfred as:
- better at understanding what kind of help they are asking for
- better at resuming work or orienting broadly without needing canned wording
- better at tracking what “this,” “that,” or an implied thread refers to
- more capable of learning from natural corrections and preferences without brittle phrase hacks
- more thoughtful about when to surface a support pattern and when to stay silent
- still bounded, inspectable, and corrigible rather than magical or opaque

Representative experiences:
- “What am I even in the middle of right now?”
- “Can we pick back up the taxes thing from last week?”
- “Don’t give me options. Just tell me the next step.”
- “No, that’s not what’s going on.”
- “Be more direct.”
- “That actually helped.”
- “Why are you bringing this up now?”

---

## 6. Success Criteria

- [ ] Support-runtime behavior is described as support projection work on one shared semantic runtime engine.
- [ ] Alfred forwards rich symbolic support state into support-domain adjudicators and extractors instead of collapsing it into thin strings.
- [ ] Session-start routing no longer depends on phrase lists or title substring matching as the primary path.
- [ ] Support need is no longer primarily classified by embedding similarity to a tiny prototype bank.
- [ ] Subject resolution no longer depends on alias-hit and token-overlap score soup as the primary path.
- [ ] Support-language observations can be extracted with quote grounding and deterministic validation.
- [ ] Pattern surfacing uses bounded semantic judgment after retrieval rather than additive heuristic scoring alone.
- [ ] Embeddings remain in place for retrieval-oriented seams.
- [ ] This PRD does not act like the shared architecture doc.

---

## 7. Milestones

### Milestone 1: Align the support projection with the shared engine
Document the support projection against the architecture doc and shared substrate contract.

Validation: support child PRDs inherit one architecture without re-explaining it.

### Milestone 2: Replace support-domain candidate-choice heuristics
Ship support-domain candidate adjudication for routing, need, subject, and surfacing seams.

Validation: those seams no longer depend primarily on heuristic score stacks.

### Milestone 3: Add grounded support observation extraction
Ship bounded support observation extraction for preferences, corrections, feedback, scope, and interpretation rejection.

Validation: grounded observations are emitted with quotes and deterministic validation.

### Milestone 4: Align docs and inspection surfaces
Update docs and inspection text so support projection behavior is described truthfully against the shared engine.

Validation: runtime behavior, docs, and related PRDs stay aligned.

---

## 8. Likely File Changes

```text
prds/184-semantic-adjudication-runtime-for-support-routing-and-learning.md
prds/185-shared-semantic-adjudication-contract-and-symbolic-runtime-inputs.md
prds/186-semantic-session-start-routing-for-resume-and-orientation.md
prds/187-semantic-need-adjudication-for-support-runtime.md
prds/188-semantic-subject-adjudication-for-support-runtime.md
prds/189-natural-language-observation-extraction-for-support-learning.md
prds/190-semantic-pattern-surfacing-and-reflection-guidance.md
docs/architecture/semantic-runtime-engine.md
docs/ARCHITECTURE.md
docs/relational-support-model.md
src/alfred/memory/support_context.py
src/alfred/support_policy.py
src/alfred/support_reflection.py
src/alfred/context_display.py
src/alfred/interfaces/pypitui/commands/show_context.py
src/alfred/interfaces/webui/server.py
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Support adjudication becomes vague or unconstrained | High | require closed schemas, candidate validation, abstain paths, and deterministic fallbacks |
| The support projection loses rich symbolic state during the transition | High | make structured projection inputs part of the shared contract in PRD #185 |
| Embeddings get removed from places where they are still the best tool | High | state the responsibility split explicitly in this PRD and child PRDs |
| This PRD starts acting like the architecture doc again | Medium | keep the engine contract in the architecture doc and PRD #185 |

---

## 10. Open Questions

1. How large can support-domain candidate packets get before prompt quality regresses?
2. Which support seams actually benefit from model judgment versus deterministic rules alone?
3. How should current support-domain inspection surfaces adapt when the generalized substrate replaces today's support-shaped records later?
