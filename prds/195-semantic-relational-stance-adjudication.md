# PRD: Semantic Relational Stance Adjudication

**Architecture Doc**: [docs/architecture/semantic-runtime-engine.md](../docs/architecture/semantic-runtime-engine.md)
**Parent PRD**: [#192 Relational Projection Work on the Semantic Runtime Engine](./192-relational-runtime-semantics-and-stance-adjudication.md)
**GitHub Issue**: [#195](https://github.com/jeremysball/alfred/issues/195)
**Priority**: High
**Status**: Draft
**Created**: 2026-04-09
**Author**: Agent

---

## 1. Problem Statement

Alfred's runtime still chooses relational stance mostly through deterministic defaults, stored scoped values, and pattern overrides.

That is useful as baseline policy, but not sufficient for the job Alfred is trying to do.

Today, the runtime can:
- load relational values by scope
- apply some pattern overrides
- apply a few thin transient adjustments
- compile a light stance summary

That creates five problems:

1. **The baseline is useful but too rigid**
   - Need and response mode should influence stance.
   - They should not be the whole story of how Alfred shows up in a live moment.

2. **Per-turn relational judgment is still underdesigned**
   - Alfred needs to shift in bounded ways when the current moment calls for more directness, more steadiness, less authority, or more emotional presence.
   - The runtime does not yet have a clean semantic seam for that.

3. **The current path mixes active learned state with live-turn improvisation**
   - Durable active values should matter.
   - But they should not be the same thing as per-turn stance judgment.

4. **A full per-turn rewrite would be too loose**
   - Asking the model to invent all relational values from scratch on every turn would be opaque and hard to trust.
   - The system needs a bounded middle ground.

5. **The support-runtime adjudication taste has not been applied yet**
   - The recent support PRDs replace heuristic final judgments with bounded semantic decisions over structured state.
   - The relational layer needs the same architecture.

This PRD applies the shared **candidate adjudication** primitive to bounded stance adjustment against a deterministic relational baseline.

---

## 2. Goals

1. Keep deterministic baseline loading for relational values.
2. Add shared candidate adjudication for per-turn relational shifts.
3. Prefer small validated deltas over unconstrained full rewrites.
4. Keep scope resolution, persistence, and activation deterministic.
5. Make the per-turn stance seam inspectable and fallback-safe.
6. Keep per-turn stance adjustment compatible with generalized deterministic evidence/update paths rather than hard-coding it to today's support-domain implementation.

---

## 3. Non-Goals

- Replacing scoped relational values or pattern loading.
- Letting the model choose unlimited per-turn relational states.
- Persisting per-turn stance deltas directly as durable truth.
- Owning relational semantics or compiler design. Those belong to PRD #193.
- Owning relational observation extraction or meta-explanation. Those belong to PRDs #196 and #197.

---

## 4. Proposed Solution

### 4.1 Keep a deterministic baseline

Before any per-turn adjudication, runtime should load the deterministic relational baseline from:
- active relational values by scope precedence
- active relational patterns or projected state made available through deterministic runtime loading
- support need and response-mode baseline policy
- validated runtime constraints from the compiler contract in PRD #193

This gives the turn a stable starting point.

### 4.2 Use the shared candidate-adjudication primitive on top of the baseline

The adjudicator should not invent the entire stance.

It should answer a narrower question:

> given the current baseline, the live relational state, and the current symbolic runtime context, should Alfred keep this baseline or apply a small validated shift for this turn?

Recommended top-level output:
- `no_change`
- or `adjust`

If `adjust`, the output may include up to a hard maximum of stance deltas.

### 4.3 Prefer bounded deltas over full value maps

Preferred output shape:
- `adjustments[]`
  - `dimension`
  - `target_value`
  - optional grounded quote
  - optional confidence

Hard constraints:
- max 3 adjustments per turn
- each `dimension` must come from the relational registry
- each `target_value` must be valid for that dimension
- duplicate dimensions are rejected
- invalid output falls back to `no_change`

Recommended safety refinement:
- by default, allow only target values that are the current value or an adjacent shift from the baseline band
- larger jumps should require an explicit override rule if later evidence shows they are necessary

### 4.4 Forward rich symbolic inputs

The stance adjudicator should receive:
- current user message
- previous assistant reply when relevant
- resolved support state
  - need
  - response mode
  - subjects
- active arc and domain context when present
- deterministic relational baseline
- live relational-state outputs from PRD #194
- active relational patterns when relevant
- shortlisted similar successful cases when relevant
- explicit output constraints

This lets the model reason over real symbolic state instead of only prompt prose.

### 4.5 Keep learning and runtime adjustment separate

Important rule:
- a per-turn stance delta is not automatically a learned preference

Instead:
- runtime may use the delta for this turn
- later evidence may show whether the shift helped
- repeated successful shifts may later influence active state through generalized deterministic update paths

This keeps the learning boundary clean.

### 4.6 Define example adjustment behavior

Illustrative outcomes:
- baseline `candor=medium`, live state invites bluntness -> adjust `candor` to `high`
- baseline `authority=medium`, user rejects advisor-like framing -> adjust `authority` to `low`
- baseline `momentum_pressure=medium`, high steadiness need -> adjust `momentum_pressure` to `low`
- baseline `warmth=medium`, high emotional tenderness -> adjust `warmth` to `high`
- baseline `challenge=medium`, high rupture risk -> adjust `challenge` to `low`

The important point is the shape, not these exact examples.

### 4.7 Keep deterministic application after validation

Once output is validated, code should:
- apply the deltas in a stable order
- produce the effective relational values for the turn
- feed the result into the compiler from PRD #193
- record the effective values in whatever deterministic turn trace or projected-state record the runtime uses at that point in the migration

The LLM does not own:
- scope precedence
- status mutation
- persistence
- value activation

### 4.8 Make fallback behavior explicit

If output is malformed, over-selected, or otherwise invalid:
- keep the deterministic baseline unchanged
- log the fallback through shared observability
- continue normally

Safe fallback is:
- `no_change`

### 4.9 Keep the seam inspectable

This adjudication should support inspection and debug traces that answer:
- what was the baseline?
- what live relational state was present?
- what adjustments were proposed?
- what adjustments were accepted?
- did runtime fall back to baseline?

This does not need to be shown to users by default, but it should be traceable.

---

## 5. User Experience Requirements

Users should experience Alfred as:
- more capable of making the right relational move for this moment
- less rigidly stuck in the baseline stance for a context
- more adaptive without becoming random or mode-switchy
- better at handling moments that need more directness, less authority, or more steadiness

Representative experiences:
- “Don’t coach me right now. Just stay with me.”
- “You can be more blunt than this.”
- “I need analysis, but not from above.”
- “This needs less pressure and more honesty.”

---

## 6. Success Criteria

- [ ] Runtime keeps a deterministic relational baseline.
- [ ] Per-turn stance adjustment happens through bounded deltas, not full rewrites.
- [ ] Output is validated strictly and falls back safely to baseline.
- [ ] Effective turn-level stance can differ from active learned state without mutating it directly.
- [ ] Deterministic turn traces or projected-state records capture the effective relational values that were actually used.

---

## 7. Milestones

### Milestone 1: Define the stance-adjudication contract
Define the baseline input, adjustment schema, validation rules, and fallback behavior.

Validation: the contract supports bounded deltas and `no_change` cleanly.

### Milestone 2: Implement the adjudication path
Run the stance adjudicator after baseline loading and live relational-state assessment.

Validation: runtime can produce validated effective relational values per turn.

### Milestone 3: Connect the effective values to the compiler and deterministic turn tracing
Feed accepted adjustments into the compiled relational contract and store what was actually used.

Validation: compiler and deterministic turn tracing reflect turn-level effective values, not only baseline state.

### Milestone 4: Add targeted tests and observability
Cover no-change, valid adjustment, over-selection, invalid dimension, invalid value, and fallback cases.

Validation: tests prove bounded behavior and safe fallback.

### Milestone 5: Align docs and inspection text
Update docs and any relevant inspection surfaces to describe stance adjudication truthfully.

Validation: docs and runtime behavior match.

---

## 8. Likely File Changes

```text
prds/195-semantic-relational-stance-adjudication.md
src/alfred/support_policy.py
src/alfred/alfred.py
src/alfred/support_reflection.py
src/alfred/memory/support_learning.py
tests/test_support_policy.py
tests/test_core_observability.py
docs/relational-support-model.md
docs/how-alfred-helps.md
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| The adjudicator becomes too freeform and rewrites everything | High | use bounded deltas with strict max counts and fallback to baseline |
| The runtime confuses per-turn stance shifts with learned preference | High | keep persistence and durable activation outside this PRD and behind deterministic substrate-managed update paths |
| Even bounded deltas feel random to users | Medium | make baseline loading deterministic and keep observability explicit |
| Large shifts are sometimes needed but blocked | Medium | start with bounded deltas, then relax carefully only if evidence shows the cap is too strict |

---

## 10. Validation Strategy

This PRD will likely require Python runtime changes and docs alignment.

Validation should focus on:
- deterministic baseline behavior
- bounded-delta validation and fallback
- separation between runtime adjustment and durable learning
- compiler integration
- deterministic turn-trace recording of effective values

---

## 11. Related PRDs

- PRD #193: Product-Owned Relational Semantics and Compiler Contract
- PRD #194: Semantic Relational-State Adjudication for Live Turns
- PRD #192: Relational Projection Work on the Semantic Runtime Engine
- PRD #197: Relational Surfacing and Meta-Explanation

---

## 12. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-09 | Keep deterministic baseline loading for relational values | Durable active state and scope precedence should remain code-owned |
| 2026-04-09 | Use bounded per-turn deltas instead of full relational rewrites | This keeps the seam inspectable, coherent, and safe |
| 2026-04-09 | Fallback to baseline on invalid output | Safe fallback is more important than forcing a questionable stance shift |
| 2026-04-09 | Record effective turn-level values separately from durable learned state | Runtime adaptation and durable learning should stay distinct |
