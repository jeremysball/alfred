# PRD: Reflection Reviews and Support Controls

**GitHub Issue**: [#169](https://github.com/jeremysball/alfred/issues/169)  
**Priority**: Medium  
**Status**: Draft  
**Created**: 2026-03-30

---

## 1. Problem Statement

Once Alfred starts learning support and relational patterns, that learning needs a bounded user-facing meaning-making surface.

Without that surface:
- Alfred becomes more adaptive but less legible
- users cannot inspect or correct learned assumptions easily
- identity and direction themes either stay latent forever or get promoted too aggressively
- reflection risks becoming either absent or overwhelming

A deeper problem also sits underneath this:
- **learning** and **reflection** are related, but they are not the same thing
- Alfred needs an internal learning loop that can improve support quietly
- Alfred also needs a deliberate reflection surface that can surface patterns, invite confirmation, and let the user revise what Alfred thinks he knows

Three more design problems matter now:

1. **Patterns are not all the same kind of object**
   - recurring blockers, support preferences, identity themes, direction themes, and calibration gaps all belong to one family
   - but they do not share the same surfacing thresholds or confirmation rules

2. **Load and surfacing are easy to confuse**
   - Alfred should often load patterns silently because they change behavior
   - he should not narrate every loaded pattern to the user

3. **Session-start reflection is under-specified**
   - Alfred should be allowed to surface a theme or pattern at session start when it materially changes the next move
   - without rules, that either becomes too timid or too intrusive

The result today is that Alfred can imagine reflective behavior, but he does not yet have a clear system for when to surface patterns, how to classify them, how to keep them bounded, and how to keep identity-level learning consensual.

---

## 2. Goals

1. Add **bounded reflection surfaces** that turn support learning into useful user-facing insight.
2. Distinguish clearly between **internal learning**, **pattern storage**, and **user-facing reflection**.
3. Use one **Pattern family** with typed kinds and different surfacing/promotion rules.
4. Surface **typed candidate and confirmed patterns** with evidence and simple actions.
5. Give users visible controls over effective support state, relational shifts, and learned themes.
6. Keep identity and direction learning **candidate-first** until the user confirms it.
7. Allow Alfred to surface patterns at session start when they materially change the next move.
8. Keep most reflective machinery invisible unless trust, calibration, or correction requires explicitness.
9. Keep reflection tied to future action, correction, or explicit understanding rather than open-ended essay generation.
10. Treat documentation and managed prompt/template updates as part of feature completion so review behavior and correction surfaces are described consistently.

---

## 3. Non-Goals

- Building an unbounded autobiographical memory browser.
- Turning Alfred into a freeform therapy or journaling product.
- Letting the model silently redefine the user's identity.
- Replacing execution support with large review rituals.
- Allowing review surfaces to become generic essays or vague self-help summaries.
- Narrating internal arc or pattern bookkeeping by default on every session start.

---

## 4. Proposed Solution

### 4.1 Distinguish learning from reflection

The architecture should separate:

1. **Learning**
   - internal adaptation and state updates
   - episode synthesis
   - support-effectiveness updates
   - relational-preference updates
   - candidate pattern generation

2. **Pattern storage**
   - durable candidate or confirmed recurring objects with evidence, confidence, and correction state

3. **Reflection**
   - user-facing pattern surfacing
   - review cards
   - explanation of support changes
   - confirmation, rejection, reset, and promotion flows

This keeps Alfred adaptive without making every internal update a user interruption.

### 4.2 Use a single Pattern family with typed kinds

V1 should use one Pattern family with explicit kinds.

Recommended v1 pattern kinds:
- `recurring_blocker`
- `support_preference`
- `identity_theme`
- `direction_theme`
- `calibration_gap`

Examples:
- recurring blocker: "Ambiguity repeatedly delays admin tasks."
- support preference: "Single-step execute prompts work better than broader plans."
- identity theme: "You tend to disown desire when goals become publicly legible."
- direction theme: "Prestige and aliveness keep pulling in different directions."
- calibration gap: "Your stated priority and actual behavior keep diverging on this thread."

All of these share:
- a claim
- evidence refs
- confidence
- scope
- status
- correction state

But they do **not** share the same surfacing threshold.

### 4.3 Add three reflection surfaces

V1 should support three reflection surfaces.

#### A. Inline reflection
Reflection can happen during live conversation when a pattern or contradiction is highly relevant to the moment.

Examples:
- "I think the real problem isn't lack of options. It's that none of them feel like yours."
- "You sound more alive when the plan gets smaller and more self-directed."

Inline reflection should be allowed when:
- it materially improves the current conversation
- the current context is already reflective or decisional, or the insight is blocking progress
- confidence is high enough to justify surfacing it now

#### B. Internal synthesis
After or during a conversation, Alfred updates:
- episodes
- support-preference candidates
- blocker candidates
- identity-theme candidates
- direction-theme candidates
- calibration-gap candidates
- review queues

This is mostly for Alfred, not for the user.

#### C. Explicit review
Alfred should support:
1. **On-demand review**
2. **Weekly review**

These are where learning becomes bounded, typed, user-visible reflection.

### 4.4 Use learning situations for matching and episodes for reflection reports

Pattern generation should work from structured learning situations rather than from coarse session blobs alone.

That allows Alfred to learn separately from:
- an execution situation
- a decision situation
- an identity reflection situation
- a direction reflection situation
- a calibration situation

Important split:
- `LearningSituation` is the primary similarity and adaptation unit for matching evidence across turns and sessions
- `SupportEpisode` is the derived report or synthesis boundary that groups related situations for reflection, review cards, and human-readable summaries

The reflection system should aggregate from learning situations into candidate patterns and then synthesize episode-level review surfaces from related situations.

### 4.5 Separate load score from move-impact score from surface score

Pattern handling should distinguish three decisions.

1. **Load score**
   - should this pattern enter `WorkingContext` at all?

2. **Move-impact score**
   - does this pattern materially change the next move Alfred would otherwise make?

3. **Surface score**
   - does the user benefit from hearing this pattern right now?

These are different decisions.

A pattern should often be loaded silently.
A pattern should be surfaced more richly only when it changes the actual help shape in a way the user benefits from understanding.

### 4.6 Define pattern load rules

A pattern should be loaded when it is relevant to:
- the current opening message or turn
- the selected life domain
- the selected operational arc
- the inferred friction state
- the current need

Representative inputs to load score:
- semantic match to the current turn
- domain overlap
- arc overlap
- friction overlap
- recency
- evidence strength
- confirmation status
- stale/corrected penalties

### 4.7 Define move-impact rules

A pattern materially affects the next move when **removing it would change the response contract in a meaningful way**.

The practical test is counterfactual:
- build the likely next move without the pattern
- build the likely next move with the pattern
- compare whether Alfred would actually help differently

A pattern has **high move impact** if it changes any of these major things:
- the chosen intervention family
- the chosen target of help
- option bandwidth
- recommendation forcefulness
- evidence mode
- whether Alfred should orient first versus activate immediately
- whether Alfred should reflect, decide, or calibrate differently

A pattern has **moderate move impact** if it changes two or more smaller things such as:
- pacing
- candor level
- companionship level
- analytical depth
- reflection depth

This is the core rule for richer surfacing.

### 4.8 Define surface levels

Patterns should have three practical surfacing levels.

#### Level 0 — silent
The pattern is loaded and used internally, but not mentioned.

Use when:
- it only affects tone or small wording
- confidence is moderate but not strong
- the user does not need the explanation

#### Level 1 — compact mention
The pattern gets a short clause.

Use when:
- it changes the move a bit
- Alfred wants to keep the move legible

Example:
- "I'm keeping this narrow because ambiguity is usually what stalls you here."

#### Level 2 — slightly richer
The pattern gets a fuller explanation because it substantially changes the next move.

Use when:
- it causes at least one major contract delta, or two meaningful minor ones
- the user benefits from understanding why Alfred is helping this way

Example:
- "I'm resuming the Web UI cleanup thread. The recurring blocker here is architecture ambiguity: once the structure question stays open, momentum drops and the work sprawls. So I'm not going to give you a menu — I'm going to pin the next boundary first."

### 4.9 Session-start pattern surfacing is allowed

Alfred should be allowed to surface a pattern or theme at session start when it materially affects the next move.

This is important because some of the most useful continuity is not just:
- what thread is active

but also:
- what kind of blockage is recurring
- what kind of help works
- what deeper tension is active
- where the user's story may be diverging from the record

However, session-start surfacing should stay bounded.

Recommended rules:
- surface at most 1-2 patterns/themes at session start
- prefer compact or slightly richer surfacing, not essays
- favor operationally useful patterns in operational starts
- favor identity/direction themes in reflective starts
- favor calibration gaps when calibration is explicitly invited or highly relevant

### 4.10 Priority by session-start type

Pattern priority should vary by interaction shape.

#### Scoped operational start
Priority order:
1. `support_preference`
2. `recurring_blocker`
3. `calibration_gap` when contradiction is operationally relevant
4. `identity_theme`
5. `direction_theme`

#### Broad orient start
Priority order:
1. `recurring_blocker`
2. `support_preference`
3. `direction_theme`
4. `identity_theme`
5. `calibration_gap`

#### Reflective start
Priority order:
1. `identity_theme` / `direction_theme`
2. `calibration_gap`
3. `recurring_blocker`
4. `support_preference`

#### Calibration start
Priority order:
1. `calibration_gap`
2. `recurring_blocker`
3. `identity_theme` / `direction_theme`
4. `support_preference`

This keeps operational starts practical and reflective starts meaning-rich.

### 4.11 Add typed review card models

Review cards should not just be generic "patterns."

Recommended v1 card types:
- **support-fit card**
- **blocker card**
- **identity-theme card**
- **direction-theme card**
- **calibration-gap card**

Minimum card fields:
- `card_id`
- `pattern_kind`
- `scope`
- `statement`
- `confidence`
- `evidence_refs`
- `proposed_action`
- `status` (`candidate`, `confirmed`, `rejected`)

Example:

```json
{
  "card_id": "card_14",
  "pattern_kind": "direction_theme",
  "scope": {"type": "global", "id": "user"},
  "statement": "A tension between external legibility and felt aliveness keeps recurring in your work decisions.",
  "confidence": 0.87,
  "evidence_refs": ["ep_204", "ep_213", "ep_227"],
  "proposed_action": "Confirm whether this is a real recurring tension and, if so, keep it visible in future direction decisions.",
  "status": "candidate"
}
```

### 4.12 Add support-memory inspection controls

Users should be able to inspect, at minimum:
- active domains and operational arcs
- effective relational values
- effective support values
- recent intervention history
- recent support-profile update events
- candidate and confirmed patterns

Users should also be able to:
- confirm a pattern
- reject a pattern
- correct or scope-limit a learned value
- reset a value to default
- ask why a value changed
- ask for evidence
- promote a confirmed durable theme into `USER.md` when appropriate

### 4.13 Use a candidate-first promotion ladder

The reflection system should formalize a promotion ladder:

1. raw evidence
2. typed episode evidence
3. candidate pattern
4. confirmed structured support memory
5. explicit durable user truth in `USER.md`

Key rule:
- **learning may silently improve scoped support behavior**
- **learning may not silently redefine the user's identity**

That means:
- support preferences can adapt quietly in narrow scopes
- broad support or relational defaults should be surfaced
- identity themes, direction themes, and durable value signals should remain candidate-first until the user confirms them
- only user-endorsed durable truths should move into `USER.md`

### 4.14 Surface broad changes explicitly

Arc- and context-level adaptation can happen in the background if it stays logged.

Broad changes should be surfaced:
- global support-profile changes
- global relational shifts
- durable value signals
- identity themes Alfred wants to keep broadly active
- direction-level patterns that would materially shape future reflection or recommendations

### 4.15 Keep reflection bounded and action-linked

Reflection should always end in one of these:
- change how Alfred helps
- change operational state
- change durable understanding
- open a deliberate reflection thread
- correct Alfred's current model

Reviews should stay small.

Recommended v1 constraints:
- at most 1-3 cards per review
- each card must include evidence
- each card must end in a practical action, confirmation question, correction option, or next reflection step

### 4.16 Default invisibility rule

Most reflective machinery should remain invisible unless legibility matters.

Default invisible:
- raw load scores
- move-impact scoring
- candidate-ranking internals
- background synthesis
- discarded or low-confidence patterns

Default visible when useful:
- a compact or slightly richer pattern explanation when it changes the next move
- evidence for stronger calibration claims
- review cards
- correction controls
- explanations of broad support-profile changes

### 4.17 Respect general-purpose use

Reflection should work for:
- execution support
- project review
- decision support
- personal workflow patterns
- identity reflection
- life-direction reflection
- recurring collaboration patterns
- executive-function recovery patterns

It should not depend on any diagnosis-specific mode.

---

## 5. User Experience Requirements

A user should be able to ask Alfred things like:
- "Review the last week."
- "What patterns have you noticed in how I get stuck?"
- "Show me what you've learned about how to help me."
- "Why are you giving me shorter next steps now?"
- "Why are you being more direct with me lately?"
- "What are you noticing about me here?"
- "That's not true about me. Undo it."
- "Yes, that's real. Remember it."

The review surface should feel:
- compact
- evidence-backed
- editable
- relationally alive
- actionable
- easy to skip when the user wants straightforward support instead

Session-start reflective surfacing should feel:
- legible
- bounded
- useful
- connected to the next move
- never like a surprise essay dump

---

## 6. Success Criteria

- [ ] Alfred supports inline, weekly, and on-demand reflection surfaces with bounded behavior.
- [ ] Patterns use one shared family with typed kinds and distinct surfacing/promotion rules.
- [ ] Alfred can load patterns silently without surfacing them automatically.
- [ ] Session-start pattern surfacing is allowed when it materially changes the next move.
- [ ] Reviews show 1-3 typed, evidence-backed cards rather than open-ended essays.
- [ ] Users can inspect effective support and relational values plus recent change history.
- [ ] Users can confirm, reject, reset, or scope-limit learned assumptions.
- [ ] Identity and direction themes remain candidate-first until user confirmation.
- [ ] Broad support or relational changes are surfaced for review.
- [ ] Reflection outputs link directly to action, correction, or durable understanding.

---

## 7. Milestones

### Milestone 1: Define the Pattern family and review-card schemas
Implement the fixed production pattern kinds plus typed reflection-card payloads.

Validation: targeted tests prove pattern cards are typed, scoped, evidence-backed, and bounded.

### Milestone 2: Add load and surfacing rules
Implement scoring and policy rules for pattern loading, move impact, and surfacing levels.

Validation: targeted tests prove patterns can be loaded silently, mentioned compactly, or surfaced more richly based on contract impact.

### Milestone 3: Add support-memory inspection surfaces
Implement user-visible ways to inspect active continuity, effective support values, relational values, and recent support-history changes.

Validation: targeted tests prove the inspection surface reads from the same source of truth as runtime support behavior.

### Milestone 4: Add confirmation, rejection, and correction flows
Implement actions to confirm, reject, reset, scope-limit, or edit learned assumptions.

Validation: targeted tests prove user corrections update durable support memory cleanly and traceably.

### Milestone 5: Add weekly and on-demand review generation
Implement bounded review flows that select a small number of high-value cards and attach practical actions or correction options.

Validation: targeted tests prove reviews stay within count limits and include evidence plus one useful next action per card.

### Milestone 6: Add inline reflection and session-start surfacing rules
Implement rules for when Alfred may surface patterns during live conversation or at session start versus keeping them internal.

Validation: targeted tests prove operational starts prioritize blocker/support patterns, reflective starts prioritize themes, and execution is not derailed by unnecessary surfacing.

### Milestone 7: Documentation and prompt/template updates
Add or update docs, user-facing explanations, and managed prompt/template content for reflection behavior, explanation surfaces, and correction flows.

Validation: docs explain the reflection/control model clearly and managed instructions reflect the same bounded review and promotion rules.

---

## 8. Likely File Changes

```text
src/alfred/memory/...                  # pattern storage and support-memory inspection data
src/alfred/context.py or orchestration # review generation inputs and inline reflection gates
src/alfred/interfaces/...              # TUI/Web UI/command surfaces for inspection and review
src/alfred/orchestration/...           # surfacing policy and move-impact rules if introduced

docs/MEMORY.md
docs/ARCHITECTURE.md
docs/how-alfred-helps.md
docs/relational-support-model.md
templates/SYSTEM.md
templates/SOUL.md
templates/USER.md
prds/169-reflection-reviews-and-support-controls.md
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Reflection becomes verbose and low-value | Medium | hard-cap review size and require action-linked cards |
| Alfred surfaces identity claims too aggressively | High | keep identity and direction themes candidate-first until user confirmation |
| Users cannot tell why Alfred changed behavior | High | expose evidence-backed support-history inspection and surface broad changes explicitly |
| Session-start pattern surfacing becomes noisy | Medium | require move-impact threshold and cap surfaced patterns to 1-2 |
| Review UX becomes a separate heavy product | Medium | keep the surface bounded and secondary to ordinary support |
| Internal learning and user-facing reflection drift apart | Medium | use the same durable support-memory source of truth for runtime and review |

---

## 10. Validation Strategy

This is primarily a Python-led feature with possible UI surfaces.

Required validation depends on touched code:

```bash
uv run ruff check src/
uv run mypy --strict src/
uv run pytest <targeted tests for touched review, memory, orchestration, and UI surfaces>
```

If browser-visible behavior is added, include targeted browser verification for the touched flow.

Docs and prompt/template updates should cover:
- reflection surfaces and when each is used
- pattern-family behavior and surfacing thresholds
- session-start surfacing rules
- support-memory inspection and correction flows
- promotion rules for candidate vs confirmed truths
- how Alfred explains broad support or relational changes

---

## 11. Related PRDs

- PRD #167: Support Memory Foundation
- PRD #168: Adaptive Support Profile and Intervention Learning
- PRD #179: Relational Support Operating Model

---

## 12. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-30 | Distinguish learning, pattern storage, and reflection | Alfred needs quiet adaptation plus deliberate user-facing meaning-making |
| 2026-03-30 | Use one Pattern family with typed kinds | Recurring blockers, support preferences, identity themes, and calibration gaps share evidence structure but need different surfacing rules |
| 2026-03-30 | Support inline, internal, and explicit review reflection surfaces | Reflection should appear in the right place instead of only one surface |
| 2026-03-30 | Keep production reflection typed and bounded | The review system should stay legible, useful, and testable |
| 2026-03-30 | Keep identity and direction learning candidate-first | Deep user truths should stay visible and consensual |
| 2026-03-30 | Session-start pattern surfacing is allowed when it materially changes the next move | High-value continuity includes recurring blockers, support preferences, and active themes, not just active threads |
| 2026-03-30 | Learning may silently improve scoped support behavior, but not silently redefine identity | Scoped adaptation should stay fast while identity remains user-controlled |
| 2026-03-30 | Most pattern machinery should remain invisible unless trust or correction requires explicitness | Alfred should feel clear and alive, not mechanically narrated |
| 2026-03-30 | Use learning situations as the primary matching unit and episodes as derived reflection reports | Reflection needs coherent reports, but the learning core should match semantically on situations rather than treat episodes as the primary write-path container |
