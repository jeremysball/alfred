"""Tests for support-learning storage in SQLiteStore."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from alfred.memory.support_learning import (
    LearningSituation,
    SupportPattern,
    SupportProfileUpdateEvent,
    SupportTranscriptSpanRef,
)
from alfred.memory.support_profile import SupportProfileScope
from alfred.storage.sqlite import SQLiteStore


@pytest.fixture
async def sqlite_store(tmp_path):
    """Create a temporary SQLiteStore for support-learning tests."""
    store = SQLiteStore(tmp_path / "support_learning.db", embedding_dim=4)
    await store._init()
    return store


@pytest.mark.asyncio
async def test_learning_situation_storage_round_trips_and_lists_recent_situations(sqlite_store):
    """Learning situations should round-trip through SQLite without losing embeddings or linked interventions."""

    session_id = "sess-learning-storage"
    messages = [
        {
            "idx": 0,
            "id": "msg-0",
            "role": "user",
            "timestamp": "2026-03-30T14:00:00+00:00",
            "content": "Let's continue the Web UI cleanup and just pick one next step.",
        },
        {
            "idx": 1,
            "id": "msg-1",
            "role": "assistant",
            "timestamp": "2026-03-30T14:01:00+00:00",
            "content": "Let's keep this narrow and choose one next move.",
        },
        {
            "idx": 2,
            "id": "msg-2",
            "role": "user",
            "timestamp": "2026-03-30T14:04:00+00:00",
            "content": "Yes, that gives me a concrete next step.",
        },
    ]
    await sqlite_store.save_session(session_id, messages, {"topic": "support-learning"})

    earlier = LearningSituation(
        situation_id="sit-webui-1",
        session_id=session_id,
        recorded_at=datetime(2026, 3, 30, 14, 1, tzinfo=UTC),
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
        relational_values_applied={"candor": "medium"},
        support_values_applied={"option_bandwidth": "single"},
        user_response_signals=("resonance",),
        outcome_signals=("next_step_chosen",),
        evidence_refs=(
            SupportTranscriptSpanRef(
                session_id=session_id,
                message_start_id="msg-0",
                message_end_id="msg-1",
            ),
        ),
    )
    later = LearningSituation(
        situation_id="sit-webui-2",
        session_id=session_id,
        recorded_at=datetime(2026, 3, 30, 14, 4, tzinfo=UTC),
        turn_text="Yes, that gives me a concrete next step.",
        embedding=(0.14, 0.84, 0.39, 0.11),
        need="activate",
        response_mode="execute",
        subject_refs=("arc:webui_cleanup",),
        arc_id="webui_cleanup",
        domain_ids=("work",),
        intervention_ids=("int-webui-2",),
        behavior_contract_summary="Stay operational and preserve the chosen next move.",
        intervention_family="narrow",
        relational_values_applied={"momentum_pressure": "medium"},
        support_values_applied={"planning_granularity": "minimal"},
        user_response_signals=("commitment",),
        outcome_signals=("resume_ready",),
        evidence_refs=(
            SupportTranscriptSpanRef(
                session_id=session_id,
                message_start_id="msg-2",
                message_end_id="msg-2",
            ),
        ),
    )

    await sqlite_store.save_learning_situation(earlier)
    await sqlite_store.save_learning_situation(later)

    assert await sqlite_store.get_learning_situation("sit-webui-1") == earlier
    assert await sqlite_store.list_learning_situations(session_id) == [earlier, later]


@pytest.mark.asyncio
async def test_similar_learning_situations_can_match_across_arcs_when_semantics_are_strong(sqlite_store):
    """Similar-situation retrieval should allow strong semantic matches from other arcs."""

    await sqlite_store.save_session(
        "sess-similar-learning",
        [
            {
                "idx": 0,
                "id": "msg-0",
                "role": "user",
                "timestamp": "2026-03-30T15:00:00+00:00",
                "content": "Let's resume one active work thread.",
            },
        ],
        {"topic": "support-learning-search"},
    )

    situations = [
        LearningSituation(
            situation_id="sit-docs",
            session_id="sess-similar-learning",
            recorded_at=datetime(2026, 3, 30, 15, 1, tzinfo=UTC),
            turn_text="Let's pick back up the docs refresh thread.",
            embedding=(0.0, 0.98, 0.02, 0.0),
            need="resume",
            response_mode="execute",
            subject_refs=("arc:docs_refresh", "domain:work"),
            arc_id="docs_refresh",
            domain_ids=("work",),
            intervention_ids=("int-docs-1",),
            behavior_contract_summary="Resume the thread and keep the next move narrow.",
            intervention_family="summarize",
            relational_values_applied={"candor": "medium"},
            support_values_applied={"option_bandwidth": "single"},
        ),
        LearningSituation(
            situation_id="sit-webui",
            session_id="sess-similar-learning",
            recorded_at=datetime(2026, 3, 30, 15, 2, tzinfo=UTC),
            turn_text="Let's continue the Web UI cleanup thread.",
            embedding=(0.0, 0.93, 0.08, 0.0),
            need="resume",
            response_mode="execute",
            subject_refs=("arc:webui_cleanup", "domain:work"),
            arc_id="webui_cleanup",
            domain_ids=("work",),
            intervention_ids=("int-webui-3",),
            behavior_contract_summary="Resume the thread and keep the next move narrow.",
            intervention_family="summarize",
            relational_values_applied={"candor": "medium"},
            support_values_applied={"option_bandwidth": "single"},
        ),
        LearningSituation(
            situation_id="sit-identity",
            session_id="sess-similar-learning",
            recorded_at=datetime(2026, 3, 30, 15, 3, tzinfo=UTC),
            turn_text="Why do I keep repeating this pattern in myself?",
            embedding=(1.0, 0.0, 0.0, 0.0),
            need="reflect",
            response_mode="identity_reflect",
            subject_refs=("identity",),
            intervention_ids=("int-identity-1",),
            behavior_contract_summary="Mirror the pattern and deepen reflection.",
            intervention_family="mirror",
            relational_values_applied={"companionship": "high"},
            support_values_applied={"reflection_depth": "deep"},
        ),
    ]
    for situation in situations:
        await sqlite_store.save_learning_situation(situation)

    matches = await sqlite_store.search_learning_situations(
        query_embedding=[0.0, 0.97, 0.03, 0.0],
        top_k=3,
        response_mode="execute",
    )

    assert [match[0].situation_id for match in matches] == ["sit-docs", "sit-webui"]
    assert matches[0][1] > matches[1][1]


@pytest.mark.asyncio
async def test_support_pattern_storage_round_trips_with_kind_scope_status_and_supporting_situations(sqlite_store):
    """Support patterns should round-trip through SQLite with their runtime overrides intact."""

    pattern = SupportPattern(
        pattern_id="pattern-narrow-next-step",
        kind="support_preference",
        scope=SupportProfileScope(type="context", id="execute"),
        status="confirmed",
        claim="Single-step operational next moves work better than menus here.",
        confidence=0.86,
        created_at=datetime(2026, 3, 30, 16, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 16, 8, tzinfo=UTC),
        supporting_situation_ids=("sit-webui-1", "sit-webui-2"),
        support_overrides={"option_bandwidth": "single"},
        relational_overrides={"momentum_pressure": "medium"},
    )

    await sqlite_store.save_support_pattern(pattern)

    assert await sqlite_store.get_support_pattern("pattern-narrow-next-step") == pattern


@pytest.mark.asyncio
async def test_support_profile_update_event_round_trips_old_new_values_and_evidence(sqlite_store):
    """Support-profile update events should round-trip through SQLite for auditability."""

    event = SupportProfileUpdateEvent(
        event_id="upd-candor-1",
        timestamp=datetime(2026, 3, 30, 16, 10, tzinfo=UTC),
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

    await sqlite_store.save_support_profile_update_event(event)

    assert await sqlite_store.get_support_profile_update_event("upd-candor-1") == event
