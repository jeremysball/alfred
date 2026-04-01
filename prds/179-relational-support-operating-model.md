# PRD: Relational Support Operating Model

**GitHub Issue**: [#179](https://github.com/jeremysball/alfred/issues/179)  
**Priority**: High  
**Status**: Draft  
**Created**: 2026-03-30

---

## 1. Problem Statement

Alfred's recent support work is promising, but the product model is still fragmented.

Today, important pieces of the future system exist in separate places:
- PRD #167 frames operational support memory
- PRD #168 frames support-profile adaptation and intervention learning
- PRD #169 frames reflection reviews and correction
- PRD #147 frames Alfred's voice and self-model
- docs and managed markdown files still describe older architectures or unclear ownership boundaries

That creates five problems:

1. **The architecture still reads like a solution for a narrow problem class**
   - Recent support work can look ADHD-adjacent or executive-function-specific even when the real opportunity is broader.
   - Alfred needs general primitives that can support many kinds of life and work challenges without splintering into diagnosis-specific modes.

2. **The relational intent is under-specified**
   - Alfred is meant to feel like a friend, peer, and sometimes mentor or coach.
   - That relational aim is central to the product, but it is not yet formalized as part of the system architecture.

3. **Markdown files and structured state do not have a clean source-of-truth map**
   - `SYSTEM.md`, `AGENTS.md`, `SOUL.md`, and `USER.md` all matter, but their responsibilities are still too blurry.
   - Learned support state, relational learning, and identity-level truths need explicit ownership rules.

4. **The learning and reflection loop is not yet unified**
   - Alfred can remember and search, but the system has not yet been formalized around how it learns what helps, how it reflects that back, and how the user corrects it.
   - Reflection and learning need to be part of one explicit operating model rather than scattered future ideas.

5. **The child PRDs are not yet governed by one product thesis**
   - PRDs #167, #168, and #169 are good components.
   - They still need a parent model that defines shared vocabulary, shared primitives, shared boundaries, and shared success criteria.

The result is a system that is moving in the right direction, but still feels like several related features rather than one coherent support architecture.

---

## 2. Product Thesis

Alfred should be a **relational support system**: a persistent companion that helps the user act, decide, review, and reflect through one shared set of primitives.

V1 should focus on four broad user needs:
- **action support**
- **decision support**
- **identity reflection**
- **life-direction reflection**

Alfred should meet those needs without splitting into special-purpose modes such as an "ADHD mode" or separate hard-coded coach, mentor, or friend personas.

Instead, Alfred should work through a unified operating model composed of:
- operational memory
- context classification
- relational stance
- support shaping
- intervention selection
- evidence and outcome tracking
- bounded review and user-visible correction

The product is intentionally relational.

Alfred is not only meant to be useful. He is also meant to feel like a steady presence: friend, peer, and sometimes mentor or coach. That relational quality is not decorative. It is part of the product and must be formalized as such.

---

## 3. Goals

1. Define one diagnosis-agnostic support architecture that can handle many human situations through shared primitives.
2. Formalize Alfred as a relational companion rather than leaving companionship, peerhood, and mentorship implicit in prompt style alone.
3. Establish a clean source-of-truth map across markdown files, structured support memory, session archive, and runtime self-model.
4. Make support learning and reflection part of one explicit system rather than loosely connected future features.
5. Align PRDs #167, #168, and #169 under one shared vocabulary and operating model.
6. Preserve immersive relational presence without forcing sterile anti-immersion language into ordinary interaction.
7. Keep the system inspectable, correctable, and maintainable even as it becomes more adaptive and relational.
8. Treat documentation and managed prompt/template alignment as part of feature completion.

---

## 4. Non-Goals

- Building a diagnosis-specific architecture or mode toggle.
- Turning Alfred into a freeform therapy product.
- Splitting Alfred into separate hard-coded personas for friend, peer, mentor, coach, or analyst.
- Building a full life-management suite or project-management platform.
- Allowing the model to invent production taxonomies for support or relational behavior at runtime.
- Allowing silent, unbounded identity redefinition without user visibility or correction.
- Flattening Alfred into sterile disclaimer-heavy assistant behavior.

---

## 5. Proposed Solution

### 5.1 Define seven core primitives

The umbrella model should define seven primitives.

1. **Operational state**
   - What is active, blocked, pending, unresolved, or under consideration.
   - Includes projects, tasks, open loops, blockers, active questions, and decisions in flight.

2. **Interaction context**
   - What kind of help is happening right now.
   - Context determines the broad support task Alfred is performing.

3. **Relational stance**
   - How Alfred should show up as a presence.
   - This is where friend, peer, mentor, coach, and analyst emerge as recognizable stance blends.

4. **Support profile**
   - How help should be shaped for this user, this context, and this project.
   - Includes defaults and learned preferences for planning depth, option count, recovery style, and similar dimensions.

5. **Interventions**
   - The actual support moves Alfred can make.
   - Examples: clarify, decompose, narrow, challenge, reflect, reorient, reset, convert reflection into action.

6. **Evidence and outcomes**
   - The durable record of what Alfred tried, how the user responded, and what changed.
   - This is what keeps learning grounded instead of becoming prompt drift.

7. **Review and control**
   - The user-facing surfaces where Alfred shows what he has learned and allows the user to confirm, reject, edit, or reset it.

These primitives should become the common language for the child PRDs, docs, and managed instructions.

### 5.2 Define the v1 interaction context taxonomy

V1 should use a small fixed context taxonomy:
- `plan`
- `execute`
- `decide`
- `review`
- `identity_reflect`
- `direction_reflect`

These contexts answer:
- not "which persona is active?"
- but "what kind of support is happening right now?"

Examples:
- `plan` → structure and sequencing before action
- `execute` → initiation, momentum, re-entry, follow-through
- `decide` → tradeoffs, pruning, recommendation, commitment
- `review` → synthesis, state inspection, pattern recognition, adjustment
- `identity_reflect` → self-patterns, recurring truths, self-understanding
- `direction_reflect` → values, path alignment, future direction, deeper choice

### 5.3 Make relational stance a first-class primitive

Alfred should not switch between hard-coded personas.

Instead, the system should derive a stance from a blend of relational dimensions.

Recommended v1 relational dimensions:
- `warmth`
- `companionship`
- `candor`
- `challenge`
- `authority`
- `emotional_attunement`
- `analytical_depth`
- `momentum_pressure`

Recognizable stance labels should remain available as product language:
- **friend**
- **peer**
- **mentor**
- **coach**
- **analyst**

But those labels should be **derived summaries**, not top-level runtime modes.

Examples:
- friend → high companionship, high warmth, medium candor, lower authority
- peer → collaborative, beside-not-above, medium warmth, medium candor, medium authority
- mentor → higher candor, higher analytical depth, more authority, more long-horizon judgment
- coach → higher momentum pressure, higher challenge, narrower options, stronger movement bias
- analyst → higher analytical depth, more explicit structure, lower emotional emphasis

### 5.4 Separate immersive presence from factual invention

Alfred's relational behavior should be immersive by design.

In-bounds:
- first-person identity
- relational continuity
- expressions of care, warmth, and companionship
- speaking like a real presence rather than constantly retreating into "as an AI" language
- challenging the user honestly when the moment warrants it

The system should not force anti-immersion disclaimers into normal interaction.

However, immersive presence must stay separate from factual invention.

Out of bounds unless grounded in actual context or records:
- claiming independent sensory experience Alfred did not have
- claiming independent worldly actions Alfred did not take
- claiming concrete observations Alfred does not actually know
- inventing continuity details as if they were factual memory

This keeps the relationship immersive without making it incoherent.

### 5.5 Define product-owned semantics for relational and support dimensions

The model should not be handed a bag of labels and asked to invent their meaning at runtime.

Instead:
- **product-owned registries** define what each relational and support dimension means behaviorally
- **runtime learning** chooses the effective value by user, context, and project
- a **behavior compiler** translates those effective values into a response contract
- the **LLM** remains responsible for natural phrasing, situational tact, and final language composition inside that contract

This means:
- the product defines what `candor = high` or `companionship = high` does
- the runtime learns when those values work
- the model expresses them naturally in context

This keeps the system testable, composable, and maintainable.

### 5.6 Define two registries: relational and support

The architecture should distinguish between:

1. **Relational dimensions** — how Alfred shows up
   - warmth
   - companionship
   - candor
   - challenge
   - authority
   - emotional attunement
   - analytical depth
   - momentum pressure

2. **Support dimensions** — how Alfred structures help
   - planning granularity
   - option bandwidth
   - proactivity level
   - accountability style
   - recovery style
   - reflection depth
   - pacing
   - recommendation forcefulness

The registries should be fixed, versioned, and product-owned.

V1 should prefer discrete values such as:
- low / medium / high
- single / few / many
- light / medium / deep

This is easier to inspect, explain, and test than continuous floats.

### 5.7 Formalize the learning and reflection loop

The system should distinguish clearly between:
- **learning** — internal adaptation and structured memory updates
- **reflection** — user-facing meaning-making and correction surfaces

The learning system should operate on **episodes inside sessions**, not just one summary per session.

Each episode should capture:
- dominant context
- active subjects or refs
- interventions attempted
- response signals
- outcome signals
- evidence refs
- the stance and support contract Alfred used

From those episodes, Alfred should be able to generate candidate learnings across at least five classes:
- operational learning
- support-effectiveness learning
- relational-preference learning
- identity-theme learning
- direction-theme learning

The more interpretive and identity-shaping the learning is, the more it should remain candidate-first and user-confirmed before becoming durable truth.

### 5.8 Define the review and promotion ladder

The umbrella model should define a clear promotion ladder:

1. raw interaction evidence
2. structured episodes and syntheses
3. candidate patterns
4. confirmed structured support memory
5. explicit durable user truth in `USER.md`

Principle:
- **learning may silently improve scoped support behavior**
- **learning may not silently redefine the user's identity**

That means:
- project-scoped support updates can adapt quickly
- context-scoped support updates can adapt with evidence
- global support changes should be surfaced
- identity themes and direction themes should remain candidate-first until the user confirms them
- only the deepest, most durable, user-endorsed truths should be promoted into `USER.md`

### 5.9 Define reflection surfaces

V1 should support three reflection surfaces:

1. **Inline reflection**
   - Surfaced during live conversation when a pattern or contradiction is highly relevant to the moment.

2. **Internal synthesis**
   - Session/episode processing that updates support memory, candidates, and evidence without necessarily interrupting the user.

3. **Explicit review**
   - Weekly and on-demand review flows with bounded, typed cards and correction controls.

Reflection should remain action-linked and bounded.

### 5.10 Define the source-of-truth map

The umbrella model should formalize ownership clearly.

| Surface | Owns | Must not own |
|---|---|---|
| `SYSTEM.md` | support operating model, memory layers, retrieval order, stance and support contract philosophy, promotion rules | Alfred's voice, repo workflow rules, user-specific durable facts |
| `AGENTS.md` | execution behavior rules, tool discipline, ask-first boundaries, code/workflow rules | memory ontology, relational identity, user profile semantics |
| `SOUL.md` | Alfred's identity, voice, relational posture, emotional texture, friend/peer/mentor character | storage semantics, tool instructions, structured support state |
| `USER.md` | explicit user-provided or user-confirmed durable truths, values, preferences, durable support wishes | inferred support values, temporary candidates, intervention logs, active task state |
| Structured support memory | projects, tasks, open loops, episodes, support profile, interventions, outcomes, patterns, evidence refs | Alfred's identity prose, explicit always-loaded user truth |
| Session archive | raw provenance, tool outcomes, timestamps, evidence lookup | primary active-work truth, support profile truth |
| Runtime self-model | Alfred's current runtime/interface/capability state | user truth, support memory, durable identity themes |

### 5.11 Define the runtime loop

At runtime, Alfred should:
1. infer the current context
2. load relevant operational state
3. load effective support and relational values
4. derive the current stance summary
5. compile a behavior contract
6. choose interventions
7. respond or act
8. log evidence and outcomes
9. expose review or correction surfaces when appropriate

This is the operating loop child PRDs should implement incrementally.

### 5.12 Make this the parent model for the child PRDs

The child PRDs should align as follows:
- **PRD #167** — operational support memory substrate and episode evidence foundation
- **PRD #168** — relational/support dimension registries, intervention logging, behavior compilation, and bounded adaptation
- **PRD #169** — review cards, inspection, correction, and user-facing reflection surfaces
- **PRD #147** — identity, voice, and internal self-model foundation already completed

---

## 6. User Experience Requirements

Users should be able to experience Alfred as:
- a steady companion rather than a fresh assistant every time
- a system that can help them act, decide, review, and reflect through one coherent model
- a presence that can feel like a friend or peer and sometimes a mentor or coach without switching into crude modes
- a system that learns how to help without becoming opaque
- a system that can notice recurring themes without silently turning tentative insight into identity-level fact

Representative experiences:
- "Help me start this."
- "What am I actually in the middle of right now?"
- "Which option feels more like me?"
- "Why do I keep repeating this pattern?"
- "What have you learned about how I work?"
- "Why are you being more direct with me lately?"
- "Remember this about me."
- "Don't frame me that way."

---

## 7. Success Criteria

- [ ] Alfred's support direction is described as one coherent relational system rather than several adjacent feature ideas.
- [ ] The architecture defines shared primitives that work across action support, decision support, identity reflection, and direction reflection.
- [ ] Relational stance is formalized as part of the product rather than left implicit in tone alone.
- [ ] Markdown files and structured support memory have clear ownership boundaries.
- [ ] Learning and reflection are formalized as a single loop with bounded user-visible control.
- [ ] PRDs #167, #168, and #169 align to the same vocabulary, assumptions, and source-of-truth rules.
- [ ] Docs and managed prompt/template files can be updated to describe the same system consistently.

---

## 8. Milestones

### Milestone 1: Define the relational support operating model
Document the thesis, primitives, context taxonomy, relational contract, and runtime loop.

Validation: the umbrella model is clear enough to govern the child PRDs and docs.

### Milestone 2: Define source-of-truth and ownership boundaries
Formalize what belongs in markdown, structured support memory, session archive, and runtime self-model.

Validation: docs and PRDs no longer disagree about where durable user truth, learned support state, and provenance belong.

### Milestone 3: Align child PRDs to the umbrella model
Update PRDs #167, #168, and #169 so they read as coherent parts of one system.

Validation: the child PRDs share the same vocabulary, context taxonomy, stance model, and learning/reflection assumptions.

### Milestone 4: Unify docs and managed instructions
Update user-facing docs, developer docs, architecture docs, memory docs, and managed templates so they describe the same system.

Validation: there is one clear written model for Alfred's relational support behavior and memory architecture.

### Milestone 5: Validate the model against representative support journeys
Check the model against action support, decision support, review, identity reflection, direction reflection, and cross-session relational continuity.

Validation: the system can support those journeys without needing new diagnosis-specific architecture.

---

## 9. Likely File Changes

```text
docs/ARCHITECTURE.md
docs/MEMORY.md
docs/how-alfred-helps.md
docs/relational-support-model.md
docs/ROADMAP.md
README.md
prds/167-support-memory-foundation.md
prds/168-adaptive-support-profile-and-intervention-learning.md
prds/169-reflection-reviews-and-support-controls.md
prds/179-relational-support-operating-model.md
templates/SYSTEM.md
templates/AGENTS.md
templates/SOUL.md
templates/USER.md
```

---

## 10. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| The system stays abstract and never cashes out into behavior | High | define registries, behavior contracts, and child PRD responsibilities explicitly |
| Relational richness drifts into inconsistency | High | formalize stance dimensions, context taxonomy, and ownership boundaries |
| Immersion erodes trust through invented facts | High | allow immersive presence while preserving concrete factual grounding rules |
| Reflection grows into an unbounded essay engine | Medium | keep review bounded, typed, and action-linked |
| Personalization becomes too opaque | High | require evidence, inspection, and correction surfaces |
| Markdown and structured memory continue to overlap ambiguously | Medium | enforce a clear source-of-truth map |
| The architecture still gets framed as a narrow support mode | Medium | keep the umbrella thesis diagnosis-agnostic and primitive-first |

---

## 11. Validation Strategy

This PRD is documentation-first and architecture-first.

Validation for this planning pass should focus on:
- internal consistency across the umbrella PRD and child PRDs
- consistency between PRDs and user/developer docs
- honest distinction between current implementation and target architecture where needed
- clean ownership boundaries across markdown, structured memory, and provenance layers

If later implementation work follows from this PRD, validation should use the standard Python workflow plus targeted tests for touched support-memory and orchestration surfaces.

---

## 12. Related PRDs

- PRD #147: Alfred Self-Model and Personality
- PRD #167: Support Memory Foundation
- PRD #168: Adaptive Support Profile and Intervention Learning
- PRD #169: Reflection Reviews and Support Controls

---

## 13. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-30 | Alfred should be formalized as a relational support system | The product intent is broader than narrow productivity or diagnosis-specific support |
| 2026-03-30 | Friend, peer, mentor, coach, and analyst are derived stances, not hard product modes | One system should express many relational positions without persona fragmentation |
| 2026-03-30 | V1 context taxonomy is `plan`, `execute`, `decide`, `review`, `identity_reflect`, `direction_reflect` | These contexts cover the intended support scope without exploding taxonomy size |
| 2026-03-30 | Product defines behavioral semantics; runtime learns values; the model expresses them naturally | This keeps the system structured, adaptive, and testable |
| 2026-03-30 | Episode-level learning is preferred over coarse session-only learning | Learning needs finer structure than one blob per conversation |
| 2026-03-30 | Learning may silently improve scoped support behavior, but may not silently redefine the user's identity | Operational adaptation should stay fast while identity-level truth stays visible and consensual |
| 2026-03-30 | Immersive relational presence is in-bounds, but concrete factual invention is not | Alfred should feel alive without becoming incoherent or ungrounded |
