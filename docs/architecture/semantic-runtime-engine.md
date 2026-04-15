# Semantic Runtime Engine

## Status
- Proposed target architecture

## Why this doc exists

Alfred's semantic-runtime planning drifted into two kinds of confusion:

1. shared runtime mechanics were being described as if they were support-domain product logic
2. current support-specific learning artifacts were being treated like the architecture itself

This doc resets the layering.

The semantic runtime engine is a **generalized semantic substrate**.
It is not a support engine, not a relational engine, and not a thin wrapper around today's support-learning schema.

Support, relational, and future domains should plug into this substrate as **projected ontologies**.

## Related docs
- `docs/ARCHITECTURE.md`
- `docs/relational-support-model.md`
- `prds/185-shared-semantic-adjudication-contract-and-symbolic-runtime-inputs.md`
- `prds/184-semantic-adjudication-runtime-for-support-routing-and-learning.md`
- `prds/192-relational-runtime-semantics-and-stance-adjudication.md`
- `prds/183-support-learning-v2-case-based-adaptation-and-full-inspection.md`

## Problem

The repo already has meaningful semantic work in flight, but the planning surface still collapses too many layers together.

Current failure modes:
- support-domain artifacts are mistaken for cross-domain architecture
- support and relational work are framed as sibling engines instead of ontology projections
- shared runtime mechanics are repeatedly re-explained in parent PRDs
- current implementation nouns leak upward and start acting like permanent architecture
- future domains look harder to add because the design appears hard-wired to today's product seams

If we keep that shape, Alfred will grow a support-shaped semantic core and then struggle to generalize it later.

## Goals

- define one ontology-agnostic semantic runtime substrate
- keep support and relational work as projected ontologies, not separate engines
- preserve the three shared runtime abstractions:
  1. candidate adjudication
  2. grounded observation extraction
  3. deterministic activation and surfacing policy
- make the projection contract explicit enough that future domains can plug in cleanly
- keep retrieval, persistence, activation, and inspection boundaries deterministic and inspectable
- prevent current implementation artifacts from becoming accidental architecture

## Non-goals

- choosing a final durable schema for generalized evidence/state records in this doc
- replacing retrieval, search, or embeddings with freeform LLM reasoning
- forcing all domains into one flattened ontology
- letting the model mutate durable state directly
- treating today's support-domain implementation as the target cross-domain design

## Current constraints

- the repo already ships support-domain learning and inspection behavior through PRD #183
- the current implementation still uses support-shaped artifacts and ledgers
- support and relational domains already have meaningful product semantics that cannot be flattened into one mushy registry
- embeddings still matter for retrieval, shortlist generation, similarity search, clustering, and duplicate suppression
- explicit user control lanes such as `/support` must outrank inference
- the runtime must remain inspectable through `/context`, `/support`, and logs or traces

Important constraint:
- the current support-specific implementation is real and must be respected during migration
- but it is **not** the semantic-runtime architecture

## Options considered

### Option A: support-first substrate generalized later
Treat the current support-domain artifact model as the shared foundation and extend relational work around it.

**Rejected because:**
- it bakes one domain's nouns into the architecture
- it makes future domains inherit support-shaped assumptions
- it confuses current implementation with target design

### Option B: separate semantic engines per domain
Let support and relational work each define their own model-facing contract, validation rules, and persistence assumptions.

**Rejected because:**
- it duplicates runtime mechanics
- it guarantees drift in validation, observability, and fallback behavior
- it makes cross-domain composition harder over time

### Option C: generalized substrate with projected ontologies
Define one shared semantic substrate and let domains project their own candidate spaces, observation vocabularies, state semantics, and surfacing rules onto it.

**Accepted because:**
- it keeps the reusable mechanics centralized
- it preserves domain-specific meaning without hard-wiring domain nouns into the engine
- it leaves the architecture open-ended for future projections

## Chosen design

The semantic runtime engine has five layers.

### 1. Runtime fact assembly
Deterministic code assembles the facts available to the turn.

Examples:
- current user message and recent exchange
- session state and response-mode context
- retrieved evidence and recent history
- active operational context
- effective domain state already loaded for the turn
- explicit user controls or confirmed truths

This is input preparation, not model judgment.

### 2. Ontology projection
A projection defines how one domain plugs into the substrate.

A projection owns:
- its ontology and vocabulary
- candidate kinds and allowed registries
- observation kinds and target rules
- how projected state should be compiled or interpreted
- what activation/surfacing semantics mean in that domain
- which inspection views matter for that domain

Examples of projections:
- support
- relational
- future projections Alfred may add later

The architecture is intentionally open-ended.

### 3. Candidate adjudication
A shared primitive for bounded choice, ranking, or abstention over a provided candidate set or closed enum.

Use this when the runtime needs to answer questions like:
- which candidate best fits?
- should any candidate be selected?
- which bounded delta or mode applies?

This primitive does **not** own persistence, activation, or promotion.

### 4. Grounded observation extraction
A shared primitive for emitting zero or more typed observations grounded in source text or other bounded evidence.

Use this when the runtime needs to answer questions like:
- what signal was expressed?
- what target did it refer to?
- what quote grounds it?

This primitive does **not** own activation, promotion, or durable truth.

### 4.5 Deterministic outcomes vs semantic outcome signals
Not every "outcome" should come from the model.
The runtime should keep two lanes:

- **deterministic outcomes**: structured facts already visible in system state
  - examples: task completed, blocker resolved, open loop reopened, explicit control used, persisted state transition observed
- **semantic outcome signals**: language-level signals that only exist in user or assistant language
  - examples: "that helped," "that's not what I meant," "this feels pushy," "I feel clearer now," rupture or repair language, natural-language progress or friction signals

The model may extract **semantic outcome signals** as grounded observations.
Deterministic code should record **deterministic outcomes** directly from structured seams.
Then policy may combine both lanes when deciding activation, persistence, surfacing, or later learning updates.

Important rule:
- the model may propose grounded outcome-like observations
- the model may **not** directly declare final durable outcomes or mutate state

### 5. Deterministic activation and surfacing policy
Code-owned policy decides what actually affects runtime behavior and what becomes durable.

This layer owns:
- validation
- fallback behavior
- precedence and conflict handling
- activation/deactivation
- persistence and status transitions
- inspection payloads
- surfacing and explanation rules

This is the trust boundary.

## First-class durable runtime artifacts

The target architecture keeps both **Pattern** and **ScopedValue** as first-class durable runtime inputs.
They have different jobs.

### Pattern
A `Pattern` is a recurring claim about what tends to happen within a projection and scope.

Examples:
- directness helps when the user is stuck on a work blocker
- abstract framing increases friction in planning contexts
- therapist-like tone raises rupture risk

Patterns should be:
- inspectable
- evidence-backed
- scope-aware
- statused, for example `candidate`, `confirmed`, `rejected`, or `retired`

Confirmed `Pattern`s should affect runtime directly.
They may also justify or reinforce `ScopedValue` changes.

### ScopedValue
A `ScopedValue` is a durable actionable value attached to a scope.
It is the architecture-level term for what current support-specific code often calls a profile value.

Representative scopes include:
- global
- context
- arc
- future projection-specific scopes when a projection defines them explicitly

Representative examples:
- `candor=high` in a work-planning context
- `option_bandwidth=low` in one overloaded arc
- `authority=low` globally

ScopedValues should be:
- inspectable
- scope-aware
- evidence-backed
- statused by deterministic policy

### Effective values
`effective values` are the compiled turn-time result after precedence is applied across:
- authored defaults
- active or confirmed `ScopedValue`s
- applicable `Pattern`s
- explicit user controls and overrides

Current repo note:
- `SupportProfileValue` is a valid current implementation type
- architecturally, the target generalized noun is `ScopedValue`

## Projection contract

Every ontology projection should be able to plug into the substrate through a bounded contract.

A projection should define at least:
- `projection_id`
- `request_kinds` it participates in
- candidate kinds or closed enums it may ask the model to judge
- observation kinds it may ask the model to extract
- allowed pattern kinds
- allowed `ScopedValue` registries or dimensions
- allowed targets and registries
- projection-specific validation rules beyond shared substrate validation
- deterministic interpretation rules after validation
- surfacing/explanation affordances relevant to that projection

The shared substrate should not need to know support-specific or relational-specific nouns in order to run.

## Boundary and contract details

### Responsibility split

| Layer | Owns |
|---|---|
| ontology projection | domain meaning, registries, allowed kinds, pattern kinds, ScopedValue dimensions, interpretation of projected state |
| LLM candidate adjudication | bounded selection, ranking, abstain, ambiguity over provided candidates |
| LLM observation extraction | bounded typed observations with grounding, including semantic outcome signals from language |
| LLM deferred synthesis | bounded proposals for Pattern candidates, ScopedValue candidates, contradiction notes, and reflection proposals |
| embeddings | retrieval, shortlist generation, similarity search, clustering, duplicate suppression |
| deterministic runtime code | fact assembly, validation, fallback, precedence, activation, persistence, status transitions, Pattern confirmation, ScopedValue promotion, surfacing, inspection, deterministic outcome recording from structured seams |

### Key invariants

- the shared engine must stay ontology-agnostic
- candidate adjudication never invents ids outside the provided candidate set
- observation extraction never promotes or activates state directly
- semantic outcome signals extracted from language remain observations until deterministic policy interprets them
- deterministic code is the only layer allowed to mutate durable state
- explicit user control outranks inference
- projections may differ in ontology, but must reuse the same substrate mechanics
- current projection-specific schemas must not be mistaken for the permanent shared substrate

## Deterministic envelope assembly, semantic perception, deferred synthesis, and policy application

The runtime should not rely on brittle production rules to understand the turn semantically.
It should use deterministic code for **coarse bounding**, then one bounded model pass for **semantic perception**, then bounded deferred synthesis when warranted, then deterministic code again for **policy and consequences**.

### Stage 1: deterministic envelope assembly

Deterministic code owns:
- projection activation for the turn
- inline vs deferred decision
- call-budget enforcement
- candidate or evidence assembly
- safe fallback selection before the model runs
- explicit trust boundaries and validator selection

Envelope inputs:
- explicit user controls and confirmed truths
- session and response-mode context
- active projections and registered request kinds
- candidate availability and evidence availability
- current effective projected state
- latency and cost budget for the turn
- trust and risk class of the decision

Envelope outputs:
- no call
- one bounded semantic perception request
- one deferred synthesis or reflection request scheduled after reply or for inspection or review

Deterministic gating rules:
1. no call if explicit user control or deterministic state already resolves the issue
2. no call if the projection is inactive or the request kind is not registered
3. no call if the candidate set or evidence packet cannot be bounded first
4. no call if the decision only affects durable state and can wait for deferred processing
5. inline perception is reserved for decisions that materially affect the current reply
6. fallback must be chosen before the call runs, not after the model improvises

Hot-path budget guidance:
- most turns should use **zero** extra semantic helper calls
- ambiguous turns may use **one** inline semantic perception pass
- a second inline helper call should be exceptional and normally reserved for explicit repair, explanation, or inspection-triggered flows

### Stage 2: bounded semantic perception pass

The model acts as the runtime's **eyes and first pass**.
It should not improvise policy.
It should inspect the bounded envelope and return only:
- candidate selections from supplied sets or enums
- grounded observations from allowed observation kinds
- abstentions where evidence is weak or ambiguous
- confidence and grounding when the contract requires them

The runtime should not freehand a new prompt for every seam.
It should derive the perception task from:
- the projection contract
- the request kind
- the allowed candidate sets and observation kinds
- the bounded evidence packet
- the validator and fallback policy for that request

In practice, the perception pass should be able to emit only two semantic result families:
- **candidate adjudication**: choose `0..n` valid candidates from the supplied set or abstain
- **grounded observation extraction**: emit zero or more valid grounded observations from allowed kinds or abstain

If a desired semantic task does not fit one of those shapes, it probably should not be its own semantic-runtime call.

### Perception result shape

To avoid a mushy mixed payload, one bounded perception pass should return one structured result envelope with three top-level lanes:
- `candidate_decisions[]`
- `observations[]`
- `abstentions[]`

`semantic outcome signals` should **not** be a separate freeform lane.
They should appear as typed items inside `observations[]`.
That keeps the result shape small while still allowing outcome-like language signals.

Recommended shape:
- `candidate_decisions[]`
  - `request_kind`
  - `projection_id`
  - `decision_kind`
  - `selected_ids` or closed-enum `decision`
  - `ranked_alternatives` when allowed
  - `confidence`
  - optional `grounding_quotes`
- `observations[]`
  - `request_kind`
  - `projection_id`
  - `kind`
  - `target` when applicable
  - `value` or `direction` when applicable
  - `quote` or `quotes`
  - `confidence`
  - optional `scope`
  - optional `source_refs`
- `abstentions[]`
  - `request_kind`
  - `projection_id`
  - `abstain_reason`
  - optional `blocked_on` field such as `missing_candidates`, `weak_evidence`, `ambiguous_text`, or `out_of_scope`

Interpretation rules:
- every item must name the `request_kind` and `projection_id` it belongs to
- observation kinds remain closed per projection
- semantic outcome signals are observation kinds, not a third primitive
- abstention is explicit and first-class, not implied by empty arrays alone
- deterministic policy may ignore, defer, or reject any item after validation

### Stage 3: deterministic policy application

After perception, deterministic code decides consequences.
This layer owns:
- validation and rejection
- precedence over explicit controls
- activation now vs defer
- persistence and status transitions
- surfacing and explanation policy
- fallback when perception output is malformed, out of bounds, or too weak

The model may perceive.
Deterministic policy decides what Alfred actually does.

## Decision table: what the perception pass may propose vs what policy decides

| Decision area | Model perception may propose | Deterministic policy decides | Default timing | Safe fallback | Separate call? |
|---|---|---|---|---|---|
| projection activation for the turn | nothing; projections are bounded before perception | which projections are active at all | inline, pre-call | no semantic call | never |
| session-start routing ambiguity | one bounded route choice or abstain | whether to trust it and whether routing affects this reply | inline only when metadata and explicit controls do not resolve the start path | default orientation path or `none` | sometimes |
| support need selection | one bounded support-mode choice or abstain | whether it changes the reply and whether support policy activates it | inline when the current reply depends on it | `unknown` or no special mode | sometimes; batch with subject or routing when possible |
| subject resolution | one or more bounded subject choices or abstain | whether the selected subjects are valid and relevant enough to use now | inline only when multiple viable subjects would materially change the reply | empty selection | sometimes; batch when possible |
| relational state selection | one bounded live relational-state choice or abstain | whether the state overrides baseline compiled state for this turn | inline only when it would change the current reply | no relational override | sometimes; batch with stance when possible |
| stance delta selection | one bounded stance delta or abstain | whether to apply the delta to the compiled stance for this turn | inline only when a bounded tone adjustment is needed | baseline compiled stance | sometimes; usually the same call family as relational state |
| grounded support, relational, or semantic outcome observations | zero or more grounded observations with quotes, targets, and abstentions, including helpfulness, correction, rupture, repair, progress, or friction signals expressed in language | whether observations validate, persist, activate now, or remain deferred evidence | deferred by default; inline only when an immediate boundary, correction, rupture, or strong outcome signal changes the reply | zero observations | usually no; prefer deferred or batched extraction |
| pattern surfacing or reflection choice | one bounded surfacing recommendation or abstain | whether to surface now, later, or never under policy rules | deferred or inspection-triggered by default | surface nothing | rarely |
| meta-explanation mode | one bounded explanation-mode recommendation or abstain | whether the user actually gets an explanation and in what form | inline only when the user asks why, what changed, or repair needs explicit explanation | `implicit` | rarely; often folded into surfacing |
| deferred synthesis for Pattern and ScopedValue candidates | bounded `pattern_candidates[]`, `scoped_value_candidates[]`, `reflection_candidates[]`, or abstentions over validated bundles | whether to store candidates, confirm patterns, promote ScopedValues, defer review, or ignore proposals | deferred only | no candidates | yes, but deferred and bounded |
| durable state update, promotion, or persistence | nothing beyond bounded proposals and observations | all durable mutation, Pattern confirmation, ScopedValue promotion, and persistence | after validation | no update | never |
| cross-projection handle linking or dedupe | optional duplicate hint only if explicitly allowed | whether to link, keep separate, or defer review | deferred | keep separate handles or skip linking | never inline |

## Data and control flow

1. assemble runtime facts deterministically
2. select the relevant ontology projection or projections for the turn
3. retrieve candidate sets or evidence with structured queries and embeddings when needed
4. assemble one bounded semantic perception envelope for the active projections and request kinds
5. run one semantic perception pass that returns bounded candidate choices, grounded observations, or abstentions
6. validate outputs through shared and projection-specific rules
7. apply deterministic activation, fallback, persistence, and surfacing policy
8. compile the effective behavior contract for the turn
9. respond
10. persist generalized runtime traces, observations, deterministic outcomes, and state updates through deterministic code
11. when warranted, schedule one deferred synthesis or reflection pass over bounded validated bundles
12. expose inspection views appropriate to the active projection(s)

## Stage-by-stage path from observations to Patterns and ScopedValues

### Stage 0: per-turn semantic perception
The hot-path perception envelope produces bounded results only:
- `candidate_decisions[]`
- `observations[]`
- `abstentions[]`

This is where the model acts as Alfred's eyes and first pass.
Semantic outcome signals belong inside `observations[]`.

### Stage 1: deterministic evidence bundle assembly
After the turn, deterministic code assembles one bounded evidence bundle from things such as:
- the turn's validated observations
- semantic outcome signals
- deterministic outcomes from structured seams
- the effective runtime values and interventions that were actually used
- scope, projection, and context references

This bundle is the substrate's inspectable unit for later synthesis.

### Stage 2: deferred synthesis and introspection
The system may run a separate **deferred synthesis envelope** over one or more validated evidence bundles.
This is the right place to batch several bounded semantic questions into one call when they share the same evidence packet and trust boundary.

A deferred synthesis pass may propose typed proposal objects in separate lanes:
- `pattern_candidates[]`
- `scoped_value_candidates[]`
- `reflection_candidates[]`
- `abstentions[]`

This is where the model may introspect, compare bundles, notice repetition, suggest contradictions, and draft reflection proposals.
It is proposal-only.
The architecture should prefer typed proposal objects over one generic mixed proposal blob.

Here, `typed` means **schema-typed**, not a required Python class hierarchy.
The architecture-level proposal kinds are:
- `PatternCandidate`
- `ScopedValueCandidate`
- `ReflectionCandidate`
- `Abstention`

What matters is:
- each kind has a closed purpose
- each kind has a closed field set
- each kind has projection-aware validators
- each kind has a deterministic lifecycle handler

The implementation may later use dataclasses, Pydantic models, `TypedDict`s, or validated dictionaries.
The architecture only requires that these proposal kinds are not freeform blobs.

### Stage 3: candidate Pattern promotion
Deterministic policy may promote a synthesis proposal into a durable `Pattern` with `candidate` status when:
- the pattern kind is valid
- the scope is valid
- evidence refs are real and inspectable
- the claim is not obviously duplicate noise or already contradicted beyond tolerance

Promotion means: this recurring claim is worth tracking.
It does **not** mean the pattern is already trusted as a runtime authority.

### Stage 4: Pattern confirmation, rejection, or retirement
Deterministic policy decides whether a candidate `Pattern` becomes `confirmed`, `rejected`, or later `retired`.

Confirmation signals may include:
- explicit user confirmation
- repeated support across multiple bounded bundles
- scope consistency
- support from both semantic outcome signals and deterministic outcomes when relevant
- low contradiction rate
- successful manual or review-surface confirmation

Patterns remain first-class runtime inputs after confirmation.
They are not merely disposable pre-value artifacts.
Established patterns should have a real effect on runtime behavior through deterministic compilation and precedence rules.

### Stage 5: ScopedValue proposal and promotion
`ScopedValue`s may be proposed from:
- repeated direct observations
- explicit user corrections or controls
- deferred synthesis output
- confirmed `Pattern`s that imply an actionable setting or constraint

Deterministic policy then decides whether a `ScopedValue` becomes candidate, shadow, active, confirmed, rejected, retired, or any future status model the projection defines.
The key point is that `ScopedValue` is a durable actionable value attached to a scope.

### Stage 6: effective runtime compilation
At reply time, Alfred compiles effective values from:
- authored defaults
- active or confirmed `ScopedValue`s
- applicable confirmed `Pattern`s
- explicit user overrides
- deterministic precedence rules

This compiled result is what actually shapes the next turn.

Patterns and ScopedValues are therefore both first-class runtime inputs, but they are not interchangeable:
- `Pattern` = recurring claim about what tends to happen
- `ScopedValue` = actionable parameter or constraint at a scope

## Current implementation note

The repo currently ships a support-domain implementation through PRD #183.
That implementation uses support-specific artifacts and support-specific inspection semantics.

Those artifacts are:
- valid current implementation
- important migration constraints
- **not** architecture primitives

Future substrate work may adapt, replace, or wrap those support-domain records with generalized substrate records.

## Migration and rollout

1. make this architecture doc the canonical source of truth for shared semantic-runtime design
2. keep PRD #185 focused on the shared substrate contract, not shared product ontology
3. treat PRDs #184 and #192 as projection-planning docs for support and relational domains
4. rewrite child PRDs so they reference this architecture doc instead of re-explaining the engine
5. reposition PRD #183 as shipped support-domain implementation, not generalized substrate design
6. when implementation work resumes, extract or replace support-specific substrate records with generalized equivalents behind deterministic adapters

## Validation strategy

Architecture alignment is good when:
- shared runtime mechanics are defined here first
- PRDs describe projection behavior and implementation slices rather than acting like architecture docs
- support and relational work reuse the same substrate abstractions
- no PRD treats support-domain artifacts as universal architecture
- future projections can be described without first rewriting the engine

## Risks and open questions

- The substrate could become too abstract if projection contracts are underspecified.
- Projection boundaries could drift if PRDs start re-inventing shared validation or fallback rules.
- Migration from today's support-specific records to generalized substrate records will need explicit adapters or schema replacement work.
- Some turns may require multiple projections at once; the selection and composition rules need later implementation detail without breaking this architecture.
- The final generalized durable record model is intentionally deferred here; that choice belongs in downstream implementation work, not this boundary doc.
