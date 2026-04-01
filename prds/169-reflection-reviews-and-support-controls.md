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

The result today is that Alfred can imagine reflective behavior, but he does not yet have a clear system for when to surface patterns, how to classify them, how to keep them bounded, and how to keep identity-level learning consensual.

---

## 2. Goals

1. Add **bounded reflection surfaces** that turn support learning into useful user-facing insight.
2. Distinguish clearly between **internal learning** and **user-facing reflection**.
3. Surface **typed candidate and confirmed patterns** with evidence and simple actions.
4. Give users visible controls over effective support state, relational shifts, and learned themes.
5. Keep identity and direction learning **candidate-first** until the user confirms it.
6. Surface broad support or relational changes rather than silently normalizing them.
7. Keep reflection tied to future action, correction, or explicit understanding rather than open-ended essay generation.
8. Treat documentation and managed prompt/template updates as part of feature completion so review behavior and correction surfaces are described consistently.

---

## 3. Non-Goals

- Building an unbounded autobiographical memory browser.
- Turning Alfred into a freeform therapy or journaling product.
- Letting the model silently redefine the user's identity.
- Replacing execution support with large review rituals.
- Allowing review surfaces to become generic essays or vague self-help summaries.

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

2. **Reflection**
   - user-facing pattern surfacing
   - review cards
   - explanation of support changes
   - confirmation, rejection, reset, and promotion flows

This keeps Alfred adaptive without making every internal update a user interruption.

### 4.2 Add three reflection surfaces

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
- support-effectiveness candidates
- relational-preference candidates
- identity-theme candidates
- direction-theme candidates
- review queues

This is mostly for Alfred, not for the user.

#### C. Explicit review
Alfred should support:
1. **On-demand review**
2. **Weekly review**

These are where learning becomes bounded, typed, user-visible reflection.

### 4.3 Use episodes as the base unit for pattern generation

Pattern generation should work from episode evidence, not only from coarse session blobs.

That allows Alfred to learn separately from:
- an execution episode
- a decision episode
- an identity reflection episode
- a direction reflection episode

The reflection system should aggregate from episode evidence into candidate patterns and review cards.

### 4.4 Add a fixed production pattern taxonomy

V1 should use a closed pattern taxonomy for production reflection.

Recommended v1 pattern types:
- `support_effectiveness`
- `recurring_blocker`
- `relational_preference`
- `identity_theme`
- `direction_tension`
- `recovery_pattern`
- `value_signal`

Examples:
- support effectiveness: "Single-step execute prompts work better than broader plans."
- recurring blocker: "Ambiguity repeatedly delays admin tasks."
- relational preference: "Peer-like candor works better than authority-heavy advice in direction reflection."
- identity theme: "You tend to disown desire when goals become publicly legible."
- direction tension: "Prestige and aliveness keep pulling in different directions."
- recovery pattern: "Clean reset language works better than guilt after drift."
- value signal: "Autonomy matters more to you than external recognition."

This keeps reflection legible and testable.

### 4.5 Add typed review card models

Review cards should not just be generic "patterns."

Recommended v1 card types:
- **support-fit card**
- **blocker card**
- **relational-fit card**
- **identity-theme card**
- **direction-tension card**

Minimum card fields:
- `card_id`
- `pattern_type`
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
  "pattern_type": "direction_tension",
  "scope": {"type": "global", "id": "user"},
  "statement": "A tension between external legibility and felt aliveness keeps recurring in your work decisions.",
  "confidence": 0.87,
  "evidence_refs": ["ep_204", "ep_213", "ep_227"],
  "proposed_action": "Confirm whether this is a real recurring tension and, if so, keep it visible in future direction decisions.",
  "status": "candidate"
}
```

### 4.6 Add support-memory inspection controls

Users should be able to inspect, at minimum:
- active projects, tasks, and open loops
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
- promote a confirmed durable theme into `USER.md` when appropriate

### 4.7 Use a candidate-first promotion ladder

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
- support effectiveness can adapt quietly in narrow scopes
- broad support or relational defaults should be surfaced
- identity themes, direction tensions, and durable value signals should remain candidate-first until the user confirms them
- only user-endorsed durable truths should move into `USER.md`

### 4.8 Surface broad changes explicitly

Project- and context-level adaptation can happen in the background if it stays logged.

Broad changes should be surfaced:
- global support-profile changes
- global relational shifts
- durable value signals
- identity themes Alfred wants to keep broadly active
- direction-level patterns that would materially shape future reflection or recommendations

### 4.9 Keep reflection bounded and action-linked

Reflection should always end in one of these:
- change how Alfred helps
- change operational state
- change durable understanding
- open a deliberate reflection thread

Reviews should stay small.

Recommended v1 constraints:
- at most 1-3 cards per review
- each card must include evidence
- each card must end in a practical action, confirmation question, correction option, or next reflection step

### 4.10 Respect general-purpose use

Reflection should work for:
- execution support
- project review
- decision support
- personal workflow patterns
- identity reflection
- life-direction reflection
- recurring collaboration patterns

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

---

## 6. Success Criteria

- [ ] Alfred supports inline, weekly, and on-demand reflection surfaces with bounded behavior.
- [ ] Reviews show 1-3 typed, evidence-backed cards rather than open-ended essays.
- [ ] Users can inspect effective support and relational values plus recent change history.
- [ ] Users can confirm, reject, reset, or scope-limit learned assumptions.
- [ ] Identity and direction themes remain candidate-first until user confirmation.
- [ ] Broad support or relational changes are surfaced for review.
- [ ] Reflection outputs link directly to action, correction, or durable understanding.

---

## 7. Milestones

### Milestone 1: Define pattern and review-card schemas
Implement the fixed production pattern taxonomy plus typed reflection-card payloads.

Validation: targeted tests prove pattern cards are typed, scoped, evidence-backed, and bounded.

### Milestone 2: Add support-memory inspection surfaces
Implement user-visible ways to inspect projects/tasks/open loops, effective support values, relational values, and recent support-history changes.

Validation: targeted tests prove the inspection surface reads from the same source of truth as runtime support behavior.

### Milestone 3: Add confirmation, rejection, and correction flows
Implement actions to confirm, reject, reset, scope-limit, or edit learned assumptions.

Validation: targeted tests prove user corrections update durable support memory cleanly and traceably.

### Milestone 4: Add weekly and on-demand review generation
Implement bounded review flows that select a small number of high-value cards and attach practical actions or correction options.

Validation: targeted tests prove reviews stay within count limits and include evidence plus one useful next action per card.

### Milestone 5: Add inline reflection rules and regression coverage
Implement rules for when Alfred may surface patterns during live conversation versus keeping them for review.

Validation: targeted tests prove inline reflection appears when contextually relevant and stays quiet when it would derail execution.

### Milestone 6: Documentation and prompt/template updates
Add or update docs, user-facing explanations, and managed prompt/template content for reflection behavior, explanation surfaces, and correction flows.

Validation: docs explain the reflection/control model clearly and managed instructions reflect the same bounded review and promotion rules.

---

## 8. Likely File Changes

```text
src/alfred/memory/...                  # pattern storage and support-memory inspection data
src/alfred/context.py or orchestration # review generation inputs and inline reflection gates
src/alfred/interfaces/...              # TUI/Web UI/command surfaces for inspection and review

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
| Review UX becomes a separate heavy product | Medium | keep the surface bounded and secondary to ordinary support |
| Internal learning and user-facing reflection drift apart | Medium | use the same durable support-memory source of truth for runtime and review |

---

## 10. Validation Strategy

This is primarily a Python-led feature with possible UI surfaces.

Required validation depends on touched code:

```bash
uv run ruff check src/
uv run mypy --strict src/
uv run pytest <targeted tests for touched review, memory, and UI surfaces>
```

If browser-visible behavior is added, include targeted browser verification for the touched flow.

Docs and prompt/template updates should cover:
- reflection surfaces and when each is used
- pattern taxonomy and review-card behavior
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
| 2026-03-30 | Distinguish learning from reflection | Alfred needs quiet adaptation plus deliberate user-facing meaning-making |
| 2026-03-30 | Support inline, internal, and explicit review reflection surfaces | Reflection should appear in the right place instead of only one surface |
| 2026-03-30 | Keep production reflection typed and bounded | The review system should stay legible, useful, and testable |
| 2026-03-30 | Keep identity and direction learning candidate-first | Deep user truths should stay visible and consensual |
| 2026-03-30 | Learning may silently improve scoped support behavior, but not silently redefine identity | Scoped adaptation should stay fast while identity remains user-controlled |
