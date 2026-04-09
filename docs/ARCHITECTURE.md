# Alfred Architecture

This document explains Alfred's current architecture and the relational support architecture formalized by completed PRD #179.

## Status

Alfred already has:
- persistent context files
- curated memories
- typed support episodes and evidence refs
- life domains, operational arcs, and arc-linked work state
- derived `ArcSituation` and `GlobalSituation` snapshots
- session archive and search
- multiple interfaces
- a runtime self-model and stronger personality layer

Alfred is now being extended into a **relational support system**.

That support layer is documented in:
- [docs/relational-support-model.md](relational-support-model.md)
- [prds/done/179-relational-support-operating-model.md](../prds/done/179-relational-support-operating-model.md)

This file keeps two things clear:
1. what Alfred already has as a runtime foundation
2. what the target support architecture adds on top

---

## 1. Current runtime foundation

### Interfaces

Alfred currently runs through multiple surfaces:
- terminal / TUI
- Web UI
- Telegram remains in the project, but the product direction is centered on the local interfaces

### Core runtime responsibilities

The runtime already handles:
- context assembly from managed markdown files
- persistent memory retrieval
- session storage and search
- LLM orchestration
- tool execution
- streaming responses
- scheduled jobs / cron infrastructure
- runtime self-model assembly for internal context

### Managed always-loaded files

Alfred's durable markdown layer is built around:
- `SYSTEM.md`
- `AGENTS.md`
- `SOUL.md`
- `USER.md`

These files are always loaded and shape behavior every turn.

Prompt fragments under `templates/prompts/` are small reusable supplements, not a second policy layer. The top-level files should stay compact and own the behavior-critical rules.

### Managed template sync

`TemplateManager.reconcile_template()` keeps template sync workspace-scoped so one checkout cannot silently overwrite another.

When an upstream template and a workspace file both change, the runtime should fail closed, mark the file as blocked for automatic sync, and write standard conflict markers instead of guessing. The same rule applies to managed prompt fragments; if one of them conflicts, Alfred blocks the owning top-level context file instead of loading a partial prompt.

That blocked state should remain visible in `/context`, in the persistent WebUI warning banner, and in the detailed WebUI context view so operators can repair drift intentionally.

The canonical recovery flow lives in [Template Sync and Conflict Recovery](template-sync.md).

### Current storage foundation

The memory foundation includes:
- durable markdown files for always-loaded context
- curated memory for selectively remembered facts
- typed support episodes and evidence refs
- life domains, operational arcs, and arc-linked work state
- derived `ArcSituation` and `GlobalSituation` snapshots
- session archive for raw searchable history and provenance

See [docs/MEMORY.md](MEMORY.md) for the memory model and the next planned extensions.

### Current operational-first seam

`src/alfred/memory/support_context.py` is the current runtime seam for support-memory retrieval. It can:
- refresh `ArcSituation` from structured arc state plus recent episode evidence
- refresh `GlobalSituation` from active domains plus top arc snapshots
- prefer structured resume and orientation context before archive fallback

---

## 2. Architectural shift in progress

The architecture is moving from:
- memory-augmented assistant

toward:
- relational support system

That shift changes the center of gravity.

The core question is no longer only:
- "what did we talk about?"

It becomes:
- "what kind of moment is this?"
- "what is active or unresolved?"
- "how should Alfred show up?"
- "what kind of help works here?"
- "what did Alfred learn from this exchange?"

This is the purpose of PRDs #167, #168, #169, and their umbrella PRD #179.

---

## 3. Target support architecture

The target support architecture adds seven primitives on top of the current runtime foundation:

1. **Operational state**
2. **Interaction context**
3. **Relational stance**
4. **Support profile**
5. **Interventions**
6. **Evidence and outcomes**
7. **Review and control**

### V1 context taxonomy

The planned v1 context taxonomy is:
- `plan`
- `execute`
- `decide`
- `review`
- `identity_reflect`
- `direction_reflect`

These are interaction contexts, not persona modes.

### Relational stance

Alfred should feel like some mix of:
- friend
- peer
- mentor
- coach
- analyst

Those are derived stance summaries, not hard-coded modes.

The runtime should compose them from relational dimensions such as:
- warmth
- companionship
- candor
- challenge
- authority
- emotional attunement
- analytical depth
- momentum pressure

### Support shaping

The runtime should also learn support dimensions such as:
- planning granularity
- option bandwidth
- proactivity
- accountability style
- recovery style
- reflection depth
- pacing
- recommendation forcefulness

Those values should be resolved by scope:
- global
- context
- project

---

## 4. Target support runtime loop

The planned runtime loop is:

1. infer context
2. load operational state
3. load effective relational values
4. load effective support values
5. derive stance summary
6. compile a behavior contract
7. choose interventions
8. respond or act
9. log evidence and outcomes
10. surface review or correction when appropriate

Important design split:
- the **product** defines what runtime dimensions mean
- the **runtime** learns which values apply
- the **model** expresses those values naturally in context

This keeps the system adaptive without letting core semantics drift.

---

## 5. Learning and reflection architecture

The planned learning system should be **learning-situation-based**, not only session-based.

### Why learning situations

A single session may contain:
- an execution exchange
- a decision exchange
- an identity reflection exchange

One session-level blob is too coarse for reliable support learning.
One whole episode report is useful for review, but it is still too coarse to be the main similarity and adaptation unit.

### Learning-situation role

Learning situations should become the typed evidence layer between:
- raw archive
- operational support memory
- support-profile updates
- reflection/review surfaces

### Episode role

`SupportEpisode` should remain a derived synthesis/report boundary built from related learning situations.
It supports review, reflection, and human-readable summary without becoming the primary learning unit again.

### Reflection role

Reflection should remain a separate user-facing layer with:
- inline reflection when highly relevant
- internal synthesis in the background
- weekly and on-demand bounded review cards
- explicit inspection and correction surfaces for learned support state

---

## 6. Source-of-truth boundaries

One major architectural goal is to stop smearing truth across markdown, search, and learned runtime state.

### Ownership map

| Surface | Owns | Must not own |
|---|---|---|
| `SYSTEM.md` | support operating model, retrieval order, promotion rules | Alfred's voice, user-specific durable truths |
| `AGENTS.md` | execution and tool behavior rules | support ontology, relational identity |
| `SOUL.md` | Alfred's identity, voice, and relational posture | storage and support semantics |
| `USER.md` | explicit user-provided or user-confirmed durable truths | inferred support values, temporary candidate patterns |
| Structured support memory | life domains, operational arcs, tasks, blockers, decisions, open loops, typed episodes, evidence refs, derived situations, support values, interventions, patterns | Alfred identity prose |
| Session archive | raw transcript provenance and recall | primary support truth |
| Runtime self-model | Alfred's current runtime state | user/support memory truth |

---

## 7. Related documents

### User-facing
- [How Alfred Helps](how-alfred-helps.md)

### Developer / architecture
- [Relational Support Model](relational-support-model.md)
- [Memory System](MEMORY.md)
- [Self-Model & Introspection](self-model.md)

### PRDs
- [PRD #179: Relational Support Operating Model](../prds/done/179-relational-support-operating-model.md)
- [PRD #167: Support Memory Foundation](../prds/done/167-support-memory-foundation.md)
- [PRD #168: Adaptive Support Profile and Intervention Learning](../prds/done/168-adaptive-support-profile-and-intervention-learning.md)
- [PRD #169: Reflection Reviews and Support Controls](../prds/done/169-reflection-reviews-and-support-controls.md)
