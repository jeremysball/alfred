"""Support-memory context helpers for derived arc situations."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from alfred.memory.support_memory import (
    ArcSituation,
    ArcSnapshot,
    GlobalSituation,
    LifeDomain,
    OperationalArc,
    SupportEpisode,
)

if TYPE_CHECKING:
    from alfred.storage.sqlite import SQLiteStore


@dataclass(eq=True)
class ArcResumeContext:
    """Structured resume payload for a fresh session that matches an existing arc."""

    arc_snapshot: ArcSnapshot
    arc_situation: ArcSituation
    recent_episodes: list[SupportEpisode] = field(default_factory=list)


@dataclass(eq=True)
class OrientationContext:
    """Structured orientation payload for broad fresh-session openings."""

    global_situation: GlobalSituation
    top_arc_snapshots: list[ArcSnapshot] = field(default_factory=list)


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    """Return values without duplicates while preserving the first-seen order."""
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _normalize_resume_text(text: str) -> str:
    """Normalize user text or arc titles for deterministic strong-match checks."""
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _find_strong_resume_arc_match(opening_message: str, arcs: Sequence[OperationalArc]) -> OperationalArc | None:
    """Return the best strong arc match for a fresh-session opening message."""
    normalized_message = _normalize_resume_text(opening_message)
    if not normalized_message:
        return None

    for arc in arcs:
        normalized_title = _normalize_resume_text(arc.title)
        if normalized_title and normalized_title in normalized_message:
            return arc
    return None


def _is_broad_orientation_message(opening_message: str) -> bool:
    """Return True when the opening message asks for broad operational orientation."""
    normalized_message = _normalize_resume_text(opening_message)
    if not normalized_message:
        return False

    return any(
        phrase in normalized_message
        for phrase in (
            "what is active right now",
            "what s active right now",
            "what is active",
            "what s active",
        )
    )


def derive_arc_situation(
    snapshot: ArcSnapshot,
    recent_episodes: list[SupportEpisode],
    *,
    now: datetime,
    staleness_seconds: int,
    refresh_reason: str,
) -> ArcSituation:
    """Derive a refreshable arc situation from structured arc state and recent episodes."""
    blockers = [blocker.title for blocker in snapshot.blockers if blocker.status not in {"resolved", "archived"}]

    next_moves: list[str] = []
    for task in snapshot.tasks:
        if task.status in {"done", "archived", "cancelled"}:
            continue
        if task.next_step:
            next_moves.append(task.next_step)
    for blocker in snapshot.blockers:
        if blocker.status in {"resolved", "archived"}:
            continue
        if blocker.next_step:
            next_moves.append(blocker.next_step)

    recent_progress: list[str] = []
    for episode in recent_episodes:
        if episode.outcome_signals:
            recent_progress.extend(episode.outcome_signals)
        elif episode.response_signals:
            recent_progress.extend(episode.response_signals)

    has_recent_episodes = bool(recent_episodes)
    return ArcSituation(
        arc_id=snapshot.arc.arc_id,
        current_state=snapshot.arc.status,
        recent_progress=_dedupe_preserve_order(recent_progress),
        blockers=_dedupe_preserve_order(blockers),
        next_moves=_dedupe_preserve_order(next_moves),
        linked_pattern_ids=[],
        computed_at=now,
        confidence=0.85 if has_recent_episodes else 0.7,
        staleness_seconds=staleness_seconds,
        refresh_reason=refresh_reason,
    )


def derive_global_situation(
    active_domains: list[LifeDomain],
    top_arc_snapshots: list[ArcSnapshot],
    *,
    now: datetime,
    staleness_seconds: int,
    refresh_reason: str,
) -> GlobalSituation:
    """Derive a refreshable broad operational situation from structured state."""
    unresolved_decisions: list[str] = []
    top_blockers: list[str] = []
    drift_risks: list[str] = []
    current_tensions: list[str] = []

    for snapshot in top_arc_snapshots:
        if snapshot.arc.status == "dormant":
            drift_risks.append(snapshot.arc.title)

        for blocker in snapshot.blockers:
            if blocker.status in {"resolved", "archived"}:
                continue
            top_blockers.append(blocker.title)

        for decision in snapshot.decisions:
            if decision.status in {"resolved", "archived"}:
                continue
            unresolved_decisions.append(decision.title)
            if decision.current_tension:
                current_tensions.append(decision.current_tension)

        for open_loop in snapshot.open_loops:
            if open_loop.status in {"resolved", "archived"}:
                continue
            if open_loop.current_tension:
                current_tensions.append(open_loop.current_tension)

    has_structured_state = bool(active_domains or top_arc_snapshots)
    return GlobalSituation(
        active_domains=_dedupe_preserve_order([domain.name for domain in active_domains]),
        top_arcs=_dedupe_preserve_order([snapshot.arc.title for snapshot in top_arc_snapshots]),
        unresolved_decisions=_dedupe_preserve_order(unresolved_decisions),
        top_blockers=_dedupe_preserve_order(top_blockers),
        drift_risks=_dedupe_preserve_order(drift_risks),
        current_tensions=_dedupe_preserve_order(current_tensions),
        computed_at=now,
        confidence=0.8 if has_structured_state else 0.6,
        staleness_seconds=staleness_seconds,
        refresh_reason=refresh_reason,
    )


async def get_fresh_arc_situation(
    store: SQLiteStore,
    arc_id: str,
    *,
    now: datetime | None = None,
    staleness_seconds: int = 900,
) -> ArcSituation | None:
    """Return a fresh arc situation, refreshing persisted state when the cache is stale."""
    effective_now = now if now is not None else datetime.now(UTC)

    cached = await store.get_arc_situation(arc_id)
    if cached is not None and not cached.is_stale(effective_now):
        return cached

    snapshot = await store.get_arc_snapshot(arc_id)
    if snapshot is None:
        return None

    recent_episodes = await store.list_support_episodes_for_arc(arc_id, limit=3)
    refreshed = derive_arc_situation(
        snapshot,
        recent_episodes,
        now=effective_now,
        staleness_seconds=staleness_seconds,
        refresh_reason="cache_miss" if cached is None else "stale_cache",
    )
    await store.save_arc_situation(refreshed)
    return refreshed


async def get_fresh_global_situation(
    store: SQLiteStore,
    *,
    now: datetime | None = None,
    staleness_seconds: int = 900,
) -> GlobalSituation:
    """Return a fresh global situation, refreshing persisted state when the cache is stale."""
    effective_now = now if now is not None else datetime.now(UTC)

    cached = await store.get_global_situation()
    if cached is not None and not cached.is_stale(effective_now):
        return cached

    active_domains = await store.list_active_life_domains(limit=4)
    candidate_arcs = await store.list_resume_arcs(limit=5)
    top_arc_snapshots: list[ArcSnapshot] = []
    for arc in candidate_arcs:
        snapshot = await store.get_arc_snapshot(arc.arc_id)
        if snapshot is not None:
            top_arc_snapshots.append(snapshot)

    refreshed = derive_global_situation(
        active_domains,
        top_arc_snapshots,
        now=effective_now,
        staleness_seconds=staleness_seconds,
        refresh_reason="cache_miss" if cached is None else "stale_cache",
    )
    await store.save_global_situation(refreshed)
    return refreshed


async def get_session_start_resume_context(
    store: SQLiteStore,
    opening_message: str,
    *,
    now: datetime | None = None,
    staleness_seconds: int = 900,
    search_archive: Callable[[str], Awaitable[Sequence[str]]] | None = None,
) -> ArcResumeContext | None:
    """Load structured resume context for a fresh-session opening message when an arc strongly matches."""
    candidate_arcs = await store.list_resume_arcs()
    matched_arc = _find_strong_resume_arc_match(opening_message, candidate_arcs)
    if matched_arc is None:
        if search_archive is not None:
            await search_archive(opening_message)
        return None

    arc_snapshot = await store.get_arc_snapshot(matched_arc.arc_id)
    if arc_snapshot is None:
        return None

    arc_situation = await get_fresh_arc_situation(
        store,
        matched_arc.arc_id,
        now=now,
        staleness_seconds=staleness_seconds,
    )
    if arc_situation is None:
        return None

    recent_episodes = await store.list_support_episodes_for_arc(matched_arc.arc_id, limit=3)
    return ArcResumeContext(
        arc_snapshot=arc_snapshot,
        arc_situation=arc_situation,
        recent_episodes=recent_episodes,
    )


async def get_session_start_orientation_context(
    store: SQLiteStore,
    opening_message: str,
    *,
    now: datetime | None = None,
    staleness_seconds: int = 900,
    search_archive: Callable[[str], Awaitable[Sequence[str]]] | None = None,
) -> OrientationContext | None:
    """Load broad structured orientation context for a fresh-session opening message."""
    if not _is_broad_orientation_message(opening_message):
        if search_archive is not None:
            await search_archive(opening_message)
        return None

    global_situation = await get_fresh_global_situation(
        store,
        now=now,
        staleness_seconds=staleness_seconds,
    )
    top_arc_snapshots: list[ArcSnapshot] = []
    for arc in await store.list_resume_arcs(limit=3):
        snapshot = await store.get_arc_snapshot(arc.arc_id)
        if snapshot is not None:
            top_arc_snapshots.append(snapshot)

    return OrientationContext(
        global_situation=global_situation,
        top_arc_snapshots=top_arc_snapshots,
    )
