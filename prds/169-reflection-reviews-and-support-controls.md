# PRD: Reflection Reviews and Support Controls

**GitHub Issue**: [#169](https://github.com/jeremysball/alfred/issues/169)  
**Priority**: Medium  
**Status**: Draft  
**Created**: 2026-03-30

---

## 1. Problem Statement

Once Alfred starts learning user-specific support patterns, that learning needs a bounded user-facing surface.

Without that surface:
- users cannot inspect or correct learned support assumptions easily
- global support changes risk becoming invisible
- longitudinal patterns stay latent instead of becoming useful
- reflection can either disappear entirely or expand into an overwhelming essay engine

Alfred needs a compact review loop that turns evidence into action without making day-to-day execution support heavier.

---

## 2. Goals

1. Add **weekly and on-demand reflection reviews** with a bounded format.
2. Give users a **visible support-memory inspection and correction surface**.
3. Surface **candidate and confirmed patterns** with evidence and simple actions.
4. Surface **global support-profile changes** for review rather than silently normalizing them.
5. Keep reflection tightly connected to future action instead of open-ended analysis.
6. Treat **documentation and managed prompt/template updates** as part of feature completion so review behavior, correction flows, and explanation surfaces stay aligned with the implemented system.

---

## 3. Non-Goals

- Building an unbounded autobiographical memory browser.
- Turning Alfred into a freeform journaling or therapy product.
- Adding aggressive proactive nudging.
- Replacing execution support with long review rituals.
- Letting the LLM promote durable user-wide patterns without visibility.

---

## 4. Proposed Solution

### 4.1 Add bounded reflection reviews

Alfred should support two review entry points:

1. **On-demand review**
   - user explicitly asks for a review, reflection, or pattern summary
2. **Weekly review**
   - default scheduled review cadence
   - can be tuned or disabled by the user later

Reviews should stay small.

Recommended v1 constraints:
- at most 1-3 cards per review
- each card must include evidence
- each card must end in a practical action, confirmation question, or adjustment

### 4.2 Add candidate and confirmed pattern cards

Each reflection card should represent one bounded pattern such as:
- a repeated blocker
- a repeated success condition
- a support-style preference Alfred has observed
- a project-level or context-level trend worth acting on

Minimum card fields:
- statement
- type
- scope
- confidence
- evidence refs
- proposed action
- status (`candidate`, `confirmed`, `rejected`)

Example:

```json
{
  "pattern_id": "pat_14",
  "type": "support_effectiveness",
  "scope": {"type": "context", "id": "admin_task"},
  "statement": "Concrete first-action prompts work better than generic reminders for admin tasks.",
  "confidence": 0.87,
  "evidence_refs": ["int_55", "int_61", "int_64"],
  "proposed_action": "Default to one physical next step for admin tasks.",
  "status": "candidate"
}
```

### 4.3 Add support-memory inspection controls

Users should be able to inspect the main adaptive memory surfaces, at minimum:
- active projects/tasks/open loops
- effective support-profile values
- recent intervention history
- candidate and confirmed patterns

Users should also be able to:
- correct a support value
- reject a candidate pattern
- confirm a pattern
- reset a value to default
- view why a value changed

### 4.4 Surface global changes explicitly

Project- and context-level adaptation can happen quietly in the background as long as it is logged.

Global support-profile changes should be surfaced through the review flow or an explicit notification surface because they affect Alfred's broad default behavior.

### 4.5 Keep reflection action-linked

Reflection should always lead back to operational behavior.

Each review card must end in one of these:
- confirm a pattern
- reject a pattern
- update a support value
- create or adjust a task/open loop
- choose a small next action

This keeps reflection useful instead of decorative.

### 4.6 Respect general-purpose use

Reflection should work for:
- execution support
- project review
- personal workflows
- research and planning
- recurring collaboration patterns

It should not depend on any diagnosis-specific mode.

---

## 5. User Experience Requirements

A user should be able to ask Alfred things like:
- "Review the last week."
- "What patterns have you noticed in how I get stuck?"
- "Show me what you've learned about how to help me."
- "Why are you giving me shorter next steps now?"
- "Undo that support change."

The review surface should feel:
- compact
- evidence-backed
- editable
- actionable
- easy to skip when the user just wants execution help

---

## 6. Success Criteria

- [ ] Alfred supports on-demand and weekly review flows with bounded output.
- [ ] Reviews show 1-3 evidence-backed pattern cards rather than open-ended essays.
- [ ] Users can inspect effective support values and recent support changes.
- [ ] Users can confirm, reject, or reset learned support assumptions.
- [ ] Global support-profile changes are surfaced for review.
- [ ] Reflection outputs link directly to future action or support adjustments.

---

## 7. Milestones

### Milestone 1: Define reflection card and pattern model
Implement the schema for candidate and confirmed patterns plus bounded reflection-card payloads.

Validation: targeted tests prove pattern cards are typed, scoped, evidence-backed, and bounded.

### Milestone 2: Add support-memory inspection surfaces
Implement a user-visible way to inspect projects/tasks/open loops, effective support-profile values, and recent intervention/change history.

Validation: targeted tests prove the inspection surface reads from the same source of truth as runtime support behavior.

### Milestone 3: Add pattern confirmation and correction flows
Implement actions to confirm, reject, reset, or edit learned support assumptions.

Validation: targeted tests prove user corrections update the durable support memory cleanly.

### Milestone 4: Add weekly and on-demand review generation
Implement bounded review flows that select a small number of high-value cards and attach practical next actions.

Validation: targeted tests prove reviews stay within bounded count limits and include evidence plus one actionable outcome per card.

### Milestone 5: Regression coverage, documentation, and prompt/template updates
Add or update tests, docs, and managed prompt/template content for reflection, support-memory inspection, and correction flows.

Validation: relevant Python validation passes, user-facing documentation explains the review/control model clearly, and managed prompt/template content reflects the bounded review and correction behavior consistently.

---

## 8. Likely File Changes

```text
src/alfred/memory/...                  # pattern storage and support-memory inspection data
src/alfred/context.py or orchestration # review generation inputs
src/alfred/interfaces/...              # TUI/Web UI/command surfaces for inspection and review

docs/MEMORY.md
docs/ARCHITECTURE.md
templates/SYSTEM.md
templates/AGENTS.md
templates/prompts/voice.md
templates/prompts/boundaries.md
prds/169-reflection-reviews-and-support-controls.md
```

---

## 9. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Reflection becomes verbose and low-value | Medium | hard-cap review size and require action-linked cards |
| Users cannot tell why Alfred changed behavior | High | surface global changes and expose evidence-backed support-history inspection |
| Review UX becomes a separate heavy product | Medium | keep the surface bounded and secondary to execution support |
| Pattern confirmation flows drift from runtime behavior | Medium | use the same durable support-memory source of truth for review and runtime |

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
- review entry points and bounded card behavior
- support-memory inspection and correction flows
- how Alfred explains global support-profile changes and learned patterns to the user

---

## 11. Related PRDs

- PRD #167: Support Memory Foundation
- PRD #168: Adaptive Support Profile and Intervention Learning

---

## 12. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-30 | Add both on-demand and weekly review entry points | Users need a pull-based flow and a light recurring synthesis loop |
| 2026-03-30 | Keep reviews bounded to 1-3 cards | Reflection should stay compact and usable |
| 2026-03-30 | Require evidence and action on every card | Reflection should improve future behavior, not just summarize the past |
| 2026-03-30 | Expose support-memory inspection and correction | Adaptive behavior must stay visible and editable |
| 2026-03-30 | Surface global support changes explicitly | Broad default behavior changes should not stay invisible |
