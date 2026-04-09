# PRD: Semantic Adjudication Runtime for Support Routing and Learning

**GitHub Issue**: [#184](https://github.com/jeremysball/alfred/issues/184)  
**Priority**: High  
**Status**: Draft  
**Created**: 2026-04-07  
**Author**: Agent

---

## 1. Problem Statement

Alfred's support runtime still depends on several seams that are more hand-tuned than principled.

Today, important support decisions are made through a mix of:
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
   - Alfred already has arcs, domains, blockers, tasks, situations, active runtime values, recent episodes, and scoped patterns.
   - The current logic often compresses that rich structure into thin strings or local heuristics instead of letting the model reason over the real state.

3. **The current seams are hard to extend and hard to trust**
   - The logic is spread across `support_context`, `support_policy`, and `support_reflection` with different local scoring rules.
   - Each seam has its own thresholds, cues, and special cases.

4. **Embeddings are doing work they are not best suited for**
   - Embeddings are strong for retrieval and shortlist generation.
   - They are weaker as the final authority for bounded semantic judgments such as “what is the user's need here?” or “should I surface this pattern now?”

5. **There is no umbrella contract for LLM adjudication yet**
   - If Alfred replaces heuristics with ad hoc model calls, the result could become opaque, inconsistent, and harder to validate.
   - The system needs one parent model that preserves symbolic structure, keeps deterministic safeguards, and defines where embeddings still belong.

The result is a runtime that already has strong symbolic foundations, but still routes and interprets user turns through seams that are too brittle for the job.

---

## 2. Goals

1. Replace heuristic support-routing seams with **bounded LLM semantic adjudication**.
2. Preserve and forward Alfred's **rich symbolic runtime state** to the LLM instead of flattening it into thin prompts.
3. Define one shared contract for semantic-adjudication inputs, outputs, validation, observability, and fallback behavior.
4. Keep embeddings responsible for retrieval, shortlist generation, clustering, and similarity search rather than final pragmatic judgments.
5. Keep persistence, scope resolution, promotion, and status transitions deterministic in code.
6. Break the work into small child PRDs rather than one oversized rewrite.
7. Keep the runtime inspectable, testable, and maintainable as model judgment expands.
8. Align this work with PRD #183 without folding the learning-model rewrite and the semantic-adjudication rewrite into one giant PRD.
9. Keep curated memory as a separate explicit memory lane rather than letting semantic adjudication flatten support memory, support learning, and remembered facts into one generic system.

---

## 3. Non-Goals

- Replacing retrieval, vector search, or clustering with LLM-only search.
- Letting the LLM write directly to storage without deterministic validation.
- Hiding symbolic runtime state behind prompt-only prose.
- Preserving the current heuristic seams long-term once the adjudicated path ships.
- Collapsing PRD #183 and this semantic-runtime work into one umbrella document.
- Turning support routing into an unconstrained freeform reasoning loop.

---

## 4. Proposed Solution

### 4.1 Use the LLM for bounded semantic adjudication

For support-runtime seams that are fundamentally semantic or pragmatic, Alfred should use direct model prompts over structured runtime state.

Target seams:
- session-start routing
- support-need adjudication
- subject adjudication
- natural-language observation extraction
- pattern surfacing and reflection guidance

Each adjudicator should answer a narrow question with a closed schema.

### 4.2 Preserve symbolic runtime information

The point is not to replace Alfred's symbolic model with prompt vibes.

The point is to let the LLM reason over the symbolic model Alfred already has.

That means adjudication requests should carry structured data such as:
- opening message or current user turn
- previous assistant reply when relevant
- candidate arcs and domains with stable ids and compact summaries
- global and arc situations
- active support and relational values
- active response mode or fresh-session state when relevant
- retrieved pattern candidates and their evidence summaries
- message ids, attempt ids, and scope refs when relevant

This symbolic packet is part of the architecture, not an implementation detail.

### 4.3 Keep deterministic safeguards as the trust boundary

Every adjudicator must be wrapped in code-owned safeguards.

Required safeguards:
- closed enums for allowed decisions
- candidate ids must come from the provided candidate set
- quote grounding when a quote or excerpt is returned
- max selection counts enforced in code
- explicit abstain / none outputs allowed
- invalid model output falls back to deterministic safe behavior
- all persistence and status mutation happens only after validation

### 4.4 Keep embeddings in their best-fit role

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
- surfacing decisions

### 4.5 Parent / child PRD structure

This PRD is the umbrella model for the following child PRDs:
- **PRD #185** — shared semantic-adjudication contract and symbolic runtime inputs
- **PRD #186** — semantic session-start routing for resume and orientation
- **PRD #187** — semantic need adjudication for support runtime
- **PRD #188** — semantic subject adjudication for support runtime
- **PRD #189** — natural-language observation extraction for support learning
- **PRD #190** — semantic pattern surfacing and reflection guidance

PRD #183 remains a sibling PRD.

Relationship to sibling PRDs:
- **this PRD** owns how Alfred makes bounded semantic judgments during runtime
- **PRD #183** owns the case-based learning model, value ledger, and full inspection surfaces
- **PRD #191** owns curated-memory auto-injection, liberalized `remember` capture, and the boundary rules that keep curated memory supplemental to support memory and support learning

Boundary rule:
- semantic adjudication may consume curated memories as one input among others
- it does not turn curated memory into the system of record for active work state or adaptive support policy

### 4.6 Repository responsibility split

Adopt this repo-wide split for support-runtime interpretation work:

- **LLM adjudication**
  - semantic routing
  - pragmatic classification
  - reference resolution
  - grounded observation extraction
  - bounded surfacing decisions

- **Embeddings**
  - retrieval
  - shortlist generation
  - similarity search
  - clustering
  - duplicate suppression

- **Deterministic code**
  - validation
  - fallback behavior
  - persistence
  - scope resolution
  - policy loading
  - promotion, demotion, and status rules

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

- [ ] Support-runtime adjudication uses one clear shared contract rather than ad hoc prompt calls or scattered heuristics.
- [ ] Alfred forwards rich symbolic state into adjudicators instead of collapsing it into thin strings.
- [ ] Session-start routing no longer depends on phrase lists or title substring matching as the primary path.
- [ ] Support need is no longer primarily classified by embedding similarity to a tiny prototype bank.
- [ ] Subject resolution no longer depends on alias-hit and token-overlap score soup as the primary path.
- [ ] Natural-language observations can be extracted with quote grounding and deterministic validation.
- [ ] Pattern surfacing uses bounded semantic judgment after retrieval rather than additive heuristic scoring alone.
- [ ] Embeddings remain in place for retrieval-oriented seams.
- [ ] Docs and child PRDs describe the same responsibility split, safety model, and memory-lane boundaries.

---

## 7. Milestones

### Milestone 1: Define the shared adjudication contract
Ship the umbrella contract for symbolic inputs, closed outputs, validation, fallback, and observability.

Validation: the child PRDs can reuse one adjudication model instead of inventing their own incompatible prompt contracts.

### Milestone 2: Replace session-start routing heuristics
Ship semantic routing for resume versus broad orientation versus neither.

Validation: fresh-session routing handles paraphrase and indirect wording without relying on phrase lists.

### Milestone 3: Replace need and subject heuristics
Ship semantic adjudication for support need and subject selection.

Validation: support runtime chooses need and subject through bounded model judgment over symbolic candidates.

### Milestone 4: Add grounded natural-language observation extraction
Ship observation extraction for corrections, preferences, feedback, scope updates, and interpretation rejection.

Validation: grounded observations are emitted with quotes, confidence, and deterministic safeguards.

### Milestone 5: Replace pattern-surfacing score stacks
Ship semantic surfacing decisions over retrieved pattern candidates.

Validation: Alfred can decide whether to surface a pattern now, not merely whether one is similar.

### Milestone 6: Align docs and inspection surfaces
Update docs and support inspection text so they describe the adjudicated runtime truthfully.

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
docs/ROADMAP.md
src/alfred/memory/support_context.py
src/alfred/support_policy.py
src/alfred/support_reflection.py
src/alfred/context_display.py
src/alfred/interfaces/pypitui/commands/show_context.py
src/alfred/interfaces/webui/server.py
docs/relational-support-model.md
docs/self-model.md
docs/websocket-protocol.md
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| LLM adjudication becomes vague or unconstrained | High | require closed schemas, candidate validation, abstain paths, and deterministic fallbacks |
| The system loses rich symbolic information during the transition | High | make structured symbolic packets part of the shared contract in PRD #185 |
| Embeddings get removed from places where they are still the best tool | High | state the responsibility split explicitly in the parent PRD and child PRDs |
| Runtime behavior becomes harder to debug | Medium | add observability for adjudicator inputs, outputs, validation failures, and fallback paths |
| Child PRDs drift into inconsistent prompt contracts | High | use this PRD as the parent model and centralize the contract in PRD #185 |
| PRD #183 and this work drift apart | Medium | keep cross-references explicit: runtime semantic judgment here, case-based learning and inspection in #183 |

---

## 10. Open Questions

1. Which adjudicators should run synchronously on the hot path versus asynchronously after response generation?
2. How much symbolic state can each adjudicator see before latency or prompt sprawl becomes a problem?
3. Which adjudication traces should be exposed through `/support` or other inspection paths?
4. Should some adjudicators use smaller, cheaper models than the main response model if the schema is narrow enough?
5. How much shared infrastructure can be reused with PRD #183's observation and case model without coupling the two PRDs too tightly?
