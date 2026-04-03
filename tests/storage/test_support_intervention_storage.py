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


async def _seed_queryable_support_interventions(
    sqlite_store: SQLiteStore,
) -> dict[str, SupportIntervention]:
    """Create a small multi-episode intervention dataset for storage queries."""
    session_one_id = "sess_support_queries_one"
    session_two_id = "sess_support_queries_two"

    await sqlite_store.save_session(
        session_one_id,
        [
            {
                "idx": 0,
                "id": "msg-a0",
                "role": "user",
                "timestamp": "2026-03-30T11:00:00+00:00",
                "content": "I need one narrow next step.",
            },
            {
                "idx": 1,
                "id": "msg-a1",
                "role": "assistant",
                "timestamp": "2026-03-30T11:01:00+00:00",
                "content": "Let's keep it to one boundary.",
            },
            {
                "idx": 2,
                "id": "msg-a2",
                "role": "user",
                "timestamp": "2026-03-30T11:02:00+00:00",
                "content": "That helps.",
            },
            {
                "idx": 3,
                "id": "msg-a3",
                "role": "assistant",
                "timestamp": "2026-03-30T11:05:00+00:00",
                "content": "Start with bootstrap wiring only.",
            },
        ],
        {"topic": "support-query-webui"},
    )
    await sqlite_store.save_session(
        session_two_id,
        [
            {
                "idx": 0,
                "id": "msg-b0",
                "role": "user",
                "timestamp": "2026-03-30T11:10:00+00:00",
                "content": "I need to compare two planning options.",
            },
            {
                "idx": 1,
                "id": "msg-b1",
                "role": "assistant",
                "timestamp": "2026-03-30T11:11:00+00:00",
                "content": "Let's compare them directly.",
            },
        ],
        {"topic": "support-query-planning"},
    )

    await sqlite_store.save_support_episode(
        SupportEpisode(
            episode_id="ep-query-1",
            session_id=session_one_id,
            schema_version=1,
            started_at=datetime(2026, 3, 30, 11, 0, tzinfo=UTC),
            ended_at=datetime(2026, 3, 30, 11, 8, tzinfo=UTC),
            dominant_need="activate",
            dominant_context="execute",
            dominant_arc_id="webui_cleanup",
            domain_ids=["work"],
            subject_refs=["bootstrap_entrypoint"],
            friction_signals=["ambiguity"],
            interventions_attempted=["narrow_next_step"],
            response_signals=["commitment"],
            outcome_signals=["next_step_chosen"],
        ),
    )
    await sqlite_store.save_support_episode(
        SupportEpisode(
            episode_id="ep-query-2",
            session_id=session_two_id,
            schema_version=1,
            started_at=datetime(2026, 3, 30, 11, 10, tzinfo=UTC),
            ended_at=datetime(2026, 3, 30, 11, 14, tzinfo=UTC),
            dominant_need="decide",
            dominant_context="plan",
            dominant_arc_id="roadmap_review",
            domain_ids=["work"],
            subject_refs=["planning_options"],
            friction_signals=["tradeoff_uncertainty"],
            interventions_attempted=["compare_options"],
            response_signals=["clarity"],
            outcome_signals=["comparison_started"],
        ),
    )

    interventions = {
        "execute_early": SupportIntervention(
            intervention_id="int-query-1",
            episode_id="ep-query-1",
            timestamp=datetime(2026, 3, 30, 11, 1, tzinfo=UTC),
            context="execute",
            arc_id="webui_cleanup",
            intervention_type="narrow_next_step",
            relational_values_applied={"companionship": "medium"},
            support_values_applied={"option_bandwidth": "single"},
            behavior_contract_summary="Keep it to one next move.",
            user_response_signals=["resonance"],
            outcome_signals=["next_step_chosen"],
            evidence_refs=[
                SupportInterventionMessageRef(
                    session_id=session_one_id,
                    message_start_id="msg-a0",
                    message_end_id="msg-a1",
                ),
            ],
        ),
        "execute_late": SupportIntervention(
            intervention_id="int-query-2",
            episode_id="ep-query-1",
            timestamp=datetime(2026, 3, 30, 11, 5, tzinfo=UTC),
            context="execute",
            arc_id="webui_cleanup",
            intervention_type="state_boundary",
            relational_values_applied={"candor": "medium"},
            support_values_applied={"recommendation_forcefulness": "high"},
            behavior_contract_summary="Name the smallest safe boundary directly.",
            user_response_signals=["clarity", "commitment"],
            outcome_signals=["boundary_decided"],
            evidence_refs=[
                SupportInterventionMessageRef(
                    session_id=session_one_id,
                    message_start_id="msg-a2",
                    message_end_id="msg-a3",
                ),
            ],
        ),
        "plan_review": SupportIntervention(
            intervention_id="int-query-3",
            episode_id="ep-query-2",
            timestamp=datetime(2026, 3, 30, 11, 11, tzinfo=UTC),
            context="plan",
            arc_id="roadmap_review",
            intervention_type="compare_options",
            relational_values_applied={"analytical_depth": "high"},
            support_values_applied={"planning_granularity": "short"},
            behavior_contract_summary="Compare the two strongest options without opening a full tree.",
            user_response_signals=["engagement"],
            outcome_signals=["comparison_started"],
            evidence_refs=[
                SupportInterventionMessageRef(
                    session_id=session_two_id,
                    message_start_id="msg-b0",
                    message_end_id="msg-b1",
                ),
            ],
        ),
    }

    for intervention in interventions.values():
        await sqlite_store.save_support_intervention(intervention)

    return interventions


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


@pytest.mark.asyncio
async def test_sqlite_store_lists_support_interventions_by_arc_and_context(sqlite_store):
    """Support interventions should be queryable by arc and context in deterministic order."""
    interventions = await _seed_queryable_support_interventions(sqlite_store)

    assert await sqlite_store.list_support_interventions_for_arc("webui_cleanup") == [
        interventions["execute_late"],
        interventions["execute_early"],
    ]
    assert await sqlite_store.list_support_interventions_for_context("execute") == [
        interventions["execute_late"],
        interventions["execute_early"],
    ]
    assert await sqlite_store.list_support_interventions_for_context("plan") == [
        interventions["plan_review"],
    ]


@pytest.mark.asyncio
async def test_sqlite_store_lists_support_interventions_by_applied_dimension(sqlite_store):
    """Support interventions should be queryable by applied relational or support dimension."""
    interventions = await _seed_queryable_support_interventions(sqlite_store)

    assert await sqlite_store.list_support_interventions_by_applied_dimension("relational", "candor") == [
        interventions["execute_late"],
    ]
    assert await sqlite_store.list_support_interventions_by_applied_dimension("support", "planning_granularity") == [
        interventions["plan_review"],
    ]
