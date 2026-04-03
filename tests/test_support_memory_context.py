"""Tests for support-memory context refresh behavior."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from alfred.memory.support_context import (
    ArcResumeContext,
    OrientationContext,
    get_fresh_arc_situation,
    get_session_start_orientation_context,
    get_session_start_resume_context,
    get_support_operational_context,
)
from alfred.memory.support_memory import (
    ArcBlocker,
    ArcDecision,
    ArcOpenLoop,
    ArcSituation,
    ArcSnapshot,
    ArcTask,
    GlobalSituation,
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


@pytest.mark.asyncio
async def test_fresh_session_resume_context_prefers_arc_state_and_episodes_before_session_search(sqlite_store):
    """A strong arc resume match should load structured state before archive recall is consulted."""
    session_id = "sess-resume-context"
    await sqlite_store.save_session(session_id, [], {"topic": "resume-support-context"})

    domain = LifeDomain(
        domain_id="domain-work",
        name="Work",
        status="active",
        salience=0.98,
        created_at=datetime(2026, 3, 30, 17, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 17, 5, tzinfo=UTC),
    )
    arc = OperationalArc(
        arc_id="arc-webui-cleanup",
        title="Web UI cleanup",
        kind="project",
        primary_domain_id=domain.domain_id,
        status="active",
        salience=0.96,
        created_at=datetime(2026, 3, 30, 17, 10, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 17, 20, tzinfo=UTC),
        last_active_at=datetime(2026, 3, 30, 17, 19, tzinfo=UTC),
        evidence_ref_ids=["ev-arc-2"],
    )
    task = ArcTask(
        task_id="task-split-bootstrap-flow",
        arc_id=arc.arc_id,
        title="Split bootstrap flow",
        status="in_progress",
        created_at=datetime(2026, 3, 30, 17, 21, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 17, 25, tzinfo=UTC),
        next_step="Extract the startup wiring from the view layer",
        evidence_ref_ids=["ev-601"],
    )
    episode = SupportEpisode(
        episode_id="ep-resume-context",
        session_id=session_id,
        schema_version=1,
        started_at=datetime(2026, 3, 30, 17, 40, tzinfo=UTC),
        ended_at=datetime(2026, 3, 30, 17, 46, tzinfo=UTC),
        dominant_need="activate",
        dominant_context="execute",
        dominant_arc_id=arc.arc_id,
        domain_ids=[domain.domain_id],
        subject_refs=["startup_wiring"],
        friction_signals=["scope_blur"],
        interventions_attempted=["state_recap"],
        response_signals=["focus"],
        outcome_signals=["resume_ready"],
    )
    stale_situation = ArcSituation(
        arc_id=arc.arc_id,
        current_state="tentative",
        recent_progress=["old_progress"],
        blockers=[],
        next_moves=["old move"],
        linked_pattern_ids=[],
        computed_at=datetime(2026, 3, 30, 16, 0, tzinfo=UTC),
        confidence=0.2,
        staleness_seconds=300,
        refresh_reason="cache_miss",
    )
    refresh_time = datetime(2026, 3, 30, 18, 0, tzinfo=UTC)

    await sqlite_store.save_life_domain(domain)
    await sqlite_store.save_operational_arc(arc)
    await sqlite_store.save_arc_task(task)
    await sqlite_store.save_support_episode(episode)
    await sqlite_store.save_arc_situation(stale_situation)

    async def unexpected_archive_search(query: str) -> list[str]:
        raise AssertionError(f"archive search should not run for strong arc match: {query}")

    resume_context = await get_session_start_resume_context(
        sqlite_store,
        "I'm resuming the Web UI cleanup thread.",
        now=refresh_time,
        staleness_seconds=900,
        search_archive=unexpected_archive_search,
    )

    assert resume_context == ArcResumeContext(
        arc_snapshot=ArcSnapshot(arc=arc, tasks=[task], blockers=[], decisions=[], open_loops=[]),
        arc_situation=ArcSituation(
            arc_id=arc.arc_id,
            current_state="active",
            recent_progress=["resume_ready"],
            blockers=[],
            next_moves=["Extract the startup wiring from the view layer"],
            linked_pattern_ids=[],
            computed_at=refresh_time,
            confidence=0.85,
            staleness_seconds=900,
            refresh_reason="stale_cache",
        ),
        recent_episodes=[episode],
    )


@pytest.mark.asyncio
async def test_orientation_message_without_arc_match_uses_global_situation_before_archive_recall(sqlite_store):
    """A broad orientation opening should refresh structured global state before archive recall."""
    domain = LifeDomain(
        domain_id="domain-work",
        name="Work",
        status="active",
        salience=0.99,
        created_at=datetime(2026, 3, 30, 18, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 18, 5, tzinfo=UTC),
    )
    arc = OperationalArc(
        arc_id="arc-webui-cleanup",
        title="Web UI cleanup",
        kind="project",
        primary_domain_id=domain.domain_id,
        status="active",
        salience=0.97,
        created_at=datetime(2026, 3, 30, 18, 10, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 18, 20, tzinfo=UTC),
        last_active_at=datetime(2026, 3, 30, 18, 19, tzinfo=UTC),
        evidence_ref_ids=["ev-arc-3"],
    )
    task = ArcTask(
        task_id="task-runtime-boundary",
        arc_id=arc.arc_id,
        title="Choose runtime boundary",
        status="in_progress",
        created_at=datetime(2026, 3, 30, 18, 21, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 18, 24, tzinfo=UTC),
        next_step="Pick the runtime entrypoint before further splitting modules",
        evidence_ref_ids=["ev-701"],
    )
    blocker = ArcBlocker(
        blocker_id="blocker-app-structure-ambiguity",
        arc_id=arc.arc_id,
        title="App structure ambiguity",
        status="active",
        created_at=datetime(2026, 3, 30, 18, 22, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 18, 26, tzinfo=UTC),
        next_step="Choose one startup seam",
        evidence_ref_ids=["ev-702"],
    )
    decision = ArcDecision(
        decision_id="decision-runtime-entrypoint",
        arc_id=arc.arc_id,
        title="Where should runtime boot?",
        status="pending",
        created_at=datetime(2026, 3, 30, 18, 23, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 18, 27, tzinfo=UTC),
        current_tension="Keep startup simple while preserving flexibility",
        evidence_ref_ids=["ev-703"],
    )
    stale_global = GlobalSituation(
        active_domains=["Old Domain"],
        top_arcs=["Old Arc"],
        unresolved_decisions=["Old Decision"],
        top_blockers=["Old Blocker"],
        drift_risks=["Old Risk"],
        current_tensions=["Old Tension"],
        computed_at=datetime(2026, 3, 30, 17, 0, tzinfo=UTC),
        confidence=0.2,
        staleness_seconds=300,
        refresh_reason="cache_miss",
    )
    refresh_time = datetime(2026, 3, 30, 19, 0, tzinfo=UTC)

    await sqlite_store.save_life_domain(domain)
    await sqlite_store.save_operational_arc(arc)
    await sqlite_store.save_arc_task(task)
    await sqlite_store.save_arc_blocker(blocker)
    await sqlite_store.save_arc_decision(decision)
    await sqlite_store.save_global_situation(stale_global)

    async def unexpected_archive_search(query: str) -> list[str]:
        raise AssertionError(f"archive search should not run for broad orientation: {query}")

    orientation_context = await get_session_start_orientation_context(
        sqlite_store,
        "What is active right now?",
        now=refresh_time,
        staleness_seconds=900,
        search_archive=unexpected_archive_search,
    )

    assert orientation_context == OrientationContext(
        global_situation=GlobalSituation(
            active_domains=["Work"],
            top_arcs=["Web UI cleanup"],
            unresolved_decisions=["Where should runtime boot?"],
            top_blockers=["App structure ambiguity"],
            drift_risks=[],
            current_tensions=["Keep startup simple while preserving flexibility"],
            computed_at=refresh_time,
            confidence=0.8,
            staleness_seconds=900,
            refresh_reason="stale_cache",
        ),
        top_arc_snapshots=[ArcSnapshot(arc=arc, tasks=[task], blockers=[blocker], decisions=[decision], open_loops=[])],
    )


@pytest.mark.asyncio
async def test_active_work_questions_resolve_from_structured_operational_state(sqlite_store):
    """Active-work questions should resolve from structured state without archive search being required."""
    domain = LifeDomain(
        domain_id="domain-work",
        name="Work",
        status="active",
        salience=0.99,
        created_at=datetime(2026, 3, 30, 19, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 19, 5, tzinfo=UTC),
    )
    arc = OperationalArc(
        arc_id="arc-webui-cleanup",
        title="Web UI cleanup",
        kind="project",
        primary_domain_id=domain.domain_id,
        status="active",
        salience=0.97,
        created_at=datetime(2026, 3, 30, 19, 10, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 19, 20, tzinfo=UTC),
        last_active_at=datetime(2026, 3, 30, 19, 19, tzinfo=UTC),
        evidence_ref_ids=["ev-arc-4"],
    )
    task = ArcTask(
        task_id="task-bootstrap-boundary",
        arc_id=arc.arc_id,
        title="Pick bootstrap boundary",
        status="in_progress",
        created_at=datetime(2026, 3, 30, 19, 21, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 19, 24, tzinfo=UTC),
        next_step="Choose the first module boundary to extract",
        evidence_ref_ids=["ev-801"],
    )
    blocker = ArcBlocker(
        blocker_id="blocker-app-structure-ambiguity",
        arc_id=arc.arc_id,
        title="App structure ambiguity",
        status="active",
        created_at=datetime(2026, 3, 30, 19, 22, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 19, 26, tzinfo=UTC),
        next_step="Choose a seam before more edits",
        evidence_ref_ids=["ev-802"],
    )
    open_loop = ArcOpenLoop(
        open_loop_id="loop-bootstrap-seam",
        arc_id=arc.arc_id,
        title="Settle the bootstrap seam",
        status="pending_review",
        created_at=datetime(2026, 3, 30, 19, 23, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 19, 27, tzinfo=UTC),
        current_tension="Need one clear runtime seam before splitting more files",
        evidence_ref_ids=["ev-803"],
    )
    stale_global = GlobalSituation(
        active_domains=["Old Domain"],
        top_arcs=["Old Arc"],
        unresolved_decisions=[],
        top_blockers=["Old Blocker"],
        drift_risks=[],
        current_tensions=["Old Tension"],
        computed_at=datetime(2026, 3, 30, 18, 0, tzinfo=UTC),
        confidence=0.2,
        staleness_seconds=300,
        refresh_reason="cache_miss",
    )
    refresh_time = datetime(2026, 3, 30, 20, 0, tzinfo=UTC)

    await sqlite_store.save_life_domain(domain)
    await sqlite_store.save_operational_arc(arc)
    await sqlite_store.save_arc_task(task)
    await sqlite_store.save_arc_blocker(blocker)
    await sqlite_store.save_arc_open_loop(open_loop)
    await sqlite_store.save_global_situation(stale_global)

    async def unexpected_archive_search(query: str) -> list[str]:
        raise AssertionError(f"archive search should not run for active-work question: {query}")

    operational_context = await get_support_operational_context(
        sqlite_store,
        "What's blocked and what open loops still need attention?",
        now=refresh_time,
        staleness_seconds=900,
        search_archive=unexpected_archive_search,
    )

    assert operational_context == OrientationContext(
        global_situation=GlobalSituation(
            active_domains=["Work"],
            top_arcs=["Web UI cleanup"],
            unresolved_decisions=[],
            top_blockers=["App structure ambiguity"],
            drift_risks=[],
            current_tensions=["Need one clear runtime seam before splitting more files"],
            computed_at=refresh_time,
            confidence=0.8,
            staleness_seconds=900,
            refresh_reason="stale_cache",
        ),
        top_arc_snapshots=[ArcSnapshot(arc=arc, tasks=[task], blockers=[blocker], decisions=[], open_loops=[open_loop])],
    )


@pytest.mark.asyncio
async def test_operational_context_falls_back_to_archive_search_when_no_structured_match_exists(sqlite_store):
    """Archive search should remain available when structured operational retrieval has no match."""
    archive_queries: list[str] = []

    async def archive_search(query: str) -> list[str]:
        archive_queries.append(query)
        return ["session-hit"]

    operational_context = await get_support_operational_context(
        sqlite_store,
        "Can you remind me what we talked about last Tuesday?",
        search_archive=archive_search,
    )

    assert operational_context is None
    assert archive_queries == ["Can you remind me what we talked about last Tuesday?"]
