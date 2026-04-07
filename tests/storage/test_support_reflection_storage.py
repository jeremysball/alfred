"""Tests for PRD #169 support-reflection storage queries."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from alfred.memory.support_learning import LearningSituation, SupportPattern, SupportProfileUpdateEvent
from alfred.memory.support_profile import SupportProfileScope
from alfred.storage.sqlite import SQLiteStore


@pytest.fixture
async def sqlite_store(tmp_path):
    return SQLiteStore(str(tmp_path / "support-reflection.db"), embedding_dim=3)



def _ts(hour: int, minute: int) -> datetime:
    return datetime(2026, 4, 5, hour, minute, tzinfo=UTC)


@pytest.mark.asyncio
async def test_support_reflection_storage_lists_patterns_for_inspection_and_recent_update_events(sqlite_store):
    """Inspection storage should list candidate/confirmed patterns and recent update events deterministically."""

    await sqlite_store.save_support_pattern(
        SupportPattern(
            pattern_id="pattern-confirmed-1",
            kind="support_preference",
            scope=SupportProfileScope(type="context", id="execute"),
            status="confirmed",
            claim="Single-step next moves work better here.",
            confidence=0.88,
            created_at=_ts(9, 0),
            updated_at=_ts(10, 10),
            supporting_situation_ids=("sit-1", "sit-2"),
            support_overrides={"option_bandwidth": "single"},
        )
    )
    await sqlite_store.save_support_pattern(
        SupportPattern(
            pattern_id="pattern-candidate-1",
            kind="direction_theme",
            scope=SupportProfileScope(type="global", id="user"),
            status="candidate",
            claim="External legibility and felt aliveness keep pulling in different directions.",
            confidence=0.84,
            created_at=_ts(9, 5),
            updated_at=_ts(10, 5),
            supporting_situation_ids=("sit-3", "sit-4"),
        )
    )
    await sqlite_store.save_support_pattern(
        SupportPattern(
            pattern_id="pattern-rejected-1",
            kind="calibration_gap",
            scope=SupportProfileScope(type="global", id="user"),
            status="rejected",
            claim="Your stated plan and actual behavior diverge here.",
            confidence=0.71,
            created_at=_ts(9, 10),
            updated_at=_ts(10, 0),
            supporting_situation_ids=("sit-5",),
        )
    )

    await sqlite_store.save_support_profile_update_event(
        SupportProfileUpdateEvent(
            event_id="upd-2",
            timestamp=_ts(10, 30),
            registry="support",
            dimension="option_bandwidth",
            scope=SupportProfileScope(type="context", id="execute"),
            old_value="few",
            new_value="single",
            reason="Repeated successful execute situations favored one next step.",
            confidence=0.9,
            status="applied",
            source_pattern_ids=("pattern-confirmed-1",),
            source_situation_ids=("sit-1", "sit-2"),
        )
    )
    await sqlite_store.save_support_profile_update_event(
        SupportProfileUpdateEvent(
            event_id="upd-1",
            timestamp=_ts(10, 20),
            registry="relational",
            dimension="candor",
            scope=SupportProfileScope(type="context", id="execute"),
            old_value="medium",
            new_value="high",
            reason="Calibration situations favored higher candor.",
            confidence=0.82,
            status="proposed",
            source_pattern_ids=("pattern-candidate-1",),
            source_situation_ids=("sit-3", "sit-4"),
        )
    )

    patterns = await sqlite_store.list_support_patterns_for_inspection()
    events = await sqlite_store.list_support_profile_update_events(limit=5)

    assert [pattern.pattern_id for pattern in patterns] == ["pattern-confirmed-1", "pattern-candidate-1"]
    assert [event.event_id for event in events] == ["upd-2", "upd-1"]


@pytest.mark.asyncio
async def test_support_reflection_storage_returns_pattern_and_update_event_details_for_drilldowns(sqlite_store):
    """Inspection drill-downs should be able to load durable records and their supporting situations."""

    await sqlite_store.save_session(
        "sess-1",
        [
            {
                "idx": 0,
                "id": "msg-0",
                "role": "user",
                "timestamp": "2026-04-05T08:00:00+00:00",
                "content": "Keep the next move narrow and direct.",
            }
        ],
        {"topic": "reflection-1"},
    )
    await sqlite_store.save_session(
        "sess-2",
        [
            {
                "idx": 0,
                "id": "msg-0",
                "role": "user",
                "timestamp": "2026-04-05T08:15:00+00:00",
                "content": "Single-step resumption worked better here too.",
            }
        ],
        {"topic": "reflection-2"},
    )

    situation_one = LearningSituation(
        situation_id="sit-1",
        session_id="sess-1",
        recorded_at=_ts(8, 0),
        turn_text="Keep the next move narrow and direct.",
        embedding=(0.1, 0.2, 0.3),
        need="activate",
        response_mode="execute",
        subject_refs=("arc:webui_cleanup",),
        arc_id="webui_cleanup",
        intervention_ids=("int-1",),
        behavior_contract_summary="Keep the next move narrow and direct.",
        intervention_family="narrow",
        support_values_applied={"option_bandwidth": "single"},
        relational_values_applied={"candor": "high"},
        user_response_signals=("clarity",),
        outcome_signals=("next_step_chosen",),
    )
    situation_two = LearningSituation(
        situation_id="sit-2",
        session_id="sess-2",
        recorded_at=_ts(8, 15),
        turn_text="Single-step resumption worked better here too.",
        embedding=(0.1, 0.2, 0.31),
        need="resume",
        response_mode="execute",
        subject_refs=("arc:docs_refresh",),
        arc_id="docs_refresh",
        intervention_ids=("int-2",),
        behavior_contract_summary="Resume the thread with one next step.",
        intervention_family="narrow",
        support_values_applied={"option_bandwidth": "single"},
        relational_values_applied={"candor": "medium"},
        user_response_signals=("resonance",),
        outcome_signals=("resume_ready",),
    )
    await sqlite_store.save_learning_situation(situation_one)
    await sqlite_store.save_learning_situation(situation_two)

    pattern = SupportPattern(
        pattern_id="pattern-confirmed-1",
        kind="support_preference",
        scope=SupportProfileScope(type="context", id="execute"),
        status="confirmed",
        claim="Single-step next moves work better here.",
        confidence=0.88,
        created_at=_ts(9, 0),
        updated_at=_ts(10, 0),
        supporting_situation_ids=("sit-1", "sit-2"),
        support_overrides={"option_bandwidth": "single"},
    )
    event = SupportProfileUpdateEvent(
        event_id="upd-1",
        timestamp=_ts(10, 20),
        registry="support",
        dimension="option_bandwidth",
        scope=SupportProfileScope(type="context", id="execute"),
        old_value="few",
        new_value="single",
        reason="Repeated execute situations favored one next step.",
        confidence=0.9,
        status="applied",
        source_pattern_ids=("pattern-confirmed-1",),
        source_situation_ids=("sit-1", "sit-2"),
    )
    await sqlite_store.save_support_pattern(pattern)
    await sqlite_store.save_support_profile_update_event(event)

    loaded_pattern = await sqlite_store.get_support_pattern("pattern-confirmed-1")
    loaded_event = await sqlite_store.get_support_profile_update_event("upd-1")
    supporting_situations = await sqlite_store.list_learning_situations_by_ids(("sit-1", "sit-2"))

    assert loaded_pattern == pattern
    assert loaded_event == event
    assert [situation.situation_id for situation in supporting_situations] == ["sit-1", "sit-2"]
