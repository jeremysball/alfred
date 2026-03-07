"""Record store interface with JSONL backend.

Designed to allow swapping JSONL for SQLite in the future.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import aiofiles

from alfred.type_defs import JsonObject, ensure_json_object


class RecordStore(Protocol):
    """Interface for record storage backends."""

    def exists(self) -> bool:
        """Return True if the backing store exists."""
        ...

    def read_all(self) -> list[JsonObject]:
        """Read all records synchronously."""
        ...

    async def read_all_async(self) -> list[JsonObject]:
        """Read all records asynchronously."""
        ...

    def iter_records(self) -> Iterator[JsonObject]:
        """Iterate records synchronously."""
        ...

    def iter_records_async(self) -> AsyncIterator[JsonObject]:
        """Iterate records asynchronously."""
        ...

    async def append(self, record: JsonObject) -> None:
        """Append a single record."""
        ...

    async def append_records(self, records: Iterable[JsonObject]) -> None:
        """Append multiple records in one write session."""
        ...

    async def rewrite(self, records: Iterable[JsonObject]) -> None:
        """Rewrite all records atomically."""
        ...


@dataclass(slots=True)
class JsonlRecordStore:
    """JSONL-backed record store."""

    path: Path

    def exists(self) -> bool:
        return self.path.exists()

    def read_all(self) -> list[JsonObject]:
        return list(self.iter_records())

    async def read_all_async(self) -> list[JsonObject]:
        records: list[JsonObject] = []
        async for record in self.iter_records_async():
            records.append(record)
        return records

    def iter_records(self) -> Iterator[JsonObject]:
        if not self.path.exists():
            return iter(())

        return self._iter_file()

    def _iter_file(self) -> Iterator[JsonObject]:
        with self.path.open() as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                yield self._parse_line(line)

    async def iter_records_async(self) -> AsyncIterator[JsonObject]:
        if not self.path.exists():
            return

        async with aiofiles.open(self.path) as file:
            async for line in file:
                line = line.strip()
                if not line:
                    continue
                yield self._parse_line(line)

    async def append(self, record: JsonObject) -> None:
        await self.append_records([record])

    async def append_records(self, records: Iterable[JsonObject]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(self.path, "a") as file:
            for record in records:
                payload = ensure_json_object(record)
                await file.write(json.dumps(payload) + "\n")

    async def rewrite(self, records: Iterable[JsonObject]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(".tmp")

        async with aiofiles.open(temp_path, "w") as file:
            for record in records:
                payload = ensure_json_object(record)
                await file.write(json.dumps(payload) + "\n")

        temp_path.replace(self.path)

    @staticmethod
    def _parse_line(line: str) -> JsonObject:
        data = json.loads(line)
        return ensure_json_object(data)
