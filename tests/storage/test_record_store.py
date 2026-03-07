"""Tests for JSONL record store backend."""

from pathlib import Path

import pytest

from src.storage.record_store import JsonlRecordStore


def test_record_store_read_empty(tmp_path: Path) -> None:
    """Missing files should return no records."""
    store = JsonlRecordStore(tmp_path / "records.jsonl")

    assert store.read_all() == []


@pytest.mark.asyncio
async def test_record_store_append_and_iter_async(tmp_path: Path) -> None:
    """Append writes records that can be read asynchronously."""
    store = JsonlRecordStore(tmp_path / "records.jsonl")

    await store.append({"name": "alpha"})
    await store.append({"name": "beta"})

    records = []
    async for record in store.iter_records_async():
        records.append(record)

    assert records == [{"name": "alpha"}, {"name": "beta"}]
    assert await store.read_all_async() == records


@pytest.mark.asyncio
async def test_record_store_rewrite_replaces_contents(tmp_path: Path) -> None:
    """Rewrite should replace existing records atomically."""
    store = JsonlRecordStore(tmp_path / "records.jsonl")

    await store.append({"name": "alpha"})
    await store.rewrite([{"name": "gamma"}])

    assert store.read_all() == [{"name": "gamma"}]
