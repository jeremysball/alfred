"""Tests for support-memory context refresh behavior."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from alfred.memory.support_context import get_fresh_arc_situation
from alfred.memory.support_memory import (
    ArcBlocker,
    ArcSituation,
    ArcTask,
    LifeDomain,
    OperationalArc,
    SupportEpisode,
)
from alfred.storage.sqlite import SQLiteStore


@pytest.fixture
async def sqlite_store(tmp_path):
    """Create a temporary SQLiteStore for support-memory context tests."""
    store = SQLiteStore(tmp_path / "support_memory_context.db")
    await store._init()
    return store


@pytest.mark.asyncio
async def test_stale_arc_situation_refreshes_from_arc_state_and_recent_episodes(sqlite_store):
    """A stale ArcSituation should be recomputed from structured arc state and recent episodes."""
    session_id = "sess-support-context"
    await sqlite_store.save_session(session_id, [], {"topic": "support-memory-context"})

    domain = LifeDomain(
        domain_id="domain-work",
        name="Work",
        status="active",
        salience=0.97,
        created_at=datetime(2026, 3, 30, 15, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 15, 5, tzinfo=UTC),
    )
    arc = OperationalArc(
        arc_id="arc-webui-cleanup",
        title="Web UI cleanup",
        kind="project",
        primary_domain_id=domain.domain_id,
        status="active",
        salience=0.95,
        created_at=datetime(2026, 3, 30, 15, 10, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 15, 20, tzinfo=UTC),
        last_active_at=datetime(2026, 3, 30, 15, 19, tzinfo=UTC),
        evidence_ref_ids=["ev-arc-1"],
    )
    task = ArcTask(
        task_id="task-extract-runtime-boot",
        arc_id=arc.arc_id,
        title="Extract runtime boot",
        status="in_progress",
        created_at=datetime(2026, 3, 30, 15, 21, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 15, 29, tzinfo=UTC),
        next_step="Move boot orchestration into a dedicated module",
        evidence_ref_ids=["ev-501"],
    )
    blocker = ArcBlocker(
        blocker_id="blocker-app-structure-ambiguity",
        arc_id=arc.arc_id,
        title="App structure ambiguity",
        status="active",
        created_at=datetime(2026, 3, 30, 15, 22, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 15, 27, tzinfo=UTC),
        next_step="Pick a boundary before editing more files",
        evidence_ref_ids=["ev-502"],
    )
    episode = SupportEpisode(
        episode_id="ep-arc-refresh",
        session_id=session_id,
        schema_version=1,
        started_at=datetime(2026, 3, 30, 15, 40, tzinfo=UTC),
        ended_at=datetime(2026, 3, 30, 15, 48, tzinfo=UTC),
        dominant_need="activate",
        dominant_context="execute",
        dominant_arc_id=arc.arc_id,
        domain_ids=[domain.domain_id],
        subject_refs=["bootstrap_boundary"],
        friction_signals=["ambiguity"],
        interventions_attempted=["narrow_next_step"],
        response_signals=["clarity"],
        outcome_signals=["next_step_chosen"],
    )
    stale_situation = ArcSituation(
        arc_id=arc.arc_id,
        current_state="tentative",
        recent_progress=["old_progress"],
        blockers=["old blocker"],
        next_moves=["old move"],
        linked_pattern_ids=["pattern-stale"],
        computed_at=datetime(2026, 3, 30, 14, 0, tzinfo=UTC),
        confidence=0.2,
        staleness_seconds=300,
        refresh_reason="cache_miss",
    )
    refresh_time = datetime(2026, 3, 30, 16, 0, tzinfo=UTC)

    await sqlite_store.save_life_domain(domain)
    await sqlite_store.save_operational_arc(arc)
    await sqlite_store.save_arc_task(task)
    await sqlite_store.save_arc_blocker(blocker)
    await sqlite_store.save_support_episode(episode)
    await sqlite_store.save_arc_situation(stale_situation)

    refreshed = await get_fresh_arc_situation(
        sqlite_store,
        arc.arc_id,
        now=refresh_time,
        staleness_seconds=900,
    )

    assert refreshed == ArcSituation(
        arc_id=arc.arc_id,
        current_state="active",
        recent_progress=["next_step_chosen"],
        blockers=["App structure ambiguity"],
        next_moves=[
            "Move boot orchestration into a dedicated module",
            "Pick a boundary before editing more files",
        ],
        linked_pattern_ids=[],
        computed_at=refresh_time,
        confidence=0.85,
        staleness_seconds=900,
        refresh_reason="stale_cache",
    )

    reloaded = await sqlite_store.get_arc_situation(arc.arc_id)
    assert reloaded == refreshed
