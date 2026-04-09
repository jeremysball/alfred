"""Tests for PRD #169 support reflection contracts and bounded read/action surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from alfred.memory.support_learning import (
    LearningSituation,
    SupportLedgerUpdateEvent,
    SupportPattern,
    SupportProfileUpdateEvent,
    SupportValueLedgerEntry,
)
from alfred.memory.support_memory import LifeDomain, OperationalArc
from alfred.memory.support_profile import SupportProfileScope, SupportProfileValue
from alfred.support_policy import ResolvedSubject, SupportTurnAssessment
from alfred.support_reflection import (
    ConfirmPatternAction,
    CorrectProfileValueAction,
    RejectPatternAction,
    ResetProfileValueAction,
    ScopeLimitProfileValueAction,
    SupportReflectionRuntime,
    review_card_from_pattern,
)


@dataclass
class FakeReflectionStore:
    """Explicit fake store for support-reflection contract tests."""

    values: list[SupportProfileValue] = field(default_factory=list)
    runtime_patterns: list[SupportPattern] = field(default_factory=list)
    inspection_patterns: list[SupportPattern] = field(default_factory=list)
    update_events: list[SupportProfileUpdateEvent] = field(default_factory=list)
    value_ledger_entries: list[SupportValueLedgerEntry] = field(default_factory=list)
    ledger_update_events: list[SupportLedgerUpdateEvent] = field(default_factory=list)
    learning_situations: list[LearningSituation] = field(default_factory=list)
    similar_situations: list[tuple[LearningSituation, float]] = field(default_factory=list)
    arcs: list[OperationalArc] = field(default_factory=list)
    domains: list[LifeDomain] = field(default_factory=list)

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

    async def get_support_profile_value(
        self,
        registry: str,
        dimension: str,
        scope: SupportProfileScope,
    ) -> SupportProfileValue | None:
        for value in self.values:
            if value.registry == registry and value.dimension == dimension and value.scope == scope:
                return value
        return None

    async def list_support_patterns_for_runtime(
        self,
        *,
        response_mode: str,
        arc_id: str | None = None,
    ) -> list[SupportPattern]:
        del response_mode, arc_id
        return list(self.runtime_patterns)

    async def list_support_patterns_for_inspection(
        self,
        *,
        statuses: tuple[str, ...] = ("candidate", "confirmed"),
        limit: int = 12,
    ) -> list[SupportPattern]:
        return [pattern for pattern in self.inspection_patterns if pattern.status in statuses][:limit]

    async def get_support_pattern(self, pattern_id: str) -> SupportPattern | None:
        for pattern in self.inspection_patterns + self.runtime_patterns:
            if pattern.pattern_id == pattern_id:
                return pattern
        return None

    async def list_support_profile_update_events(
        self,
        *,
        limit: int = 12,
    ) -> list[SupportProfileUpdateEvent]:
        return list(self.update_events)[:limit]

    async def get_support_profile_update_event(self, event_id: str) -> SupportProfileUpdateEvent | None:
        for event in self.update_events:
            if event.event_id == event_id:
                return event
        return None

    async def list_support_value_ledger_entries(self) -> list[SupportValueLedgerEntry]:
        return list(self.value_ledger_entries)

    async def list_support_ledger_update_events(self) -> list[SupportLedgerUpdateEvent]:
        return list(self.ledger_update_events)

    async def list_recent_learning_situations(self, *, limit: int = 6) -> list[LearningSituation]:
        return list(self.learning_situations)[:limit]

    async def list_learning_situations_by_ids(self, situation_ids: tuple[str, ...]) -> list[LearningSituation]:
        wanted = set(situation_ids)
        return [situation for situation in self.learning_situations if situation.situation_id in wanted]

    async def search_learning_situations(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 5,
        response_mode: str | None = None,
        need: str | None = None,
    ) -> list[tuple[LearningSituation, float]]:
        del query_embedding
        matches = list(self.similar_situations)
        if response_mode is not None:
            matches = [match for match in matches if match[0].response_mode == response_mode]
        if need is not None:
            matches = [match for match in matches if match[0].need == need]
        return matches[:top_k]

    async def save_support_pattern(self, pattern: SupportPattern) -> None:
        self.runtime_patterns = [existing for existing in self.runtime_patterns if existing.pattern_id != pattern.pattern_id]
        self.inspection_patterns = [existing for existing in self.inspection_patterns if existing.pattern_id != pattern.pattern_id]
        self.runtime_patterns.append(pattern)
        self.inspection_patterns.append(pattern)

    async def save_support_profile_update_event(self, event: SupportProfileUpdateEvent) -> None:
        self.update_events = [existing for existing in self.update_events if existing.event_id != event.event_id]
        self.update_events.append(event)
        self.update_events.sort(key=lambda item: (item.timestamp, item.event_id), reverse=True)

    async def save_support_profile_value(self, profile_value: SupportProfileValue) -> None:
        self.values = [
            existing
            for existing in self.values
            if not (
                existing.registry == profile_value.registry
                and existing.dimension == profile_value.dimension
                and existing.scope == profile_value.scope
            )
        ]
        self.values.append(profile_value)

    async def delete_support_profile_value(
        self,
        registry: str,
        dimension: str,
        scope: SupportProfileScope,
    ) -> None:
        self.values = [
            existing
            for existing in self.values
            if not (
                existing.registry == registry
                and existing.dimension == dimension
                and existing.scope == scope
            )
        ]

    async def list_resume_arcs(self, limit: int = 12) -> list[OperationalArc]:
        return list(self.arcs)[:limit]

    async def list_active_life_domains(self, limit: int = 6) -> list[LifeDomain]:
        return list(self.domains)[:limit]



def _ts(hour: int, minute: int) -> datetime:
    return datetime(2026, 4, 5, hour, minute, tzinfo=UTC)



def _make_pattern(
    *,
    pattern_id: str,
    kind: str,
    status: str,
    scope: SupportProfileScope,
    claim: str,
    confidence: float = 0.84,
    supporting_ids: tuple[str, ...] = ("sit-1", "sit-2"),
    support_overrides: dict[str, str] | None = None,
    relational_overrides: dict[str, str] | None = None,
) -> SupportPattern:
    return SupportPattern(
        pattern_id=pattern_id,
        kind=kind,  # type: ignore[arg-type]
        scope=scope,
        status=status,  # type: ignore[arg-type]
        claim=claim,
        confidence=confidence,
        created_at=_ts(9, 0),
        updated_at=_ts(10, 0),
        supporting_situation_ids=supporting_ids,
        support_overrides=support_overrides or {},
        relational_overrides=relational_overrides or {},
    )



def _make_learning_situation(*, situation_id: str, arc_id: str | None = None) -> LearningSituation:
    return LearningSituation(
        situation_id=situation_id,
        session_id="sess-1",
        recorded_at=_ts(8, 0),
        turn_text="Keep the next move narrow and direct.",
        embedding=(0.1, 0.2, 0.3),
        need="activate",
        response_mode="execute",
        subject_refs=("arc:webui_cleanup",) if arc_id else (),
        arc_id=arc_id,
        intervention_ids=("int-1",),
        behavior_contract_summary="Keep the next move narrow and direct.",
        intervention_family="narrow",
        support_values_applied={"option_bandwidth": "single"},
        relational_values_applied={"candor": "high"},
        user_response_signals=("clarity",),
        outcome_signals=("next_step_chosen",),
    )


def _make_value_ledger_entry(
    *,
    value_id: str,
    registry: str,
    dimension: str,
    scope: SupportProfileScope,
    value: str,
    status: str,
    confidence: float,
    evidence_count: int,
    contradiction_count: int,
    updated_at: datetime,
) -> SupportValueLedgerEntry:
    return SupportValueLedgerEntry(
        value_id=value_id,
        registry=registry,  # type: ignore[arg-type]
        dimension=dimension,
        scope=scope,
        value=value,
        status=status,  # type: ignore[arg-type]
        source="case_promotion",
        confidence=confidence,
        evidence_count=evidence_count,
        contradiction_count=contradiction_count,
        last_case_id="case-1",
        created_at=_ts(7, 30),
        updated_at=updated_at,
        why="Derived from finalized learning cases.",
    )



def _make_ledger_update_event(
    *,
    event_id: str,
    entity_id: str,
    registry: str,
    dimension: str,
    scope: SupportProfileScope,
    new_status: str,
    new_value: str,
    created_at: datetime,
) -> SupportLedgerUpdateEvent:
    return SupportLedgerUpdateEvent(
        event_id=event_id,
        entity_type="value",
        entity_id=entity_id,
        registry=registry,  # type: ignore[arg-type]
        dimension_or_kind=dimension,
        scope=scope,
        old_status=None,
        new_status=new_status,  # type: ignore[arg-type]
        old_value=None,
        new_value=new_value,
        trigger_case_ids=("case-1", "case-2"),
        reason="Evidence threshold met.",
        confidence=0.82,
        created_at=created_at,
    )



def _make_runtime_store() -> FakeReflectionStore:
    execute_scope = SupportProfileScope(type="context", id="execute")
    arc_scope = SupportProfileScope(type="arc", id="webui_cleanup")
    global_scope = SupportProfileScope(type="global", id="user")
    return FakeReflectionStore(
        values=[
            SupportProfileValue(
                registry="support",
                dimension="option_bandwidth",
                scope=execute_scope,
                value="few",
                status="confirmed",
                confidence=0.9,
                source="explicit",
                created_at=_ts(7, 0),
                updated_at=_ts(7, 0),
            ),
            SupportProfileValue(
                registry="support",
                dimension="planning_granularity",
                scope=arc_scope,
                value="minimal",
                status="confirmed",
                confidence=0.91,
                source="corrected",
                created_at=_ts(7, 10),
                updated_at=_ts(7, 10),
            ),
            SupportProfileValue(
                registry="relational",
                dimension="candor",
                scope=execute_scope,
                value="medium",
                status="confirmed",
                confidence=0.88,
                source="explicit",
                created_at=_ts(7, 20),
                updated_at=_ts(7, 20),
            ),
        ],
        runtime_patterns=[
            _make_pattern(
                pattern_id="pattern-runtime-1",
                kind="support_preference",
                status="confirmed",
                scope=execute_scope,
                claim="Single-step next moves work better here.",
                support_overrides={"option_bandwidth": "single"},
            )
        ],
        inspection_patterns=[
            _make_pattern(
                pattern_id="pattern-runtime-1",
                kind="support_preference",
                status="confirmed",
                scope=execute_scope,
                claim="Single-step next moves work better here.",
                support_overrides={"option_bandwidth": "single"},
            ),
            _make_pattern(
                pattern_id="pattern-candidate-1",
                kind="direction_theme",
                status="candidate",
                scope=global_scope,
                claim="External legibility and felt aliveness keep pulling in different directions.",
            ),
        ],
        update_events=[
            SupportProfileUpdateEvent(
                event_id="upd-1",
                timestamp=_ts(10, 30),
                registry="relational",
                dimension="candor",
                scope=execute_scope,
                old_value="medium",
                new_value="high",
                reason="Repeated strong calibration situations responded better to direct candor.",
                confidence=0.82,
                status="proposed",
                source_pattern_ids=("pattern-candidate-1",),
                source_situation_ids=("sit-1", "sit-2"),
            )
        ],
        learning_situations=[
            _make_learning_situation(situation_id="sit-1", arc_id="webui_cleanup"),
            _make_learning_situation(situation_id="sit-2", arc_id="webui_cleanup"),
        ],
        similar_situations=[
            (_make_learning_situation(situation_id="sit-1", arc_id="webui_cleanup"), 0.94),
            (_make_learning_situation(situation_id="sit-2", arc_id="webui_cleanup"), 0.91),
        ],
        arcs=[
            OperationalArc(
                arc_id="webui_cleanup",
                title="Web UI cleanup",
                kind="project",
                status="active",
                salience=0.91,
                created_at=_ts(6, 0),
                updated_at=_ts(10, 0),
                primary_domain_id="work",
                last_active_at=_ts(10, 5),
            )
        ],
        domains=[
            LifeDomain(
                domain_id="work",
                name="Work",
                status="active",
                salience=0.95,
                created_at=_ts(6, 0),
                updated_at=_ts(10, 0),
            )
        ],
    )



def test_review_card_derives_from_support_pattern_without_creating_parallel_truth() -> None:
    """Patterns should derive one user-facing card without becoming a second durable truth system."""

    pattern = _make_pattern(
        pattern_id="pattern-direction-1",
        kind="direction_theme",
        status="candidate",
        scope=SupportProfileScope(type="global", id="user"),
        claim="External legibility and felt aliveness keep pulling in different directions.",
        supporting_ids=("sit-204", "sit-213", "sit-227"),
    )

    card = review_card_from_pattern(pattern)

    assert card.source_pattern_id == "pattern-direction-1"
    assert card.card_kind == "direction_theme"
    assert card.scope == SupportProfileScope(type="global", id="user")
    assert card.status == "candidate"
    assert card.evidence_refs == ("sit-204", "sit-213", "sit-227")
    assert card.statement == pattern.claim
    assert "Confirm" in card.proposed_action



def test_review_card_rejects_unknown_card_kinds_and_missing_next_actions() -> None:
    """Review cards should stay bounded and action-linked."""

    from alfred.support_reflection import ReviewCard

    with pytest.raises(ValueError, match="Unsupported review card kind"):
        ReviewCard(
            card_id="card-1",
            source_pattern_id="pattern-1",
            card_kind="mystery",  # type: ignore[arg-type]
            scope=SupportProfileScope(type="global", id="user"),
            status="candidate",
            statement="Something vague is happening.",
            confidence=0.7,
            evidence_refs=("sit-1",),
            proposed_action="Confirm or reject it.",
        )

    with pytest.raises(ValueError, match="proposed_action"):
        ReviewCard(
            card_id="card-2",
            source_pattern_id="pattern-2",
            card_kind="blocker",
            scope=SupportProfileScope(type="global", id="user"),
            status="candidate",
            statement="Ambiguity keeps stalling work threads.",
            confidence=0.7,
            evidence_refs=("sit-1",),
            proposed_action="",
        )


@pytest.mark.asyncio
async def test_support_inspection_snapshot_includes_v2_value_ledger_entries_and_recent_ledger_events() -> None:
    store = _make_runtime_store()
    execute_scope = SupportProfileScope(type="context", id="execute")
    arc_scope = SupportProfileScope(type="arc", id="webui_cleanup")

    store.value_ledger_entries = [
        _make_value_ledger_entry(
            value_id="val-1",
            registry="relational",
            dimension="candor",
            scope=execute_scope,
            value="medium",
            status="shadow",
            confidence=0.62,
            evidence_count=1,
            contradiction_count=0,
            updated_at=_ts(11, 0),
        ),
        _make_value_ledger_entry(
            value_id="val-2",
            registry="support",
            dimension="option_bandwidth",
            scope=execute_scope,
            value="single",
            status="active_auto",
            confidence=0.81,
            evidence_count=3,
            contradiction_count=0,
            updated_at=_ts(11, 5),
        ),
        _make_value_ledger_entry(
            value_id="val-3",
            registry="support",
            dimension="planning_granularity",
            scope=arc_scope,
            value="minimal",
            status="confirmed",
            confidence=0.93,
            evidence_count=4,
            contradiction_count=0,
            updated_at=_ts(11, 10),
        ),
    ]

    store.ledger_update_events = [
        _make_ledger_update_event(
            event_id="led-1",
            entity_id="val-1",
            registry="relational",
            dimension="candor",
            scope=execute_scope,
            new_status="shadow",
            new_value="medium",
            created_at=_ts(10, 0),
        ),
        _make_ledger_update_event(
            event_id="led-2",
            entity_id="val-2",
            registry="support",
            dimension="option_bandwidth",
            scope=execute_scope,
            new_status="active_auto",
            new_value="single",
            created_at=_ts(10, 30),
        ),
    ]

    runtime = SupportReflectionRuntime(store=store)  # type: ignore[arg-type]

    snapshot = await runtime.build_inspection_snapshot(response_mode="execute", arc_id="webui_cleanup")

    value_entries = snapshot.learned_state.value_ledger_entries
    assert [entry.registry for entry in value_entries] == ["relational", "support", "support"]
    assert value_entries[0].dimension == "candor"
    assert value_entries[0].status == "shadow"
    assert value_entries[1].dimension == "option_bandwidth"
    assert value_entries[1].value == "single"

    summary = snapshot.learned_state.value_ledger_summary
    assert summary["total"] == 3
    assert summary["counts_by_registry"] == {"relational": 1, "support": 2}
    assert summary["counts_by_status"]["shadow"] == 1
    assert summary["counts_by_status"]["active_auto"] == 1
    assert summary["counts_by_status"]["confirmed"] == 1

    recent_events = snapshot.learned_state.recent_ledger_update_events
    assert [event.event_id for event in recent_events] == ["led-2", "led-1"]
    assert recent_events[0].new_status == "active_auto"


@pytest.mark.asyncio
async def test_support_inspection_snapshot_reads_runtime_and_learned_state_from_one_source_of_truth() -> None:
    """The inspection snapshot should reuse the same runtime truth Alfred already resolves."""

    store = _make_runtime_store()
    runtime = SupportReflectionRuntime(store=store)  # type: ignore[arg-type]

    snapshot = await runtime.build_inspection_snapshot(response_mode="execute", arc_id="webui_cleanup")

    assert snapshot.request.response_mode == "execute"
    assert snapshot.active_runtime_state.active_arc_id == "webui_cleanup"
    assert snapshot.active_runtime_state.effective_support_values["option_bandwidth"] == "single"
    assert snapshot.active_runtime_state.effective_support_values["planning_granularity"] == "minimal"
    assert snapshot.active_runtime_state.effective_relational_values["candor"] == "medium"
    assert snapshot.active_runtime_state.active_patterns[0].pattern_id == "pattern-runtime-1"
    assert snapshot.learned_state.candidate_patterns[0].pattern_id == "pattern-candidate-1"
    assert snapshot.learned_state.confirmed_patterns[0].pattern_id == "pattern-runtime-1"
    assert snapshot.learned_state.recent_update_events[0].event_id == "upd-1"
    assert snapshot.learned_state.recent_interventions[0].situation_id == "sit-1"
    assert snapshot.active_domains[0].domain_id == "work"
    assert snapshot.active_arcs[0].arc_id == "webui_cleanup"


@pytest.mark.asyncio
async def test_support_inspection_drilldowns_explain_pattern_update_event_and_effective_value_details() -> None:
    """Inspection drill-downs should expose the durable records behind the snapshot."""

    store = _make_runtime_store()
    runtime = SupportReflectionRuntime(store=store)  # type: ignore[arg-type]

    pattern_detail = await runtime.get_pattern_detail("pattern-candidate-1")
    update_detail = await runtime.get_update_event_detail("upd-1")
    explanation = await runtime.explain_effective_value(
        registry="support",
        dimension="option_bandwidth",
        response_mode="execute",
        arc_id="webui_cleanup",
    )

    assert pattern_detail is not None
    assert pattern_detail.pattern.pattern_id == "pattern-candidate-1"
    assert [s.situation_id for s in pattern_detail.supporting_situations] == ["sit-1", "sit-2"]

    assert update_detail is not None
    assert update_detail.event.event_id == "upd-1"
    assert update_detail.source_patterns[0].pattern_id == "pattern-candidate-1"
    assert [s.situation_id for s in update_detail.source_situations] == ["sit-1", "sit-2"]

    assert explanation.winning_value == "single"
    assert explanation.source_kind == "pattern"
    assert explanation.source_pattern_ids == ("pattern-runtime-1",)
    assert explanation.source_scope == SupportProfileScope(type="context", id="execute")



def test_support_correction_actions_allow_pattern_confirmation_and_profile_value_edits_only() -> None:
    """The correction contract should make pattern-text edits impossible in v1."""

    confirm = ConfirmPatternAction(pattern_id="pattern-1", reason="Yes, that pattern is real.")
    reject = RejectPatternAction(pattern_id="pattern-2", reason="No, that does not fit.")
    correct = CorrectProfileValueAction(
        registry="support",
        dimension="option_bandwidth",
        scope=SupportProfileScope(type="context", id="execute"),
        new_value="single",
        reason="Be narrower in execute mode.",
    )
    reset = ResetProfileValueAction(
        registry="relational",
        dimension="candor",
        scope=SupportProfileScope(type="context", id="execute"),
        reason="Go back to the default here.",
    )
    scope_limit = ScopeLimitProfileValueAction(
        registry="support",
        dimension="planning_granularity",
        source_scope=SupportProfileScope(type="global", id="user"),
        target_scope=SupportProfileScope(type="arc", id="webui_cleanup"),
        reason="Only keep this narrower for the Web UI cleanup arc.",
    )

    assert confirm.pattern_id == "pattern-1"
    assert reject.pattern_id == "pattern-2"
    assert correct.new_value == "single"
    assert reset.scope.type == "context"
    assert scope_limit.target_scope.type == "arc"

    with pytest.raises(ValueError, match="new_value"):
        CorrectProfileValueAction(
            registry="support",
            dimension="option_bandwidth",
            scope=SupportProfileScope(type="context", id="execute"),
            new_value="",
            reason="missing",
        )



def test_support_correction_actions_capture_auditable_targets_and_requested_scope_changes() -> None:
    """Typed actions should preserve target identity and audit metadata for later application."""

    action = ScopeLimitProfileValueAction(
        registry="support",
        dimension="planning_granularity",
        source_scope=SupportProfileScope(type="global", id="user"),
        target_scope=SupportProfileScope(type="context", id="execute"),
        reason="Only keep this narrower in execute mode.",
    )

    assert action.registry == "support"
    assert action.dimension == "planning_granularity"
    assert action.source_scope == SupportProfileScope(type="global", id="user")
    assert action.target_scope == SupportProfileScope(type="context", id="execute")
    assert "execute mode" in action.reason


@pytest.mark.asyncio
async def test_reflection_contracts_keep_patterns_durable_cards_derived_and_value_edits_auditable() -> None:
    """The milestone proof should keep runtime truth, learned truth, and reflection outputs separate."""

    store = _make_runtime_store()
    runtime = SupportReflectionRuntime(store=store)  # type: ignore[arg-type]
    pattern = await runtime.get_pattern_detail("pattern-runtime-1")
    snapshot = await runtime.build_inspection_snapshot(response_mode="execute", arc_id="webui_cleanup")
    card = review_card_from_pattern(store.runtime_patterns[0])
    action = CorrectProfileValueAction(
        registry="support",
        dimension="option_bandwidth",
        scope=SupportProfileScope(type="context", id="execute"),
        new_value="single",
        reason="Keep execute-mode options narrow.",
    )

    assert pattern is not None
    assert card.source_pattern_id == "pattern-runtime-1"
    assert snapshot.active_runtime_state.active_patterns[0].pattern_id == "pattern-runtime-1"
    assert action.dimension == "option_bandwidth"
    assert snapshot.active_runtime_state.effective_support_values["option_bandwidth"] == "single"


@pytest.mark.asyncio
async def test_reflection_runtime_loads_relevant_patterns_silently_before_considering_surfacing() -> None:
    """Loaded patterns should stay available even when only some deserve visible surfacing."""

    store = _make_runtime_store()
    runtime = SupportReflectionRuntime(store=store)  # type: ignore[arg-type]

    guidance = await runtime.build_turn_guidance(
        assessment=SupportTurnAssessment(
            need="activate",
            subjects=(ResolvedSubject(kind="arc", id="webui_cleanup"),),
        ),
        response_mode="execute",
        query_embedding=[0.1, 0.2, 0.3],
        fresh_session=False,
    )

    assert {decision.pattern.pattern_id for decision in guidance.loaded_patterns} == {
        "pattern-runtime-1",
        "pattern-candidate-1",
    }
    assert any(
        decision.pattern.pattern_id == "pattern-candidate-1" and decision.surface_level == "silent"
        for decision in guidance.loaded_patterns
    )
    assert [decision.pattern.pattern_id for decision in guidance.surfaced_patterns] == ["pattern-runtime-1"]


@pytest.mark.asyncio
async def test_reflection_runtime_distinguishes_silent_compact_and_richer_surface_levels() -> None:
    """Reflection load decisions should distinguish silent, compact, and richer surfacing."""

    store = _make_runtime_store()
    store.inspection_patterns.append(
        _make_pattern(
            pattern_id="pattern-blocker-1",
            kind="recurring_blocker",
            status="confirmed",
            scope=SupportProfileScope(type="arc", id="webui_cleanup"),
            claim="Architecture ambiguity keeps stalling the Web UI cleanup thread.",
            confidence=0.9,
            supporting_ids=("sit-1", "sit-2"),
            support_overrides={"planning_granularity": "minimal", "option_bandwidth": "single"},
        )
    )
    store.inspection_patterns.append(
        _make_pattern(
            pattern_id="pattern-calibration-1",
            kind="calibration_gap",
            status="candidate",
            scope=SupportProfileScope(type="global", id="user"),
            claim="Your stated priority and actual behavior keep diverging on this thread.",
            confidence=0.92,
            supporting_ids=("sit-1", "sit-2"),
        )
    )
    runtime = SupportReflectionRuntime(store=store)  # type: ignore[arg-type]

    execute_guidance = await runtime.build_turn_guidance(
        assessment=SupportTurnAssessment(
            need="activate",
            subjects=(ResolvedSubject(kind="arc", id="webui_cleanup"),),
        ),
        response_mode="execute",
        query_embedding=[0.1, 0.2, 0.3],
        fresh_session=True,
    )
    review_guidance = await runtime.build_turn_guidance(
        assessment=SupportTurnAssessment(
            need="calibrate",
            subjects=(ResolvedSubject(kind="current_turn", id=None),),
        ),
        response_mode="review",
        query_embedding=[0.1, 0.2, 0.3],
        fresh_session=False,
    )

    assert any(
        decision.pattern.pattern_id == "pattern-candidate-1" and decision.surface_level == "silent"
        for decision in execute_guidance.loaded_patterns
    )
    assert any(
        decision.pattern.pattern_id == "pattern-runtime-1" and decision.surface_level == "compact"
        for decision in execute_guidance.loaded_patterns
    )
    assert any(
        decision.pattern.pattern_id == "pattern-calibration-1" and decision.surface_level == "rich"
        for decision in review_guidance.loaded_patterns
    )


@pytest.mark.asyncio
async def test_reflection_runtime_prioritizes_operational_reflective_and_calibration_starts_differently() -> None:
    """Fresh-session surfacing should change priority by start type."""

    store = _make_runtime_store()
    store.inspection_patterns.append(
        _make_pattern(
            pattern_id="pattern-blocker-1",
            kind="recurring_blocker",
            status="confirmed",
            scope=SupportProfileScope(type="arc", id="webui_cleanup"),
            claim="Architecture ambiguity keeps stalling the Web UI cleanup thread.",
            confidence=0.9,
            supporting_ids=("sit-1", "sit-2"),
            support_overrides={"planning_granularity": "minimal"},
        )
    )
    store.inspection_patterns.append(
        _make_pattern(
            pattern_id="pattern-identity-1",
            kind="identity_theme",
            status="candidate",
            scope=SupportProfileScope(type="global", id="user"),
            claim="You disown desire when goals become publicly legible.",
            confidence=0.9,
            supporting_ids=("sit-1", "sit-2"),
        )
    )
    store.inspection_patterns.append(
        _make_pattern(
            pattern_id="pattern-calibration-1",
            kind="calibration_gap",
            status="candidate",
            scope=SupportProfileScope(type="global", id="user"),
            claim="Your stated priority and actual behavior keep diverging on this thread.",
            confidence=0.92,
            supporting_ids=("sit-1", "sit-2"),
        )
    )
    runtime = SupportReflectionRuntime(store=store)  # type: ignore[arg-type]

    execute_guidance = await runtime.build_turn_guidance(
        assessment=SupportTurnAssessment(need="activate", subjects=(ResolvedSubject(kind="arc", id="webui_cleanup"),)),
        response_mode="execute",
        query_embedding=[0.1, 0.2, 0.3],
        fresh_session=True,
    )
    reflective_guidance = await runtime.build_turn_guidance(
        assessment=SupportTurnAssessment(need="reflect", subjects=(ResolvedSubject(kind="direction", id=None),)),
        response_mode="direction_reflect",
        query_embedding=[0.1, 0.2, 0.3],
        fresh_session=True,
    )
    calibration_guidance = await runtime.build_turn_guidance(
        assessment=SupportTurnAssessment(need="calibrate", subjects=(ResolvedSubject(kind="current_turn", id=None),)),
        response_mode="review",
        query_embedding=[0.1, 0.2, 0.3],
        fresh_session=True,
    )

    assert execute_guidance.surfaced_patterns[0].pattern.kind == "support_preference"
    assert reflective_guidance.surfaced_patterns[0].pattern.kind == "identity_theme"
    assert calibration_guidance.surfaced_patterns[0].pattern.kind == "calibration_gap"


@pytest.mark.asyncio
async def test_reflection_runtime_caps_session_start_surfacing_to_two_patterns() -> None:
    """Fresh-session surfacing should stay bounded even when several patterns qualify."""

    store = _make_runtime_store()
    store.inspection_patterns.extend(
        [
            _make_pattern(
                pattern_id="pattern-blocker-1",
                kind="recurring_blocker",
                status="confirmed",
                scope=SupportProfileScope(type="arc", id="webui_cleanup"),
                claim="Architecture ambiguity keeps stalling the Web UI cleanup thread.",
                confidence=0.9,
                supporting_ids=("sit-1", "sit-2"),
                support_overrides={"planning_granularity": "minimal"},
            ),
            _make_pattern(
                pattern_id="pattern-calibration-1",
                kind="calibration_gap",
                status="candidate",
                scope=SupportProfileScope(type="global", id="user"),
                claim="Your stated priority and actual behavior keep diverging on this thread.",
                confidence=0.92,
                supporting_ids=("sit-1", "sit-2"),
            ),
            _make_pattern(
                pattern_id="pattern-identity-1",
                kind="identity_theme",
                status="candidate",
                scope=SupportProfileScope(type="global", id="user"),
                claim="You disown desire when goals become publicly legible.",
                confidence=0.9,
                supporting_ids=("sit-1", "sit-2"),
            ),
        ]
    )
    runtime = SupportReflectionRuntime(store=store)  # type: ignore[arg-type]

    guidance = await runtime.build_turn_guidance(
        assessment=SupportTurnAssessment(need="activate", subjects=(ResolvedSubject(kind="arc", id="webui_cleanup"),)),
        response_mode="execute",
        query_embedding=[0.1, 0.2, 0.3],
        fresh_session=True,
    )

    assert len(guidance.surfaced_patterns) == 2


@pytest.mark.asyncio
async def test_reflection_prompt_guidance_stays_natural_and_hides_internal_labels() -> None:
    """Rendered reflection guidance should steer the move without exposing internal scoring jargon."""

    store = _make_runtime_store()
    runtime = SupportReflectionRuntime(store=store)  # type: ignore[arg-type]

    guidance = await runtime.build_turn_guidance(
        assessment=SupportTurnAssessment(
            need="activate",
            subjects=(ResolvedSubject(kind="arc", id="webui_cleanup"),),
        ),
        response_mode="execute",
        query_embedding=[0.1, 0.2, 0.3],
        fresh_session=True,
    )
    rendered = runtime.render_prompt_section(guidance)

    assert "## Reflection Guidance" in rendered
    assert "Single-step next moves work better here." in rendered
    assert "keep it natural" in rendered.lower()
    assert "load_score" not in rendered
    assert "move_impact" not in rendered
    assert "surface_level" not in rendered


@pytest.mark.asyncio
async def test_support_reflection_runtime_applies_pattern_confirmation_and_profile_value_corrections_traceably() -> None:
    """Correction flows should update durable pattern/value truth and log the requested change."""

    store = _make_runtime_store()
    runtime = SupportReflectionRuntime(store=store)  # type: ignore[arg-type]

    pattern_result = await runtime.apply_correction_action(
        ConfirmPatternAction(pattern_id="pattern-candidate-1", reason="Yes, that tension is real."),
        now=_ts(11, 0),
    )
    value_result = await runtime.apply_correction_action(
        CorrectProfileValueAction(
            registry="support",
            dimension="option_bandwidth",
            scope=SupportProfileScope(type="context", id="execute"),
            new_value="single",
            reason="Keep execute-mode options narrow.",
        ),
        now=_ts(11, 5),
    )

    confirmed_pattern = next(pattern for pattern in store.inspection_patterns if pattern.pattern_id == "pattern-candidate-1")
    corrected_value = next(
        value
        for value in store.values
        if value.registry == "support"
        and value.dimension == "option_bandwidth"
        and value.scope == SupportProfileScope(type="context", id="execute")
    )

    assert confirmed_pattern.status == "confirmed"
    assert corrected_value.value == "single"
    assert corrected_value.source == "corrected"
    assert pattern_result.changed_patterns[0].pattern_id == "pattern-candidate-1"
    assert value_result.changed_values[0].dimension == "option_bandwidth"
    assert any(event.dimension == "option_bandwidth" and event.status == "applied" for event in store.update_events)


@pytest.mark.asyncio
async def test_support_reflection_runtime_scope_limit_and_reset_rewrite_profile_value_scope_cleanly() -> None:
    """Scope-limiting and resetting a profile value should move or remove the durable override cleanly."""

    store = _make_runtime_store()
    store.values.append(
        SupportProfileValue(
            registry="support",
            dimension="planning_granularity",
            scope=SupportProfileScope(type="global", id="user"),
            value="full",
            status="confirmed",
            confidence=0.9,
            source="explicit",
            created_at=_ts(7, 30),
            updated_at=_ts(7, 30),
        )
    )
    runtime = SupportReflectionRuntime(store=store)  # type: ignore[arg-type]

    await runtime.apply_correction_action(
        ScopeLimitProfileValueAction(
            registry="support",
            dimension="planning_granularity",
            source_scope=SupportProfileScope(type="global", id="user"),
            target_scope=SupportProfileScope(type="arc", id="webui_cleanup"),
            reason="Only keep this more detailed planning style for the Web UI cleanup arc.",
        ),
        now=_ts(11, 10),
    )
    await runtime.apply_correction_action(
        ResetProfileValueAction(
            registry="support",
            dimension="planning_granularity",
            scope=SupportProfileScope(type="arc", id="webui_cleanup"),
            reason="Go back to the default arc behavior here.",
        ),
        now=_ts(11, 15),
    )

    assert all(
        value.scope != SupportProfileScope(type="global", id="user") or value.dimension != "planning_granularity"
        for value in store.values
    )
    assert all(
        value.scope != SupportProfileScope(type="arc", id="webui_cleanup") or value.dimension != "planning_granularity"
        for value in store.values
    )
    assert any(event.status == "reverted" and event.dimension == "planning_granularity" for event in store.update_events)


@pytest.mark.asyncio
async def test_support_reflection_runtime_builds_bounded_on_demand_and_weekly_reviews() -> None:
    """Review generation should stay bounded, typed, and include recent broad changes."""

    store = _make_runtime_store()
    store.inspection_patterns.extend(
        [
            _make_pattern(
                pattern_id="pattern-blocker-1",
                kind="recurring_blocker",
                status="confirmed",
                scope=SupportProfileScope(type="arc", id="webui_cleanup"),
                claim="Architecture ambiguity keeps stalling the Web UI cleanup thread.",
                confidence=0.9,
                supporting_ids=("sit-1", "sit-2"),
            ),
            _make_pattern(
                pattern_id="pattern-identity-1",
                kind="identity_theme",
                status="candidate",
                scope=SupportProfileScope(type="global", id="user"),
                claim="You disown desire when goals become publicly legible.",
                confidence=0.87,
                supporting_ids=("sit-1", "sit-2"),
            ),
            _make_pattern(
                pattern_id="pattern-older-1",
                kind="support_preference",
                status="confirmed",
                scope=SupportProfileScope(type="global", id="user"),
                claim="Broader option sets used to work better here.",
                confidence=0.65,
                supporting_ids=("sit-1",),
            ),
        ]
    )
    store.update_events.insert(
        0,
        SupportProfileUpdateEvent(
            event_id="upd-global-1",
            timestamp=_ts(10, 45),
            registry="relational",
            dimension="candor",
            scope=SupportProfileScope(type="global", id="user"),
            old_value="medium",
            new_value="high",
            reason="Broad calibration work favored higher candor.",
            confidence=0.81,
            status="proposed",
            source_pattern_ids=("pattern-candidate-1",),
            source_situation_ids=("sit-1", "sit-2"),
        ),
    )
    runtime = SupportReflectionRuntime(store=store)  # type: ignore[arg-type]

    weekly_report = await runtime.build_review_report(mode="weekly", now=_ts(11, 20))
    on_demand_report = await runtime.build_review_report(mode="on_demand", now=_ts(11, 20))

    assert 1 <= len(weekly_report.cards) <= 3
    assert 1 <= len(on_demand_report.cards) <= 3
    assert weekly_report.cards[0].card_kind in {"support_fit", "blocker", "identity_theme", "direction_theme", "calibration_gap"}
    assert any(change.event_id == "upd-global-1" for change in weekly_report.recent_changes)
    assert "Review" in runtime.render_review_report(on_demand_report)
