# Relational Support Model

**Status:** Active projection architecture. This document describes the current support and relational product projections that sit on top of Alfred's shared semantic runtime substrate.

## Relationship to the architecture doc

This file is downstream of:
- [docs/architecture/semantic-runtime-engine.md](architecture/semantic-runtime-engine.md)

That architecture doc owns:
- the generalized semantic substrate
- the projection contract
- the shared runtime abstractions
- the deterministic/model responsibility split

This document owns:
- support and relational product semantics
- current projection boundaries
- product-facing runtime loops and user experience expectations

It is **not** the shared substrate contract.

## Overview

Alfred is being formalized as a **relational support system for orientation, continuity, calibration, and action**.

The aim is not a diagnosis-specific helper or a pile of adjacent support features.
The aim is one system that can:
- re-orient the user when they are foggy
- recover continuity across days and weeks of work
- lower activation friction
- help make decisions
- surface honest reflection
- hold up an evidence-backed mirror

This model sits on one shared semantic substrate with multiple projections.
Today the most important projections are:
- **support**
- **relational**

Future projections should remain possible.

## Product thesis

Alfred should help through one shared product loop:
1. understand what kind of moment this is
2. load what matters operationally
3. recover recent continuity when needed
4. decide how to show up relationally
5. decide how to shape help
6. choose an intervention
7. observe what happened
8. compare story to evidence when calibration matters
9. learn from it
10. surface important changes back to the user when appropriate

## Why projections matter

The architecture is shared, but the ontologies are not.

### Support projection
The support projection owns questions like:
- what kind of help is needed right now?
- what subject or thread is active?
- what operational continuity should be loaded?
- what support preference or pattern should affect the move?

### Relational projection
The relational projection owns questions like:
- how should Alfred show up in this moment?
- what stance constraints or shifts are appropriate?
- did the user express a relational preference or boundary?
- does the current turn require relational explanation or repair-sensitive acknowledgment?

Important rule:
- support and relational are **projections of the substrate**, not separate runtime engines

## Core jobs vs interaction contexts

These are not the same thing.

### Core jobs
The user-facing jobs Alfred must be able to do are:
- **orient**
- **resume**
- **activate**
- **decide**
- **reflect**
- **calibrate**

### V1 interaction contexts
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
- they should remain first-class product requirements even when they do not appear as separate runtime labels

## Projection-owned primitives

### 1. Operational state
Durable support state such as:
- projects
- tasks
- open loops
- blockers
- decisions in flight

### 2. Interaction context
The dominant support task in the current episode.

### 3. Relational stance
How Alfred should show up as a presence.

### 4. Support profile
How help should be shaped for this user, context, and project.

### 5. Interventions
The support moves Alfred can make.

### 6. Evidence and outcomes
The domain-facing record of what Alfred tried, what happened, and what later mattered.

### 7. Review and control
The user-facing inspection, explanation, and correction layer.

These are product primitives for the current projections.
They are not the generic semantic substrate.

## Session search is a first-class capability

Session search remains essential.

It is not the whole product thesis, but it is one of the core capabilities that makes the larger system work.

Alfred needs searchable session history for:
- fast re-entry into the last day or week of work
- provenance for pattern claims
- calibration against prior statements, predictions, and decisions
- evidence-backed review
- avoiding pointless recap requests when the record already exists

Structured projection state does not replace session search.
It sits on top of it.

Transcript sessions should remain the raw archive for provenance, replay, and recall. Active continuity should live in operational state, projection state, and fresh situation snapshots.

## Curated memory stays separate and supplemental

Curated memory still matters, but it has a narrower job.

It should hold:
- explicit reusable facts
- explicit durable preferences
- recurring instructions likely to matter again
- durable decisions and constraints worth semantic retrieval later

It should not become:
- the system of record for active work state
- the system of record for effective support or relational values
- a dumping ground for inferred identity themes or candidate patterns

Relevant curated memories may be auto-injected into runtime context.
`search_memories` should remain available for targeted lookup, inspection, or narrower retrieval when the default injected context is not enough.

Boundary rule:
- structured projection state owns active domain continuity
- semantic-runtime learning owns adaptive policy and evidence updates
- curated memory supplements both, but does not silently replace either one

## Relational stance model

The runtime should distinguish between:
- **stance labels** for explanation and readability
- **stance dimensions** for actual runtime composition

### Stance labels
- friend
- peer
- mentor
- coach
- analyst

### Relational dimensions
Recommended v1 dimensions:
- `warmth`
- `companionship`
- `candor`
- `challenge`
- `authority`
- `emotional_attunement`
- `analytical_depth`
- `momentum_pressure`

The runtime should resolve dimension values first, then derive a stance summary such as:
- friend/coach blend
- peer/analyst blend
- friend/mentor blend

This keeps Alfred coherent while still expressive.

## Support-shaping model

Support shaping should use a separate fixed registry.

Recommended v1 support dimensions:
- `planning_granularity`
- `option_bandwidth`
- `proactivity_level`
- `accountability_style`
- `recovery_style`
- `reflection_depth`
- `pacing`
- `recommendation_forcefulness`

Important split:
- **relational dimensions** control how Alfred shows up
- **support dimensions** control how Alfred structures help

## Product-owned semantics

The runtime should not ask the model to invent what dimensions mean.

Instead:
- the product defines behavioral semantics for each dimension
- projected state selects effective values
- a behavior compiler turns those values into a compact response contract
- the model composes natural language inside that contract

That means the model infers phrasing, not product semantics.
The prompt contract should steer behavior without forcing stock wording or exposing internal policy labels by default.

## Semantic runtime usage inside these projections

The support and relational projections both reuse the shared substrate abstractions from the architecture doc:

1. **candidate adjudication**
2. **grounded observation extraction**
3. **deterministic activation and surfacing policy**

These are runtime mechanics, not product ontologies.

### Candidate adjudication
Use this when the runtime needs a bounded choice or ranking among candidates.

Examples:
- resume vs orient vs neither
- support need selection
- subject resolution
- pattern surfacing
- live relational-state and stance deltas

### Grounded observation extraction
Use this when the runtime needs zero or more typed observations from language.

Examples:
- support preference
- correction
- interpretation rejection
- relational preference
- relational boundary
- stance feedback

### Deterministic activation and surfacing policy
This layer stays code-owned.
It decides:
- what becomes active for the current turn
- what stays candidate-only
- what becomes durable learning input
- what is surfaced, explained, or kept silent

Important split:
- the model may judge or extract
- the runtime validates, activates, persists, and explains
- user-facing control surfaces still outrank inference

See [docs/architecture/semantic-runtime-engine.md](architecture/semantic-runtime-engine.md) for the shared boundary doc.

## Learning and evidence model

This product model needs a generalized evidence and adaptive-state story, but it should not hard-code one support-specific artifact model as the architecture.

Rules:
- the substrate should support grounded observations, bounded state updates, and inspectable evidence
- projections may need different durable record shapes over time
- no current projection-specific schema should be treated as universal architecture by default

### Current implementation note

The repo currently ships support-domain learning and inspection behavior through PRD #183.
That work is real and important, but it should be interpreted as:
- current support-domain implementation
- migration constraint
- not the general substrate design

## Learning classes

The runtime should distinguish at least five learning classes:
- **operational learning**
- **support-effectiveness learning**
- **relational-preference learning**
- **identity-theme learning**
- **direction-theme learning**

These classes should not share the same promotion rules.

No silent collapse rule:
- curated memories should not automatically become support-profile values
- projection observations should not automatically become curated memories
- learned patterns should not silently rewrite explicit durable truth

## Calibration model

Calibration should be explicit, not implied.

Alfred should be able to compare:
- what the user says matters versus what the record shows
- what the user predicted versus what happened
- what the user planned versus what later unfolded
- what themes feel true versus what evidence supports

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

## Reflection model

Reflection is the user-facing meaning-making layer. It is not the same thing as the shared substrate.

### Reflection surfaces
1. **Inline reflection** — surfaced during live conversation when highly relevant
2. **Internal synthesis** — mostly hidden state updates after or during conversation
3. **Explicit review** — weekly or on-demand bounded review cards
4. **Inspection and correction** — bounded user-invoked views over support state, recent changes, and typed correction actions

### Pattern taxonomy
The current v1 pattern family uses these durable kinds:
- `support_preference`
- `recurring_blocker`
- `identity_theme`
- `direction_theme`
- `calibration_gap`

These patterns may be `candidate`, `confirmed`, or `rejected`.
Candidate and confirmed patterns can feed reflection surfaces. Only confirmed patterns should silently participate in runtime policy.

### Review cards
Current v1 review cards are **derived from durable patterns**, not stored as a second truth layer.

The current v1 review-card kinds are:
- `support_fit`
- `blocker`
- `identity_theme`
- `direction_theme`
- `calibration_gap`

Reviews stay bounded to 1-3 cards. Each card should include evidence plus an action, confirmation question, or correction path.

## Promotion ladder

The target ladder is:
1. raw evidence
2. typed projected observations and validated runtime signals
3. candidate pattern or candidate state update
4. confirmed projection state or durable domain memory
5. explicit durable user truth in `USER.md`

Key rule:
- learning may silently improve scoped runtime behavior
- learning may not silently redefine the user's identity

That means identity and direction themes stay candidate-first until the user confirms them.

## Source-of-truth map

| Surface | Owns |
|---|---|
| `SYSTEM.md` | support operating model, retrieval order, promotion rules |
| `AGENTS.md` | execution rules, tooling posture, safety/permission rules for work |
| `SOUL.md` | Alfred's identity, voice, and relational posture |
| `USER.md` | explicit user-provided or user-confirmed durable truths |
| projection state stores | operational continuity, projection values, patterns, evidence, inspection payloads |
| session archive | raw transcript provenance, recall, and calibration evidence |
| runtime self-model | Alfred's current interface/runtime state |

## Relational contract

The system should allow immersive relational presence.

In-bounds:
- first-person identity
- warmth, care, companionship
- speaking as a real presence rather than constantly distancing with "as an AI"
- honest challenge when context warrants it

Still required:
- do not invent concrete sensory or world-state facts Alfred does not have
- do not invent actions Alfred did not take
- do not treat tentative interpretive themes as settled identity truth without visibility or confirmation

## Runtime loop

The target runtime loop is:
1. infer context
2. load operational state and recover recent continuity when needed
3. assemble deterministic runtime facts and candidate sets
4. activate the relevant projection or projections for the turn
5. run **candidate adjudication** when the turn needs bounded selection or ranking
6. run **grounded observation extraction** when the turn may contain learnable signals
7. validate and apply **deterministic activation and surfacing policy**
8. load effective relational values and effective support values
9. derive stance summary and compile behavior contract
10. choose interventions
11. decide whether any loaded pattern or stance explanation should stay silent, get a compact mention, or get a richer explanation
12. respond or act
13. record evidence, state updates, and traces through deterministic runtime code
14. calibrate against the record when relevant
15. surface review, inspection, or correction when appropriate

## PRD map

- **PRD #179** — umbrella model and ownership map
- **PRD #183** — current shipped support-domain learning and inspection implementation
- **PRD #184** — support projection work on the semantic runtime engine
- **PRD #185** — generic semantic-runtime substrate contract and projection envelope
- **PRD #192** — relational projection work on the semantic runtime engine
- **PRD #147** — self-model and personality foundation already completed

## Current implementation note

Alfred already has important foundations:
- always-loaded markdown context files
- persistent memories
- searchable session archive
- typed support and operational memory
- life domains, operational arcs, and arc-linked work state
- derived situation snapshots
- operational-first support-context helpers for resume, orient, and active-work retrieval
- self-model and personality work

What is still being formalized here is the next layer:
- the generalized semantic runtime substrate
- support and relational projections that plug into that substrate
- behavior compilation
- bounded calibration surfaces
- review and correction surfaces

That is the architecture this document is meant to make explicit at the product/projection level.
