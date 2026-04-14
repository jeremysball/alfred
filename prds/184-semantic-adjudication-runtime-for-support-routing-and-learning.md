# PRD: Semantic Adjudication Runtime for Support Routing and Learning

**Architecture Doc**: [docs/architecture/semantic-runtime-engine.md](../docs/architecture/semantic-runtime-engine.md)  
**GitHub Issue**: [#184](https://github.com/jeremysball/alfred/issues/184)  
**Priority**: High  
**Status**: Draft  
**Created**: 2026-04-07  
**Author**: Agent

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

1. **Semantic judgments are delegated to weak mechanisms**
   - Session-start routing, support-need classification, subject resolution, and pattern surfacing are pragmatic judgments.
   - Those are not a great fit for phrase families, cue maps, or small prototype banks.

2. **Rich symbolic state is computed, then underused**
   - Alfred already has arcs, domains, blockers, tasks, situations, active runtime values, recent attempts, observations, cases, and scoped patterns.
   - The current logic often compresses that structure into thin strings or local heuristics.

3. **The current seams are hard to extend and hard to trust**
   - The logic is spread across `support_context`, `support_policy`, and `support_reflection` with different local scoring rules.
   - Each seam has its own thresholds, cues, and special cases.

4. **Embeddings are doing work they are not best suited for**
   - Embeddings are strong for retrieval and shortlist generation.
   - They are weaker as the final authority for bounded semantic judgments such as “what is the user's need here?” or “should I surface this pattern now?”

5. **The architecture is still described too seam-by-seam**
   - Alfred risks growing several semantic mini-systems instead of one reusable runtime.
   - The support-domain work should be framed as applications of a shared semantic runtime engine, not as a pile of unrelated classifiers.

---

## 2. Goals

1. Reframe support-runtime semantics as applications of the shared semantic runtime engine in `docs/architecture/semantic-runtime-engine.md`.
2. Replace heuristic support-routing seams with bounded LLM semantic adjudication where the job is fundamentally a candidate choice or ranking.
3. Replace brittle language parsing with bounded grounded observation extraction where the job is to emit typed support observations.
4. Keep persistence, activation, promotion, and surfacing deterministic in code.
5. Preserve and forward Alfred's rich symbolic runtime state instead of flattening it into thin prompts.
6. Keep embeddings responsible for retrieval, shortlist generation, clustering, and similarity search rather than final pragmatic judgments.
7. Break the work into small child PRDs without losing the shared architecture.
8. Keep this work aligned with PRD #183's shared attempt / observation / case foundation.

---

## 3. Non-Goals

- Replacing retrieval, vector search, or clustering with LLM-only search.
- Letting the LLM write directly to storage without deterministic validation.
- Hiding symbolic runtime state behind prompt-only prose.
- Treating support routing, support learning, and curated memory as one generic memory lane.
- Turning support routing into an unconstrained freeform reasoning loop.

---

## 4. Proposed Solution

### 4.1 Support work should plug into the shared semantic runtime engine

The support-domain work is an application of three shared abstractions:

1. **candidate adjudication**
2. **grounded observation extraction**
3. **deterministic activation and surfacing policy**

This PRD mainly owns the first and second abstractions for support-domain seams.
The third abstraction remains code-owned and shared with PRD #183.

### 4.2 Use candidate adjudication for bounded support choices

For support-runtime seams that are fundamentally semantic or pragmatic, Alfred should use bounded model judgment over structured runtime facts and candidate sets.

Target support-domain candidate-adjudication seams:
- session-start routing
- support-need adjudication
- subject adjudication
- pattern surfacing and reflection guidance

Each adjudicator should answer a narrow question with a closed schema.

### 4.3 Use grounded observation extraction for support-language signals

For seams where the runtime needs typed observations from natural language, Alfred should use bounded extraction rather than phrase hacks.

Target support-domain observation-extraction seams:
- corrections
- support preferences
- feedback
- scope updates
- interpretation rejection

The extractor may emit zero or more observations.
It does not activate, promote, or persist values by itself.

### 4.4 Preserve symbolic runtime information

The point is not to replace Alfred's symbolic model with prompt vibes.

The point is to let the LLM reason over the symbolic model Alfred already has.

That means support-domain requests should carry structured data such as:
- current user turn
- previous assistant reply when relevant
- candidate arcs and domains with stable ids and compact summaries
- global and arc situations
- active support and relational values
- recent attempts, observations, cases, and relevant patterns
- message ids, attempt ids, and scope refs when relevant

This symbolic packet is part of the architecture, not an implementation detail.

### 4.5 Keep deterministic safeguards as the trust boundary

Every support-domain adjudicator or extractor must be wrapped in code-owned safeguards.

Required safeguards:
- closed enums for allowed decisions
- candidate ids must come from the provided candidate set
- quote grounding when quotes are returned
- max selection counts enforced in code
- explicit abstain / none outputs allowed
- invalid model output falls back to deterministic safe behavior
- all persistence and status mutation happens only after validation

### 4.6 Keep embeddings in their best-fit role

Embeddings should remain primary for:
- memory retrieval
- session search
- similar-case retrieval
- shortlist generation
- clustering and deduplication

Embeddings should not remain the final authority for:
- turn need classification
- subject resolution
- correction detection
- pattern surfacing decisions

### 4.7 Child PRD structure

This PRD governs support-domain applications of the shared engine:
- **PRD #185** — shared semantic runtime contract and symbolic runtime inputs
- **PRD #186** — semantic session-start routing for resume and orientation
- **PRD #187** — semantic need adjudication for support runtime
- **PRD #188** — semantic subject adjudication for support runtime
- **PRD #189** — natural-language observation extraction for support learning
- **PRD #190** — semantic pattern surfacing and reflection guidance

Boundary rule:
- PRD #185 owns the common contract for candidate adjudication and observation extraction
- PRD #183 owns shared learning records, status semantics, activation, and inspection truth
- this PRD owns the support-domain semantic applications of that shared architecture

---

## 5. User Experience Requirements

Users should experience Alfred as:
- better at understanding what kind of help they are asking for
- better at resuming work or orienting broadly without needing canned wording
- better at tracking what “this,” “that,” or an implied thread refers to
- more capable of learning from natural corrections and preferences without brittle phrase hacks
- more thoughtful about when to surface a pattern and when to stay silent
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

- [ ] Support-runtime semantics are described as applications of one shared semantic runtime engine rather than ad hoc prompt calls or scattered heuristics.
- [ ] Alfred forwards rich symbolic state into support-domain adjudicators and extractors instead of collapsing it into thin strings.
- [ ] Session-start routing no longer depends on phrase lists or title substring matching as the primary path.
- [ ] Support need is no longer primarily classified by embedding similarity to a tiny prototype bank.
- [ ] Subject resolution no longer depends on alias-hit and token-overlap score soup as the primary path.
- [ ] Support-language observations can be extracted with quote grounding and deterministic validation.
- [ ] Pattern surfacing uses bounded semantic judgment after retrieval rather than additive heuristic scoring alone.
- [ ] Embeddings remain in place for retrieval-oriented seams.
- [ ] Docs and child PRDs describe the same shared engine, safety model, and memory-lane boundaries.

---

## 7. Milestones

### Milestone 1: Align the support parent with the shared engine
Document the support-domain boundary against the shared semantic runtime engine and the shared PRD #183 learning boundary.

Validation: support-domain child PRDs inherit one architecture instead of describing parallel systems.

### Milestone 2: Replace support-domain candidate-choice heuristics
Ship support-domain candidate adjudication for routing, need, subject, and surfacing seams.

Validation: those seams no longer depend primarily on heuristic score stacks.

### Milestone 3: Add grounded support observation extraction
Ship bounded support observation extraction for preferences, corrections, feedback, scope, and interpretation rejection.

Validation: grounded observations are emitted with quotes and deterministic validation.

### Milestone 4: Align docs and inspection surfaces
Update docs and inspection text so support-runtime behavior is described truthfully against the shared engine.

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
| LLM adjudication becomes vague or unconstrained | High | require closed schemas, candidate validation, abstain paths, and deterministic fallbacks |
| The support domain loses rich symbolic information during the transition | High | make structured symbolic packets part of the shared contract in PRD #185 |
| Embeddings get removed from places where they are still the best tool | High | state the responsibility split explicitly in the parent PRD and child PRDs |
| Runtime behavior becomes harder to debug | Medium | add observability for adjudicator inputs, outputs, validation failures, and fallback paths |
| Child PRDs drift into inconsistent prompt contracts | High | centralize the contract in PRD #185 and the architecture in the semantic runtime engine doc |
| Support and relational domains drift into parallel semantic systems | High | keep both domains explicitly mapped to the same shared engine |

---

## 10. Open Questions

1. Which support-domain adjudicators should run synchronously on the hot path versus asynchronously after response generation?
2. How much symbolic state can each support-domain request see before latency or prompt sprawl becomes a problem?
3. Which adjudication traces should be exposed through `/support` or other inspection paths?
4. Should some support-domain adjudicators use smaller, cheaper models than the main response model if the schema is narrow enough?
5. How much shared infrastructure can be reused with PRD #183's observation and case model without coupling the two PRDs too tightly?
