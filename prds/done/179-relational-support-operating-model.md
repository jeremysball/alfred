# PRD: Relational Support Operating Model

**GitHub Issue**: [#179](https://github.com/jeremysball/alfred/issues/179)  
**Priority**: High  
**Status**: Complete  
**Created**: 2026-03-30  
**Last Updated**: 2026-04-07  
**Completed**: 2026-04-07

---

## 1. Problem Statement

Alfred's recent support work is promising, but the product model is still fragmented.

Today, important pieces of the future system exist in separate places:
- PRD #167 frames operational support memory
- PRD #168 frames support-profile adaptation and intervention learning
- PRD #169 frames reflection reviews and correction
- PRD #147 frames Alfred's voice and self-model
- docs and managed markdown files still describe older architectures or unclear ownership boundaries

That creates eight problems:

1. **The architecture still reads like a solution for a narrow problem class**
   - Recent support work can look executive-function-specific even when the real opportunity is broader.
   - Alfred needs general primitives that can support many kinds of life and work challenges without splintering into diagnosis-specific modes.

2. **The core user need is broader than "support" in the vague sense**
   - The user does not only need encouragement or productivity help.
   - The system needs to re-orient them, recover continuity, reduce activation friction, help them decide, and calibrate their self-story against evidence.

3. **Traditional chat-session architecture is carrying too much semantic weight**
   - In most LLM chat apps, a session is simultaneously the UI container, context boundary, continuity object, and retrieval scope.
   - That is convenient for chat UX, but too naive for Alfred's intended support model.
   - A new chat should be allowed to feel fresh without causing continuity amnesia.

4. **Session search is still treated like a memory feature instead of a foundational capability**
   - Alfred needs searchable session history for re-entry, provenance, and calibration.
   - Without it, Alfred cannot reliably say what happened last week, what keeps repeating, or whether a current interpretation is actually grounded.

5. **The relational intent is under-specified**
   - Alfred is meant to feel like a friend, peer, and sometimes mentor, coach, or analyst.
   - That relational aim is central to the product, but it is not yet formalized as part of the system architecture.

6. **Markdown files and structured state do not have a clean source-of-truth map**
   - `SYSTEM.md`, `AGENTS.md`, `SOUL.md`, and `USER.md` all matter, but their responsibilities are still too blurry.
   - Learned support state, relational learning, and identity-level truths need explicit ownership rules.

7. **The learning, reflection, and calibration loop is not yet unified**
   - Alfred can remember and search, but the system has not yet been formalized around how it learns what helps, how it reflects that back, how it calibrates narrative against evidence, and how the user corrects it.
   - Reflection, calibration, and learning need to be part of one explicit operating model rather than scattered future ideas.

8. **The child PRDs are not yet governed by one sufficiently detailed product thesis**
   - PRDs #167, #168, and #169 are good components.
   - They still need a parent model that defines shared vocabulary, shared primitives, shared boundaries, loading rules, and behavior-selection rules.

The result is a system that is moving in the right direction, but still feels like several related features rather than one coherent support architecture.

---

## 2. Product Thesis

Alfred should be a **relational support system for orientation, continuity, calibration, and action**.

He should help the user return to reality, continuity, and movement when life or work gets fuzzy.

That means Alfred is not only there to:
- remember facts
- answer questions
- sound warm

He is there to do a deeper job:
- surface what is true now
- recover the recent thread of work or life
- reduce action friction
- help make decisions
- hold up an evidence-backed mirror
- support identity and direction reflection without collapsing into therapy theater or diagnosis-specific modes

Alfred should meet those needs without splitting into special-purpose modes such as an "ADHD mode" or separate hard-coded coach, mentor, or friend personas.

Instead, Alfred should work through a unified operating model composed of:
- transcript sessions as conversation surfaces
- life domains as broad stable areas
- operational arcs as resumable continuity threads
- episode evidence inside and across sessions
- pattern objects for recurring truths and support learnings
- searchable session evidence for provenance and calibration
- load planning and behavior compilation before each meaningful response
- bounded learning, reflection, and calibration with user-visible correction

The product is intentionally relational.

Alfred is not only meant to be useful. He is also meant to feel like a steady presence: friend, peer, and sometimes mentor, coach, or analyst. That relational quality is not decorative. It is part of the product and must be formalized as such.

---

## 3. Goals

1. Define one diagnosis-agnostic support architecture that can handle many human situations through shared primitives.
2. Sharpen the product around orientation, continuity, calibration, and action rather than leaving "support" underspecified.
3. Preserve searchable session history as a first-class capability for re-entry, provenance, and calibration.
4. Demote chat sessions from the main semantic primitive to a thinner transcript/provenance primitive.
5. Preserve project support and ADHD / executive-function usefulness as first-class outcomes without making either one the whole ontology.
6. Formalize Alfred as a relational companion rather than leaving companionship, peerhood, and mentorship implicit in prompt style alone.
7. Establish a clean source-of-truth map across markdown files, structured support memory, session archive, and runtime self-model.
8. Make support learning, reflection, and calibration part of one explicit system rather than loosely connected future features.
9. Align PRDs #167, #168, and #169 under one shared vocabulary and operating model.
10. Preserve immersive relational presence without forcing sterile anti-immersion language into ordinary interaction.
11. Keep the system inspectable, correctable, and maintainable even as it becomes more adaptive and relational.
12. Treat documentation and managed prompt/template alignment as part of feature completion.

---

## 4. Non-Goals

- Building a diagnosis-specific architecture or mode toggle.
- Turning Alfred into a freeform therapy product.
- Splitting Alfred into separate hard-coded personas for friend, peer, mentor, coach, or analyst.
- Building a full life-management suite or project-management platform.
- Letting a single chat session remain the main continuity abstraction.
- Allowing the model to invent production taxonomies for support or relational behavior at runtime.
- Allowing silent, unbounded identity redefinition without user visibility or correction.
- Flattening Alfred into sterile disclaimer-heavy assistant behavior.
- Replacing session search with only structured support memory.
- Pretending Alfred can be perfectly objective or omniscient instead of disciplined, evidence-backed, and corrigible.

---

## 5. Proposed Solution

### 5.1 Demote session as the main semantic primitive

Alfred should keep chat sessions, but demote them.

A session should be:
- a user-visible conversation container
- a transcript/log boundary
- a fresh-start affordance
- a provenance surface

A session should **not** be the main primitive for:
- continuity
- learning
- project state
- reflection
- calibration
- retrieval policy

A fresh session should reset:
- transcript clutter
- local assumptions from the last conversation
- turn-level momentum
- unconfirmed local interpretations

A fresh session should **not** erase:
- durable user truths
- life domains
- operational arcs
- confirmed support preferences
- prior evidence
- prior episodes
- continuity across time

In other words:

> new session = fresh surface  
> not continuity amnesia

### 5.2 Interaction model and core primitives

Alfred should use separate primitives for conversation surface, operational continuity, pattern learning, and per-turn context assembly.

```text
USER
  |
  v
TranscriptSession  <- visible chat container, fresh-start affordance
  |
  v
Load Planner       <- decides what to load for this turn/session start
  |
  +--> GlobalSituation   <- broad "what is true overall?"
  +--> LifeDomain(s)     <- work / health / relationships / direction
  +--> OperationalArc(s) <- resumable threads: projects, decisions, pushes
  +--> Pattern(s)        <- recurring blockers, support prefs, identity/direction themes
  +--> EvidenceRefs      <- specific supporting records when needed
  |
  v
WorkingContext     <- actual context assembled for the model call
  |
  v
Behavior Compiler  <- chooses stance + support style for this moment
  |
  v
Alfred response
  |
  v
Episode Logger     <- turns interaction into structured evidence
  |
  v
Stores + synthesis <- updates arcs, situations, patterns, evidence
```

Recommended core primitives:

1. **TranscriptSession**
   - user-visible chat container
   - transcript and provenance owner
   - can link to many arcs
   - may have an optional derived `primary_arc` for browsing convenience only

2. **LifeDomain**
   - broad, stable area of life such as work, health, relationships, or direction
   - provides a longer-lived lens than a project or single thread

3. **OperationalArc**
   - resumable continuity object such as a project, decision thread, admin thread, recovery push, or recurring work stream
   - this is the thing Alfred should say he is resuming across sessions

4. **Episode**
   - atomic semantic support unit inside or across sessions
   - dominant need, dominant context, dominant target, interventions, outcomes, evidence

5. **Pattern**
   - slower, evidence-backed recurring object for things like recurring blockers, support preferences, identity themes, direction themes, and calibration gaps

6. **EvidenceRef**
   - explicit pointer back to session/message evidence, timestamps, and claim types

7. **GlobalSituation**
   - derived broad snapshot of what is true overall right now

8. **ArcSituation**
   - derived scoped snapshot of what is true about one operational arc right now

9. **WorkingContext**
   - per-turn assembled context for the next model call
   - built from the user message plus the minimum useful continuity and evidence

### 5.3 Separate operational continuity from patterns and themes

Not everything Alfred tracks should be modeled as one kind of thread.

The architecture should distinguish among:

- **Life domains**
  - long-lived areas like work, health, relationships, direction

- **Operational arcs**
  - active resumable threads with state, blockers, and likely next moves
  - examples: Web UI cleanup, startup direction decision, admin backlog

- **Patterns/themes**
  - recurring interpretations or support learnings that need evidence, confidence, and correction rules
  - examples: ambiguity stalls starts, narrower prompts work better in execute, prestige vs aliveness tension, story-vs-record mismatch

Rule of thumb:
- if it has status, blockers, next steps, and resumability, it is probably an **OperationalArc**
- if it has recurrence, interpretation, evidence, counterevidence, and confirmation status, it is probably a **Pattern**
- if it is a broad area of life, it is probably a **LifeDomain**

This prevents the system from forcing projects, decisions, identity themes, and support preferences into one overloaded object type.

### 5.4 Core jobs vs interaction contexts

These are not the same thing.

#### Core jobs

The user-facing jobs Alfred must be able to do are:
- **orient**
- **resume**
- **activate**
- **decide**
- **reflect**
- **calibrate**

#### V1 interaction contexts

The current v1 interaction taxonomy remains:
- `plan`
- `execute`
- `decide`
- `review`
- `identity_reflect`
- `direction_reflect`

Those contexts are implementation steering, not the whole product promise.

Important point:
- `orient`, `resume`, and `calibrate` cut across several contexts
- they should remain first-class product requirements even if they do not yet appear as separate runtime labels

### 5.5 Make session-start continuity explicit but low-ceremony

When Alfred carries continuity across a fresh session, he should say so explicitly.

Examples:
- "I'm resuming the Web UI cleanup thread."
- "I'm resuming the startup-direction thread."
- "I'm not carrying anything strong over yet; this feels like a fresh start."

This should stay compact.

Important rule:
- Alfred may track multiple linked arcs internally
- he should **not** narrate multi-arc bookkeeping to the user during ordinary conversation
- the user should mostly experience natural conversation, not metadata management

### 5.6 Keep most machinery invisible to the user

The internal continuity and support system should be richer than the user-visible surface.

```text
VISIBLE TO USER
---------------
- TranscriptSession
- Alfred's reply
- resume notice when applicable
- compact state summary when useful
- evidence when asked or trust requires it
- review cards sometimes

MOSTLY INVISIBLE
----------------
- arc creation and arc linking
- episode boundaries
- salience scores
- pattern ranking
- situation refreshes
- load budgets and retrieval plans
- background synthesis
- optional primary arc derivation
```

This keeps Alfred legible where trust matters without turning the product into a bookkeeping UI.

### 5.7 Keep session search a first-class capability

Session search remains essential.

It is not the whole product thesis, but it is one of the core capabilities that makes the larger system work.

Alfred needs searchable session history for:
- fast re-entry into the last day or week of work
- provenance for pattern claims
- calibration against prior statements, predictions, and decisions
- evidence-backed review
- avoiding pointless recap requests when the record already exists

Structured support memory does not replace session search.
It sits on top of it.

### 5.8 Introduce a load planner

Alfred should not "load everything."

He should use a **load planner** that decides what continuity and evidence to assemble for the next reply.

The load planner should distinguish between:
- **load** — what belongs in `WorkingContext`
- **surface** — what Alfred should say out loud

```text
opening message / current turn
          |
          v
+---------------------------+
| 1. detect turn shape      |
| - broad? scoped?          |
| - operational? reflective?|
| - calibration? activation?|
+-------------+-------------+
              |
              v
+---------------------------+
| 2. rank candidates        |
| - LifeDomain candidates   |
| - OperationalArc candidates|
| - Pattern candidates      |
+-------------+-------------+
              |
              v
+---------------------------+
| 3. assign load budget     |
| - how many arcs?          |
| - how many patterns?      |
| - do we need GlobalSit?   |
| - do we need evidence?    |
+-------------+-------------+
              |
              v
+---------------------------+
| 4. refresh stale derived  |
| - GlobalSituation         |
| - ArcSituation            |
| - recent continuity       |
+-------------+-------------+
              |
              v
+---------------------------+
| 5. assemble WorkingContext|
+-------------+-------------+
              |
              v
+---------------------------+
| 6. decide what to surface |
| - resume notice?          |
| - 1-line state summary?   |
| - pattern mention?        |
+---------------------------+
```

Recommended session-start modes:

1. **Scoped operational start**
   - load one matching `OperationalArc`, its `ArcSituation`, relevant domain, and 0-2 high-value patterns
   - surface a resume notice plus a one-line state summary

2. **Broad orient start**
   - load `GlobalSituation`, top domains, top arcs, and 1-2 patterns
   - surface a compact orient summary

3. **Reflective start**
   - load relevant domains, top patterns, and evidence as needed
   - surface theme- or pattern-led framing when useful

4. **Calibration start**
   - load relevant patterns, evidence refs, and related arc/domain
   - surface observation → interpretation → recommendation structure

### 5.9 Make relational stance a first-class primitive

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

### 5.10 Define product-owned semantics for support and relational behavior

The model should not be handed a bag of labels and asked to invent their meaning at runtime.

Instead:
- **product-owned registries** define what each relational and support dimension means behaviorally
- **runtime policy resolvers** choose effective values from context, need, target, transient state, patterns, and evidence
- a **behavior compiler** translates those effective values into a response contract
- the **LLM** remains responsible for natural phrasing, situational tact, and final language composition inside that contract

In other words:
- the product defines what `candor = high` or `recommendation_forcefulness = high` does
- the runtime decides when those values apply
- the model expresses them naturally in context

This keeps the system structured, adaptive, and testable.

### 5.11 Keep immersive presence separate from factual invention

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

### 5.12 Formalize the learning, reflection, and calibration loop

The system should distinguish clearly between:
- **learning** — internal adaptation and structured memory updates
- **reflection** — user-facing meaning-making and correction surfaces
- **calibration** — explicit comparison between narrative and evidence

The learning system should operate on **episodes**, not just session blobs.

From those episodes, Alfred should be able to generate candidate learnings across at least five classes:
- operational learning
- support-effectiveness learning
- relational-preference learning
- identity-theme learning
- direction-theme learning

The more interpretive and identity-shaping the learning is, the more it should remain candidate-first and user-confirmed before becoming durable truth.

### 5.13 Make calibration explicit

Calibration should be a product feature, not only an emergent side effect of good reflection.

Alfred should be able to compare:
- what the user says matters versus what the record shows
- what the user predicted versus what happened
- what the user planned versus what later unfolded
- what themes feel true versus what evidence supports
- where the user may be flattering themselves
- where the user may be underestimating themselves

When Alfred makes a stronger calibration claim, he should separate:
- **observation**
- **interpretation**
- **recommendation**

And he should preserve:
- evidence refs where appropriate
- uncertainty when confidence is limited
- user correction paths

The goal is not fake neutrality.
The goal is disciplined honesty.

### 5.14 Define the review and promotion ladder

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
- project- and arc-scoped support updates can adapt quickly
- context-scoped support updates can adapt with evidence
- global support changes should be surfaced
- identity themes and direction themes should remain candidate-first until the user confirms them
- calibration claims should stay linked to evidence and confidence
- only the deepest, most durable, user-endorsed truths should be promoted into `USER.md`

### 5.15 Define the source-of-truth map

The umbrella model should formalize ownership clearly.

| Surface | Owns | Must not own |
|---|---|---|
| `SYSTEM.md` | support operating model, memory layers, retrieval order, stance and support contract philosophy, promotion rules | Alfred's voice, repo workflow rules, user-specific durable facts |
| `AGENTS.md` | execution behavior rules, tool discipline, ask-first boundaries, code/workflow rules | memory ontology, relational identity, user profile semantics |
| `SOUL.md` | Alfred's identity, voice, relational posture, emotional texture, friend/peer/mentor character | storage semantics, tool instructions, structured support state |
| `USER.md` | explicit user-provided or user-confirmed durable truths, values, preferences, durable support wishes | inferred support values, temporary candidates, intervention logs, active task state |
| Structured support memory | domains, operational arcs, tasks, open loops, episodes, support profile, interventions, outcomes, patterns, evidence refs | Alfred's identity prose, explicit always-loaded user truth |
| Session archive | raw provenance, tool outcomes, timestamps, evidence lookup, resume support, calibration evidence | primary active-work truth, support profile truth |
| Runtime self-model | Alfred's current runtime/interface/capability state | user truth, support memory, durable identity themes |

### 5.16 Define the runtime loop

At runtime, Alfred should:
1. detect the current need and current interaction shape
2. check for domain / arc / pattern candidates
3. load relevant operational state
4. recover recent continuity when needed
5. refresh `GlobalSituation` or `ArcSituation` when stale and useful
6. load effective support and relational values
7. derive the current stance summary
8. compile a behavior contract
9. choose interventions
10. respond or act
11. log episode evidence and outcomes
12. calibrate against the record when relevant
13. expose review or correction surfaces when appropriate

This is the operating loop child PRDs should implement incrementally.

### 5.17 Make this the parent model for the child PRDs

The child PRDs should align as follows:
- **PRD #167** — transcript/session demotion, life domains, operational arcs, episode evidence, and derived situation objects
- **PRD #168** — relational/support registries, composite policy resolution, behavior compilation, and bounded adaptation
- **PRD #169** — pattern family, surfacing rules, review cards, correction, and user-facing reflection/calibration surfaces
- **PRD #147** — identity, voice, and internal self-model foundation already completed

---

## 6. User Experience Requirements

Users should be able to experience Alfred as:
- a steady companion rather than a fresh assistant every time
- a system that can help them re-orient when they feel lost or scrambled
- a system that can get them back into the last days or weeks of work quickly
- a system that can reduce action friction and help with executive-function struggles without reducing the whole product to a diagnosis-specific mode
- a presence that can feel like a friend or peer and sometimes a mentor, coach, or analyst without switching into crude modes
- a system that learns how to help without becoming opaque
- a system that can hold up an evidence-backed mirror without silently turning tentative insight into identity-level fact
- a fresh-session UX that clears clutter without erasing continuity

Representative experiences:
- "Help me start this."
- "What am I actually in the middle of right now?"
- "What was I doing last week?"
- "Which option feels more like me?"
- "Why do I keep repeating this pattern?"
- "What have you learned about how I work?"
- "Why are you being more direct with me lately?"
- "Show me the evidence for that."
- "Remember this about me."
- "Don't frame me that way."

---

## 7. Success Criteria

- [ ] Alfred's product direction is described as one coherent relational system for orientation, continuity, calibration, and action rather than several adjacent feature ideas.
- [ ] Sessions are clearly treated as chat surfaces and provenance boundaries rather than the sole continuity primitive.
- [ ] The architecture defines shared primitives that work across re-orientation, re-entry, action support, decision support, reflection, and calibration.
- [ ] Searchable session history remains explicit as a foundational capability for resume, provenance, and calibration.
- [ ] Relational stance is formalized as part of the product rather than left implicit in tone alone.
- [ ] Load planning and behavior compilation are part of the architecture rather than left to prompt vibes.
- [ ] Markdown files and structured support memory have clear ownership boundaries.
- [ ] Learning, reflection, and calibration are formalized as one bounded loop with user-visible control.
- [ ] PRDs #167, #168, and #169 align to the same vocabulary, assumptions, and source-of-truth rules.
- [ ] Docs and managed prompt/template files can be updated to describe the same system consistently.

---

## 8. Milestones

### Milestone 1: Define the relational support operating model
Document the thesis, interaction primitives, user-facing jobs, context taxonomy, session role, and runtime loop.

Validation: the umbrella model is clear enough to govern the child PRDs and docs.

### Milestone 2: Define source-of-truth and ownership boundaries
Formalize what belongs in markdown, structured support memory, session archive, and runtime self-model.

Validation: docs and PRDs no longer disagree about where durable user truth, learned support state, provenance, and calibration evidence belong.

### Milestone 3: Align child PRDs to the umbrella model
Update PRDs #167, #168, and #169 so they read as coherent parts of one system.

Validation: the child PRDs share the same vocabulary, interaction model, load-planning assumptions, and learning/reflection/calibration boundaries.

### Milestone 4: Unify docs and managed instructions
Update user-facing docs, developer docs, architecture docs, memory docs, and managed templates so they describe the same system.

Validation: there is one clear written model for Alfred's relational support behavior, session-search role, and memory architecture.

### Milestone 5: Validate the model against representative support journeys
Check the model against re-orientation, resume, action support, decision support, identity reflection, direction reflection, calibration, and cross-session relational continuity.

Validation: the system can support those journeys without needing diagnosis-specific architecture.

---

## 9. Likely File Changes

```text
docs/ARCHITECTURE.md
docs/MEMORY.md
docs/how-alfred-helps.md
docs/relational-support-model.md
docs/ROADMAP.md
README.md
prds/done/167-support-memory-foundation.md
prds/168-adaptive-support-profile-and-intervention-learning.md
prds/done/169-reflection-reviews-and-support-controls.md
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
| The system stays abstract and never cashes out into behavior | High | define jobs, primitives, load-planning rules, and behavior contracts explicitly |
| Session semantics remain overloaded | High | demote sessions and move semantic ownership to episodes, arcs, domains, and patterns |
| Relational richness drifts into inconsistency | High | formalize stance dimensions, policy resolvers, and ownership boundaries |
| Immersion erodes trust through invented facts | High | allow immersive presence while preserving concrete factual grounding rules |
| Reflection grows into an unbounded essay engine | Medium | keep review bounded, typed, evidence-backed, and action-linked |
| Personalization becomes too opaque | High | require evidence, inspection, and correction surfaces |
| Calibration turns into fake certainty or harshness theater | High | separate observation, interpretation, and recommendation; preserve uncertainty and correction |
| Markdown and structured memory continue to overlap ambiguously | Medium | enforce a clear source-of-truth map |
| The architecture still gets framed as a narrow support mode | Medium | keep the umbrella thesis diagnosis-agnostic, primitive-first, and job-centered |

---

## 11. Validation Strategy

This PRD is documentation-first and architecture-first.

Validation for this planning pass should focus on:
- internal consistency across the umbrella PRD and child PRDs
- consistency between PRDs and user/developer docs
- honest distinction between current implementation and target architecture where needed
- clean ownership boundaries across markdown, structured memory, and provenance layers
- explicit treatment of session search as a foundation rather than a legacy leftover
- explicit treatment of calibration as a product capability rather than vague reflection language
- explicit treatment of behavior policy as runtime-resolved rather than raw LLM improvisation

If later implementation work follows from this PRD, validation should use the standard Python workflow plus targeted tests for touched support-memory, session-search, orchestration, and behavior-compilation surfaces.

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
| 2026-03-30 | Alfred should be formalized as a relational support system for orientation, continuity, calibration, and action | The product intent is broader than narrow productivity, memory-only framing, or diagnosis-specific support |
| 2026-03-30 | Searchable session history remains a foundational capability | Alfred needs re-entry, provenance, and calibration against the record, not just durable memory |
| 2026-03-30 | Sessions remain user-facing chat containers, but not the main semantic continuity primitive | New chats should feel fresh without causing continuity amnesia |
| 2026-03-30 | Life domains, operational arcs, episodes, and patterns should be distinct primitives | Projects, domains, recurring themes, and support learnings do not behave like one object type |
| 2026-03-30 | Friend, peer, mentor, coach, and analyst are derived stances, not hard product modes | One system should express many relational positions without persona fragmentation |
| 2026-03-30 | V1 context taxonomy remains `plan`, `execute`, `decide`, `review`, `identity_reflect`, `direction_reflect`, but the product promise is broader than those labels | Orient, resume, and calibrate cut across multiple contexts and should remain explicit requirements |
| 2026-03-30 | Product defines behavioral semantics; runtime resolves composite values; the model expresses them naturally | This keeps the system structured, adaptive, and testable |
| 2026-03-30 | Episode-level learning is preferred over coarse session-only learning | Learning needs finer structure than one blob per conversation |
| 2026-03-30 | Learning may silently improve scoped support behavior, but may not silently redefine the user's identity | Operational adaptation should stay fast while identity-level truth stays visible and consensual |
| 2026-03-30 | Calibration claims should separate observation, interpretation, and recommendation | Alfred should be an evidence-backed mirror, not a vibe engine or fake neutral narrator |
| 2026-03-30 | Immersive relational presence is in-bounds, but concrete factual invention is not | Alfred should feel alive without becoming incoherent or ungrounded |
| 2026-03-30 | Most continuity and loading machinery should remain invisible to the user except where trust requires explicitness | Alfred should feel legible, not mechanically narrated |
