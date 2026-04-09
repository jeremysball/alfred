"""Tests for Milestone 5 support-learning contracts and bounded adaptation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from alfred.memory.support_learning import (
    FinalizedLearningCaseBundle,
    LearningCase,
    LearningSituation,
    OutcomeObservation,
    SupportAttempt,
    SupportLedgerUpdateEvent,
    SupportPattern,
    SupportPatternLedgerEntry,
    SupportProfileUpdateEvent,
    SupportTranscriptSpanRef,
    SupportValueLedgerEntry,
    apply_bounded_adaptation,
    derive_bounded_adaptation,
    derive_learning_case,
    derive_value_ledger_updates_from_cases,
)
from alfred.memory.support_profile import SupportProfileScope, SupportProfileValue
from alfred.support_policy import (
    ResolvedSubject,
    SupportPolicyPattern,
    SupportTurnAssessment,
    compile_support_behavior_contract,
    resolve_support_policy,
)


class FakeLearningStore:
    """Async fake store that records bounded-adaptation writes."""

    def __init__(self) -> None:
        self.learning_situations: list[LearningSituation] = []
        self.patterns: list[SupportPattern] = []
        self.update_events: list[SupportProfileUpdateEvent] = []
        self.profile_values: list[SupportProfileValue] = []

    async def save_learning_situation(self, situation: LearningSituation) -> None:
        self.learning_situations.append(situation)

    async def save_support_pattern(self, pattern: SupportPattern) -> None:
        self.patterns.append(pattern)

    async def save_support_profile_update_event(self, event: SupportProfileUpdateEvent) -> None:
        self.update_events.append(event)

    async def save_support_profile_value(self, profile_value: SupportProfileValue) -> None:
        self.profile_values.append(profile_value)


class FakePolicyValueStore:
    """Minimal fake store for resolving persisted profile values back into runtime policy."""

    def __init__(self, values: list[SupportProfileValue]) -> None:
        self.values = values

    async def resolve_support_profile_value(
        self,
        registry: str,
        dimension: str,
        *,
        context_id: str | None = None,
        arc_id: str | None = None,
    ) -> SupportProfileValue | None:
        scopes_to_try: list[SupportProfileScope] = []
        if arc_id is not None:
            scopes_to_try.append(SupportProfileScope(type="arc", id=arc_id))
        if context_id is not None:
            scopes_to_try.append(SupportProfileScope(type="context", id=context_id))
        scopes_to_try.append(SupportProfileScope(type="global", id="user"))

        for scope in scopes_to_try:
            for value in self.values:
                if value.registry == registry and value.dimension == dimension and value.scope == scope:
                    return value
        return None


def _make_finalized_learning_case_bundle(
    *,
    attempt_id: str,
    case_id: str,
    scope: SupportProfileScope,
    created_at: datetime,
    finalized_at: datetime | None,
    response_mode: str,
    support_values: dict[str, str] | None = None,
    relational_values: dict[str, str] | None = None,
    overall_score: float = 0.8,
    promotion_eligibility: bool = True,
    status: str = "complete",
) -> FinalizedLearningCaseBundle:
    active_arc_id = scope.id if scope.type == "arc" else None
    attempt = SupportAttempt(
        attempt_id=attempt_id,
        session_id=f"session-{attempt_id}",
        user_message_id=f"user-{attempt_id}",
        assistant_message_id=f"assistant-{attempt_id}",
        created_at=created_at,
        need="activate" if scope.type == "arc" else "reflect",
        response_mode=response_mode,
        subject_refs=(f"{scope.type}:{scope.id}",),
        active_arc_id=active_arc_id,
        active_domain_ids=("work",),
        effective_support_values=support_values or {},
        effective_relational_values=relational_values or {},
        intervention_family="narrow" if response_mode == "execute" else "mirror",
        intervention_refs=(),
        prompt_contract_summary="Test support contract summary.",
        operational_snapshot_ref=None,
    )

    case = LearningCase(
        case_id=case_id,
        attempt_id=attempt.attempt_id,
        status=status,  # type: ignore[arg-type]
        scope=scope,
        created_at=created_at,
        finalized_at=finalized_at,
        aggregate_signals=("clarity",),
        positive_evidence_count=1 if promotion_eligibility else 0,
        negative_evidence_count=0,
        contradiction_count=0,
        conversation_score=overall_score,
        operational_score=overall_score if scope.type == "arc" else 0.0,
        overall_score=overall_score,
        promotion_eligibility=promotion_eligibility,
        evidence_refs=(),
        summary="Test learning case." if status != "open" else None,
    )
    return FinalizedLearningCaseBundle(learning_case=case, attempt=attempt)


def test_v2_learning_artifacts_round_trip_with_real_refs() -> None:
    """Support attempts, observations, and cases should preserve the v2 storage contract."""

    attempt = SupportAttempt(
        attempt_id="attempt-webui-1",
        session_id="sess-812",
        user_message_id="msg-user-445",
        assistant_message_id="msg-assistant-446",
        created_at=datetime(2026, 4, 7, 12, 10, tzinfo=UTC),
        need="activate",
        response_mode="execute",
        active_arc_id="webui_cleanup",
        active_domain_ids=("work",),
        subject_refs=("arc:webui_cleanup", "domain:work"),
        effective_support_values={
            "option_bandwidth": "single",
            "planning_granularity": "minimal",
        },
        effective_relational_values={
            "candor": "high",
            "warmth": "medium",
        },
        intervention_family="narrow",
        intervention_refs=("int-webui-1",),
        prompt_contract_summary="Keep the next move narrow, direct, and execution-focused.",
        operational_snapshot_ref="arc:webui_cleanup@snap-2026-04-07T12:10:00Z",
    )
    observation = OutcomeObservation(
        observation_id="obs-webui-1",
        attempt_id="attempt-webui-1",
        observed_at=datetime(2026, 4, 7, 12, 18, tzinfo=UTC),
        source_type="work_state_transition",
        signals=("task_started", "blocker_narrowed", "clarity"),
        signal_polarity="positive",
        signal_strength=0.82,
        evidence_refs=(
            SupportTranscriptSpanRef(
                session_id="sess-812",
                message_start_id="msg-user-445",
                message_end_id="msg-assistant-446",
            ),
        ),
        operational_delta_refs=("task:webui-bootstrap", "blocker:script-order"),
        notes="The user started the bootstrap task and the main blocker narrowed.",
    )
    case = LearningCase(
        case_id="case-webui-1",
        attempt_id="attempt-webui-1",
        status="complete",
        scope=SupportProfileScope(type="arc", id="webui_cleanup"),
        created_at=datetime(2026, 4, 7, 12, 10, tzinfo=UTC),
        finalized_at=datetime(2026, 4, 7, 12, 25, tzinfo=UTC),
        aggregate_signals=("task_started", "blocker_narrowed", "clarity"),
        positive_evidence_count=3,
        negative_evidence_count=0,
        contradiction_count=0,
        conversation_score=0.78,
        operational_score=0.91,
        overall_score=0.85,
        promotion_eligibility=True,
        evidence_refs=(
            SupportTranscriptSpanRef(
                session_id="sess-812",
                message_start_id="msg-user-445",
                message_end_id="msg-assistant-446",
            ),
        ),
        summary="Narrow direct execution support correlated with concrete movement in the active arc.",
    )

    attempt_record = attempt.to_record()
    observation_record = observation.to_record()
    case_record = case.to_record()

    assert SupportAttempt.from_record(attempt_record) == attempt
    assert OutcomeObservation.from_record(observation_record) == observation
    assert LearningCase.from_record(case_record) == case
    assert attempt_record["user_message_id"] == "msg-user-445"
    assert observation_record["signals"] == '["task_started", "blocker_narrowed", "clarity"]'
    assert case_record["scope_type"] == "arc"
    assert case_record["promotion_eligibility"] is True



def test_derive_learning_case_scores_conversational_and_operational_evidence() -> None:
    """Deterministic case derivation should score mixed-source evidence into one promotable case."""

    attempt = SupportAttempt(
        attempt_id="attempt-webui-1",
        session_id="sess-812",
        user_message_id="msg-user-445",
        assistant_message_id="msg-assistant-446",
        created_at=datetime(2026, 4, 7, 12, 10, tzinfo=UTC),
        need="activate",
        response_mode="execute",
        active_arc_id="webui_cleanup",
        active_domain_ids=("work",),
        subject_refs=("arc:webui_cleanup", "domain:work"),
        effective_support_values={"option_bandwidth": "single"},
        effective_relational_values={"candor": "high"},
        intervention_family="narrow",
        prompt_contract_summary="Keep the next move narrow and direct.",
    )
    observations = (
        OutcomeObservation(
            observation_id="obs-webui-1",
            attempt_id=attempt.attempt_id,
            observed_at=datetime(2026, 4, 7, 12, 15, tzinfo=UTC),
            source_type="next_user_turn",
            signals=("clarity", "commitment"),
            signal_polarity="positive",
            signal_strength=0.76,
            evidence_refs=(
                SupportTranscriptSpanRef(
                    session_id=attempt.session_id,
                    message_start_id="msg-user-447",
                    message_end_id="msg-user-447",
                ),
            ),
            notes="The user accepted the narrow plan and committed to act.",
        ),
        OutcomeObservation(
            observation_id="obs-webui-2",
            attempt_id=attempt.attempt_id,
            observed_at=datetime(2026, 4, 7, 12, 18, tzinfo=UTC),
            source_type="work_state_transition",
            signals=("task_started", "blocker_resolved"),
            signal_polarity="positive",
            signal_strength=0.88,
            operational_delta_refs=("task:webui-bootstrap", "blocker:script-order"),
            notes="The user started the task and resolved the blocker.",
        ),
    )

    learning_case = derive_learning_case(attempt=attempt, observations=observations)

    assert learning_case == LearningCase(
        case_id="case-attempt-webui-1",
        attempt_id=attempt.attempt_id,
        status="complete",
        scope=SupportProfileScope(type="arc", id="webui_cleanup"),
        created_at=attempt.created_at,
        finalized_at=datetime(2026, 4, 7, 12, 18, tzinfo=UTC),
        aggregate_signals=("clarity", "commitment", "task_started", "blocker_resolved"),
        positive_evidence_count=4,
        negative_evidence_count=0,
        contradiction_count=0,
        conversation_score=0.76,
        operational_score=0.88,
        overall_score=0.82,
        promotion_eligibility=True,
        evidence_refs=(
            SupportTranscriptSpanRef(
                session_id=attempt.session_id,
                message_start_id="msg-user-447",
                message_end_id="msg-user-447",
            ),
        ),
        summary="Attempt attempt-webui-1 produced enough directional evidence to finalize a promotable case.",
    )



def test_derive_learning_case_marks_neutral_only_evidence_as_insufficient() -> None:
    """Neutral-only evidence should stay inspectable but never become promotion-eligible."""

    attempt = SupportAttempt(
        attempt_id="attempt-docs-1",
        session_id="sess-900",
        user_message_id="msg-user-900",
        assistant_message_id="msg-assistant-901",
        created_at=datetime(2026, 4, 7, 13, 0, tzinfo=UTC),
        need="reflect",
        response_mode="review",
        subject_refs=("domain:work",),
        effective_support_values={"reflection_depth": "medium"},
        effective_relational_values={"warmth": "high"},
        intervention_family="mirror",
        prompt_contract_summary="Mirror the uncertainty without forcing a decision.",
    )
    observations = (
        OutcomeObservation(
            observation_id="obs-docs-1",
            attempt_id=attempt.attempt_id,
            observed_at=datetime(2026, 4, 7, 13, 10, tzinfo=UTC),
            source_type="manual_review",
            signals=("follow_up_needed",),
            signal_polarity="neutral",
            signal_strength=0.6,
            notes="The attempt stayed ambiguous and needs more evidence.",
        ),
    )

    learning_case = derive_learning_case(attempt=attempt, observations=observations)

    assert learning_case == LearningCase(
        case_id="case-attempt-docs-1",
        attempt_id=attempt.attempt_id,
        status="insufficient_evidence",
        scope=SupportProfileScope(type="context", id="review"),
        created_at=attempt.created_at,
        finalized_at=datetime(2026, 4, 7, 13, 10, tzinfo=UTC),
        aggregate_signals=("follow_up_needed",),
        positive_evidence_count=0,
        negative_evidence_count=0,
        contradiction_count=0,
        conversation_score=0.15,
        operational_score=0.0,
        overall_score=0.15,
        promotion_eligibility=False,
        evidence_refs=(),
        summary="Attempt attempt-docs-1 finalized with insufficient directional evidence.",
    )



def test_derive_value_ledger_updates_persists_shadow_rows_below_exact_scope_thresholds() -> None:
    """One promotable case should persist inspectable shadow rows before exact-scope thresholds are met."""

    now = datetime(2026, 4, 7, 16, 0, tzinfo=UTC)
    arc_bundle = _make_finalized_learning_case_bundle(
        attempt_id="attempt-arc-1",
        case_id="case-arc-1",
        scope=SupportProfileScope(type="arc", id="webui_cleanup"),
        created_at=datetime(2026, 4, 7, 15, 0, tzinfo=UTC),
        finalized_at=datetime(2026, 4, 7, 15, 10, tzinfo=UTC),
        response_mode="execute",
        support_values={"option_bandwidth": "single"},
        overall_score=0.81,
    )

    arc_result = derive_value_ledger_updates_from_cases(
        focus_bundle=arc_bundle,
        scoped_bundles=(arc_bundle,),
        existing_value_entries={},
        now=now,
    )

    assert len(arc_result.value_entries) == 1
    arc_entry = arc_result.value_entries[0]
    assert arc_entry == SupportValueLedgerEntry(
        value_id="value-support-option_bandwidth-arc-webui_cleanup-single",
        registry="support",
        dimension="option_bandwidth",
        scope=SupportProfileScope(type="arc", id="webui_cleanup"),
        value="single",
        status="shadow",
        source="auto_case",
        confidence=0.81,
        evidence_count=1,
        contradiction_count=0,
        last_case_id="case-arc-1",
        created_at=now,
        updated_at=now,
        why="support option_bandwidth=single has 1 supporting promotable cases and 0 conflicting promotable cases in this arc scope.",
    )
    assert arc_result.update_events == (
        SupportLedgerUpdateEvent(
            event_id="event-value-support-option_bandwidth-arc-webui_cleanup-single-shadow-case-arc-1",
            entity_type="value",
            entity_id=arc_entry.value_id,
            registry="support",
            dimension_or_kind="option_bandwidth",
            scope=arc_entry.scope,
            old_status=None,
            new_status="shadow",
            old_value=None,
            new_value="single",
            trigger_case_ids=("case-arc-1",),
            reason=arc_entry.why,
            confidence=0.81,
            created_at=now,
        ),
    )

    context_bundle = _make_finalized_learning_case_bundle(
        attempt_id="attempt-context-1",
        case_id="case-context-1",
        scope=SupportProfileScope(type="context", id="review"),
        created_at=datetime(2026, 4, 7, 15, 20, tzinfo=UTC),
        finalized_at=datetime(2026, 4, 7, 15, 30, tzinfo=UTC),
        response_mode="review",
        relational_values={"warmth": "high"},
        overall_score=0.77,
    )

    context_result = derive_value_ledger_updates_from_cases(
        focus_bundle=context_bundle,
        scoped_bundles=(context_bundle,),
        existing_value_entries={},
        now=now,
    )

    assert context_result.value_entries == (
        SupportValueLedgerEntry(
            value_id="value-relational-warmth-context-review-high",
            registry="relational",
            dimension="warmth",
            scope=SupportProfileScope(type="context", id="review"),
            value="high",
            status="shadow",
            source="auto_case",
            confidence=0.77,
            evidence_count=1,
            contradiction_count=0,
            last_case_id="case-context-1",
            created_at=now,
            updated_at=now,
            why="relational warmth=high has 1 supporting promotable cases and 0 conflicting promotable cases in this context scope.",
        ),
    )
    assert context_result.update_events == (
        SupportLedgerUpdateEvent(
            event_id="event-value-relational-warmth-context-review-high-shadow-case-context-1",
            entity_type="value",
            entity_id="value-relational-warmth-context-review-high",
            registry="relational",
            dimension_or_kind="warmth",
            scope=SupportProfileScope(type="context", id="review"),
            old_status=None,
            new_status="shadow",
            old_value=None,
            new_value="high",
            trigger_case_ids=("case-context-1",),
            reason="relational warmth=high has 1 supporting promotable cases and 0 conflicting promotable cases in this context scope.",
            confidence=0.77,
            created_at=now,
        ),
    )



def test_derive_value_ledger_updates_promotes_after_threshold_and_blocks_when_conflicts_win() -> None:
    """Repeated exact-scope evidence should promote, while equal-strength conflicts should block activation."""

    shadow_now = datetime(2026, 4, 7, 16, 0, tzinfo=UTC)
    first_arc_bundle = _make_finalized_learning_case_bundle(
        attempt_id="attempt-arc-1",
        case_id="case-arc-1",
        scope=SupportProfileScope(type="arc", id="webui_cleanup"),
        created_at=datetime(2026, 4, 7, 15, 0, tzinfo=UTC),
        finalized_at=datetime(2026, 4, 7, 15, 10, tzinfo=UTC),
        response_mode="execute",
        support_values={"option_bandwidth": "single"},
        overall_score=0.81,
    )
    first_result = derive_value_ledger_updates_from_cases(
        focus_bundle=first_arc_bundle,
        scoped_bundles=(first_arc_bundle,),
        existing_value_entries={},
        now=shadow_now,
    )
    existing_entries = {
        (
            entry.registry,
            entry.dimension,
            entry.scope.type,
            entry.scope.id,
            entry.value,
        ): entry
        for entry in first_result.value_entries
    }

    promote_now = datetime(2026, 4, 7, 16, 5, tzinfo=UTC)
    second_arc_bundle = _make_finalized_learning_case_bundle(
        attempt_id="attempt-arc-2",
        case_id="case-arc-2",
        scope=SupportProfileScope(type="arc", id="webui_cleanup"),
        created_at=datetime(2026, 4, 7, 15, 30, tzinfo=UTC),
        finalized_at=datetime(2026, 4, 7, 15, 40, tzinfo=UTC),
        response_mode="execute",
        support_values={"option_bandwidth": "single"},
        overall_score=0.83,
    )
    promotion_result = derive_value_ledger_updates_from_cases(
        focus_bundle=second_arc_bundle,
        scoped_bundles=(first_arc_bundle, second_arc_bundle),
        existing_value_entries=existing_entries,
        now=promote_now,
    )

    assert promotion_result.value_entries == (
        SupportValueLedgerEntry(
            value_id="value-support-option_bandwidth-arc-webui_cleanup-single",
            registry="support",
            dimension="option_bandwidth",
            scope=SupportProfileScope(type="arc", id="webui_cleanup"),
            value="single",
            status="active_auto",
            source="auto_case",
            confidence=0.82,
            evidence_count=2,
            contradiction_count=0,
            last_case_id="case-arc-2",
            created_at=shadow_now,
            updated_at=promote_now,
            why="support option_bandwidth=single has 2 supporting promotable cases and 0 conflicting promotable cases in this arc scope.",
        ),
    )
    assert promotion_result.update_events == (
        SupportLedgerUpdateEvent(
            event_id="event-value-support-option_bandwidth-arc-webui_cleanup-single-active_auto-case-arc-2",
            entity_type="value",
            entity_id="value-support-option_bandwidth-arc-webui_cleanup-single",
            registry="support",
            dimension_or_kind="option_bandwidth",
            scope=SupportProfileScope(type="arc", id="webui_cleanup"),
            old_status="shadow",
            new_status="active_auto",
            old_value="single",
            new_value="single",
            trigger_case_ids=("case-arc-1", "case-arc-2"),
            reason=(
                "support option_bandwidth=single has 2 supporting promotable cases and 0 "
                "conflicting promotable cases in this arc scope."
            ),
            confidence=0.82,
            created_at=promote_now,
        ),
    )

    conflict_now = datetime(2026, 4, 7, 16, 10, tzinfo=UTC)
    conflict_bundles = (
        _make_finalized_learning_case_bundle(
            attempt_id="attempt-conflict-1",
            case_id="case-conflict-1",
            scope=SupportProfileScope(type="arc", id="ops_cleanup"),
            created_at=datetime(2026, 4, 7, 14, 0, tzinfo=UTC),
            finalized_at=datetime(2026, 4, 7, 14, 10, tzinfo=UTC),
            response_mode="execute",
            support_values={"option_bandwidth": "single"},
            overall_score=0.8,
        ),
        _make_finalized_learning_case_bundle(
            attempt_id="attempt-conflict-2",
            case_id="case-conflict-2",
            scope=SupportProfileScope(type="arc", id="ops_cleanup"),
            created_at=datetime(2026, 4, 7, 14, 20, tzinfo=UTC),
            finalized_at=datetime(2026, 4, 7, 14, 30, tzinfo=UTC),
            response_mode="execute",
            support_values={"option_bandwidth": "many"},
            overall_score=0.79,
        ),
        _make_finalized_learning_case_bundle(
            attempt_id="attempt-conflict-3",
            case_id="case-conflict-3",
            scope=SupportProfileScope(type="arc", id="ops_cleanup"),
            created_at=datetime(2026, 4, 7, 14, 40, tzinfo=UTC),
            finalized_at=datetime(2026, 4, 7, 14, 50, tzinfo=UTC),
            response_mode="execute",
            support_values={"option_bandwidth": "many"},
            overall_score=0.78,
        ),
        _make_finalized_learning_case_bundle(
            attempt_id="attempt-conflict-4",
            case_id="case-conflict-4",
            scope=SupportProfileScope(type="arc", id="ops_cleanup"),
            created_at=datetime(2026, 4, 7, 15, 0, tzinfo=UTC),
            finalized_at=datetime(2026, 4, 7, 15, 10, tzinfo=UTC),
            response_mode="execute",
            support_values={"option_bandwidth": "single"},
            overall_score=0.82,
        ),
    )
    conflict_result = derive_value_ledger_updates_from_cases(
        focus_bundle=conflict_bundles[-1],
        scoped_bundles=conflict_bundles,
        existing_value_entries={},
        now=conflict_now,
    )

    single_entry = next(entry for entry in conflict_result.value_entries if entry.value == "single")
    many_entry = next(entry for entry in conflict_result.value_entries if entry.value == "many")
    assert single_entry.status == "shadow"
    assert single_entry.evidence_count == 2
    assert single_entry.contradiction_count == 2
    assert many_entry.status == "shadow"
    assert many_entry.evidence_count == 2
    assert many_entry.contradiction_count == 2



def test_v2_value_pattern_and_update_event_records_preserve_status_and_provenance() -> None:
    """V2 ledger rows should preserve explicit statuses and provenance through record helpers."""

    value_entry = SupportValueLedgerEntry(
        value_id="val-candor-execute-1",
        registry="relational",
        dimension="candor",
        scope=SupportProfileScope(type="context", id="execute"),
        value="high",
        status="active_auto",
        source="auto_case",
        confidence=0.83,
        evidence_count=4,
        contradiction_count=1,
        last_case_id="case-webui-2",
        created_at=datetime(2026, 4, 7, 12, 26, tzinfo=UTC),
        updated_at=datetime(2026, 4, 7, 12, 31, tzinfo=UTC),
        why="Repeated successful execute cases favored stronger candor.",
    )
    pattern_entry = SupportPatternLedgerEntry(
        pattern_id="pattern-execute-directness",
        registry="relational",
        kind="support_preference",
        scope=SupportProfileScope(type="context", id="execute"),
        status="active_auto",
        claim="Direct candor plus narrow next steps works better during execute turns.",
        evidence_count=5,
        contradiction_count=1,
        confidence=0.81,
        source_case_ids=("case-webui-1", "case-webui-2"),
        created_at=datetime(2026, 4, 7, 12, 26, tzinfo=UTC),
        updated_at=datetime(2026, 4, 7, 12, 31, tzinfo=UTC),
        why="Multiple successful execute cases converged on the same support preference.",
    )
    update_event = SupportLedgerUpdateEvent(
        event_id="evt-candor-auto-1",
        entity_type="value",
        entity_id="val-candor-execute-1",
        registry="relational",
        dimension_or_kind="candor",
        scope=SupportProfileScope(type="context", id="execute"),
        old_status="shadow",
        new_status="active_auto",
        old_value="medium",
        new_value="high",
        trigger_case_ids=("case-webui-1", "case-webui-2"),
        reason="Repeated successful execute cases supported stronger candor.",
        confidence=0.83,
        created_at=datetime(2026, 4, 7, 12, 31, tzinfo=UTC),
    )

    value_record = value_entry.to_record()
    pattern_record = pattern_entry.to_record()
    event_record = update_event.to_record()

    assert SupportValueLedgerEntry.from_record(value_record) == value_entry
    assert SupportPatternLedgerEntry.from_record(pattern_record) == pattern_entry
    assert SupportLedgerUpdateEvent.from_record(event_record) == update_event
    assert value_record["status"] == "active_auto"
    assert value_record["evidence_count"] == 4
    assert pattern_record["source_case_ids"] == '["case-webui-1", "case-webui-2"]'
    assert pattern_record["why"] == "Multiple successful execute cases converged on the same support preference."
    assert event_record["old_status"] == "shadow"
    assert event_record["trigger_case_ids"] == '["case-webui-1", "case-webui-2"]'



def test_learning_situation_round_trips_with_embedding_contract_and_linked_interventions() -> None:
    """Learning situations should preserve the semantic learning contract through record helpers."""

    situation = LearningSituation(
        situation_id="sit-webui-1",
        session_id="sess-812",
        recorded_at=datetime(2026, 3, 30, 14, 5, tzinfo=UTC),
        turn_text="Let's continue the Web UI cleanup and just pick one next step.",
        embedding=(0.12, 0.91, 0.34, 0.08),
        need="resume",
        response_mode="execute",
        subject_refs=("arc:webui_cleanup", "domain:work"),
        arc_id="webui_cleanup",
        domain_ids=("work",),
        intervention_ids=("int-webui-1",),
        behavior_contract_summary="Resume the thread, keep it narrow, and recommend one next move.",
        intervention_family="summarize",
        relational_values_applied={
            "candor": "medium",
            "companionship": "medium",
        },
        support_values_applied={
            "option_bandwidth": "single",
            "planning_granularity": "minimal",
        },
        user_response_signals=("resonance",),
        outcome_signals=("next_step_chosen",),
        evidence_refs=(
            SupportTranscriptSpanRef(
                session_id="sess-812",
                message_start_id="msg-445",
                message_end_id="msg-446",
            ),
        ),
    )

    record = situation.to_record()

    assert LearningSituation.from_record(record) == situation
    assert record["embedding"] == "[0.12, 0.91, 0.34, 0.08]"
    assert record["subject_refs"] == '["arc:webui_cleanup", "domain:work"]'
    assert record["intervention_ids"] == '["int-webui-1"]'


def test_support_pattern_round_trips_with_kind_scope_status_and_supporting_situations() -> None:
    """Support patterns should preserve kind, scope, status, and runtime overrides through record helpers."""

    pattern = SupportPattern(
        pattern_id="pattern-narrow-next-step",
        kind="support_preference",
        scope=SupportProfileScope(type="context", id="execute"),
        status="confirmed",
        claim="Single-step operational next moves work better than menus here.",
        confidence=0.86,
        created_at=datetime(2026, 3, 30, 14, 20, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 14, 28, tzinfo=UTC),
        supporting_situation_ids=("sit-webui-1", "sit-webui-2"),
        support_overrides={"option_bandwidth": "single"},
        relational_overrides={"momentum_pressure": "medium"},
    )

    record = pattern.to_record()

    assert SupportPattern.from_record(record) == pattern
    assert record["scope_type"] == "context"
    assert record["scope_id"] == "execute"


def test_support_profile_update_event_round_trips_old_new_values_and_evidence() -> None:
    """Support-profile update events should preserve reversible change metadata through record helpers."""

    event = SupportProfileUpdateEvent(
        event_id="upd-candor-1",
        timestamp=datetime(2026, 3, 30, 14, 35, tzinfo=UTC),
        registry="relational",
        dimension="candor",
        scope=SupportProfileScope(type="context", id="direction_reflect"),
        old_value="medium",
        new_value="high",
        reason="Repeated strong calibration situations responded better to more direct candor.",
        confidence=0.84,
        status="proposed",
        source_pattern_ids=("pattern-higher-candor",),
        source_situation_ids=("sit-dir-1", "sit-dir-2"),
    )

    record = event.to_record()

    assert SupportProfileUpdateEvent.from_record(record) == event
    assert record["scope_type"] == "context"
    assert record["scope_id"] == "direction_reflect"


def test_bounded_adaptation_auto_updates_arc_and_context_support_values_from_similar_successful_situations() -> None:
    """Repeated strong similar situations should produce low-risk scoped support updates with audit events."""

    current_arc_situation = LearningSituation(
        situation_id="sit-current-arc",
        session_id="sess-current",
        recorded_at=datetime(2026, 3, 30, 17, 0, tzinfo=UTC),
        turn_text="Let's keep moving on the Web UI cleanup.",
        embedding=(0.0, 1.0, 0.0, 0.0),
        need="activate",
        response_mode="execute",
        subject_refs=("arc:webui_cleanup",),
        arc_id="webui_cleanup",
        behavior_contract_summary="Keep the next move narrow.",
        intervention_family="narrow",
        support_values_applied={"option_bandwidth": "few"},
    )
    similar_situations = [
        (
            LearningSituation(
                situation_id="sit-docs-1",
                session_id="sess-prior-1",
                recorded_at=datetime(2026, 3, 30, 16, 0, tzinfo=UTC),
                turn_text="Let's continue the docs refresh and just pick one next step.",
                embedding=(0.0, 0.98, 0.02, 0.0),
                need="activate",
                response_mode="execute",
                subject_refs=("arc:docs_refresh",),
                arc_id="docs_refresh",
                behavior_contract_summary="Keep the next move narrow.",
                intervention_family="narrow",
                support_values_applied={"option_bandwidth": "single"},
                user_response_signals=("resonance",),
                outcome_signals=("next_step_chosen",),
            ),
            0.95,
        ),
        (
            LearningSituation(
                situation_id="sit-admin-1",
                session_id="sess-prior-2",
                recorded_at=datetime(2026, 3, 30, 16, 10, tzinfo=UTC),
                turn_text="Let's continue the admin cleanup and just pick one next step.",
                embedding=(0.0, 0.96, 0.04, 0.0),
                need="activate",
                response_mode="execute",
                subject_refs=("arc:admin_cleanup",),
                arc_id="admin_cleanup",
                behavior_contract_summary="Keep the next move narrow.",
                intervention_family="narrow",
                support_values_applied={"option_bandwidth": "single"},
                user_response_signals=("commitment",),
                outcome_signals=("resume_ready",),
            ),
            0.91,
        ),
    ]
    existing_values = {
        ("support", "option_bandwidth", "arc", "webui_cleanup"): SupportProfileValue(
            registry="support",
            dimension="option_bandwidth",
            scope=SupportProfileScope(type="arc", id="webui_cleanup"),
            value="few",
            status="confirmed",
            confidence=0.92,
            source="explicit",
            created_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        ),
    }

    result = derive_bounded_adaptation(
        current_situation=current_arc_situation,
        similar_situations=similar_situations,
        existing_profile_values=existing_values,
        now=datetime(2026, 3, 30, 17, 5, tzinfo=UTC),
    )

    assert len(result.profile_updates) == 1
    assert result.profile_updates[0].scope == SupportProfileScope(type="arc", id="webui_cleanup")
    assert result.profile_updates[0].dimension == "option_bandwidth"
    assert result.profile_updates[0].value == "single"
    assert len(result.update_events) == 1
    assert result.update_events[0].status == "applied"
    assert result.update_events[0].old_value == "few"
    assert result.update_events[0].new_value == "single"

    current_context_situation = LearningSituation(
        situation_id="sit-current-context",
        session_id="sess-current",
        recorded_at=datetime(2026, 3, 30, 17, 20, tzinfo=UTC),
        turn_text="Help me decide between these two options.",
        embedding=(0.1, 0.0, 1.0, 0.0),
        need="decide",
        response_mode="decide",
        subject_refs=("current_turn",),
        behavior_contract_summary="Compare the options directly.",
        intervention_family="compare",
        support_values_applied={"recommendation_forcefulness": "medium"},
    )
    context_result = derive_bounded_adaptation(
        current_situation=current_context_situation,
        similar_situations=[
            (
                LearningSituation(
                    situation_id="sit-decide-1",
                    session_id="sess-prior-3",
                    recorded_at=datetime(2026, 3, 30, 16, 30, tzinfo=UTC),
                    turn_text="Help me decide and be direct about the recommendation.",
                    embedding=(0.08, 0.0, 0.96, 0.0),
                    need="decide",
                    response_mode="decide",
                    subject_refs=("current_turn",),
                    behavior_contract_summary="Compare and recommend directly.",
                    intervention_family="recommend",
                    support_values_applied={"recommendation_forcefulness": "high"},
                    user_response_signals=("clarity",),
                    outcome_signals=("boundary_decided",),
                ),
                0.93,
            ),
            (
                LearningSituation(
                    situation_id="sit-decide-2",
                    session_id="sess-prior-4",
                    recorded_at=datetime(2026, 3, 30, 16, 40, tzinfo=UTC),
                    turn_text="Recommend one option clearly.",
                    embedding=(0.05, 0.0, 0.94, 0.0),
                    need="decide",
                    response_mode="decide",
                    subject_refs=("current_turn",),
                    behavior_contract_summary="Recommend one option directly.",
                    intervention_family="recommend",
                    support_values_applied={"recommendation_forcefulness": "high"},
                    user_response_signals=("resonance",),
                    outcome_signals=("comparison_started",),
                ),
                0.89,
            ),
        ],
        existing_profile_values={},
        now=datetime(2026, 3, 30, 17, 25, tzinfo=UTC),
    )

    assert len(context_result.profile_updates) == 1
    assert context_result.profile_updates[0].scope == SupportProfileScope(type="context", id="decide")
    assert context_result.profile_updates[0].dimension == "recommendation_forcefulness"
    assert context_result.profile_updates[0].value == "high"


def test_bounded_adaptation_surfaces_broader_changes_as_patterns_or_reviewable_candidates() -> None:
    """Broader relational changes should stay surfaced instead of silently auto-updating."""

    current_situation = LearningSituation(
        situation_id="sit-direction-current",
        session_id="sess-current",
        recorded_at=datetime(2026, 3, 30, 18, 0, tzinfo=UTC),
        turn_text="Tell me honestly what you think about this direction.",
        embedding=(1.0, 0.0, 0.0, 0.0),
        need="calibrate",
        response_mode="direction_reflect",
        subject_refs=("direction",),
        behavior_contract_summary="Be candid and grounded.",
        intervention_family="challenge",
        relational_values_applied={"candor": "medium"},
    )
    existing_values = {
        ("relational", "candor", "context", "direction_reflect"): SupportProfileValue(
            registry="relational",
            dimension="candor",
            scope=SupportProfileScope(type="context", id="direction_reflect"),
            value="medium",
            status="confirmed",
            confidence=0.9,
            source="explicit",
            created_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        ),
    }

    result = derive_bounded_adaptation(
        current_situation=current_situation,
        similar_situations=[
            (
                LearningSituation(
                    situation_id="sit-direction-1",
                    session_id="sess-prior-1",
                    recorded_at=datetime(2026, 3, 30, 17, 10, tzinfo=UTC),
                    turn_text="Be more direct with me here.",
                    embedding=(0.98, 0.0, 0.0, 0.0),
                    need="calibrate",
                    response_mode="direction_reflect",
                    subject_refs=("direction",),
                    behavior_contract_summary="Be candid and grounded.",
                    intervention_family="challenge",
                    relational_values_applied={"candor": "high"},
                    user_response_signals=("clarity",),
                    outcome_signals=("deepening",),
                ),
                0.94,
            ),
            (
                LearningSituation(
                    situation_id="sit-direction-2",
                    session_id="sess-prior-2",
                    recorded_at=datetime(2026, 3, 30, 17, 20, tzinfo=UTC),
                    turn_text="I need you to be more honest here.",
                    embedding=(0.96, 0.0, 0.0, 0.0),
                    need="calibrate",
                    response_mode="direction_reflect",
                    subject_refs=("direction",),
                    behavior_contract_summary="Be candid and grounded.",
                    intervention_family="challenge",
                    relational_values_applied={"candor": "high"},
                    user_response_signals=("resonance",),
                    outcome_signals=("deepening",),
                ),
                0.91,
            ),
        ],
        existing_profile_values=existing_values,
        now=datetime(2026, 3, 30, 18, 5, tzinfo=UTC),
    )

    assert result.profile_updates == ()
    assert len(result.patterns) == 1
    assert result.patterns[0].kind == "support_preference"
    assert result.patterns[0].status == "candidate"
    assert result.patterns[0].relational_overrides == {"candor": "high"}
    assert len(result.update_events) == 1
    assert result.update_events[0].status == "proposed"
    assert result.update_events[0].dimension == "candor"
    assert result.update_events[0].new_value == "high"


@pytest.mark.asyncio
async def test_apply_bounded_adaptation_persists_learning_situation_updates_patterns_and_events() -> None:
    """Applying bounded adaptation should persist the current situation plus all derived artifacts."""

    store = FakeLearningStore()
    current_situation = LearningSituation(
        situation_id="sit-current-persist",
        session_id="sess-current",
        recorded_at=datetime(2026, 3, 30, 19, 0, tzinfo=UTC),
        turn_text="Let's continue and keep this as a single next step.",
        embedding=(0.0, 1.0, 0.0, 0.0),
        need="activate",
        response_mode="execute",
        subject_refs=("arc:webui_cleanup",),
        arc_id="webui_cleanup",
        behavior_contract_summary="Keep the next move narrow.",
        intervention_family="narrow",
        relational_values_applied={"candor": "medium"},
        support_values_applied={"option_bandwidth": "few"},
    )
    existing_values = {
        ("support", "option_bandwidth", "arc", "webui_cleanup"): SupportProfileValue(
            registry="support",
            dimension="option_bandwidth",
            scope=SupportProfileScope(type="arc", id="webui_cleanup"),
            value="few",
            status="confirmed",
            confidence=0.9,
            source="explicit",
            created_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        ),
        ("relational", "candor", "context", "execute"): SupportProfileValue(
            registry="relational",
            dimension="candor",
            scope=SupportProfileScope(type="context", id="execute"),
            value="medium",
            status="confirmed",
            confidence=0.9,
            source="explicit",
            created_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        ),
    }

    result = await apply_bounded_adaptation(
        store=store,
        current_situation=current_situation,
        similar_situations=[
            (
                LearningSituation(
                    situation_id="sit-sim-1",
                    session_id="sess-prior-1",
                    recorded_at=datetime(2026, 3, 30, 18, 40, tzinfo=UTC),
                    turn_text="Just give me one next step and be direct.",
                    embedding=(0.0, 0.98, 0.02, 0.0),
                    need="activate",
                    response_mode="execute",
                    subject_refs=("arc:docs_refresh",),
                    arc_id="docs_refresh",
                    behavior_contract_summary="Keep the next move narrow.",
                    intervention_family="narrow",
                    relational_values_applied={"candor": "high"},
                    support_values_applied={"option_bandwidth": "single"},
                    user_response_signals=("clarity",),
                    outcome_signals=("next_step_chosen",),
                ),
                0.94,
            ),
            (
                LearningSituation(
                    situation_id="sit-sim-2",
                    session_id="sess-prior-2",
                    recorded_at=datetime(2026, 3, 30, 18, 45, tzinfo=UTC),
                    turn_text="One next step works best here and honesty helps.",
                    embedding=(0.0, 0.96, 0.04, 0.0),
                    need="activate",
                    response_mode="execute",
                    subject_refs=("arc:admin_cleanup",),
                    arc_id="admin_cleanup",
                    behavior_contract_summary="Keep the next move narrow.",
                    intervention_family="narrow",
                    relational_values_applied={"candor": "high"},
                    support_values_applied={"option_bandwidth": "single"},
                    user_response_signals=("resonance",),
                    outcome_signals=("resume_ready",),
                ),
                0.91,
            ),
        ],
        existing_profile_values=existing_values,
        now=datetime(2026, 3, 30, 19, 5, tzinfo=UTC),
    )

    assert store.learning_situations == [current_situation]
    assert store.profile_values == list(result.profile_updates)
    assert store.patterns == list(result.patterns)
    assert store.update_events == list(result.update_events)
    assert len(store.profile_values) == 1
    assert len(store.patterns) == 1
    assert len(store.update_events) == 2


@pytest.mark.asyncio
async def test_support_learning_core_links_intervention_situation_pattern_and_update_event_without_episode_ownership() -> None:
    """The learning core should write situations first, then change a future contract without episode ownership."""

    store = FakeLearningStore()
    current_situation = LearningSituation(
        situation_id="sit-proof-current",
        session_id="sess-proof",
        recorded_at=datetime(2026, 3, 30, 20, 0, tzinfo=UTC),
        turn_text="Let's continue the Web UI cleanup and keep this to one next step.",
        embedding=(0.0, 1.0, 0.0, 0.0),
        need="activate",
        response_mode="execute",
        subject_refs=("arc:webui_cleanup",),
        arc_id="webui_cleanup",
        intervention_ids=("int-proof-1",),
        behavior_contract_summary="Keep the next move narrow and direct.",
        intervention_family="narrow",
        relational_values_applied={"candor": "medium"},
        support_values_applied={"option_bandwidth": "few"},
    )
    existing_values = {
        ("support", "option_bandwidth", "arc", "webui_cleanup"): SupportProfileValue(
            registry="support",
            dimension="option_bandwidth",
            scope=SupportProfileScope(type="arc", id="webui_cleanup"),
            value="few",
            status="confirmed",
            confidence=0.9,
            source="explicit",
            created_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        ),
        ("relational", "candor", "context", "execute"): SupportProfileValue(
            registry="relational",
            dimension="candor",
            scope=SupportProfileScope(type="context", id="execute"),
            value="medium",
            status="confirmed",
            confidence=0.9,
            source="explicit",
            created_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        ),
    }

    result = await apply_bounded_adaptation(
        store=store,
        current_situation=current_situation,
        similar_situations=[
            (
                LearningSituation(
                    situation_id="sit-proof-1",
                    session_id="sess-proof-1",
                    recorded_at=datetime(2026, 3, 30, 19, 30, tzinfo=UTC),
                    turn_text="One next step and stronger honesty worked here.",
                    embedding=(0.0, 0.98, 0.02, 0.0),
                    need="activate",
                    response_mode="execute",
                    subject_refs=("arc:docs_refresh",),
                    arc_id="docs_refresh",
                    behavior_contract_summary="Keep the next move narrow and direct.",
                    intervention_family="narrow",
                    relational_values_applied={"candor": "high"},
                    support_values_applied={"option_bandwidth": "single"},
                    user_response_signals=("clarity",),
                    outcome_signals=("next_step_chosen",),
                ),
                0.94,
            ),
            (
                LearningSituation(
                    situation_id="sit-proof-2",
                    session_id="sess-proof-2",
                    recorded_at=datetime(2026, 3, 30, 19, 35, tzinfo=UTC),
                    turn_text="Single-step next moves and directness worked here too.",
                    embedding=(0.0, 0.96, 0.04, 0.0),
                    need="activate",
                    response_mode="execute",
                    subject_refs=("arc:admin_cleanup",),
                    arc_id="admin_cleanup",
                    behavior_contract_summary="Keep the next move narrow and direct.",
                    intervention_family="narrow",
                    relational_values_applied={"candor": "high"},
                    support_values_applied={"option_bandwidth": "single"},
                    user_response_signals=("resonance",),
                    outcome_signals=("resume_ready",),
                ),
                0.91,
            ),
        ],
        existing_profile_values=existing_values,
        now=datetime(2026, 3, 30, 20, 5, tzinfo=UTC),
    )

    assert store.learning_situations[0].intervention_ids == ("int-proof-1",)
    assert result.profile_updates[0].scope == SupportProfileScope(type="arc", id="webui_cleanup")
    assert result.patterns[0].status == "candidate"

    resolved_policy = await resolve_support_policy(
        store=FakePolicyValueStore(store.profile_values),  # type: ignore[arg-type]
        assessment=SupportTurnAssessment(
            need="activate",
            subjects=(ResolvedSubject(kind="arc", id="webui_cleanup"),),
        ),
        response_mode="execute",
        patterns=tuple(
            SupportPolicyPattern(
                name=pattern.claim,
                relational_overrides=pattern.relational_overrides,
                support_overrides=pattern.support_overrides,
            )
            for pattern in store.patterns
        ),
    )
    behavior_contract = compile_support_behavior_contract(resolved_policy)

    assert behavior_contract.support_values["option_bandwidth"] == "single"
    assert behavior_contract.relational_values["candor"] == "high"

