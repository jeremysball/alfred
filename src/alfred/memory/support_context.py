"""Support-memory context helpers for derived arc situations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from alfred.memory.support_memory import ArcSituation, ArcSnapshot, SupportEpisode

if TYPE_CHECKING:
    from alfred.storage.sqlite import SQLiteStore


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
