"""Template sync metadata contract for managed workspace files."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

__all__ = ["TemplateBaseSnapshot", "TemplateSyncRecord", "TemplateSyncState", "TemplateSyncStore"]


@dataclass(slots=True)
class TemplateBaseSnapshot:
    """Last known clean template content used as the merge base."""

    content: str
    hash: str
    captured_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Normalize incoming values into the expected concrete types."""
        if not isinstance(self.captured_at, datetime):
            self.captured_at = datetime.fromisoformat(str(self.captured_at))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the base snapshot into JSON-friendly data."""
        return {
            "content": self.content,
            "hash": self.hash,
            "captured_at": self.captured_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TemplateBaseSnapshot:
        """Rehydrate a base snapshot from serialized JSON data."""
        return cls(
            content=data["content"],
            hash=data["hash"],
            captured_at=datetime.fromisoformat(data["captured_at"]) if data.get("captured_at") else datetime.now(UTC),
        )


class TemplateSyncState(StrEnum):
    """State of a managed template in the sync lifecycle."""

    PENDING = "pending"
    CLEAN = "clean"
    MERGED = "merged"
    CONFLICTED = "conflicted"


@dataclass(slots=True)
class TemplateSyncRecord:
    """Persisted metadata for one managed template file."""

    name: str
    template_path: Path
    workspace_path: Path
    template_hash: str
    workspace_hash: str
    base_hash: str
    base_snapshot: TemplateBaseSnapshot | None = None
    state: TemplateSyncState = TemplateSyncState.PENDING
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Normalize incoming values into the expected concrete types."""
        self.template_path = Path(self.template_path)
        self.workspace_path = Path(self.workspace_path)
        if not isinstance(self.state, TemplateSyncState):
            self.state = TemplateSyncState(self.state)
        if not isinstance(self.updated_at, datetime):
            self.updated_at = datetime.fromisoformat(str(self.updated_at))
        if self.base_snapshot is not None and self.base_snapshot.hash != self.base_hash:
            raise ValueError("base_hash must match base_snapshot.hash")

    def is_clean(self) -> bool:
        """Return True when the workspace file is usable without intervention."""
        return self.state in {TemplateSyncState.CLEAN, TemplateSyncState.MERGED}

    def needs_merge(self) -> bool:
        """Return True when Alfred should attempt a merge before using the file."""
        return self.state is TemplateSyncState.PENDING

    def is_conflicted(self) -> bool:
        """Return True when the file is blocked by unresolved conflict markers."""
        return self.state is TemplateSyncState.CONFLICTED

    def to_dict(self) -> dict[str, Any]:
        """Serialize the record into JSON-friendly data."""
        data: dict[str, Any] = {
            "name": self.name,
            "template_path": str(self.template_path),
            "workspace_path": str(self.workspace_path),
            "template_hash": self.template_hash,
            "workspace_hash": self.workspace_hash,
            "base_hash": self.base_hash,
            "state": self.state.value,
            "updated_at": self.updated_at.isoformat(),
        }
        if self.base_snapshot is not None:
            data["base_snapshot"] = self.base_snapshot.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TemplateSyncRecord:
        """Rehydrate a record from serialized JSON data."""
        base_snapshot_data = data.get("base_snapshot")
        base_snapshot = TemplateBaseSnapshot.from_dict(base_snapshot_data) if base_snapshot_data else None
        return cls(
            name=data["name"],
            template_path=Path(data["template_path"]),
            workspace_path=Path(data["workspace_path"]),
            template_hash=data["template_hash"],
            workspace_hash=data["workspace_hash"],
            base_hash=data["base_hash"],
            base_snapshot=base_snapshot,
            state=data.get("state", TemplateSyncState.PENDING),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(UTC),
        )


class TemplateSyncStore:
    """JSON-backed store for template sync records."""

    VERSION = 1

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, TemplateSyncRecord] = {}
        self._load()

    def get(self, name: str) -> TemplateSyncRecord | None:
        """Get a single record by template name."""
        return self._records.get(name)

    def list_records(self) -> list[TemplateSyncRecord]:
        """Return all records in stable name order."""
        return [self._records[name] for name in sorted(self._records)]

    def save(self, record: TemplateSyncRecord) -> None:
        """Save or replace a single record and persist the store."""
        self._records[record.name] = record
        self._write()

    def save_many(self, records: list[TemplateSyncRecord]) -> None:
        """Save multiple records and persist the store once."""
        for record in records:
            self._records[record.name] = record
        self._write()

    def delete(self, name: str) -> None:
        """Delete a record if it exists and persist the store."""
        if name in self._records:
            del self._records[name]
            self._write()

    def _load(self) -> None:
        """Load records from disk, or start empty if the file is absent."""
        if not self.path.exists():
            return

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid template sync store: {self.path}") from exc

        version = data.get("version", self.VERSION)
        if version != self.VERSION:
            raise ValueError(f"Unsupported template sync store version: {version}")

        raw_records = data.get("records", {})
        if not isinstance(raw_records, dict):
            raise ValueError(f"Invalid template sync store format: {self.path}")

        self._records = {name: TemplateSyncRecord.from_dict(record_data) for name, record_data in raw_records.items()}

    def _write(self) -> None:
        """Persist the current store state using an atomic rename."""
        payload = {
            "version": self.VERSION,
            "records": {name: self._records[name].to_dict() for name in sorted(self._records)},
        }
        temp_path = self.path.with_name(f"{self.path.name}.tmp")
        temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp_path.replace(self.path)
