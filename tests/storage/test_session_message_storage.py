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


@pytest.mark.asyncio
async def test_save_session_replaces_canonical_message_rows_after_history_edit(sqlite_store):
    """Re-saving shorter edited history should replace stale canonical transcript rows."""
    session_id = "sess_rewrite"
    initial_messages = [
        {
            "idx": 0,
            "id": "msg-0",
            "role": "user",
            "content": "First draft",
            "timestamp": "2026-03-30T12:10:00+00:00",
        },
        {
            "idx": 1,
            "id": "msg-1",
            "role": "assistant",
            "content": "First reply",
            "timestamp": "2026-03-30T12:11:00+00:00",
        },
        {
            "idx": 2,
            "id": "msg-2",
            "role": "user",
            "content": "Second draft",
            "timestamp": "2026-03-30T12:12:00+00:00",
        },
    ]
    updated_messages = [
        {
            "idx": 0,
            "id": "msg-0",
            "role": "user",
            "content": "First draft",
            "timestamp": "2026-03-30T12:10:00+00:00",
        },
        {
            "idx": 1,
            "id": "msg-1",
            "role": "assistant",
            "content": "First reply, revised",
            "timestamp": "2026-03-30T12:11:30+00:00",
        },
    ]

    await sqlite_store.save_session(session_id, initial_messages, {"revision": "initial"})
    await sqlite_store.save_session(session_id, updated_messages, {"revision": "revised"})

    loaded_session = await sqlite_store.load_session(session_id)
    assert loaded_session is not None
    assert loaded_session["messages"] == updated_messages
    assert loaded_session["metadata"] == {"revision": "revised"}

    async with aiosqlite.connect(sqlite_store.db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row

        async with db.execute(
            """
            SELECT message_id, message_idx, payload_json
            FROM session_messages
            WHERE session_id = ?
            ORDER BY message_idx ASC
            """,
            (session_id,),
        ) as cursor:
            transcript_rows = await cursor.fetchall()

        async with db.execute(
            "SELECT message_count, metadata FROM sessions WHERE session_id = ?",
            (session_id,),
        ) as cursor:
            session_row = await cursor.fetchone()

    assert [(row["message_id"], row["message_idx"]) for row in transcript_rows] == [
        ("msg-0", 0),
        ("msg-1", 1),
    ]
    assert [json.loads(row["payload_json"]) for row in transcript_rows] == updated_messages
    assert session_row is not None
    assert session_row["message_count"] == 2
    assert json.loads(session_row["metadata"]) == {"revision": "revised"}
