# Alfred Memory System

This document explains Alfred's memory model as it exists today and the planned support-memory extensions now being formalized by PRDs #167, #168, #169, and #179.

## Status

Alfred already has a durable memory foundation:
- always-loaded markdown files
- curated remembered facts
- searchable session archive

The next step is to turn that foundation into a **support memory system** rather than treating search alone as the product center.

---

## 1. Current memory foundation

### Always-loaded files

These files are loaded every turn and provide durable, high-priority context:
- `SYSTEM.md`
- `AGENTS.md`
- `SOUL.md`
- `USER.md`

Use them for:
- stable operating rules
- Alfred's identity and voice
- explicit durable user preferences and truths

These files are expensive but always available.

### Curated memory

Curated memory stores facts Alfred explicitly decides to remember.

Use it for:
- durable user preferences
- recurring project context
- stable decisions likely to matter later
- memorable facts worth retrieving semantically

Curated memory is not the same thing as raw conversation history.

### Session archive

The session archive stores searchable conversation history and tool-call provenance.

Use it for:
- recall requests
- provenance and evidence lookup
- time-bounded history
- details too specific or temporary for curated memory

---

## 2. The architectural change in progress

The current foundation is good for recall.

It is not yet enough for a support system that needs to answer questions like:
- what is active right now?
- what is blocked?
- what decision is still open?
- what kind of help works in this context?
- what recurring pattern is Alfred noticing?

The new direction is:
- keep archive and search
- but make them supporting primitives rather than the whole runtime model

---

## 3. Target support-memory layers

The planned support-memory architecture adds structured layers on top of the current foundation.

### Layer 1: Raw archive
What it is:
- sessions
- messages
- tool outcomes
- timestamps
- raw provenance

Role:
- evidence lookup
- recall
- debugging
- auditability

### Layer 2: Typed episode evidence
What it is:
- structured interaction episodes inside sessions
- one dominant context per episode
- intervention and outcome traces

Role:
- the main evidence substrate for later learning
- finer-grained than one summary per session

### Layer 3: Operational support memory
What it is:
- projects
- tasks
- open loops
- blockers
- decisions in flight

Role:
- the primary runtime state for active support
- what Alfred should consult first when helping the user move or resume

### Layer 4: Support and relational profile state
What it is:
- effective support values
- effective relational values
- intervention history
- update events

Role:
- how Alfred learns what kind of help works
- how Alfred learns how to show up across contexts

### Layer 5: Pattern and review state
What it is:
- candidate patterns
- confirmed patterns
- review cards
- correction history

Role:
- bounded reflection
- user-visible explanation and control

### Layer 6: Durable explicit user truth
What it is:
- explicit user-provided or user-confirmed durable truths in `USER.md`

Role:
- always-loaded identity-level preferences, values, and truths that should shape nearly every future conversation

---

## 4. Retrieval order

### Current principle
When prior context may matter:
1. current conversation
2. durable always-loaded files
3. curated memory
4. session archive

### Target support principle
When Alfred is helping the user act, decide, review, or reflect:
1. current conversation
2. relevant operational support memory
3. relevant support/relational profile state
4. relevant typed episode evidence
5. curated memory when appropriate
6. session archive for provenance, recall, or fallback

That changes the center of gravity from:
- "what did we talk about?"

to:
- "what is active, what is unresolved, what kind of moment is this, and what kind of help works here?"

---

## 5. Promotion ladder

Not every observation should become durable identity truth.

The planned promotion ladder is:
1. raw evidence
2. typed episode evidence
3. candidate pattern
4. confirmed structured support memory
5. explicit durable user truth in `USER.md`

Key rule:
- learning may silently improve narrow, scoped support behavior
- learning may not silently redefine the user's identity

That means:
- project-scoped support updates can adapt quickly
- context-scoped support updates can adapt with evidence
- broader changes should be surfaced
- identity themes and direction tensions should remain candidate-first until confirmed

---

## 6. What belongs where

| Kind of information | Home |
|---|---|
| Alfred's operating philosophy | `SYSTEM.md` |
| Alfred's identity and voice | `SOUL.md` |
| Explicit user-confirmed durable truths | `USER.md` |
| Stable remembered fact worth semantic retrieval | curated memory |
| Raw past conversation | session archive |
| Active project / task / open loop | structured support memory |
| What support style works in a context | structured support memory |
| Candidate identity theme | structured support memory until confirmed |
| Durable user-endorsed identity truth | `USER.md` |

---

## 7. Reflection and correction

The new memory model is not only about storage.

It also supports:
- explanation of why Alfred is helping a certain way
- weekly and on-demand review
- confirmation or rejection of learned patterns
- resetting or editing support assumptions
- promoting confirmed truths into `USER.md` only when appropriate

That is what turns memory into a real support system instead of a search layer.

---

## 8. Related documents

- [How Alfred Helps](how-alfred-helps.md)
- [Relational Support Model](relational-support-model.md)
- [Architecture](ARCHITECTURE.md)
- [PRD #167: Support Memory Foundation](../prds/167-support-memory-foundation.md)
- [PRD #168: Adaptive Support Profile and Intervention Learning](../prds/168-adaptive-support-profile-and-intervention-learning.md)
- [PRD #169: Reflection Reviews and Support Controls](../prds/169-reflection-reviews-and-support-controls.md)
- [PRD #179: Relational Support Operating Model](../prds/179-relational-support-operating-model.md)
