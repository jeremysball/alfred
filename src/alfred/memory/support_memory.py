"""Typed support memory models for episodes and evidence refs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def _dump_datetime(value: datetime | None) -> str | None:
    """Serialize a datetime to ISO-8601 text."""
    return value.isoformat() if value is not None else None


def _load_datetime(value: Any) -> datetime:
    """Parse a datetime value from SQLite storage."""
    if isinstance(value, datetime):
        return value
    if value is None:
        raise ValueError("Expected a datetime value")
    return datetime.fromisoformat(str(value))


def _load_optional_datetime(value: Any) -> datetime | None:
    """Parse an optional datetime value from SQLite storage."""
    if value is None:
        return None
    return _load_datetime(value)


def _dump_str_list(values: list[str]) -> str:
    """Serialize a list of strings as JSON text."""
    return json.dumps(values)


def _load_str_list(value: Any) -> list[str]:
    """Deserialize a JSON list of strings from SQLite storage."""
    if value is None:
        return []
    if isinstance(value, str):
        decoded: Any = json.loads(value)
    else:
        decoded = value
    if decoded is None:
        return []
    return [str(item) for item in decoded]


@dataclass(eq=True)
class EvidenceRef:
    """Pointer from structured support memory back to a transcript record."""

    evidence_id: str
    episode_id: str
    session_id: str
    message_start_idx: int
    timestamp: datetime
    message_end_idx: int | None = None
    excerpt: str | None = None
    domain_ids: list[str] = field(default_factory=list)
    arc_ids: list[str] = field(default_factory=list)
    claim_type: str = "stated_priority"
    confidence: float = 0.0

    def to_record(self) -> dict[str, Any]:
        """Convert the evidence ref into a SQLite-ready record."""
        return {
            "evidence_id": self.evidence_id,
            "episode_id": self.episode_id,
            "session_id": self.session_id,
            "message_start_idx": self.message_start_idx,
            "message_end_idx": self.message_end_idx,
            "excerpt": self.excerpt,
            "timestamp": _dump_datetime(self.timestamp),
            "domain_ids": _dump_str_list(self.domain_ids),
            "arc_ids": _dump_str_list(self.arc_ids),
            "claim_type": self.claim_type,
            "confidence": self.confidence,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> EvidenceRef:
        """Build an evidence ref from a SQLite row or dict."""
        return cls(
            evidence_id=str(record["evidence_id"]),
            episode_id=str(record["episode_id"]),
            session_id=str(record["session_id"]),
            message_start_idx=int(record["message_start_idx"]),
            timestamp=_load_datetime(record["timestamp"]),
            message_end_idx=None if record.get("message_end_idx") is None else int(record["message_end_idx"]),
            excerpt=record.get("excerpt"),
            domain_ids=_load_str_list(record.get("domain_ids")),
            arc_ids=_load_str_list(record.get("arc_ids")),
            claim_type=str(record["claim_type"]),
            confidence=float(record["confidence"]),
        )


@dataclass(eq=True)
class SupportEpisode:
    """Typed support episode that groups evidence within a transcript session."""

    episode_id: str
    session_id: str
    started_at: datetime
    dominant_need: str
    dominant_context: str
    schema_version: int = 1
    ended_at: datetime | None = None
    dominant_arc_id: str | None = None
    domain_ids: list[str] = field(default_factory=list)
    subject_refs: list[str] = field(default_factory=list)
    friction_signals: list[str] = field(default_factory=list)
    interventions_attempted: list[str] = field(default_factory=list)
    response_signals: list[str] = field(default_factory=list)
    outcome_signals: list[str] = field(default_factory=list)
    evidence_refs: list[EvidenceRef] = field(default_factory=list)

    def to_record(self) -> dict[str, Any]:
        """Convert the support episode into a SQLite-ready record."""
        return {
            "episode_id": self.episode_id,
            "session_id": self.session_id,
            "schema_version": self.schema_version,
            "started_at": _dump_datetime(self.started_at),
            "ended_at": _dump_datetime(self.ended_at),
            "dominant_need": self.dominant_need,
            "dominant_context": self.dominant_context,
            "dominant_arc_id": self.dominant_arc_id,
            "domain_ids": _dump_str_list(self.domain_ids),
            "subject_refs": _dump_str_list(self.subject_refs),
            "friction_signals": _dump_str_list(self.friction_signals),
            "interventions_attempted": _dump_str_list(self.interventions_attempted),
            "response_signals": _dump_str_list(self.response_signals),
            "outcome_signals": _dump_str_list(self.outcome_signals),
        }

    @classmethod
    def from_record(
        cls,
        record: Mapping[str, Any],
        evidence_refs: list[EvidenceRef] | None = None,
    ) -> SupportEpisode:
        """Build a support episode from a SQLite row or dict."""
        return cls(
            episode_id=str(record["episode_id"]),
            session_id=str(record["session_id"]),
            started_at=_load_datetime(record["started_at"]),
            dominant_need=str(record["dominant_need"]),
            dominant_context=str(record["dominant_context"]),
            schema_version=int(record.get("schema_version", 1)),
            ended_at=_load_optional_datetime(record.get("ended_at")),
            dominant_arc_id=record.get("dominant_arc_id"),
            domain_ids=_load_str_list(record.get("domain_ids")),
            subject_refs=_load_str_list(record.get("subject_refs")),
            friction_signals=_load_str_list(record.get("friction_signals")),
            interventions_attempted=_load_str_list(record.get("interventions_attempted")),
            response_signals=_load_str_list(record.get("response_signals")),
            outcome_signals=_load_str_list(record.get("outcome_signals")),
            evidence_refs=evidence_refs or [],
        )
