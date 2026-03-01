"""Lock-free JSONL store using Compare-And-Swap (CAS).

Implements optimistic concurrency control without locks.
Each write specifies the expected state; the operation succeeds
only if the current state matches.

.. warning::

    File-based CAS has a race window between version check and atomic rename.
    Two processes checking version simultaneously can both proceed, causing
    the second write to overwrite the first. See docs/CAS_ATOMICITY.md for details.

    This implementation provides "eventual consistency" suitable for low-
    contention scenarios. For strict serializability, use SQLite or add
    file locking.
"""

import hashlib
import json
import os
import tempfile
from collections.abc import AsyncIterator, Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiofiles


class CASConflictError(Exception):
    """Raised when CAS operation fails due to concurrent modification.

    The caller should retry the read-modify-write cycle.
    """

    def __init__(self, expected_version: str, actual_version: str):
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"CAS conflict: expected version {expected_version}, "
            f"but found {actual_version}"
        )


@dataclass(frozen=True)
class Version:
    """Immutable version identifier for a file state.

    Uses content hash for CAS comparison. The mtime_ns and size
    are informational but NOT part of equality - only content_hash
    matters for detecting changes.
    """
    content_hash: str
    mtime_ns: int
    size: int

    def __eq__(self, other: object) -> bool:
        """Versions are equal if their content hashes match."""
        if not isinstance(other, Version):
            return NotImplemented
        return self.content_hash == other.content_hash

    def __hash__(self) -> int:
        """Hash based only on content_hash."""
        return hash(self.content_hash)

    @classmethod
    def from_path(cls, path: Path) -> "Version | None":
        """Compute version from file path."""
        if not path.exists():
            return None
        stat = path.stat()
        # Hash first 4KB + last 4KB for large files (fingerprinting)
        content = path.read_bytes()
        return cls(
            content_hash=hashlib.blake2b(content, digest_size=16).hexdigest(),
            mtime_ns=stat.st_mtime_ns,
            size=stat.st_size,
        )

    @classmethod
    def from_content(cls, content: bytes) -> "Version":
        """Compute version from content (for new files)."""
        return cls(
            content_hash=hashlib.blake2b(content, digest_size=16).hexdigest(),
            mtime_ns=0,
            size=len(content),
        )


class CASStore:
    """Lock-free append-only and rewrite store using CAS.

    All mutating operations are atomic and optimistic:
    - They specify the expected version
    - They fail with CASConflictError if the file changed
    - Callers must retry on conflict

    This eliminates locks and prevents deadlocks while ensuring
    consistency in concurrent scenarios.
    """

    def __init__(self, path: Path, line_separator: str = "\n"):
        self.path = path
        self.line_separator = line_separator
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Ensure parent directory exists."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def read_version(self) -> Version | None:
        """Get current version of the store.

        Returns None if file doesn't exist.
        """
        return await self._version_async(self.path)

    async def read_all(
        self, expected_version: Version | None = None
    ) -> tuple[list[dict[str, Any]], Version]:
        """Read all records with optional version check.

        Args:
            expected_version: If provided, raises CASConflictError if file changed

        Returns:
            Tuple of (records, current_version)

        Raises:
            CASConflictError: If expected_version doesn't match current version
        """
        current_version = await self.read_version()

        if expected_version is not None and current_version != expected_version:
            raise CASConflictError(
                expected_version=str(expected_version),
                actual_version=str(current_version),
            )

        if current_version is None:
            return [], current_version or Version.from_content(b"")

        records = await self._read_records()
        return records, current_version

    async def append(
        self,
        record: dict[str, Any],
        expected_version: Version | None = None,
    ) -> Version:
        """Append a single record atomically using CAS.

        Args:
            record: Record to append
            expected_version: Version the caller believes is current.
                If None, automatically retries on conflict.
                If provided, raises CASConflictError on conflict.

        Returns:
            New version after successful append

        Raises:
            CASConflictError: If file was modified since expected_version
        """
        line = json.dumps(record, separators=(",", ":")) + self.line_separator
        line_bytes = line.encode("utf-8")

        if expected_version is not None:
            # Strict mode: caller wants explicit control
            return await self._append_bytes(line_bytes, expected_version)

        # Automatic retry mode: use compare_and_swap for atomic read-modify-write
        def transform(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
            new_record = json.loads(line_bytes.decode("utf-8").strip())
            records.append(new_record)
            return records

        final_records, new_version = await self.compare_and_swap(transform)
        return new_version

    async def append_batch(
        self,
        records: list[dict[str, Any]],
        expected_version: Version | None = None,
    ) -> Version:
        """Append multiple records atomically using CAS.

        All records are written together or not at all.
        """
        if not records:
            return expected_version or await self.read_version() or Version.from_content(b"")

        if expected_version is not None:
            lines = [
                json.dumps(r, separators=(",", ":")) + self.line_separator
                for r in records
            ]
            content = "".join(lines).encode("utf-8")
            return await self._append_bytes(content, expected_version)

        # Automatic retry mode: use compare_and_swap for atomic read-modify-write
        def transform(existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
            return existing + records

        final_records, new_version = await self.compare_and_swap(transform)
        return new_version

    async def rewrite(
        self,
        records: list[dict[str, Any]],
        expected_version: Version | None = None,
    ) -> Version:
        """Replace entire contents atomically using CAS.

        Args:
            records: New records to write
            expected_version: Version the caller believes is current.
                If None, automatically retries on conflict.

        Returns:
            New version after successful write

        Raises:
            CASConflictError: If file was modified since expected_version
                (only when expected_version is provided)
        """
        lines = [
            json.dumps(r, separators=(",", ":")) + self.line_separator
            for r in records
        ]
        content = "".join(lines).encode("utf-8")

        if expected_version is not None:
            # Strict mode
            return await self._write_content(content, expected_version, append=False)

        # Automatic retry mode
        for _ in range(100):
            version = await self.read_version()
            try:
                return await self._write_content(content, version, append=False)
            except CASConflictError:
                continue

        raise CASConflictError("unknown", "exhausted retries")

    async def compare_and_swap(
        self,
        transform: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
        max_retries: int = 1000,
    ) -> tuple[list[dict[str, Any]], Version]:
        """Read, transform, and write atomically with automatic retry.

        This is the core CAS primitive. It implements the read-modify-write
        cycle with automatic conflict detection and retry.

        .. warning:: CRITICAL - DO NOT CAPTURE STALE DATA

            The transform function is called with FRESH data on each retry.
            You MUST use the parameter passed to transform, not variables
            captured from outer scope.

            WRONG - loses data on retry:
                records = await store.read_all()  # Stale!
                await store.compare_and_swap(lambda r: records)  # Ignores r!

            CORRECT - uses fresh data:
                await store.compare_and_swap(lambda records:
                    records.append(new_item)
                    return records
                )

            The lambda parameter (r/records) contains FRESH data on retry.
            Using captured variables causes silent data loss.

        Args:
            transform: Function that takes current records and returns new records
            max_retries: Maximum retry attempts before giving up

        Returns:
            Tuple of (final_records, new_version)

        Raises:
            CASConflictError: If max_retries exceeded
        """
        for attempt in range(max_retries):
            # Read file content and compute version atomically
            # This eliminates TOCTOU between read_version() and read_all()
            if not self.path.exists():
                version: Version | None = None
                records = []
            else:
                content = await self._read_file_bytes()
                version = Version.from_content(content)
                records = self._parse_content(content)

            new_records = transform(records)

            try:
                new_version = await self.rewrite(new_records, expected_version=version)
                return new_records, new_version
            except CASConflictError:
                if attempt == max_retries - 1:
                    raise
                # Retry with fresh read
                continue

        # Should never reach here
        raise CASConflictError("unknown", "unknown")

    def _parse_content(self, content: bytes) -> list[dict[str, Any]]:
        """Parse JSONL content into records."""
        records = []
        if not content:
            return records

        for line in content.decode("utf-8").split(self.line_separator):
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records

    async def iter_records(self) -> AsyncIterator[dict[str, Any]]:
        """Iterate over records (memory-efficient, no version check)."""
        if not self.path.exists():
            return

        async with aiofiles.open(self.path) as f:
            async for line in f:
                line = line.strip()
                if line:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        # Skip corrupt lines
                        continue

    # --- Private methods ---

    async def _version_async(self, path: Path) -> Version | None:
        """Async wrapper for version computation."""
        # Run sync file ops in thread pool
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, Version.from_path, path)

    async def _read_records(self) -> list[dict[str, Any]]:
        """Read all records from file."""
        records = []
        async for record in self.iter_records():
            records.append(record)
        return records

    async def _append_bytes(
        self,
        content: bytes,
        expected_version: Version | None,
    ) -> Version:
        """Append bytes to file using CAS."""
        return await self._write_content(content, expected_version, append=True)

    def _versions_equal(self, v1: Version | None, v2: Version | None) -> bool:
        """Check if two versions are equivalent for CAS.

        Treats "missing file" (None) and "empty file" as different states
        unless both have the same content hash (or both are None).
        """
        if v1 is None and v2 is None:
            return True
        if v1 is None or v2 is None:
            return False
        return v1.content_hash == v2.content_hash

    async def _write_content(
        self,
        content: bytes,
        expected_version: Version | None,
        append: bool = False,
    ) -> Version:
        """Write content atomically with CAS check.

        The CAS check works by:
        1. Creating a temp file with new content
        2. Atomically renaming temp to target (POSIX atomic rename)
        3. BUT: For append, we need to include existing content

        .. warning:: RACE WINDOW

            Between the version check (below) and the os.replace() call,
            another process could modify the file. Both processes might
            pass the version check and proceed to rename, causing the
            second rename to overwrite the first.

            This is a fundamental limitation of file-based CAS. The race
            window is small (~1-10 microseconds) but non-zero. Use file
            locking or SQLite if strict serializability is required.
        """
        # NOTE: This version check has a race window. Another process
        # could modify the file after this check but before os.replace().
        # See docstring above and docs/CAS_ATOMICITY.md for details.
        current_version = await self._version_async(self.path)

        if not self._versions_equal(current_version, expected_version):
            raise CASConflictError(
                expected_version=str(expected_version),
                actual_version=str(current_version),
            )

        # Compute new content
        if append and self.path.exists():
            existing = await self._read_file_bytes()
            final_content = existing + content
        else:
            final_content = content

        # Write to temp file
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            suffix=".tmp",
        )
        try:
            os.write(temp_fd, final_content)
            os.fsync(temp_fd)  # Ensure data hits disk
            os.close(temp_fd)

            # Atomic rename (POSIX guarantees this is atomic)
            # On Linux: atomic metadata update
            # On macOS: atomic exchange
            os.replace(temp_path, self.path)

            # Sync directory to ensure rename is durable
            dir_fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)

        except Exception:
            # Cleanup temp file on failure
            with suppress(FileNotFoundError):
                os.unlink(temp_path)
            raise

        return Version.from_content(final_content)

    async def _read_file_bytes(self) -> bytes:
        """Read entire file as bytes."""
        async with aiofiles.open(self.path, "rb") as f:
            return await f.read()
