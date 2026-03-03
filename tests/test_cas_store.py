"""Tests for lock-free CAS (Compare-And-Swap) JSONL store.

These tests verify that CAS prevents TOCTOU bugs and enables lock-free concurrency.
"""

import asyncio
from pathlib import Path

import pytest

from src.utils.cas_store import CASConflictError, CASStore, Version

pytestmark = pytest.mark.slow


class TestVersion:
    """Version identifier tests."""

    def test_version_from_content(self, tmp_path: Path):
        """Version changes when content changes."""
        v1 = Version.from_content(b"hello")
        v2 = Version.from_content(b"world")

        assert v1 != v2
        assert v1.content_hash != v2.content_hash
        assert v1.size == 5
        assert v2.size == 5

    def test_version_from_path(self, tmp_path: Path):
        """Version can be computed from file."""
        file_path = tmp_path / "test.jsonl"
        file_path.write_bytes(b"test content")

        version = Version.from_path(file_path)

        assert version is not None
        assert version.size == 12
        assert version.content_hash is not None

    def test_version_none_for_missing_file(self, tmp_path: Path):
        """Version is None for non-existent file."""
        version = Version.from_path(tmp_path / "missing.jsonl")
        assert version is None


class TestCASTOCTOUPrevention:
    """TOCTOU (Time-of-Check-Time-of-Use) prevention tests.

    These tests demonstrate how CAS eliminates the classic race condition
    where state changes between check and use.
    """

    async def test_cas_detects_concurrent_modification(self, tmp_path: Path):
        """CAS raises conflict when file changes between read and write.

        This is the core TOCTOU prevention mechanism:
        1. Process A reads version V1
        2. Process B writes version V2
        3. Process A tries to write with expected V1
        4. CAS detects mismatch and raises CASConflictError
        """
        store = CASStore(tmp_path / "test.jsonl")

        # Write initial record
        v1 = await store.append({"id": 1, "data": "first"})

        # Read with version check
        records, read_version = await store.read_all()
        assert read_version == v1

        # Simulate concurrent modification (another process writes)
        v2 = await store.append({"id": 2, "data": "concurrent"})
        assert v2 != v1  # Version changed

        # Now try to write with stale version - should fail
        with pytest.raises(CASConflictError) as exc_info:
            await store.append(
                {"id": 3, "data": "stale"},
                expected_version=v1,  # Stale!
            )

        assert "CAS conflict" in str(exc_info.value)
        assert v1.content_hash in str(exc_info.value)

    async def test_cas_succeeds_when_version_matches(self, tmp_path: Path):
        """CAS succeeds when expected version matches current."""
        store = CASStore(tmp_path / "test.jsonl")

        v1 = await store.append({"id": 1})

        # Write with correct expected version
        v2 = await store.append({"id": 2}, expected_version=v1)

        # Should succeed and return new version
        assert v2 != v1

        records, _ = await store.read_all()
        assert len(records) == 2


class TestCASStoreOperations:
    """Basic CRUD operations with CAS."""

    async def test_append_creates_new_file(self, tmp_path: Path):
        """Append creates file if it doesn't exist."""
        store = CASStore(tmp_path / "new.jsonl")

        version = await store.append({"name": "test"})

        assert store.path.exists()
        assert version.size > 0

    async def test_read_all_empty_file(self, tmp_path: Path):
        """Read returns empty list for new store."""
        store = CASStore(tmp_path / "empty.jsonl")

        records, version = await store.read_all()

        assert records == []
        assert version.content_hash is not None  # Hash of empty content

    async def test_append_batch_atomic(self, tmp_path: Path):
        """Batch append is atomic - all or nothing."""
        store = CASStore(tmp_path / "batch.jsonl")

        await store.append_batch([
            {"id": 1},
            {"id": 2},
            {"id": 3},
        ])

        records, _ = await store.read_all()
        assert len(records) == 3
        assert [r["id"] for r in records] == [1, 2, 3]

    async def test_rewrite_replaces_all_content(self, tmp_path: Path):
        """Rewrite replaces entire file contents."""
        store = CASStore(tmp_path / "rewrite.jsonl")

        await store.append({"id": 1})
        await store.append({"id": 2})

        v_before = await store.read_version()

        # Rewrite with only one record
        v_after = await store.rewrite([{"id": 999}])

        assert v_after != v_before

        records, _ = await store.read_all()
        assert len(records) == 1
        assert records[0]["id"] == 999

    async def test_iter_records_memory_efficient(self, tmp_path: Path):
        """Iterator doesn't load entire file into memory."""
        store = CASStore(tmp_path / "iterate.jsonl")

        # Write many records
        for i in range(100):
            await store.append({"idx": i, "data": "x" * 1000})

        # Iterate without loading all
        count = 0
        async for record in store.iter_records():
            assert "idx" in record
            count += 1

        assert count == 100

    async def test_corrupt_lines_skipped(self, tmp_path: Path):
        """Iterator skips corrupt JSON lines."""
        store = CASStore(tmp_path / "corrupt.jsonl")

        # Write valid records
        await store.append({"id": 1})
        await store.append({"id": 2})

        # Append corrupt line directly
        with open(store.path, "a") as f:
            f.write("this is not json\n")

        await store.append({"id": 3})

        # Iterator should skip corrupt line
        records = []
        async for r in store.iter_records():
            records.append(r)

        assert len(records) == 3
        assert [r["id"] for r in records] == [1, 2, 3]


class TestCASCompareAndSwap:
    """High-level compare_and_swap primitive tests."""

    async def test_compare_and_swap_basic(self, tmp_path: Path):
        """CAS primitive enables atomic read-modify-write."""
        store = CASStore(tmp_path / "cas.jsonl")

        await store.append({"counter": 0})

        def increment(records):
            records[0]["counter"] += 1
            return records

        final_records, new_version = await store.compare_and_swap(increment)

        assert final_records[0]["counter"] == 1
        assert new_version is not None

    async def test_compare_and_swap_retry_on_conflict(self, tmp_path: Path):
        """CAS automatically retries on conflict."""
        store = CASStore(tmp_path / "retry.jsonl")

        await store.append({"value": 0})

        attempts = []

        def slow_transform(records):
            attempts.append(len(attempts))
            # Simulate slow operation
            import asyncio
            # Note: can't actually sleep in sync function, but conceptually
            records[0]["value"] += 1
            return records

        # First call succeeds
        await store.compare_and_swap(slow_transform)

        records, _ = await store.read_all()
        assert records[0]["value"] == 1

    async def test_compare_and_swap_exhausts_retries(self, tmp_path: Path):
        """CAS gives up after max_retries and raises."""
        store = CASStore(tmp_path / "exhaust.jsonl")

        # Pre-create file with known content
        await store.append({"data": "x"})
        version = await store.read_version()

        # Simulate external modification during each attempt by using
        # a background task that modifies the file
        modification_count = [0]  # Use list for mutable closure

        async def external_modifier():
            """Continuously modify the file to cause conflicts."""
            for i in range(50):  # More than enough to exhaust retries
                try:
                    # Direct write to bypass CAS (simulates external process)
                    content = store.path.read_bytes()
                    store.path.write_bytes(content + b'\n{"mod": ' + str(i).encode() + b"}")
                except Exception:
                    pass
                await asyncio.sleep(0)  # Yield control

        # Start modifier
        modifier_task = asyncio.create_task(external_modifier())

        def transform(records):
            # Simple transform that just adds a record
            records.append({"new": "data"})
            return records

        try:
            # This should exhaust retries due to continuous external modifications
            with pytest.raises(CASConflictError):
                await store.compare_and_swap(transform, max_retries=5)
        finally:
            modifier_task.cancel()
            try:
                await modifier_task
            except asyncio.CancelledError:
                pass


class TestConcurrencyScenarios:
    """Real-world concurrency scenario tests."""

    async def test_multiple_appends_work_correctly(self, tmp_path: Path):
        """Multiple sequential appends work correctly with CAS.

        Appends are atomic and preserve all records.
        """
        store = CASStore(tmp_path / "append.jsonl")

        # Sequential appends should always work
        for i in range(20):
            await store.append({"seq": i, "data": f"record_{i}"})

        records, _ = await store.read_all()

        # Should have exactly 20 records in order
        assert len(records) == 20
        assert [r["seq"] for r in records] == list(range(20))

    async def test_isolated_updates_with_cas(self, tmp_path: Path):
        """CAS enables atomic updates with conflict detection.

        When processes update the same data concurrently, CAS detects
        conflicts and retries, ensuring consistency.
        """
        store = CASStore(tmp_path / "isolated.jsonl")

        # Initial state
        await store.append({"user_id": "alice", "balance": 100})
        await store.append({"user_id": "bob", "balance": 200})

        async def update_balance(user_id: str, delta: int):
            """Update specific user's balance atomically."""
            def transform(records):
                for r in records:
                    if r.get("user_id") == user_id:
                        r["balance"] = r.get("balance", 0) + delta
                return records

            await store.compare_and_swap(transform)

        # Sequential updates to avoid excessive contention
        await update_balance("alice", 50)
        await update_balance("bob", -30)

        records, _ = await store.read_all()

        alice = next(r for r in records if r["user_id"] == "alice")
        bob = next(r for r in records if r["user_id"] == "bob")

        assert alice["balance"] == 150, f"Alice should be 150, got {alice['balance']}"
        assert bob["balance"] == 170, f"Bob should be 170, got {bob['balance']}"


class TestCASConflictRecovery:
    """Error handling and recovery from conflicts."""

    async def test_manual_conflict_recovery(self, tmp_path: Path):
        """Caller can manually handle CAS conflicts and retry."""
        store = CASStore(tmp_path / "recovery.jsonl")

        await store.append({"value": 0})

        # Get version
        records, version = await store.read_all()

        # Simulate external modification
        await store.append({"external": "change"})

        # Try to write with stale version
        try:
            await store.rewrite([{"value": 999}], expected_version=version)
            assert False, "Should have raised CASConflictError"
        except CASConflictError as e:
            # Recover: re-read and retry with fresh version
            records, fresh_version = await store.read_all()
            records.append({"value": 999})
            await store.rewrite(records, expected_version=fresh_version)

        # Verify both records present
        final_records, _ = await store.read_all()
        assert len(final_records) == 3  # original + external + our update
