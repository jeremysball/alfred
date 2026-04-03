"""Typed support memory models for episodes, evidence refs, domains, arcs, and arc work state."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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
    message_start_id: str
    timestamp: datetime
    message_end_id: str | None = None
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
            "message_start_id": self.message_start_id,
            "message_end_id": self.message_end_id,
            "excerpt": self.excerpt,
            "timestamp": _dump_datetime(self.timestamp),
            "domain_ids": _dump_str_list(self.domain_ids),
            "arc_ids": _dump_str_list(self.arc_ids),
            "claim_type": self.claim_type,
            "confidence": self.confidence,
        }

    @staticmethod
    def _resolve_session_message(
        messages: Sequence[Mapping[str, Any]],
        *,
        message_id: str,
        label: str,
    ) -> tuple[Mapping[str, Any], str, int]:
        """Resolve a session message from its persisted message ID."""
        matches: list[tuple[Mapping[str, Any], str, int]] = []
        for fallback_idx, message in enumerate(messages):
            resolved_idx = int(message.get("idx", fallback_idx))
            resolved_id = str(message.get("id", "")).strip()
            if resolved_id != message_id:
                continue
            matches.append((message, resolved_id, resolved_idx))

        if not matches:
            raise ValueError(f"Could not resolve {label} session message from id={message_id}")

        if len(matches) > 1:
            raise ValueError(f"Multiple session messages matched the {label} selector")

        return matches[0]

    @classmethod
    def from_session_message_span(
        cls,
        *,
        evidence_id: str,
        episode_id: str,
        session_id: str,
        messages: Sequence[Mapping[str, Any]],
        message_start_id: str,
        message_end_id: str | None = None,
        timestamp: datetime | None = None,
        excerpt: str | None = None,
        domain_ids: list[str] | None = None,
        arc_ids: list[str] | None = None,
        claim_type: str = "stated_priority",
        confidence: float = 0.0,
    ) -> EvidenceRef:
        """Build an evidence ref from a persisted transcript message-ID span.

        The helper resolves the selected messages from the session archive,
        preserves the transcript payload unchanged, and uses the span's first
        message as the default excerpt and timestamp source when those fields
        are not provided explicitly.
        """
        resolved_start_message, resolved_start_id, resolved_start_idx = cls._resolve_session_message(
            messages,
            message_id=message_start_id,
            label="start",
        )

        if message_end_id is None:
            resolved_end_message = resolved_start_message
            resolved_end_id = resolved_start_id
            resolved_end_idx = resolved_start_idx
        else:
            resolved_end_message, resolved_end_id, resolved_end_idx = cls._resolve_session_message(
                messages,
                message_id=message_end_id,
                label="end",
            )

        if resolved_start_idx > resolved_end_idx:
            raise ValueError(
                f"Evidence span must start before it ends: start_id={resolved_start_id} end_id={resolved_end_id}",
            )

        evidence_timestamp = timestamp
        if evidence_timestamp is None:
            evidence_timestamp = _load_optional_datetime(resolved_start_message.get("timestamp"))
        if evidence_timestamp is None:
            evidence_timestamp = _load_optional_datetime(resolved_end_message.get("timestamp"))
        if evidence_timestamp is None:
            raise ValueError("Session messages must include a timestamp or an explicit timestamp must be provided")

        resolved_excerpt = excerpt
        if resolved_excerpt is None:
            content = resolved_start_message.get("content")
            if content is not None:
                resolved_excerpt = str(content)

        return cls(
            evidence_id=evidence_id,
            episode_id=episode_id,
            session_id=session_id,
            message_start_id=resolved_start_id,
            message_end_id=resolved_end_id,
            timestamp=evidence_timestamp,
            excerpt=resolved_excerpt,
            domain_ids=list(domain_ids or []),
            arc_ids=list(arc_ids or []),
            claim_type=claim_type,
            confidence=confidence,
        )

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> EvidenceRef:
        """Build an evidence ref from a SQLite row or dict."""
        return cls(
            evidence_id=str(record["evidence_id"]),
            episode_id=str(record["episode_id"]),
            session_id=str(record["session_id"]),
            message_start_id=str(record["message_start_id"]),
            timestamp=_load_datetime(record["timestamp"]),
            message_end_id=None if record.get("message_end_id") is None else str(record["message_end_id"]),
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


@dataclass(eq=True)
class LifeDomain:
    """Durable high-level support domain.

    Linked arcs are derived from operational arcs that point at this domain, so the
    domain record avoids storing a redundant linked_arc_ids list.
    """

    domain_id: str
    name: str
    status: str
    salience: float
    created_at: datetime
    updated_at: datetime
    linked_pattern_ids: list[str] = field(default_factory=list)

    def to_record(self) -> dict[str, Any]:
        """Convert the life domain into a SQLite-ready record."""
        return {
            "domain_id": self.domain_id,
            "name": self.name,
            "status": self.status,
            "salience": self.salience,
            "created_at": _dump_datetime(self.created_at),
            "updated_at": _dump_datetime(self.updated_at),
            "linked_pattern_ids": _dump_str_list(self.linked_pattern_ids),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> LifeDomain:
        """Build a life domain from a SQLite row or dict."""
        return cls(
            domain_id=str(record["domain_id"]),
            name=str(record["name"]),
            status=str(record["status"]),
            salience=float(record["salience"]),
            created_at=_load_datetime(record["created_at"]),
            updated_at=_load_datetime(record["updated_at"]),
            linked_pattern_ids=_load_str_list(record.get("linked_pattern_ids")),
        )


@dataclass(eq=True)
class OperationalArc:
    """Durable resumable operational thread linked to one primary life domain."""

    arc_id: str
    title: str
    kind: str
    status: str
    salience: float
    created_at: datetime
    updated_at: datetime
    primary_domain_id: str | None = None
    last_active_at: datetime | None = None
    evidence_ref_ids: list[str] = field(default_factory=list)

    def to_record(self) -> dict[str, Any]:
        """Convert the operational arc into a SQLite-ready record."""
        return {
            "arc_id": self.arc_id,
            "title": self.title,
            "kind": self.kind,
            "primary_domain_id": self.primary_domain_id,
            "status": self.status,
            "salience": self.salience,
            "created_at": _dump_datetime(self.created_at),
            "updated_at": _dump_datetime(self.updated_at),
            "last_active_at": _dump_datetime(self.last_active_at),
            "evidence_ref_ids": _dump_str_list(self.evidence_ref_ids),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> OperationalArc:
        """Build an operational arc from a SQLite row or dict."""
        return cls(
            arc_id=str(record["arc_id"]),
            title=str(record["title"]),
            kind=str(record["kind"]),
            primary_domain_id=record.get("primary_domain_id"),
            status=str(record["status"]),
            salience=float(record["salience"]),
            created_at=_load_datetime(record["created_at"]),
            updated_at=_load_datetime(record["updated_at"]),
            last_active_at=_load_optional_datetime(record.get("last_active_at")),
            evidence_ref_ids=_load_str_list(record.get("evidence_ref_ids")),
        )


@dataclass(eq=True)
class ArcTask:
    """Durable arc-linked actionable item."""

    task_id: str
    arc_id: str
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    next_step: str | None = None
    evidence_ref_ids: list[str] = field(default_factory=list)

    def to_record(self) -> dict[str, Any]:
        """Convert the arc task into a SQLite-ready record."""
        return {
            "task_id": self.task_id,
            "arc_id": self.arc_id,
            "title": self.title,
            "status": self.status,
            "created_at": _dump_datetime(self.created_at),
            "updated_at": _dump_datetime(self.updated_at),
            "next_step": self.next_step,
            "evidence_ref_ids": _dump_str_list(self.evidence_ref_ids),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> ArcTask:
        """Build an arc task from a SQLite row or dict."""
        return cls(
            task_id=str(record["task_id"]),
            arc_id=str(record["arc_id"]),
            title=str(record["title"]),
            status=str(record["status"]),
            created_at=_load_datetime(record["created_at"]),
            updated_at=_load_datetime(record["updated_at"]),
            next_step=record.get("next_step"),
            evidence_ref_ids=_load_str_list(record.get("evidence_ref_ids")),
        )


@dataclass(eq=True)
class ArcBlocker:
    """Durable arc-linked blocker or constraint."""

    blocker_id: str
    arc_id: str
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    next_step: str | None = None
    evidence_ref_ids: list[str] = field(default_factory=list)

    def to_record(self) -> dict[str, Any]:
        """Convert the arc blocker into a SQLite-ready record."""
        return {
            "blocker_id": self.blocker_id,
            "arc_id": self.arc_id,
            "title": self.title,
            "status": self.status,
            "created_at": _dump_datetime(self.created_at),
            "updated_at": _dump_datetime(self.updated_at),
            "next_step": self.next_step,
            "evidence_ref_ids": _dump_str_list(self.evidence_ref_ids),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> ArcBlocker:
        """Build an arc blocker from a SQLite row or dict."""
        return cls(
            blocker_id=str(record["blocker_id"]),
            arc_id=str(record["arc_id"]),
            title=str(record["title"]),
            status=str(record["status"]),
            created_at=_load_datetime(record["created_at"]),
            updated_at=_load_datetime(record["updated_at"]),
            next_step=record.get("next_step"),
            evidence_ref_ids=_load_str_list(record.get("evidence_ref_ids")),
        )


@dataclass(eq=True)
class ArcDecision:
    """Durable arc-linked decision or choice point."""

    decision_id: str
    arc_id: str
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    current_tension: str | None = None
    evidence_ref_ids: list[str] = field(default_factory=list)

    def to_record(self) -> dict[str, Any]:
        """Convert the arc decision into a SQLite-ready record."""
        return {
            "decision_id": self.decision_id,
            "arc_id": self.arc_id,
            "title": self.title,
            "status": self.status,
            "created_at": _dump_datetime(self.created_at),
            "updated_at": _dump_datetime(self.updated_at),
            "current_tension": self.current_tension,
            "evidence_ref_ids": _dump_str_list(self.evidence_ref_ids),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> ArcDecision:
        """Build an arc decision from a SQLite row or dict."""
        return cls(
            decision_id=str(record["decision_id"]),
            arc_id=str(record["arc_id"]),
            title=str(record["title"]),
            status=str(record["status"]),
            created_at=_load_datetime(record["created_at"]),
            updated_at=_load_datetime(record["updated_at"]),
            current_tension=record.get("current_tension"),
            evidence_ref_ids=_load_str_list(record.get("evidence_ref_ids")),
        )


@dataclass(eq=True)
class ArcOpenLoop:
    """Durable arc-linked unresolved commitment or return thread."""

    open_loop_id: str
    arc_id: str
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    current_tension: str | None = None
    evidence_ref_ids: list[str] = field(default_factory=list)

    def to_record(self) -> dict[str, Any]:
        """Convert the arc open loop into a SQLite-ready record."""
        return {
            "open_loop_id": self.open_loop_id,
            "arc_id": self.arc_id,
            "title": self.title,
            "status": self.status,
            "created_at": _dump_datetime(self.created_at),
            "updated_at": _dump_datetime(self.updated_at),
            "current_tension": self.current_tension,
            "evidence_ref_ids": _dump_str_list(self.evidence_ref_ids),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> ArcOpenLoop:
        """Build an arc open loop from a SQLite row or dict."""
        return cls(
            open_loop_id=str(record["open_loop_id"]),
            arc_id=str(record["arc_id"]),
            title=str(record["title"]),
            status=str(record["status"]),
            created_at=_load_datetime(record["created_at"]),
            updated_at=_load_datetime(record["updated_at"]),
            current_tension=record.get("current_tension"),
            evidence_ref_ids=_load_str_list(record.get("evidence_ref_ids")),
        )


@dataclass(eq=True)
class ArcSnapshot:
    """Composed structured view of one operational arc and its linked work state."""

    arc: OperationalArc
    tasks: list[ArcTask] = field(default_factory=list)
    blockers: list[ArcBlocker] = field(default_factory=list)
    decisions: list[ArcDecision] = field(default_factory=list)
    open_loops: list[ArcOpenLoop] = field(default_factory=list)


@dataclass(eq=True)
class ArcSituation:
    """Derived, refreshable runtime summary for one operational arc."""

    arc_id: str
    current_state: str
    computed_at: datetime
    confidence: float
    staleness_seconds: int
    refresh_reason: str
    recent_progress: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    next_moves: list[str] = field(default_factory=list)
    linked_pattern_ids: list[str] = field(default_factory=list)

    def is_stale(self, now: datetime) -> bool:
        """Return True when the situation should be refreshed before reuse."""
        return now >= self.computed_at + timedelta(seconds=self.staleness_seconds)

    def to_record(self) -> dict[str, Any]:
        """Convert the arc situation into a SQLite-ready record."""
        return {
            "arc_id": self.arc_id,
            "current_state": self.current_state,
            "recent_progress": _dump_str_list(self.recent_progress),
            "blockers": _dump_str_list(self.blockers),
            "next_moves": _dump_str_list(self.next_moves),
            "linked_pattern_ids": _dump_str_list(self.linked_pattern_ids),
            "computed_at": _dump_datetime(self.computed_at),
            "confidence": self.confidence,
            "staleness_seconds": self.staleness_seconds,
            "refresh_reason": self.refresh_reason,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> ArcSituation:
        """Build an arc situation from a SQLite row or dict."""
        return cls(
            arc_id=str(record["arc_id"]),
            current_state=str(record["current_state"]),
            recent_progress=_load_str_list(record.get("recent_progress")),
            blockers=_load_str_list(record.get("blockers")),
            next_moves=_load_str_list(record.get("next_moves")),
            linked_pattern_ids=_load_str_list(record.get("linked_pattern_ids")),
            computed_at=_load_datetime(record["computed_at"]),
            confidence=float(record["confidence"]),
            staleness_seconds=int(record["staleness_seconds"]),
            refresh_reason=str(record["refresh_reason"]),
        )


@dataclass(eq=True)
class GlobalSituation:
    """Derived, refreshable runtime summary across active domains and arcs."""

    computed_at: datetime
    confidence: float
    staleness_seconds: int
    refresh_reason: str
    active_domains: list[str] = field(default_factory=list)
    top_arcs: list[str] = field(default_factory=list)
    unresolved_decisions: list[str] = field(default_factory=list)
    top_blockers: list[str] = field(default_factory=list)
    drift_risks: list[str] = field(default_factory=list)
    current_tensions: list[str] = field(default_factory=list)

    def is_stale(self, now: datetime) -> bool:
        """Return True when the situation should be refreshed before reuse."""
        return now >= self.computed_at + timedelta(seconds=self.staleness_seconds)

    def to_record(self) -> dict[str, Any]:
        """Convert the global situation into a SQLite-ready record."""
        return {
            "situation_id": "global",
            "active_domains": _dump_str_list(self.active_domains),
            "top_arcs": _dump_str_list(self.top_arcs),
            "unresolved_decisions": _dump_str_list(self.unresolved_decisions),
            "top_blockers": _dump_str_list(self.top_blockers),
            "drift_risks": _dump_str_list(self.drift_risks),
            "current_tensions": _dump_str_list(self.current_tensions),
            "computed_at": _dump_datetime(self.computed_at),
            "confidence": self.confidence,
            "staleness_seconds": self.staleness_seconds,
            "refresh_reason": self.refresh_reason,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> GlobalSituation:
        """Build a global situation from a SQLite row or dict."""
        return cls(
            active_domains=_load_str_list(record.get("active_domains")),
            top_arcs=_load_str_list(record.get("top_arcs")),
            unresolved_decisions=_load_str_list(record.get("unresolved_decisions")),
            top_blockers=_load_str_list(record.get("top_blockers")),
            drift_risks=_load_str_list(record.get("drift_risks")),
            current_tensions=_load_str_list(record.get("current_tensions")),
            computed_at=_load_datetime(record["computed_at"]),
            confidence=float(record["confidence"]),
            staleness_seconds=int(record["staleness_seconds"]),
            refresh_reason=str(record["refresh_reason"]),
        )
