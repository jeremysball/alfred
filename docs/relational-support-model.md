# Relational Support Model

**Status:** Planned architecture. This document describes the target support model being formalized by PRD #179 and child PRDs #167, #168, and #169.

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

The model is intentionally relational:
- Alfred should feel like a companion
- friend, peer, mentor, coach, and analyst are part of the product language
- those are not separate hard-coded personas
- they are derived stance summaries produced by one runtime system

## Product thesis

Alfred should help through one shared support loop:
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
- they should remain first-class product requirements even if they do not yet appear as separate runtime labels

## Seven core primitives

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
The durable record of what Alfred tried and what happened.

### 7. Review and control
The user-facing inspection, explanation, and correction layer.

## Session search is a first-class capability

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

Transcript sessions should remain the raw archive for provenance, replay, and recall. Active continuity should live in life domains, operational arcs, arc-linked work state, and fresh situation snapshots.

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
- runtime state selects effective values
- a behavior compiler turns those values into a compact response contract
- the model composes natural language inside that contract

That means the model infers phrasing, not product semantics.
The prompt contract should steer behavior without forcing stock wording or exposing internal policy labels by default.

## Learning model

The learning system should operate on **learning situations inside sessions**.

### Why learning situations
A single conversation can move through multiple contexts:
- execution
- decision support
- identity reflection
- direction reflection

One session blob is too coarse for reliable learning.
A full episode report is useful later for review, but it is too coarse to be the only similarity and adaptation unit.

### Learning-situation concept
Each learning situation should capture:
- dominant support need / response mode for the moment
- subject refs
- interventions attempted
- response signals
- outcome signals
- evidence refs
- the relational and support contract used

### Episode role
`SupportEpisode` should remain a derived synthesis/report boundary.
It can summarize several learning situations later for review, reflection, and correction surfaces.

## Learning classes

The runtime should distinguish at least five learning classes:
- **operational learning**
- **support-effectiveness learning**
- **relational-preference learning**
- **identity-theme learning**
- **direction-theme learning**

These classes should not share the same promotion rules.

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

Reflection is the user-facing meaning-making layer. It is not the same thing as learning.

### Reflection surfaces
1. **Inline reflection** — surfaced during live conversation when highly relevant
2. **Internal synthesis** — mostly hidden state updates after or during conversation
3. **Explicit review** — weekly or on-demand bounded review cards

### Pattern taxonomy
Recommended v1 production pattern types:
- `support_effectiveness`
- `recurring_blocker`
- `relational_preference`
- `identity_theme`
- `direction_tension`
- `recovery_pattern`
- `value_signal`
- `calibration_gap`

### Review cards
Recommended v1 review-card types:
- support-fit
- blocker
- relational-fit
- identity-theme
- direction-tension
- calibration-gap

Reviews should stay bounded to 1-3 cards and each card should include evidence plus an action, confirmation question, or correction path.

## Promotion ladder

The target ladder is:
1. raw evidence
2. typed episode evidence
3. candidate pattern
4. confirmed structured support memory
5. explicit durable user truth in `USER.md`

Key rule:
- learning may silently improve scoped support behavior
- learning may not silently redefine the user's identity

That means identity and direction themes stay candidate-first until the user confirms them.

## Source-of-truth map

| Surface | Owns |
|---|---|
| `SYSTEM.md` | support operating model, retrieval order, promotion rules |
| `AGENTS.md` | execution rules, tooling posture, safety/permission rules for work |
| `SOUL.md` | Alfred's identity, voice, and relational posture |
| `USER.md` | explicit user-provided or user-confirmed durable truths |
| Structured support memory | life domains, operational arcs, arc-linked work state, typed episodes, evidence refs, derived situations, support values, interventions, patterns |
| Session archive | raw transcript provenance, recall, and calibration evidence |
| Runtime self-model | Alfred's current interface/runtime state |

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
2. load operational state
3. recover recent continuity when needed
4. load effective relational values
5. load effective support values
6. derive stance summary
7. compile behavior contract
8. choose interventions
9. respond or act
10. log evidence and outcomes
11. calibrate against the record when relevant
12. surface review or correction when appropriate

## PRD map

- **PRD #179** — umbrella model and ownership map
- **PRD #167** — operational support memory and episode evidence foundation
- **PRD #168** — relational/support registries, behavior compiler, bounded adaptation
- **PRD #169** — reflection surfaces, review cards, correction controls
- **PRD #147** — self-model and personality foundation already completed

## Current implementation note

Alfred already has important foundations:
- always-loaded markdown context files
- persistent memories
- searchable session archive
- typed episodes and evidence refs
- life domains, operational arcs, and arc-linked work state
- derived `ArcSituation` and `GlobalSituation` snapshots
- operational-first support-context helpers for resume, orient, and active-work retrieval
- self-model and personality work

What is still being formalized here is the next layer:
- relational/support registries
- behavior compilation
- bounded calibration surfaces
- review and correction surfaces

That is the architecture this document is meant to make explicit.
