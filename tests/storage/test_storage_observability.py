from __future__ import annotations

import json

import aiosqlite
import pytest

from alfred.storage.sqlite import SQLiteStore


@pytest.fixture
async def sqlite_store(tmp_path):
    store = SQLiteStore(tmp_path / "storage-observability.db", embedding_dim=3)
    await store._init()
    return store


async def _seed_summary_vector(
    sqlite_store: SQLiteStore,
    summary_id: str,
    embedding: list[float],
) -> None:
    async with aiosqlite.connect(sqlite_store.db_path) as db:
        await sqlite_store._load_extensions(db)
        await db.execute(
            "INSERT INTO session_summaries_vec (summary_id, embedding) VALUES (?, ?)",
            (summary_id, json.dumps(embedding)),
        )
        await db.commit()


@pytest.mark.asyncio
async def test_sqlite_store_logs_search_and_persistence_boundaries(
    sqlite_store: SQLiteStore,
    caplog: pytest.LogCaptureFixture,
) -> None:
    message_embedding = [1.0, 0.0, 0.0]
    summary_embedding = [1.0, 0.0, 0.0]
    session_id = "session-log"
    summary_id = "summary-log"

    session_messages = [
        {
            "idx": 0,
            "id": "msg-0",
            "role": "user",
            "content": "hello",
            "timestamp": "2026-03-21T00:00:00+00:00",
            "embedding": message_embedding,
        }
    ]
    summary = {
        "summary_id": summary_id,
        "session_id": session_id,
        "message_count": 1,
        "first_message_idx": 0,
        "last_message_idx": 0,
        "summary_text": "A concise summary",
        "embedding": summary_embedding,
        "version": 1,
    }

    with caplog.at_level("DEBUG", logger="alfred.storage.sqlite"):
        await sqlite_store.save_session(
            session_id,
            session_messages,
            metadata={"source": "observability-test"},
        )
        await sqlite_store.save_summary(summary)
        await _seed_summary_vector(sqlite_store, summary_id, summary_embedding)
        summary_results = await sqlite_store.search_summaries(summary_embedding, top_k=1)
        message_results = await sqlite_store.search_session_messages(
            session_id,
            message_embedding,
            top_k=1,
        )

    assert summary_results[0]["summary_id"] == summary_id
    assert message_results[0]["message_idx"] == 0

    storage_messages = [record.message for record in caplog.records if record.name == "alfred.storage.sqlite"]
    assert any(message.startswith("event=storage.session_save.start") for message in storage_messages)
    assert any(message.startswith("event=storage.session_save.completed") and "duration_ms=" in message for message in storage_messages)
    assert any("message_count=1" in message for message in storage_messages)
    assert any("has_metadata=true" in message for message in storage_messages)

    assert any(message.startswith("event=storage.session_summary_save.start") for message in storage_messages)
    assert any(
        message.startswith("event=storage.session_summary_save.completed") and "duration_ms=" in message for message in storage_messages
    )
    assert any("summary_id=summary-log" in message for message in storage_messages)
    assert any("has_embedding=true" in message for message in storage_messages)

    assert any(message.startswith("event=storage.session_summary_search.start") for message in storage_messages)
    assert any(
        message.startswith("event=storage.session_summary_search.completed") and "duration_ms=" in message for message in storage_messages
    )
    assert any("result_count=1" in message for message in storage_messages)

    assert any(message.startswith("event=storage.session_message_search.start") for message in storage_messages)
    assert any(
        message.startswith("event=storage.session_message_search.completed") and "duration_ms=" in message for message in storage_messages
    )
    assert any("session_id=session-log" in message for message in storage_messages)
    assert any("result_count=1" in message for message in storage_messages)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "call_kwargs", "expected_event"),
    [
        (
            "save_session",
            {
                "session_id": "session-log",
                "messages": [
                    {
                        "idx": 0,
                        "id": "msg-0",
                        "role": "user",
                        "content": "hello",
                        "timestamp": "2026-03-21T00:00:00+00:00",
                    }
                ],
                "metadata": {"source": "observability-test"},
            },
            "storage.session_save.failed",
        ),
        (
            "save_summary",
            {
                "summary": {
                    "summary_id": "summary-log",
                    "session_id": "session-log",
                    "message_count": 1,
                    "first_message_idx": 0,
                    "last_message_idx": 0,
                    "summary_text": "A concise summary",
                    "version": 1,
                }
            },
            "storage.session_summary_save.failed",
        ),
    ],
)
async def test_storage_persistence_logs_failure_boundaries(
    sqlite_store: SQLiteStore,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    method_name: str,
    call_kwargs: dict[str, object],
    expected_event: str,
) -> None:
    async def _boom(_db: object) -> None:
        raise RuntimeError("storage unavailable")

    monkeypatch.setattr(sqlite_store, "_load_extensions", _boom)

    with (
        caplog.at_level("DEBUG", logger="alfred.storage.sqlite"),
        pytest.raises(
            RuntimeError,
            match="storage unavailable",
        ),
    ):
        await getattr(sqlite_store, method_name)(**call_kwargs)

    storage_messages = [record.message for record in caplog.records if record.name == "alfred.storage.sqlite"]
    assert any(message.startswith(f"event={expected_event}") for message in storage_messages)
    assert any("error_type=RuntimeError" in message for message in storage_messages)
    assert any("duration_ms=" in message for message in storage_messages)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "call_args", "expected_event"),
    [
        (
            "search_summaries",
            ([1.0, 0.0, 0.0],),
            "storage.session_summary_search.failed",
        ),
        (
            "search_session_messages",
            ("session-log", [1.0, 0.0, 0.0]),
            "storage.session_message_search.failed",
        ),
    ],
)
async def test_storage_search_logs_failure_boundaries(
    sqlite_store: SQLiteStore,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    method_name: str,
    call_args: tuple[object, ...],
    expected_event: str,
) -> None:
    async def _boom(_db: object) -> None:
        raise RuntimeError("storage unavailable")

    monkeypatch.setattr(sqlite_store, "_load_extensions", _boom)

    with (
        caplog.at_level("DEBUG", logger="alfred.storage.sqlite"),
        pytest.raises(
            RuntimeError,
            match="storage unavailable",
        ),
    ):
        await getattr(sqlite_store, method_name)(*call_args, top_k=1)

    storage_messages = [record.message for record in caplog.records if record.name == "alfred.storage.sqlite"]
    assert any(message.startswith(f"event={expected_event}") for message in storage_messages)
    assert any("error_type=RuntimeError" in message for message in storage_messages)
    assert any("duration_ms=" in message for message in storage_messages)
