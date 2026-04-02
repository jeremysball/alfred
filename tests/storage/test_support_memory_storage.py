"""Tests for support memory storage in SQLiteStore."""

from __future__ import annotations

from datetime import UTC, datetime

import aiosqlite
import pytest

from alfred.memory.support_memory import EvidenceRef, SupportEpisode
from alfred.storage.sqlite import SQLiteStore


@pytest.fixture
async def sqlite_store(tmp_path):
    """Create a temporary SQLiteStore for support-memory tests."""
    store = SQLiteStore(tmp_path / "support_memory.db")
    await store._init()
    return store


@pytest.mark.asyncio
async def test_episode_and_evidence_round_trip_through_sqlite_store(sqlite_store):
    """Support episodes and evidence refs should round-trip through SQLite."""
    session_id = "sess_support_memory"
    messages = [
        {"idx": 0, "id": "msg-0", "role": "user", "content": "We're blocked on app structure."},
        {"idx": 1, "id": "msg-1", "role": "assistant", "content": "Let's narrow the next step."},
        {"idx": 2, "id": "msg-2", "role": "user", "content": "The bootstrap entrypoint should stay slim."},
        {"idx": 3, "id": "msg-3", "role": "assistant", "content": "Agreed, let's isolate it."},
    ]
    metadata = {"topic": "support-memory"}

    await sqlite_store.save_session(session_id, messages, metadata)

    episode_one = SupportEpisode(
        episode_id="ep-1",
        session_id=session_id,
        schema_version=1,
        started_at=datetime(2026, 3, 30, 10, 0, tzinfo=UTC),
        ended_at=datetime(2026, 3, 30, 10, 12, tzinfo=UTC),
        dominant_need="activate",
        dominant_context="execute",
        dominant_arc_id="arc-webui",
        domain_ids=["work"],
        subject_refs=["bootstrap_entrypoint", "app_structure"],
        friction_signals=["ambiguity", "initiation_friction"],
        interventions_attempted=["narrow_next_step"],
        response_signals=["commitment"],
        outcome_signals=["next_step_chosen"],
        evidence_refs=[
            EvidenceRef(
                evidence_id="ev-1a",
                episode_id="ep-1",
                session_id=session_id,
                message_start_idx=0,
                message_end_idx=1,
                excerpt="We're blocked on app structure.",
                timestamp=datetime(2026, 3, 30, 10, 1, tzinfo=UTC),
                domain_ids=["work"],
                arc_ids=["arc-webui"],
                claim_type="stated_blocker",
                confidence=0.83,
            ),
            EvidenceRef(
                evidence_id="ev-1b",
                episode_id="ep-1",
                session_id=session_id,
                message_start_idx=2,
                message_end_idx=2,
                excerpt="The bootstrap entrypoint should stay slim.",
                timestamp=datetime(2026, 3, 30, 10, 6, tzinfo=UTC),
                domain_ids=["work"],
                arc_ids=["arc-webui"],
                claim_type="stated_goal",
                confidence=0.78,
            ),
        ],
    )
    episode_two = SupportEpisode(
        episode_id="ep-2",
        session_id=session_id,
        schema_version=1,
        started_at=datetime(2026, 3, 30, 10, 20, tzinfo=UTC),
        ended_at=datetime(2026, 3, 30, 10, 28, tzinfo=UTC),
        dominant_need="decide",
        dominant_context="plan",
        dominant_arc_id="arc-webui",
        domain_ids=["work"],
        subject_refs=["bootstrap_entrypoint"],
        friction_signals=["tradeoff_uncertainty"],
        interventions_attempted=["compare_boundaries"],
        response_signals=["clarity"],
        outcome_signals=["boundary_decided"],
        evidence_refs=[
            EvidenceRef(
                evidence_id="ev-2a",
                episode_id="ep-2",
                session_id=session_id,
                message_start_idx=3,
                message_end_idx=3,
                excerpt="Agreed, let's isolate it.",
                timestamp=datetime(2026, 3, 30, 10, 22, tzinfo=UTC),
                domain_ids=["work"],
                arc_ids=["arc-webui"],
                claim_type="stated_decision",
                confidence=0.91,
            )
        ],
    )

    await sqlite_store.save_support_episode(episode_one)
    await sqlite_store.save_support_episode(episode_two)

    loaded_session = await sqlite_store.load_session(session_id)
    assert loaded_session is not None
    assert loaded_session["messages"] == messages
    assert loaded_session["metadata"] == metadata

    loaded_episode = await sqlite_store.get_support_episode("ep-1")
    assert loaded_episode == episode_one

    loaded_episodes = await sqlite_store.list_support_episodes(session_id)
    assert loaded_episodes == [episode_one, episode_two]

    async with aiosqlite.connect(sqlite_store.db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        async with db.execute("SELECT COUNT(*) FROM sessions WHERE session_id = ?", (session_id,)) as cursor:
            row = await cursor.fetchone()
            assert row[0] == 1
