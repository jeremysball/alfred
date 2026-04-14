# Semantic Runtime Engine

## Status
- Proposed

## Why this doc exists

The current semantic-runtime plan is spread across many seam-specific PRDs.
That makes the work look larger and more fragmented than it really is.

This doc compresses that work into one reusable runtime architecture with three abstractions:

1. **candidate adjudication**
2. **grounded observation extraction**
3. **deterministic activation and surfacing policy**

The goal is to give Alfred one semantic engine with several product ontologies, not several unrelated semantic mini-systems.

## Related docs
- `docs/ARCHITECTURE.md`
- `docs/relational-support-model.md`
- `prds/184-semantic-adjudication-runtime-for-support-routing-and-learning.md`
- `prds/185-shared-semantic-adjudication-contract-and-symbolic-runtime-inputs.md`
- `prds/189-natural-language-observation-extraction-for-support-learning.md`
- `prds/192-relational-runtime-semantics-and-stance-adjudication.md`
- `prds/196-natural-language-relational-preference-and-boundary-extraction.md`
- `prds/183-support-learning-v2-case-based-adaptation-and-full-inspection.md`

## Problem

Alfred already has rich symbolic runtime state:
- operational arcs and domains
- derived situations
- support and relational values
- attempt / observation / case learning records
- patterns, evidence refs, and searchable history

But the current planning surface still describes too many independent semantic seams:
- session-start routing
- need adjudication
- subject adjudication
- observation extraction
- pattern surfacing
- relational-state adjudication
- stance adjudication
- relational extraction
- meta-explanation

Those are real product surfaces, but architecturally they mostly reduce to a smaller set of reusable operations.

Without that compression, the repo risks:
- duplicated prompt contracts
- duplicated validation rules
- inconsistent observability
- parallel support vs relational runtimes
- muddy ownership between model judgment and deterministic policy

## Goals

- define one reusable semantic runtime architecture
- keep support and relational semantics as domain ontologies, not separate engines
- make the model-facing primitives small, bounded, and reusable
- keep persistence, activation, promotion, scope resolution, and surfacing policy deterministic
- give downstream PRDs one architecture doc to reference instead of re-explaining the system

## Non-goals

- replacing session search, retrieval, or embeddings with LLM-only reasoning
- letting the LLM write directly to persistence or status transitions
- collapsing curated memory, support learning, and explicit user truth into one memory lane
- forcing every runtime question through one giant generic prompt

## Current constraints

- Alfred already has a shared learning foundation in PRD #183: `SupportAttempt` -> `OutcomeObservation` -> `LearningCase`
- support and relational dimensions already exist as product concepts and runtime inputs
- embeddings still matter for retrieval, shortlist generation, and similar-case recall
- explicit control lanes such as `/support` must remain stronger than inference
- the runtime must stay inspectable through `/context`, `/support`, and logs

## Options considered

### Option A: seam-specific semantic systems
Build separate architecture for routing, need detection, subject resolution, observation extraction, relational stance, and meta-explanation.

**Rejected because:**
- duplicates infrastructure
- encourages drift across seams
- makes support and relational work look more different than they are

### Option B: one semantic runtime engine with reusable primitives
Use one shared engine with small model-facing primitives and deterministic policy around them.

**Accepted because:**
- compresses the architecture cleanly
- keeps product semantics separate from runtime mechanics
- gives PRDs a common contract and vocabulary

## Chosen design

The semantic runtime engine has four layers.

### 1. Runtime facts
Deterministic, code-owned state assembled before model judgment.

Examples:
- current turn and recent exchange
- active arc, domain, and situation state
- candidate ids and summaries
- effective support and relational values
- recent attempts, observations, cases, and confirmed patterns
- explicit user controls and durable truths

This layer is not one of the three abstractions. It is the input foundation they operate on.

### 2. Candidate adjudication
A bounded primitive for choosing, ranking, or abstaining among candidates.

Use this when the runtime asks:
- which support need best fits this turn?
- which subject candidate does “this” refer to?
- should this be treated as resume, orient, or neither?
- which pattern is relevant enough to surface now?
- what bounded relational delta fits this moment?

Contract shape:
- request kind
- candidate set or closed enum
- relevant runtime facts and summaries
- constraints such as max selections and abstain policy

Result shape:
- selected or ranked candidates
- confidence
- abstain or ambiguity state
- grounding refs when applicable
- no persistence side effects by itself

### 3. Grounded observation extraction
A bounded primitive for emitting zero or more typed observations from language.

Use this when the runtime asks:
- did the user express a preference, boundary, or correction?
- did the user reject Alfred’s interpretation?
- did the user give stance feedback or signal rupture?

Contract shape:
- request kind / ontology
- user message and previous assistant reply when relevant
- relevant runtime facts when needed
- target registry and constraints

Result shape:
- zero or more typed observations
- quotes grounded in source text
- targets, directions, confidence, and scope where relevant
- no promotion or activation by itself

### 4. Deterministic activation and surfacing policy
A code-owned layer that decides what affects runtime behavior and what becomes durable.

This layer owns:
- validation
- scope precedence
- fallback behavior
- activation and deactivation
- promotion and status transitions
- inspection payloads
- surfacing rules and explanation thresholds

This is where Alfred decides:
- what becomes active for this turn
- what stays candidate-only
- what may influence future learning
- what should stay silent
- what deserves compact or explicit explanation

## Boundary and contract details

### Responsibility split

| Layer | Owns |
|---|---|
| LLM candidate adjudication | bounded selection, ranking, abstain, ambiguity over provided candidates |
| LLM observation extraction | bounded typed observations with quote grounding |
| embeddings | retrieval, similarity search, shortlist generation, clustering, duplicate suppression |
| deterministic runtime code | facts assembly, validation, fallback, activation, promotion, persistence, scope precedence, surfacing |

### Key invariants

- candidate adjudication never invents ids outside the provided candidate set
- observation extraction never promotes or activates state directly
- deterministic code is the only layer allowed to mutate durable state
- explicit user control outranks inference
- curated memory remains supplemental rather than becoming the system of record
- support and relational domains reuse the same runtime mechanics even when they use different ontologies

## Domain mapping

The engine is shared. The ontologies differ.

### Support-domain applications
Primarily PRDs #184 through #190:
- routing
- need adjudication
- subject adjudication
- support observation extraction
- pattern surfacing

### Relational-domain applications
Primarily PRDs #192 through #197:
- live relational-state adjudication
- stance adjudication
- relational observation extraction
- relational surfacing and meta-explanation

### Shared activation and learning boundary
PRD #183 remains the shared owner of:
- attempts
- observations
- cases
- ledger/status semantics
- inspection truth

## Data and control flow

1. assemble runtime facts deterministically
2. retrieve candidate sets or relevant history with embeddings and structured queries when needed
3. run either candidate adjudication or grounded observation extraction
4. validate the result deterministically
5. apply activation, fallback, promotion, and surfacing policy in code
6. compile the effective behavior contract for the turn
7. respond
8. persist attempts, observations, cases, and updates through the shared learning model

## Migration and rollout

1. align parent docs and PRDs to this shared architecture
2. make PRD #185 the shared contract doc for the two model-facing primitives
3. keep child PRDs as implementation slices, but describe them as applications of the shared primitives
4. preserve PRD #183 as the single shared activation/learning boundary

## Validation strategy

Architecture validation should confirm:
- support and relational PRDs reuse the same runtime mechanics
- no child PRD invents a parallel validation or persistence model
- docs distinguish model judgment from deterministic policy clearly
- observability can explain acceptance, rejection, abstain, and fallback paths

## Risks and open questions

- The shared primitive may become too generic if seam-specific constraints are not documented.
- Candidate payloads may grow too large if fact assembly is not budgeted carefully.
- Some seams may need asynchronous execution while others stay on the response hot path.
- The exact reusable type layer can still be dataclasses, Pydantic models, or typed dicts; this doc does not choose that implementation detail.
