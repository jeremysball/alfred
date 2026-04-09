# PRD: Relational Runtime Semantics and Stance Adjudication

**GitHub Issue**: [#192](https://github.com/jeremysball/alfred/issues/192)  
**Priority**: High  
**Status**: Draft  
**Created**: 2026-04-09  
**Author**: Agent

---

## 1. Problem Statement

Alfred's recent support-runtime PRDs sharpen the architecture for support routing, case-based learning, and inspection. The relational layer still lags behind that design quality.

Today, important relational behavior still depends too much on:
- prompt voice and template prose
- hand-tuned default tables
- thin transient flags
- raw relational values that do not yet cash out into concrete runtime behavior
- weak or missing seams for relational preference extraction and stance explanation

That creates six problems:

1. **Relational semantics are still too implicit**
   - Alfred has relational dimensions such as `candor`, `companionship`, and `authority`.
   - The product does not yet define those dimensions crisply enough as runtime behavior.
   - The current compiler still reads too much like a value dump.

2. **The live relational moment lacks a bounded semantic seam**
   - The runtime needs to judge things like fragility, invitation for directness, steadiness needs, rupture risk, and openness to challenge.
   - Thin transient flags and hand-written adjustments are not enough for that job.

3. **Stance selection is still too default-driven**
   - Alfred is meant to shift gracefully among friend, peer, mentor, coach, and analyst positions without becoming crude persona modes.
   - Right now, stance selection still depends too heavily on defaults, scoped values, and pattern overrides rather than bounded semantic judgment.

4. **Relational learning signals are underpowered**
   - Users express relational preferences and boundaries in ordinary language.
   - Alfred still lacks a dedicated, grounded path for extracting those signals as first-class relational observations.

5. **Relational explanation is underdesigned**
   - Alfred needs a principled answer to questions like “why are you being more direct right now?”
   - The runtime does not yet have a bounded seam for deciding when to keep a stance shift implicit and when to explain it.

6. **The relational layer needs better architectural boundaries**
   - PRD #183 already defines the shared learning ledger, status model, and inspection surfaces Alfred should use.
   - The relational layer should not create a parallel learning architecture.
   - It needs a sibling runtime model that plugs into #183 cleanly instead of bypassing it.

The result is a relational layer that feels mushy: too much prompt vibe, too little bounded runtime judgment, and unclear separation among live stance selection, learned preferences, and user-facing explanation.

---

## 2. Goals

1. Define one parent architecture for Alfred's relational runtime as a sibling to PRD #184.
2. Keep one shared learning, ledger, and inspection model with PRD #183 rather than creating a second relational learning system.
3. Replace heuristic or prompt-only relational judgments with bounded semantic adjudication where the job is fundamentally pragmatic.
4. Define product-owned relational semantics that cash out into concrete compiler behavior.
5. Define a bounded live-turn relational-state seam that informs stance selection without becoming freeform psychologizing.
6. Define a bounded stance-adjudication seam that applies small validated shifts against a deterministic baseline.
7. Define a dedicated relational observation path for natural-language preferences, boundaries, stance feedback, and rupture signals.
8. Define a bounded meta-explanation seam for when Alfred should explain his relational stance or shift.
9. Keep embeddings focused on retrieval, shortlist generation, and similar-case recall rather than final relational judgment.
10. Keep docs, prompts, inspection text, and runtime behavior aligned.

---

## 3. Non-Goals

- Creating separate hard-coded personas for friend, peer, mentor, coach, or analyst.
- Building a separate relational learning ledger outside PRD #183.
- Letting the LLM write directly to persistence or status transitions.
- Turning Alfred into an unbounded therapy-theater runtime.
- Replacing support need, subject, or pattern-surfacing PRDs with relational work.
- Preserving current heuristic seams long-term when a bounded adjudicated seam supersedes them.

---

## 4. Proposed Solution

### 4.1 Treat the relational layer as a sibling runtime, not a parallel product

PRDs #183 through #190 already define a strong direction for:
- case-based learning
- bounded semantic adjudication for support-routing seams
- explicit inspection and ledger semantics

This PRD extends that taste into the relational layer.

The relational layer should own:
- product semantics for relational dimensions
- live relational-state adjudication
- stance adjudication
- relational observation extraction
- relational surfacing and meta-explanation

The relational layer should **not** own:
- a separate value ledger
- a separate pattern ledger
- separate persistence invariants
- a separate inspection truth

Those remain shared with PRD #183.

### 4.2 Use the same responsibility split as the new support PRDs

Adopt this split for relational-runtime interpretation work:

- **LLM adjudication**
  - live relational-state judgment
  - bounded stance adjustment
  - relational preference and boundary extraction
  - relational meta-explanation and surfacing

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
  - status mutation
  - inspection payloads

### 4.3 PRD map

This parent PRD governs the following child PRDs:

- **PRD #193 — Product-Owned Relational Semantics and Compiler Contract**
  - define what each relational dimension means behaviorally
  - define richer compiler outputs and readable stance summaries

- **PRD #194 — Semantic Relational-State Adjudication for Live Turns**
  - infer the live relational conditions of the moment through bounded semantic judgment

- **PRD #195 — Semantic Relational Stance Adjudication**
  - choose bounded per-turn stance deltas against a deterministic baseline

- **PRD #196 — Natural-Language Relational Preference and Boundary Extraction**
  - extract grounded relational preferences, boundaries, stance feedback, and rupture signals from normal conversation

- **PRD #197 — Relational Surfacing and Meta-Explanation**
  - decide when Alfred should keep the stance implicit, give a compact explanation, or explain a larger shift

Relationship to existing PRDs:
- **PRD #183** owns the shared learning, case, ledger, and inspection model
- **PRD #184** owns the umbrella support-runtime semantic adjudication architecture
- **PRD #185** owns the shared adjudication envelope, validation, fallback, and observability model
- **PRDs #186–#190** own support-routing and reflection seams that remain support-focused

### 4.4 Keep one shared runtime loop

The target runtime loop for relational behavior should be:

1. resolve support need, response mode, and subjects through the support-runtime path
2. load active relational values and active relational patterns through the shared ledger rules from PRD #183
3. build a deterministic relational baseline for the turn
4. adjudicate the live relational state when the moment warrants it
5. adjudicate a bounded stance delta against the baseline
6. compile the effective relational contract
7. decide whether the stance should stay implicit or get a compact or richer explanation
8. respond naturally inside that contract
9. record attempts, observations, and cases through the shared PRD #183 model
10. expose active state through `/context` and full ledger / traces through `/support`

### 4.5 Keep stance selection bounded

The relational runtime should not ask the model to invent an entire new relational state on every turn.

Preferred architecture:
- deterministic code loads the active baseline
- LLM adjudication may apply **small validated changes** when the moment warrants it
- code validates those changes and compiles the final contract
- learning later decides whether repeated successful shifts become active state through PRD #183

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

### 4.7 Inspection model

Relational work must preserve the split established in PRD #183:

- **`/context`** shows effective runtime state
  - active relational values
  - active source and scope
  - current effective stance summary or contract summary
  - recent automatic changes when relevant

- **`/support`** shows the full ledger and trace model
  - active, shadow, confirmed, rejected, retired values
  - active, candidate, confirmed, rejected, retired patterns
  - cases, observations, update events, and provenance

This parent PRD should not introduce a second relational inspection truth.

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

- [ ] Alfred's relational runtime is described as one coherent architecture rather than a mix of prompt voice, default tables, and ad hoc flags.
- [ ] Product-owned relational semantics and compiler behavior are specified clearly enough that raw values no longer stand in for behavior.
- [ ] The live relational moment is handled through a bounded adjudication seam rather than only through fixed transient flags.
- [ ] Stance selection is based on bounded deltas against a deterministic baseline rather than unconstrained rewrites.
- [ ] Relational preferences and boundaries can be extracted from ordinary language with grounding and validation.
- [ ] Alfred can decide when to keep stance implicit and when to explain it through a bounded meta-explanation seam.
- [ ] Embeddings remain focused on retrieval and shortlist roles.
- [ ] PRD #183 remains the single ledger and inspection model for both support and relational learning.
- [ ] Docs and managed prompts can describe the shipped relational runtime truthfully.

---

## 7. Milestones

### Milestone 1: Define the relational runtime map and responsibility split
Document the relational sibling architecture, the shared boundary with PRD #183, and the child-PRD map.

Validation: the relational work has one parent model and does not invent a parallel learning architecture.

### Milestone 2: Define product-owned semantics and compiler behavior
Ship the semantics and compiler contract in PRD #193.

Validation: relational dimensions cash out into concrete compiler behavior and readable stance summaries.

### Milestone 3: Add live relational-state and stance adjudication seams
Ship PRDs #194 and #195.

Validation: Alfred can assess the live relational moment and apply bounded stance shifts against a deterministic baseline.

### Milestone 4: Add grounded relational observation extraction
Ship PRD #196.

Validation: ordinary language can produce relational observations without bypassing deterministic learning rules.

### Milestone 5: Add bounded relational surfacing and explanation
Ship PRD #197.

Validation: Alfred can usually keep relational machinery implicit while still explaining stance shifts when appropriate.

### Milestone 6: Align docs, prompts, and inspection surfaces
Update docs, templates, and inspection payloads so they describe the same runtime.

Validation: docs, prompts, and shipped behavior agree.

---

## 8. Likely File Changes

```text
prds/192-relational-runtime-semantics-and-stance-adjudication.md
prds/193-product-owned-relational-semantics-and-compiler-contract.md
prds/194-semantic-relational-state-adjudication-for-live-turns.md
prds/195-semantic-relational-stance-adjudication.md
prds/196-natural-language-relational-preference-and-boundary-extraction.md
prds/197-relational-surfacing-and-meta-explanation.md
docs/ROADMAP.md
docs/relational-support-model.md
docs/how-alfred-helps.md
docs/self-model.md
templates/SYSTEM.md
templates/prompts/voice.md
src/alfred/support_policy.py
src/alfred/support_reflection.py
src/alfred/memory/support_learning.py
src/alfred/context_display.py
src/alfred/interfaces/pypitui/commands/show_context.py
src/alfred/interfaces/webui/server.py
src/alfred/interfaces/webui/static/js/components/context-viewer.js
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| The relational layer creates a second learning system parallel to PRD #183 | High | keep #183 as the single ledger, status, and inspection model |
| Relational adjudication becomes vague or therapist-like | High | keep the ontology small, outputs closed, and fallbacks explicit |
| Stance shifts become too freeform and hard to trust | High | use deterministic baselines plus bounded deltas rather than unconstrained rewrites |
| Meta-explanation becomes over-narration | Medium | keep implicit behavior as the default and make explanation bounded |
| Prompt docs outrun runtime reality again | High | require docs and prompt alignment as part of completion |
| Relational extraction duplicates PRD #189 badly | Medium | keep #196 tightly scoped to relational observations and compatible with the shared learning model |

---

## 10. Validation Strategy

This PRD is architecture-first and documentation-first.

Validation for the planning pass should focus on:
- alignment with PRDs #179, #183, #184, and #185
- clear separation between relational runtime seams and shared learning / inspection seams
- explicit reuse of the support-runtime taste for bounded adjudication, fallback, and observability
- clear child-PRD ownership boundaries without overlap-heavy duplication

Implementation work from this parent PRD will likely touch Python and documentation, and may later affect JavaScript inspection surfaces.

Required validation for implementation should therefore include the relevant workflows for touched files:

### Python workflow
```bash
uv run ruff check src/
uv run mypy --strict src/
uv run pytest <targeted tests for touched support-policy, reflection, learning, and inspection surfaces>
```

### JavaScript workflow
```bash
npm run js:check
```

---

## 11. Related PRDs

- PRD #179: Relational Support Operating Model
- PRD #183: Support Learning V2 - Case-Based Adaptation and Full Inspection
- PRD #184: Semantic Adjudication Runtime for Support Routing and Learning
- PRD #185: Shared Semantic Adjudication Contract and Symbolic Runtime Inputs
- PRD #189: Natural-Language Observation Extraction for Support Learning

---

## 12. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-09 | Create a parent relational-runtime PRD as a sibling to PRD #184 | The relational layer needs the same architectural sharpness the support-runtime adjudication work now has |
| 2026-04-09 | Keep one shared learning, ledger, and inspection model with PRD #183 | The relational layer should not create a parallel persistence and status architecture |
| 2026-04-09 | Use bounded adjudication for live relational-state judgment, stance selection, extraction, and explanation seams | These are pragmatic semantic jobs, not good fits for raw heuristics or prompt vibes |
| 2026-04-09 | Keep embeddings focused on retrieval and shortlist roles | The newer support PRDs already establish this split, and the relational layer should follow it |
| 2026-04-09 | Prefer bounded stance deltas against a deterministic baseline over full per-turn relational rewrites | This preserves coherence, inspectability, and cleaner learning provenance |
| 2026-04-09 | Keep relational machinery implicit by default and explain it only when useful or necessary | Alfred should feel natural rather than mechanically narrated |
