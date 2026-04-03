"""Tests for support-profile value storage in SQLiteStore."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from alfred.memory.support_profile import SupportProfileScope, SupportProfileValue
from alfred.storage.sqlite import SQLiteStore


@pytest.fixture
async def sqlite_store(tmp_path):
    """Create a temporary SQLiteStore for support-profile tests."""
    store = SQLiteStore(tmp_path / "support_profile.db")
    await store._init()
    return store


@pytest.mark.asyncio
async def test_support_profile_values_round_trip_through_sqlite_store(sqlite_store):
    """Support-profile values should round-trip through SQLite without losing scope or evidence refs."""
    global_relational = SupportProfileValue(
        registry="relational",
        dimension="warmth",
        scope=SupportProfileScope(type="global", id="user"),
        value="high",
        status="confirmed",
        confidence=1.0,
        source="explicit",
        created_at=datetime(2026, 3, 30, 10, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 10, 0, tzinfo=UTC),
        evidence_refs=("ev-global",),
    )
    context_support = SupportProfileValue(
        registry="support",
        dimension="option_bandwidth",
        scope=SupportProfileScope(type="context", id="execute"),
        value="single",
        status="observed",
        confidence=0.87,
        source="auto_adapted",
        created_at=datetime(2026, 3, 30, 10, 5, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 10, 8, tzinfo=UTC),
        evidence_refs=("ev-1", "ev-2"),
    )
    arc_support = SupportProfileValue(
        registry="support",
        dimension="pacing",
        scope=SupportProfileScope(type="arc", id="webui_cleanup"),
        value="brisk",
        status="candidate",
        confidence=0.61,
        source="corrected",
        created_at=datetime(2026, 3, 30, 10, 9, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 10, 11, tzinfo=UTC),
        evidence_refs=("ev-arc",),
    )

    await sqlite_store.save_support_profile_value(global_relational)
    await sqlite_store.save_support_profile_value(context_support)
    await sqlite_store.save_support_profile_value(arc_support)

    assert (
        await sqlite_store.get_support_profile_value(
            "support",
            "option_bandwidth",
            SupportProfileScope(type="context", id="execute"),
        )
        == context_support
    )

    assert await sqlite_store.list_support_profile_values() == [
        global_relational,
        context_support,
        arc_support,
    ]


@pytest.mark.asyncio
async def test_sqlite_store_resolves_most_specific_support_profile_value(sqlite_store):
    """Support-profile resolution should prefer arc, then context, then global scope."""
    global_value = SupportProfileValue(
        registry="support",
        dimension="option_bandwidth",
        scope=SupportProfileScope(type="global", id="user"),
        value="few",
        status="confirmed",
        confidence=0.93,
        source="explicit",
        created_at=datetime(2026, 3, 30, 11, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 11, 0, tzinfo=UTC),
        evidence_refs=("ev-global",),
    )
    context_value = SupportProfileValue(
        registry="support",
        dimension="option_bandwidth",
        scope=SupportProfileScope(type="context", id="execute"),
        value="single",
        status="observed",
        confidence=0.81,
        source="auto_adapted",
        created_at=datetime(2026, 3, 30, 11, 5, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 11, 6, tzinfo=UTC),
        evidence_refs=("ev-context",),
    )
    arc_value = SupportProfileValue(
        registry="support",
        dimension="option_bandwidth",
        scope=SupportProfileScope(type="arc", id="webui_cleanup"),
        value="many",
        status="candidate",
        confidence=0.55,
        source="corrected",
        created_at=datetime(2026, 3, 30, 11, 7, tzinfo=UTC),
        updated_at=datetime(2026, 3, 30, 11, 8, tzinfo=UTC),
        evidence_refs=("ev-arc",),
    )

    await sqlite_store.save_support_profile_value(global_value)
    await sqlite_store.save_support_profile_value(context_value)
    await sqlite_store.save_support_profile_value(arc_value)

    assert (
        await sqlite_store.resolve_support_profile_value(
            "support",
            "option_bandwidth",
            context_id="execute",
            arc_id="webui_cleanup",
        )
        == arc_value
    )
    assert (
        await sqlite_store.resolve_support_profile_value(
            "support",
            "option_bandwidth",
            context_id="execute",
        )
        == context_value
    )
    assert (
        await sqlite_store.resolve_support_profile_value(
            "support",
            "option_bandwidth",
            context_id="plan",
        )
        == global_value
    )
    assert await sqlite_store.resolve_support_profile_value("support", "option_bandwidth") == global_value
    assert await sqlite_store.resolve_support_profile_value("support", "pacing", context_id="execute") is None
