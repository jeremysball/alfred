"""Tests for canonical transcript message storage in SQLiteStore."""

from __future__ import annotations

import json

import aiosqlite
import pytest

from alfred.storage.sqlite import SQLiteStore


@pytest.fixture
async def sqlite_store(tmp_path):
    """Create a temporary SQLiteStore for transcript normalization tests."""
    store = SQLiteStore(tmp_path / "session_messages.db")
    await store._init()
    return store


@pytest.mark.asyncio
async def test_session_round_trips_through_canonical_session_messages(sqlite_store):
    """Sessions should round-trip through canonical transcript rows rather than a session JSON blob."""
    session_id = "sess_canonical"
    messages = [
        {
            "idx": 0,
            "id": "msg-0",
            "role": "user",
            "content": "Walk me back into the thread.",
            "timestamp": "2026-03-30T12:00:00+00:00",
        },
        {
            "idx": 1,
            "id": "msg-1",
            "role": "assistant",
            "content": "The Web UI cleanup arc is still active.",
            "timestamp": "2026-03-30T12:01:00+00:00",
            "toolCalls": [{"toolCallId": "tool-1", "status": "success"}],
        },
    ]
    metadata = {"topic": "transcript-normalization"}

    await sqlite_store.save_session(session_id, messages, metadata)

    loaded_session = await sqlite_store.load_session(session_id)
    assert loaded_session is not None
    assert loaded_session["messages"] == messages
    assert loaded_session["metadata"] == metadata

    async with aiosqlite.connect(sqlite_store.db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row

        async with db.execute("PRAGMA table_info(sessions)") as cursor:
            session_columns = {row["name"] for row in await cursor.fetchall()}

        async with db.execute(
            """
            SELECT session_id, message_id, message_idx, role, timestamp, payload_json
            FROM session_messages
            WHERE session_id = ?
            ORDER BY message_idx ASC
            """,
            (session_id,),
        ) as cursor:
            transcript_rows = await cursor.fetchall()

    assert "messages" not in session_columns
    assert [
        (row["session_id"], row["message_id"], row["message_idx"], row["role"], row["timestamp"])
        for row in transcript_rows
    ] == [
        (session_id, "msg-0", 0, "user", "2026-03-30T12:00:00+00:00"),
        (session_id, "msg-1", 1, "assistant", "2026-03-30T12:01:00+00:00"),
    ]
    assert [json.loads(row["payload_json"]) for row in transcript_rows] == messages
