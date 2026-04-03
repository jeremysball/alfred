"""Tests for support memory storage in SQLiteStore."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime

import aiosqlite
import pytest

from alfred.memory.support_memory import (
    ArcBlocker,
    ArcDecision,
    ArcOpenLoop,
    ArcSnapshot,
    ArcTask,
    EvidenceRef,
    LifeDomain,
    OperationalArc,
    SupportEpisode,
)
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


@pytest.mark.asyncio
async def test_promoting_session_message_spans_to_message_id_evidence_refs_keeps_session_archive_unchanged(sqlite_store):
    """Promoting message-ID evidence refs from a session should not mutate the stored archive."""
    session_id = "sess_support_memory_promotion"
    messages = [
        {
            "idx": 0,
            "id": "msg-0",
            "role": "user",
            "timestamp": "2026-03-30T10:00:00+00:00",
            "content": "We're blocked on app structure.",
        },
        {
            "idx": 1,
            "id": "msg-1",
            "role": "assistant",
            "timestamp": "2026-03-30T10:01:00+00:00",
            "content": "Let's narrow the next step.",
        },
        {
            "idx": 2,
            "id": "msg-2",
            "role": "user",
            "timestamp": "2026-03-30T10:06:00+00:00",
            "content": "The bootstrap entrypoint should stay slim.",
        },
        {
            "idx": 3,
            "id": "msg-3",
            "role": "assistant",
            "timestamp": "2026-03-30T10:08:00+00:00",
            "content": "Agreed, let's isolate it.",
        },
    ]
    metadata = {"topic": "support-memory", "promotion": "evidence"}

    await sqlite_store.save_session(session_id, messages, metadata)

    loaded_session = await sqlite_store.load_session(session_id)
    assert loaded_session is not None
    session_snapshot = deepcopy(loaded_session["messages"])
    metadata_snapshot = deepcopy(loaded_session["metadata"])

    evidence_one = EvidenceRef.from_session_message_span(
        evidence_id="ev-promoted-1",
        episode_id="ep-promoted",
        session_id=session_id,
        messages=loaded_session["messages"],
        message_start_id="msg-0",
        message_end_id="msg-1",
        domain_ids=["work"],
        arc_ids=["arc-webui"],
        claim_type="stated_blocker",
        confidence=0.84,
    )
    evidence_two = EvidenceRef.from_session_message_span(
        evidence_id="ev-promoted-2",
        episode_id="ep-promoted",
        session_id=session_id,
        messages=loaded_session["messages"],
        message_start_id="msg-2",
        message_end_id="msg-3",
        domain_ids=["work"],
        arc_ids=["arc-webui"],
        claim_type="stated_decision",
        confidence=0.92,
    )

    assert evidence_one == EvidenceRef(
        evidence_id="ev-promoted-1",
        episode_id="ep-promoted",
        session_id=session_id,
        message_start_id="msg-0",
        message_end_id="msg-1",
        excerpt="We're blocked on app structure.",
        timestamp=datetime(2026, 3, 30, 10, 0, tzinfo=UTC),
        domain_ids=["work"],
        arc_ids=["arc-webui"],
        claim_type="stated_blocker",
        confidence=0.84,
    )
    assert evidence_two == EvidenceRef(
        evidence_id="ev-promoted-2",
        episode_id="ep-promoted",
        session_id=session_id,
        message_start_id="msg-2",
        message_end_id="msg-3",
        excerpt="The bootstrap entrypoint should stay slim.",
        timestamp=datetime(2026, 3, 30, 10, 6, tzinfo=UTC),
        domain_ids=["work"],
        arc_ids=["arc-webui"],
        claim_type="stated_decision",
        confidence=0.92,
    )

    reloaded_session = await sqlite_store.load_session(session_id)
    assert reloaded_session is not None
    assert reloaded_session["messages"] == session_snapshot
    assert reloaded_session["metadata"] == metadata_snapshot


@pytest.mark.asyncio
async def test_life_domain_and_operational_arc_round_trip_without_session_search(sqlite_store):
    """Life domains and operational arcs should round-trip without using session storage."""
    domain = LifeDomain(
        domain_id="domain-work",
        name="Work",
        status="active",
        salience=0.93,
        created_at=datetime(2026, 3, 30, 11, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 11, 5, tzinfo=UTC),
        linked_pattern_ids=["pattern-initiation-support"],
    )
    arc = OperationalArc(
        arc_id="arc-webui-cleanup",
        title="Web UI cleanup",
        kind="project",
        primary_domain_id=domain.domain_id,
        status="active",
        salience=0.96,
        created_at=datetime(2026, 3, 30, 11, 10, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 11, 20, tzinfo=UTC),
        last_active_at=datetime(2026, 3, 30, 11, 18, tzinfo=UTC),
        evidence_ref_ids=["ev-1a", "ev-1b"],
    )

    await sqlite_store.save_life_domain(domain)
    await sqlite_store.save_operational_arc(arc)

    loaded_domain = await sqlite_store.get_life_domain(domain.domain_id)
    assert loaded_domain == domain

    loaded_arc = await sqlite_store.get_operational_arc(arc.arc_id)
    assert loaded_arc == arc

    updated_domain = replace(
        domain,
        status="dormant",
        salience=0.61,
        updated_at=datetime(2026, 3, 31, 8, 30, tzinfo=UTC),
        linked_pattern_ids=["pattern-initiation-support", "pattern-reentry"],
    )
    updated_arc = replace(
        arc,
        status="dormant",
        salience=0.72,
        updated_at=datetime(2026, 3, 31, 8, 35, tzinfo=UTC),
        last_active_at=datetime(2026, 3, 31, 8, 10, tzinfo=UTC),
        evidence_ref_ids=["ev-1a", "ev-1b", "ev-2a"],
    )

    await sqlite_store.save_life_domain(updated_domain)
    await sqlite_store.save_operational_arc(updated_arc)

    reloaded_domain = await sqlite_store.get_life_domain(domain.domain_id)
    assert reloaded_domain == updated_domain

    reloaded_arc = await sqlite_store.get_operational_arc(arc.arc_id)
    assert reloaded_arc == updated_arc

    async with aiosqlite.connect(sqlite_store.db_path) as db, db.execute("SELECT COUNT(*) FROM sessions") as cursor:
        row = await cursor.fetchone()
        assert row[0] == 0


@pytest.mark.asyncio
async def test_active_arcs_are_listed_in_resume_order_for_a_domain(sqlite_store):
    """Active and dormant arcs should be listed in one resume-oriented order for a domain."""
    work_domain = LifeDomain(
        domain_id="domain-work",
        name="Work",
        status="active",
        salience=0.94,
        created_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 12, 5, tzinfo=UTC),
    )
    health_domain = LifeDomain(
        domain_id="domain-health",
        name="Health",
        status="active",
        salience=0.71,
        created_at=datetime(2026, 3, 30, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 12, 5, tzinfo=UTC),
    )
    await sqlite_store.save_life_domain(work_domain)
    await sqlite_store.save_life_domain(health_domain)

    admin_arc = OperationalArc(
        arc_id="arc-admin-push",
        title="Admin push",
        kind="admin_thread",
        primary_domain_id=work_domain.domain_id,
        status="active",
        salience=0.91,
        created_at=datetime(2026, 3, 30, 12, 10, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 12, 40, tzinfo=UTC),
        last_active_at=datetime(2026, 3, 30, 12, 35, tzinfo=UTC),
    )
    deep_work_arc = OperationalArc(
        arc_id="arc-deep-work",
        title="Deep work sprint",
        kind="project",
        primary_domain_id=work_domain.domain_id,
        status="active",
        salience=0.91,
        created_at=datetime(2026, 3, 30, 12, 12, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 12, 45, tzinfo=UTC),
        last_active_at=datetime(2026, 3, 30, 12, 42, tzinfo=UTC),
    )
    dormant_research_arc = OperationalArc(
        arc_id="arc-research-thread",
        title="Research thread",
        kind="research_thread",
        primary_domain_id=work_domain.domain_id,
        status="dormant",
        salience=0.99,
        created_at=datetime(2026, 3, 30, 12, 15, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 12, 50, tzinfo=UTC),
        last_active_at=datetime(2026, 3, 30, 12, 48, tzinfo=UTC),
    )
    archived_arc = OperationalArc(
        arc_id="arc-archived-cleanup",
        title="Archived cleanup",
        kind="project",
        primary_domain_id=work_domain.domain_id,
        status="archived",
        salience=1.0,
        created_at=datetime(2026, 3, 30, 12, 20, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 12, 55, tzinfo=UTC),
        last_active_at=datetime(2026, 3, 30, 12, 54, tzinfo=UTC),
    )
    other_domain_arc = OperationalArc(
        arc_id="arc-health-recovery",
        title="Health recovery",
        kind="recovery_push",
        primary_domain_id=health_domain.domain_id,
        status="active",
        salience=1.0,
        created_at=datetime(2026, 3, 30, 12, 25, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 12, 58, tzinfo=UTC),
        last_active_at=datetime(2026, 3, 30, 12, 56, tzinfo=UTC),
    )

    for arc in [admin_arc, deep_work_arc, dormant_research_arc, archived_arc, other_domain_arc]:
        await sqlite_store.save_operational_arc(arc)

    loaded_arcs = await sqlite_store.list_resume_arcs_for_domain(work_domain.domain_id)

    assert loaded_arcs == [deep_work_arc, admin_arc, dormant_research_arc]


@pytest.mark.asyncio
async def test_arc_operational_state_round_trips_tasks_blockers_decisions_and_open_loops(sqlite_store):
    """Arc-linked operational work objects should persist without using session search."""
    domain = LifeDomain(
        domain_id="domain-work",
        name="Work",
        status="active",
        salience=0.97,
        created_at=datetime(2026, 3, 30, 13, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 13, 5, tzinfo=UTC),
    )
    arc = OperationalArc(
        arc_id="arc-webui-cleanup",
        title="Web UI cleanup",
        kind="project",
        primary_domain_id=domain.domain_id,
        status="active",
        salience=0.95,
        created_at=datetime(2026, 3, 30, 13, 10, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 13, 20, tzinfo=UTC),
        last_active_at=datetime(2026, 3, 30, 13, 19, tzinfo=UTC),
        evidence_ref_ids=["ev-arc-1"],
    )
    task = ArcTask(
        task_id="task-split-bootstrap-flow",
        arc_id=arc.arc_id,
        title="Split bootstrap flow",
        status="in_progress",
        created_at=datetime(2026, 3, 30, 13, 21, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 13, 26, tzinfo=UTC),
        next_step="Extract runtime boot into its own module",
        evidence_ref_ids=["ev-441"],
    )
    blocker = ArcBlocker(
        blocker_id="blocker-app-structure-ambiguity",
        arc_id=arc.arc_id,
        title="App structure ambiguity",
        status="active",
        created_at=datetime(2026, 3, 30, 13, 22, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 13, 27, tzinfo=UTC),
        next_step="Choose a bootstrap boundary",
        evidence_ref_ids=["ev-442"],
    )
    decision = ArcDecision(
        decision_id="decision-runtime-boot-location",
        arc_id=arc.arc_id,
        title="Where runtime should boot",
        status="pending_review",
        created_at=datetime(2026, 3, 30, 13, 23, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 13, 28, tzinfo=UTC),
        current_tension="Keep the entrypoint thin without hiding app wiring",
        evidence_ref_ids=["ev-443"],
    )
    open_loop = ArcOpenLoop(
        open_loop_id="open-loop-pick-bootstrap-boundary",
        arc_id=arc.arc_id,
        title="Pick bootstrap boundary",
        status="waiting",
        created_at=datetime(2026, 3, 30, 13, 24, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 13, 29, tzinfo=UTC),
        current_tension="Need a crisp seam before refactoring spreads",
        evidence_ref_ids=["ev-444"],
    )

    await sqlite_store.save_life_domain(domain)
    await sqlite_store.save_operational_arc(arc)
    await sqlite_store.save_arc_task(task)
    await sqlite_store.save_arc_blocker(blocker)
    await sqlite_store.save_arc_decision(decision)
    await sqlite_store.save_arc_open_loop(open_loop)

    assert await sqlite_store.list_arc_tasks(arc.arc_id) == [task]
    assert await sqlite_store.list_arc_blockers(arc.arc_id) == [blocker]
    assert await sqlite_store.list_arc_decisions(arc.arc_id) == [decision]
    assert await sqlite_store.list_arc_open_loops(arc.arc_id) == [open_loop]

    async with aiosqlite.connect(sqlite_store.db_path) as db, db.execute("SELECT COUNT(*) FROM sessions") as cursor:
        row = await cursor.fetchone()
        assert row[0] == 0


@pytest.mark.asyncio
async def test_arc_snapshot_reads_structured_work_state_without_transcript_search(sqlite_store):
    """One arc snapshot should compose structured work state without using session search."""
    domain = LifeDomain(
        domain_id="domain-work",
        name="Work",
        status="active",
        salience=0.97,
        created_at=datetime(2026, 3, 30, 14, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 14, 5, tzinfo=UTC),
    )
    arc = OperationalArc(
        arc_id="arc-webui-cleanup",
        title="Web UI cleanup",
        kind="project",
        primary_domain_id=domain.domain_id,
        status="active",
        salience=0.95,
        created_at=datetime(2026, 3, 30, 14, 10, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 14, 20, tzinfo=UTC),
        last_active_at=datetime(2026, 3, 30, 14, 19, tzinfo=UTC),
        evidence_ref_ids=["ev-arc-1"],
    )
    earlier_task = ArcTask(
        task_id="task-outline-bootstrap-boundary",
        arc_id=arc.arc_id,
        title="Outline bootstrap boundary",
        status="todo",
        created_at=datetime(2026, 3, 30, 14, 21, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 14, 22, tzinfo=UTC),
        next_step="List the current startup responsibilities",
        evidence_ref_ids=["ev-451"],
    )
    later_task = ArcTask(
        task_id="task-extract-runtime-boot",
        arc_id=arc.arc_id,
        title="Extract runtime boot",
        status="in_progress",
        created_at=datetime(2026, 3, 30, 14, 25, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 14, 29, tzinfo=UTC),
        next_step="Move boot orchestration into a dedicated module",
        evidence_ref_ids=["ev-452"],
    )
    blocker = ArcBlocker(
        blocker_id="blocker-app-structure-ambiguity",
        arc_id=arc.arc_id,
        title="App structure ambiguity",
        status="active",
        created_at=datetime(2026, 3, 30, 14, 23, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 14, 27, tzinfo=UTC),
        next_step="Pick a boundary before editing more files",
        evidence_ref_ids=["ev-453"],
    )
    decision = ArcDecision(
        decision_id="decision-runtime-boot-location",
        arc_id=arc.arc_id,
        title="Where runtime should boot",
        status="pending_review",
        created_at=datetime(2026, 3, 30, 14, 24, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 14, 28, tzinfo=UTC),
        current_tension="Keep the entrypoint thin without obscuring app wiring",
        evidence_ref_ids=["ev-454"],
    )
    open_loop = ArcOpenLoop(
        open_loop_id="open-loop-confirm-bootstrap-boundary",
        arc_id=arc.arc_id,
        title="Confirm bootstrap boundary",
        status="waiting",
        created_at=datetime(2026, 3, 30, 14, 26, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 14, 30, tzinfo=UTC),
        current_tension="Need a crisp seam before changing startup flow",
        evidence_ref_ids=["ev-455"],
    )

    await sqlite_store.save_life_domain(domain)
    await sqlite_store.save_operational_arc(arc)
    await sqlite_store.save_arc_task(later_task)
    await sqlite_store.save_arc_task(earlier_task)
    await sqlite_store.save_arc_blocker(blocker)
    await sqlite_store.save_arc_decision(decision)
    await sqlite_store.save_arc_open_loop(open_loop)

    snapshot = await sqlite_store.get_arc_snapshot(arc.arc_id)

    assert snapshot == ArcSnapshot(
        arc=arc,
        tasks=[earlier_task, later_task],
        blockers=[blocker],
        decisions=[decision],
        open_loops=[open_loop],
    )

    async with aiosqlite.connect(sqlite_store.db_path) as db, db.execute("SELECT COUNT(*) FROM sessions") as cursor:
        row = await cursor.fetchone()
        assert row[0] == 0
