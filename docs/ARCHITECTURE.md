# Alfred Architecture

This document is the top-level architecture overview for Alfred.
It explains the current runtime foundation, the semantic-runtime direction, and where the first-class boundary docs live.

## Status

Alfred already has:
- persistent context files
- curated memories
- typed support and operational memory
- session archive and search
- multiple interfaces
- runtime self-model assembly
- shipped support-domain learning and inspection behavior

The architecture is now centered on a **generalized semantic runtime substrate** with **projected ontologies** layered on top.

The canonical boundary doc for that design is:
- [docs/architecture/semantic-runtime-engine.md](architecture/semantic-runtime-engine.md)

Current projection-specific architecture is described in:
- [docs/relational-support-model.md](relational-support-model.md)
- [prds/184-semantic-adjudication-runtime-for-support-routing-and-learning.md](../prds/184-semantic-adjudication-runtime-for-support-routing-and-learning.md)
- [prds/192-relational-runtime-semantics-and-stance-adjudication.md](../prds/192-relational-runtime-semantics-and-stance-adjudication.md)

Important layering rule:
- **architecture docs** own system shape, boundaries, contracts, invariants, and migration direction
- **PRDs** own product slices, milestones, behavior, and validation
- **current implementation schemas** do not automatically become architecture

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
- typed support and operational memory
- life domains, operational arcs, and arc-linked work state
- derived situation snapshots
- session archive for raw searchable history and provenance

See [docs/MEMORY.md](MEMORY.md) for the memory model and planned extensions.

---

## 2. Semantic runtime direction

The semantic runtime should be understood through one shared architecture, not through support-first or seam-first mini-systems.

See [docs/architecture/semantic-runtime-engine.md](architecture/semantic-runtime-engine.md) for the full boundary doc.

The compressed model has three shared abstractions:

1. **candidate adjudication**
   - bounded model judgment over a provided candidate set or closed enum
2. **grounded observation extraction**
   - bounded model extraction of zero or more typed observations grounded in source evidence
3. **deterministic activation and surfacing policy**
   - code-owned validation, fallback, precedence, persistence, activation, inspection, and explanation rules

Those abstractions run on top of deterministic runtime facts and open-ended **ontology projections**.

Important design split:
- the **architecture** defines the substrate and projection contract
- each **projection** defines its domain ontology and product semantics
- the **model** makes bounded judgments inside closed contracts
- the **runtime** validates, activates, persists, and surfaces state deterministically

---

## 3. Projected ontologies

The current architecture assumes the substrate is open-ended.
Support and relational work are important current projections, not the whole engine.

### Support projection

The support projection owns semantics such as:
- operational continuity
- support need selection
- help-shaping dimensions
- subject resolution
- support pattern surfacing
- support-domain correction and preference signals

### Relational projection

The relational projection owns semantics such as:
- stance dimensions
- live relational conditions
- relational boundaries and preferences
- stance explanation rules
- relational surfacing and repair-sensitive behavior

### Future projections

The substrate should allow additional projections later without requiring a new engine.

That means new domains should be able to define:
- their own candidate spaces
- their own observation vocabularies
- their own deterministic interpretation rules
- their own inspection needs

without rewriting the shared runtime mechanics.

---

## 4. Current implementation note

The repo currently contains shipped support-domain learning and inspection behavior from PRD #183.

That work matters, but it should be interpreted correctly:
- it is a **current support-domain implementation slice**
- it is **not** the generalized semantic-runtime architecture
- it may be adapted, wrapped, or replaced when the generalized substrate lands

This distinction matters because the architecture must remain open-ended and ontology-agnostic.

---

## 5. Projection-specific product model

The main product-facing projection document is:
- [Relational Support Model](relational-support-model.md)

That document owns support and relational product semantics such as:
- core jobs
- support shaping
- relational stance semantics
- review and correction surfaces
- how the current projections fit together product-wise

It should not become the shared semantic-runtime contract.
That shared contract belongs in the architecture doc plus the generic substrate-contract PRD.

---

## 6. Source-of-truth boundaries

One major architectural goal is to stop smearing truth across markdown, search, runtime state, and domain-specific ledgers.

### Ownership map

| Surface | Owns | Must not own |
|---|---|---|
| `SYSTEM.md` | operating model, retrieval order, promotion rules | Alfred's voice, user-specific durable truths |
| `AGENTS.md` | execution and tool behavior rules | product ontologies, Alfred identity |
| `SOUL.md` | Alfred's identity, voice, and relational posture | storage and semantic-runtime contracts |
| `USER.md` | explicit user-provided or user-confirmed durable truths | inferred domain state, candidate patterns |
| architecture docs | system shape, boundaries, contracts, invariants | milestone/task sequencing |
| PRDs | product scope, user-visible behavior, milestones, validation | canonical architecture ownership |
| projection state stores | domain-specific active state, evidence, and inspection payloads | shared runtime mechanics |
| session archive | raw transcript provenance and recall | primary product truth |
| runtime self-model | Alfred's current interface/runtime state | user/domain truth |

---

## 7. Related documents

### Architecture docs
- [Semantic Runtime Engine](architecture/semantic-runtime-engine.md)
- [Memory System](MEMORY.md)
- [Self-Model & Introspection](self-model.md)

### Projection / product model docs
- [Relational Support Model](relational-support-model.md)
- [How Alfred Helps](how-alfred-helps.md)

### Key PRDs
- [PRD #179: Relational Support Operating Model](../prds/done/179-relational-support-operating-model.md)
- [PRD #183: Support Learning V2 Foundation](../prds/183-support-learning-v2-case-based-adaptation-and-full-inspection.md)
- [PRD #184: Support projection work on the semantic runtime engine](../prds/184-semantic-adjudication-runtime-for-support-routing-and-learning.md)
- [PRD #185: Generic semantic-runtime substrate contract](../prds/185-shared-semantic-adjudication-contract-and-symbolic-runtime-inputs.md)
- [PRD #192: Relational projection work on the semantic runtime engine](../prds/192-relational-runtime-semantics-and-stance-adjudication.md)
