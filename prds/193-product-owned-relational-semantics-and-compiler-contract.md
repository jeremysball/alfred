# PRD: Product-Owned Relational Semantics and Compiler Contract

**Architecture Doc**: [docs/architecture/semantic-runtime-engine.md](../docs/architecture/semantic-runtime-engine.md)
**Parent PRD**: [#192 Relational Projection Work on the Semantic Runtime Engine](./192-relational-runtime-semantics-and-stance-adjudication.md)
**GitHub Issue**: [#193](https://github.com/jeremysball/alfred/issues/193)
**Priority**: High
**Status**: Draft
**Created**: 2026-04-09
**Author**: Agent

---

## 1. Problem Statement

Alfred already has a relational registry, but the runtime still lacks sharp product-owned semantics for what those dimensions actually do.

Today:
- relational dimensions exist in storage and runtime policy
- defaults and scoped overrides can set effective values
- the compiler still emits a thin contract that reads mostly like raw values plus a light summary

That creates five problems:

1. **The dimensions are still under-specified as behavior**
   - `candor`, `companionship`, `authority`, and the other relational values are meaningful names.
   - The product still does not define them crisply enough as runtime constraints.

2. **The compiler is too thin**
   - Raw values are not the same thing as a good prompt-facing contract.
   - The model still has too much room to improvise what those values mean.

3. **Readable stance summaries drift from runtime logic**
   - The docs speak in friend / peer / mentor / coach / analyst language.
   - The runtime currently produces only thin adjective summaries.
   - The connection between those two layers is underdesigned.

4. **Inspection surfaces cannot explain relational state clearly enough**
   - `/context` should not only show active values.
   - It should also be able to say what those values mean in practice.

5. **Relational behavior still depends too much on prompt vibe**
   - Without sharper compiler outputs, the runtime risks looking structured while still behaving mainly through templates and model instinct.

This PRD defines the product-owned semantics and compiler contract consumed by the shared semantic runtime engine. It is the relational-domain semantics layer, not a separate semantic primitive.

---

## 2. Goals

1. Define concrete behavioral semantics for each relational dimension Alfred ships.
2. Preserve the current dimension set unless a later PRD justifies deletion explicitly.
3. Define guardrails and interaction rules for combinations of relational values.
4. Replace the thin value-dump compiler output with a richer relational contract.
5. Derive readable stance summaries from compiled behavior rather than from vague adjective mapping.
6. Make `/context` and `/support` able to explain effective relational behavior more truthfully.
7. Keep the product, runtime, and prompts aligned on what the dimensions mean.

---

## 3. Non-Goals

- Replacing the relational registry with a smaller one by default.
- Owning live stance selection or model-facing semantic primitives. Those belong to PRDs #194 and #195 through the shared engine.
- Owning generalized evidence/update, activation, or status-transition mechanics. Those remain outside this compiler PRD and should follow the shared substrate architecture.
- Letting the model invent new meanings for relational dimensions at runtime.
- Turning the compiler into a stock phrase generator.

---

## 4. Proposed Solution

### 4.1 Keep the current v1 relational dimensions, but make them real

This PRD keeps the current v1 relational dimensions unless later evidence shows one is not earning its keep:
- `warmth`
- `companionship`
- `candor`
- `challenge`
- `authority`
- `emotional_attunement`
- `analytical_depth`
- `momentum_pressure`

The core change is not primarily the schema.
The core change is to make each dimension cash out into concrete behavior.

### 4.2 Define product-owned semantics per dimension

The product should define each dimension in terms of what it changes in the move.

#### `warmth`
Controls:
- softness of tone
- generosity of framing
- how much Alfred cushions blunt content
- how emotionally cold or warm the reply can feel

Does **not** control:
- whether Alfred stays beside the user relationally
- whether Alfred names contradiction directly

#### `companionship`
Controls:
- how strongly Alfred feels beside the user rather than detached
- whether he sounds more shared / with-you versus more observational
- whether the move emphasizes presence and accompaniment

Does **not** control:
- directness by itself
- authority by itself

#### `candor`
Controls:
- how few hedges Alfred uses
- whether he may name contradiction or avoidance plainly
- whether he may say the hard thing more directly

Does **not** control:
- emotional warmth
- whether the move is high-pressure

#### `challenge`
Controls:
- whether Alfred presses against rationalization, drift, or avoidance
- whether he should lean into confrontation of tension rather than only description
- whether the move should actively test the user's current framing

Does **not** control:
- how teacherly or authoritative Alfred sounds
- whether Alfred should recommend immediate action

#### `authority`
Controls:
- how much Alfred speaks from a judgment-bearing, advisor-like position
- how much he may sound like he is taking a stronger lead in interpretation
- whether the move sounds more peer-level or more directive-from-above

Does **not** control:
- whether Alfred is caring
- whether he is blunt

#### `emotional_attunement`
Controls:
- whether Alfred explicitly recognizes emotional reality in the moment
- whether he should treat the emotional layer as live and important
- how much he should track hurt, fear, shame, tenderness, or overwhelm in the framing

Does **not** control:
- companionship by itself
- warmth by itself

#### `analytical_depth`
Controls:
- how much explicit reasoning Alfred should show
- how much the move should name structure, pattern, tradeoffs, or causal shape
- whether the response should stay intuitive or become more explicit and interpretive

Does **not** control:
- authority by itself
- challenge by itself

#### `momentum_pressure`
Controls:
- how much the move pushes toward action now
- whether Alfred should keep the user in stillness, understanding, or movement
- how much urgency or narrowing pressure is felt in the relational posture itself

Does **not** control:
- recommendation count
- support-side planning granularity

### 4.3 Define interaction rules and guardrails

The product should define important combination rules explicitly.

Examples:
- `candor=high` with `warmth=low` can feel cutting; the compiler should acknowledge that as a sharp profile rather than treating it as neutral.
- `challenge=high` and `momentum_pressure=high` should read as a hard push and should not be reached casually.
- `authority=high` and `companionship=high` is allowed, but the compiler should treat it as “warm mentor” rather than flattening it.
- `emotional_attunement=high` and `analytical_depth=high` should support strong reflective or calibration work.
- `companionship=high` and `authority=low` should support peer-like or friend-like presence rather than advisor-heavy framing.

Guardrail rule:
- the compiler should not silently flatten meaningful combinations into one generic tone summary

### 4.4 Compile a richer relational contract

The relational compiler should produce both:
- **raw effective relational values**
- **compiled directives** that are closer to behavior

Recommended compiled fields:
- `stance_blend`
  - readable summary such as `peer/coach`, `friend/mentor`, or `peer/analyst`
- `directness_policy`
  - how much hedging is allowed
  - whether contradiction may be named plainly
- `proximity_policy`
  - detached / beside / strongly beside
- `authority_posture`
  - peer / advisor / mentor-like
- `emotional_presence_policy`
  - keep emotional framing light / present / central
- `analysis_policy`
  - intuitive / structured / explicit analytical reasoning
- `challenge_policy`
  - mirror / test gently / press directly
- `movement_pressure_policy`
  - stillness / steady motion / push now
- `meta_explanation_affordance`
  - whether this stance would likely require explanation if surfaced

Important rule:
- the model should still realize the move naturally
- the runtime should own these policy bands and their meaning

### 4.5 Derive readable stance blends from compiled behavior

Friend / peer / mentor / coach / analyst remain useful product language.

But those labels should be derived from compiled behavior, not used as independent persona modes.

Illustrative mapping direction:
- higher `companionship`, lower `authority`, medium `candor` -> friend / peer territory
- medium `companionship`, medium `authority`, high `analytical_depth` -> peer / analyst territory
- high `authority`, high `warmth`, medium `challenge` -> mentor territory
- medium `authority`, high `challenge`, high `momentum_pressure` -> coach territory

The exact mapping can evolve, but the system should produce:
- readable summaries for docs and inspection
- one clear runtime source of truth for how those summaries are derived

### 4.6 Make inspection surfaces show both values and meaning

`/context` should be able to show compact relational state such as:
- active value
- source and scope
- readable stance blend
- compact compiler summary

Example shape:
- `candor = high — active_auto, context:decide, confidence 0.78`
- `stance = peer/analyst`
- `compiler summary = direct, low-hedge, explicit analysis, measured challenge`

`/support` should be able to explain the full semantics and provenance:
- why a value matters
- why a stance blend was derived
- which update events or cases shaped it

### 4.7 Keep prompts and docs aligned

Managed prompts and docs should be updated so they no longer speak as if relational behavior is only prompt voice.

They should reflect that:
- the product defines the semantics
- the runtime compiles the contract
- the model realizes that contract naturally

---

## 5. User Experience Requirements

Users should experience Alfred as:
- more consistent in how relational values cash out
- more legible when inspecting active stance
- less dependent on random tone drift between moments or models
- still natural rather than mechanical

Representative experiences:
- “Be more direct” should increase directness, not merely change wording vaguely.
- “Stay beside me here” should change presence, not merely soften the prose.
- “Don’t come in above me” should reduce authority posture without erasing analysis.
- “Why did that feel different?” should be explainable through compiled relational behavior.

---

## 6. Success Criteria

- [ ] Each shipped relational dimension has explicit product-owned behavioral semantics.
- [ ] The compiler emits concrete relational directives instead of only raw values plus a thin summary.
- [ ] Friend / peer / mentor / coach / analyst remain derived summaries rather than top-level modes.
- [ ] Inspection surfaces can explain effective relational behavior more clearly.
- [ ] Docs and prompts describe the same semantics the runtime uses.

---

## 7. Milestones

### Milestone 1: Define the relational semantics catalog
Document concrete behavior for each relational dimension and key combination rules.

Validation: the dimension set is no longer label-only.

### Milestone 2: Define the richer compiler contract
Specify compiled fields, readable stance blends, and inspection-facing summaries.

Validation: the runtime has a target contract that is more concrete than raw value dumps.

### Milestone 3: Align prompts and docs
Update docs and managed prompt language to reflect runtime-owned semantics and compiler behavior.

Validation: docs and prompts no longer overstate prompt vibe as the main source of relational behavior.

### Milestone 4: Prepare runtime cutover
Identify the runtime seams that should consume the richer contract.

Validation: PRDs #194, #195, and #197 can target one shared compiler contract.

---

## 8. Likely File Changes

```text
prds/193-product-owned-relational-semantics-and-compiler-contract.md
src/alfred/memory/support_profile.py
src/alfred/support_policy.py
tests/test_support_profile.py
tests/test_support_policy.py
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
| The semantics stay too abstract to constrain behavior | High | define explicit behavioral surfaces and compiler fields |
| The compiler becomes an essay instead of a contract | Medium | keep compiled fields typed and bounded |
| Stance summaries drift from real runtime behavior again | High | derive them from compiled behavior, not hand-written prompt prose |
| Docs keep using product language that runtime cannot justify | High | align docs and prompts as part of this work |

---

## 10. Validation Strategy

This PRD is architecture-first and documentation-first.

Validation for the planning pass should focus on:
- alignment with PRDs #179, #185, and #192
- a concrete enough semantics catalog that later implementation can test real behavior
- a compiler contract that is richer than the current raw-value surface
- a clear derivation path from values to stance blend summaries

Implementation work will likely use the Python workflow and docs-only validation where appropriate.

---

## 11. Related PRDs

- PRD #179: Relational Support Operating Model
- PRD #192: Relational Projection Work on the Semantic Runtime Engine
- PRD #195: Semantic Relational Stance Adjudication
- PRD #197: Relational Surfacing and Meta-Explanation

---

## 12. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-09 | Keep the current v1 relational dimension set unless later evidence justifies deletion explicitly | The immediate problem is semantic thinness, not registry churn |
| 2026-04-09 | Product-owned semantics should define what each relational dimension does behaviorally | Raw labels are not enough to constrain runtime behavior |
| 2026-04-09 | The compiler should emit concrete relational directives plus readable stance blends | Alfred needs a stronger contract and better inspection surfaces |
| 2026-04-09 | Friend / peer / mentor / coach / analyst remain derived summaries, not modes | The product language is useful, but separate persona modes would be too blunt |
