"""Tests for support intervention storage in SQLiteStore."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from alfred.memory.support_memory import SupportEpisode, SupportIntervention, SupportInterventionMessageRef
from alfred.storage.sqlite import SQLiteStore


@pytest.fixture
async def sqlite_store(tmp_path):
    """Create a temporary SQLiteStore for support-intervention tests."""
    store = SQLiteStore(tmp_path / "support_intervention.db")
    await store._init()
    return store


@pytest.mark.asyncio
async def test_support_interventions_round_trip_through_sqlite_store(sqlite_store):
    """Support interventions should round-trip through SQLite with ordered message-span provenance."""
    session_id = "sess_support_interventions"
    messages = [
        {
            "idx": 0,
            "id": "msg-0",
            "role": "user",
            "timestamp": "2026-03-30T10:00:00+00:00",
            "content": "I'm spinning on the entrypoint again.",
        },
        {
            "idx": 1,
            "id": "msg-1",
            "role": "assistant",
            "timestamp": "2026-03-30T10:01:00+00:00",
            "content": "Let's keep this narrow and pick one next move.",
        },
        {
            "idx": 2,
            "id": "msg-2",
            "role": "user",
            "timestamp": "2026-03-30T10:02:00+00:00",
            "content": "Okay, one file boundary would help.",
        },
        {
            "idx": 3,
            "id": "msg-3",
            "role": "assistant",
            "timestamp": "2026-03-30T10:04:00+00:00",
            "content": "Start with the bootstrap wiring only.",
        },
        {
            "idx": 4,
            "id": "msg-4",
            "role": "user",
            "timestamp": "2026-03-30T10:05:00+00:00",
            "content": "Yes, that gives me a concrete next step.",
        },
    ]

    await sqlite_store.save_session(session_id, messages, {"topic": "support-interventions"})

    episode = SupportEpisode(
        episode_id="ep-204",
        session_id=session_id,
        schema_version=1,
        started_at=datetime(2026, 3, 30, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 3, 30, 10, 8, tzinfo=UTC),
        dominant_need="activate",
        dominant_context="execute",
        dominant_arc_id="webui_cleanup",
        domain_ids=["work"],
        subject_refs=["bootstrap_entrypoint"],
        friction_signals=["ambiguity"],
        interventions_attempted=["narrow_next_step"],
        response_signals=["commitment"],
        outcome_signals=["next_step_chosen"],
    )
    await sqlite_store.save_support_episode(episode)

    intervention_one = SupportIntervention(
        intervention_id="int-55",
        episode_id="ep-204",
        timestamp=datetime(2026, 3, 30, 10, 1, tzinfo=UTC),
        context="execute",
        arc_id="webui_cleanup",
        intervention_type="narrow_next_step",
        relational_values_applied={
            "companionship": "medium",
            "momentum_pressure": "high",
        },
        support_values_applied={
            "planning_granularity": "minimal",
            "option_bandwidth": "single",
        },
        behavior_contract_summary="Keep this narrow, recommend one concrete move, and avoid branching the plan.",
        user_response_signals=["resonance"],
        outcome_signals=["next_step_chosen"],
        evidence_refs=[
            SupportInterventionMessageRef(
                session_id=session_id,
                message_start_id="msg-2",
                message_end_id="msg-2",
            ),
            SupportInterventionMessageRef(
                session_id=session_id,
                message_start_id="msg-0",
                message_end_id="msg-1",
            ),
        ],
    )
    intervention_two = SupportIntervention(
        intervention_id="int-56",
        episode_id="ep-204",
        timestamp=datetime(2026, 3, 30, 10, 4, tzinfo=UTC),
        context="execute",
        arc_id="webui_cleanup",
        intervention_type="state_boundary",
        relational_values_applied={
            "candor": "medium",
        },
        support_values_applied={
            "recommendation_forcefulness": "high",
        },
        behavior_contract_summary="Name the smallest safe boundary and keep the recommendation direct.",
        user_response_signals=["clarity", "commitment"],
        outcome_signals=["boundary_decided"],
        evidence_refs=[
            SupportInterventionMessageRef(
                session_id=session_id,
                message_start_id="msg-3",
                message_end_id="msg-4",
            ),
        ],
    )

    await sqlite_store.save_support_intervention(intervention_one)
    await sqlite_store.save_support_intervention(intervention_two)

    assert await sqlite_store.get_support_intervention("int-55") == intervention_one
    assert await sqlite_store.list_support_interventions_for_episode("ep-204") == [
        intervention_one,
        intervention_two,
    ]
