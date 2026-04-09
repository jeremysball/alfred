# Architecture: Cross-Domain Learning (Shared Substrate, Separate Symbolic Worlds)

## Status

Design direction. This document records what we want at the architecture level, so we can write smaller PRDs without re-arguing first principles.

## Summary

We want Alfred to learn across domains (operational support, relational support, and biographical memory) without:
- forcing a false dichotomy (“operational *or* relational”) when many patterns span both
- collapsing everything into one mushy ontology
- surfacing the same underlying insight multiple times in different voices

The core move is:

1. **Shared learning substrate** (grounded evidence → attempts/observations → cases)
2. **Separate domain symbolic worlds** (operational model vs relational model: different objects, validators, promotion rules)
3. **A coordination layer** for:
   - cross-domain identity linking
   - primary ownership
   - surfacing deduplication

This is *not* “one system and multiple views into the same domain model.”
It is “one substrate and multiple compiled symbolic models.”

---

## 1) Domains and boundaries

### Operational domain (symbolic world)
Owns models like:
- arcs, tasks, blockers, decisions, open loops
- operational patterns (e.g. recurring blocker, calibration gap)
- operational surfacing and reflection guidance

Primary question: **“What is happening in work-state and how do we move?”**

### Relational domain (symbolic world)
Owns models like:
- relational stance dimensions + stance deltas
- relational preferences/boundaries
- rupture/repair signals and trust-sensitive dynamics
- relational surfacing and meta-explanation

Primary question: **“How should Alfred show up, and what keeps trust intact?”**

### Biographical / narrative lane
Biographical facts and life history belong in **curated memory** (and USER.md when truly always-on). They are not the same artifact type as operational/relational learning.

Primary question: **“What durable explicit truths about the user should be recallable later?”**

---

## 2) The shared substrate (the part we unify)

We unify the *evidence and learning lifecycle*, not the domain ontology.

### 2.1 Evidence atoms
All learning must ultimately ground in evidence atoms with provenance.

Evidence sources include:
- transcript spans (message_id + exact quote)
- explicit user feedback / corrections
- support-control actions (/support flows)
- operational transitions (task completed, blocker narrowed, decision resolved)

Invariants:
- evidence must have real session/message refs (no fabricated placeholders)
- quotes must be exact substrings of source messages

### 2.2 Attempts → observations → cases
We want one shared lifecycle (as in PRD #183):
- `SupportAttempt`: what Alfred tried
- `OutcomeObservation`: what happened after
- `LearningCase`: the join of attempt + observations + operational transitions

Invariants:
- extractors emit observations; **they do not promote** values/patterns directly
- promotion/demotion remains controlled and inspectable

---

## 3) Separate symbolic worlds (the part we do *not* unify)

Each domain defines:
- its own **ontology** (pattern types, state objects)
- its own **validators**
- its own **promotion rules**
- its own **surfacing adjudicator**

This is intentional: operational and relational are different symbolic languages.

### Example: same underlying phenomenon, two projections
User says: “I shut down when you push me.”

- Relational projection (primary): pressure boundary / rupture risk / stance constraint
- Operational projection (secondary): planning tactic constraint; a “pressure causes stall” blocker pattern

Both can be true without forcing one schema.

---

## 4) Cross-domain identity without a single ontology

To avoid duplicated “same idea” artifacts, we introduce a thin cross-domain linking object.

### 4.1 Pattern handle (cross-domain identity)
A `PatternHandle` is not a domain model. It is a stable identity for “this underlying learned thing.”

Policy:
- **Every candidate pattern and every promoted/confirmed pattern has a handle** (even purely single-domain patterns).
- **Observations do not mint handles.** Observations remain substrate evidence; handles begin at the candidate-pattern artifact layer.
- Cross-domain patterns are represented as **one handle with multiple projections**.

Suggested fields:
- `handle_id`
- `canonical_label` (short human name)
- `evidence_ids[]` (**canonical shared grounding lives on the handle**)
- `projections[]`: list of `(domain, domain_pattern_id)`

A handle may have:
- one projection (purely operational *or* purely relational)
- multiple projections (cross-domain)

### 4.2 Ownership
Each handle has **one primary domain**.

Ownership means:
- who gets first-class modeling responsibility
- who has the right to **introduce** the pattern to the user

Secondary domains may:
- reference the handle
- apply it as a constraint
- elaborate when the user explicitly asks from that domain

### 4.3 Handle linking and non-destructive dedupe

A handle only exists once a **candidate pattern** exists. When the system is about to create a new candidate pattern, it must decide:

- **attach**: add a new domain projection onto an existing handle
- **create**: create a new handle with a new candidate projection

Policy:
- **Be conservative.** False merges are worse than duplicates.
- **Never destructively merge handles automatically.** If uncertain, create a new handle.
- Allow the system to record non-destructive hints such as `possible_duplicate_of=[handle_id...]` for later review.
- The user can prune or merge later through inspection/control surfaces.

---

## 5) Lane assignment (creating projections + choosing a primary)

We treat “operational vs relational” as two decisions:

1. **Projection decision:** which domain(s) get a projection?
2. **Primary decision:** if multiple projections exist, which domain is primary?

### 5.1 Projection decision rules
Create a projection in a domain when:
- the evidence supports a valid domain object *and*
- storing it in that domain will change future behavior in that domain

Otherwise:
- keep it as evidence/candidate until additional cases exist

### 5.2 Primary decision tie-breakers (proposed)
Primary should be chosen by *intervention locus and risk*, not metaphysics.

Ordered tie-breakers:
1. **Explicit user framing**
   - user is talking about boundary/tone/trust → relational
   - user is talking about progress/blockers/structure → operational
2. **Trust/rupture risk if wrong**
   - if wrong classification risks misattunement → relational
3. **Action locus**
   - lever is stance/how Alfred shows up → relational
   - lever is plan/structure/next step → operational
4. **Stability / existing ownership**
   - preserve existing primary unless new evidence forces change

User override should exist (explicit command or extracted meta-request).

---

## 6) Surfacing coordination (dedupe across domains)

Surfacing is a UX event. We need one coordinating contract.

### 6.1 Surfacing event log
Maintain a shared log of surfacing events:
- `handle_id`
- `surfaced_by_domain`
- `surface_kind` (pattern surfacing, stance explanation, boundary acknowledgment)
- `surface_level` (implicit/compact/rich)
- timestamp

### 6.2 Introduction rights
- Only the **primary domain** may do *fresh surfacing* (“here’s a pattern I’m noticing”).
- Secondary domains may reference (“as we discussed…”) but should not re-introduce.

### 6.3 Cooldowns
After a fresh surfacing event:
- apply a cooldown window during which no other domain may freshly surface the same handle

### 6.4 Turn budgets
Default budgets:
- 0–1 fresh surfacing items per turn
- allow 2 only when the user explicitly asks for reflection / meta-explanation

---

## 7) Inspection and user control

This architecture only works if users can inspect and correct it.

### 7.1 Handle-first inspection

Principle:
- Users operate on **PatternHandles first**.
- Domain projections stay separately inspectable, but the handle is the coordination unit.

Minimum inspection surfaces:

- `/context`
  - compact view of **effective runtime state**
  - includes active handles (and their projections) that are currently influencing behavior
  - shows `primary_domain` and the "why" (evidence count / last update event / scope)

- `/support patterns`
  - list PatternHandles with filters:
    - status: `active`, `candidate`, `confirmed`, `rejected`, `retired`, `archived`
    - domain: `operational`, `relational`, `any`
    - scope: `global`, `context:<x>`, `arc:<id>`

- `/support pattern <handle_id>`
  - shared fields: label, primary domain, scope, canonical evidence refs, surfacing state
  - projections present: operational and/or relational summaries
  - duplicate links: `duplicate_of`, `possible_duplicate_of[]`

- `/support pattern <handle_id> operational|relational`
  - drills into the chosen domain projection’s symbolic world and status

### 7.2 Correction actions (projection-scoped vs handle-scoped)

**Projection-scoped actions** (because operational and relational have different semantics):
- confirm/reject/retire a specific projection
  - e.g. `/support pattern <id> confirm operational`

**Handle-scoped actions** (because they govern cross-domain coordination and UX):
- set ownership:
  - `/support pattern <id> set-primary operational|relational`
- control surfacing:
  - `/support pattern <id> suppress [--until <date>]`
  - `/support pattern <id> allow-surfacing`
- mark duplicates (see below)

### 7.3 Duplicate handling (single-canonical, non-destructive)

We treat duplicate handling as **archival + reinforcement**, not destructive merging.

#### 7.3.1 `duplicate-of` operation

Command:
- `/support pattern <handle_id_A> duplicate-of <handle_id_B>`

Semantics:
- `A` becomes **archived as a duplicate**:
  - never loaded into effective runtime state
  - never surfaced
  - hidden from default lists (but visible via `archived` filters)
  - always inspectable (no deletion)
- `B` becomes the **canonical handle**.
- **Projection inheritance:** `B` inherits any missing projections from `A` (union of symbolic representations).
- **Reinforcement:** `B`’s evidence set / case counts / contradiction counts incorporate `A`’s evidence via linking (no rewriting required).

Policy:
- conservative by default; the system should not perform this automatically.
- user-driven and reversible.

#### 7.3.2 Single-canonical constraint

Rules:
- each handle may have at most one `duplicate_of_handle_id`
- prevent cycles
- if chains exist (A → B → C), the system should compress them so A points directly to C

Undo:
- `/support pattern <handle_id_A> unduplicate`
  - restores A to normal visibility/load rules
  - **does not subtract** any previously contributed reinforcement/evidence from the canonical handle

---

## 8) How this maps to the existing PRD stack

This doc is intended to align and de-conflict these PRDs (not replace them):

Shared substrate:
- PRD #183 (attempt → observation → case)

Operational symbolic world + surfacing:
- PRD #190 (pattern surfacing adjudication)

Relational symbolic world + extraction + surfacing:
- PRD #196 (relational preference/boundary extraction)
- PRD #197 (relational meta-explanation surfacing)

What’s missing (candidate future PRD):
- a cross-domain **handle + ownership + surfacing coordination** contract

---

## 9) Open questions (to decide explicitly)

1. Secondary projection policy:
   - when do we add a second (or third) domain projection to an existing handle?
   - do we do it whenever evidence supports it, or only when explicitly adjudicated as cross-domain?
   - do we allow automatic secondary projections within a single case when evidence overlap is high (same case_id/evidence_ids)?

2. Primary decision mechanism:
   - deterministic rules only, or bounded semantic adjudication (with strict validators + fallback)?

3. User override UX:
   - commands only, natural language extraction, or both?

4. Relationship state richness:
   - does the relational symbolic world need explicit long-lived objects like `RelationshipState` / rupture-repair records, or do we keep it as values + patterns only?
