"""Typed support memory models for episodes, evidence refs, domains, arcs, and arc work state."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Literal

from alfred.memory.support_profile import V1_INTERACTION_CONTEXT_IDS, validate_registry_value


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


def _dump_str_dict(values: Mapping[str, str]) -> str:
    """Serialize a mapping of strings as JSON text."""
    return json.dumps(dict(values))


def _load_str_dict(value: Any) -> dict[str, str]:
    """Deserialize a JSON object of strings from SQLite storage."""
    if value is None:
        return {}
    if isinstance(value, str):
        decoded: Any = json.loads(value)
    else:
        decoded = value
    if decoded is None:
        return {}
    if not isinstance(decoded, Mapping):
        raise ValueError("Expected a JSON object of string values")
    return {str(key): str(item) for key, item in decoded.items()}


def _validate_trimmed_string(value: Any, *, label: str) -> str:
    """Require a non-empty trimmed string field."""
    if not isinstance(value, str):
        actual_type = type(value).__name__
        raise ValueError(f"{label} must be a string, got {actual_type}")
    if not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty trimmed string")
    return value


def _validate_string_list(value: Any, *, label: str) -> list[str]:
    """Require a list of non-empty trimmed strings."""
    if not isinstance(value, list):
        actual_type = type(value).__name__
        raise ValueError(f"{label} must be a list of strings, got {actual_type}")
    return [_validate_trimmed_string(item, label=f"{label} entry") for item in value]


def _validate_applied_values(
    value: Any,
    *,
    registry: Literal["relational", "support"],
    label: str,
) -> dict[str, str]:
    """Require a mapping of validated support-profile dimension/value pairs."""
    if not isinstance(value, Mapping):
        actual_type = type(value).__name__
        raise ValueError(f"{label} must be a mapping of dimension ids to values, got {actual_type}")

    normalized: dict[str, str] = {}
    for raw_dimension, raw_value in value.items():
        dimension = _validate_trimmed_string(raw_dimension, label=f"{label} dimension")
        validated_value = _validate_trimmed_string(raw_value, label=f"{label} value")
        validate_registry_value(registry, dimension, validated_value)
        normalized[dimension] = validated_value
    return normalized


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


@dataclass(eq=True, frozen=True)
class SupportInterventionMessageRef:
    """Minimal same-session transcript span attached to one support intervention."""

    session_id: str
    message_start_id: str
    message_end_id: str

    def __post_init__(self) -> None:
        """Reject malformed transcript provenance spans."""
        object.__setattr__(self, "session_id", _validate_trimmed_string(self.session_id, label="session_id"))
        object.__setattr__(
            self,
            "message_start_id",
            _validate_trimmed_string(self.message_start_id, label="message_start_id"),
        )
        object.__setattr__(
            self,
            "message_end_id",
            _validate_trimmed_string(self.message_end_id, label="message_end_id"),
        )

    def to_record(self) -> dict[str, Any]:
        """Convert the message span ref into a JSON-ready record."""
        return {
            "session_id": self.session_id,
            "message_start_id": self.message_start_id,
            "message_end_id": self.message_end_id,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> SupportInterventionMessageRef:
        """Build a message span ref from a JSON-decoded record."""
        return cls(
            session_id=str(record["session_id"]),
            message_start_id=str(record["message_start_id"]),
            message_end_id=str(record["message_end_id"]),
        )


@dataclass(eq=True)
class SupportIntervention:
    """Validated episode-level intervention record with typed message-span provenance."""

    intervention_id: str
    episode_id: str
    timestamp: datetime
    context: str
    intervention_type: str
    behavior_contract_summary: str
    relational_values_applied: dict[str, str] = field(default_factory=dict)
    support_values_applied: dict[str, str] = field(default_factory=dict)
    user_response_signals: list[str] = field(default_factory=list)
    outcome_signals: list[str] = field(default_factory=list)
    evidence_refs: list[SupportInterventionMessageRef] = field(default_factory=list)
    schema_version: int = 1
    arc_id: str | None = None

    def __post_init__(self) -> None:
        """Reject malformed intervention records."""
        if self.schema_version != 1:
            raise ValueError(f"Unsupported support intervention schema version: {self.schema_version!r}. Expected 1")

        self.intervention_id = _validate_trimmed_string(self.intervention_id, label="intervention_id")
        self.episode_id = _validate_trimmed_string(self.episode_id, label="episode_id")
        self.intervention_type = _validate_trimmed_string(self.intervention_type, label="intervention_type")
        self.behavior_contract_summary = _validate_trimmed_string(
            self.behavior_contract_summary,
            label="behavior_contract_summary",
        )

        if not isinstance(self.timestamp, datetime):
            actual_type = type(self.timestamp).__name__
            raise ValueError(f"timestamp must be a datetime, got {actual_type}")

        self.context = _validate_trimmed_string(self.context, label="context")
        if self.context not in V1_INTERACTION_CONTEXT_IDS:
            allowed_contexts = ", ".join(V1_INTERACTION_CONTEXT_IDS)
            raise ValueError(f"Unsupported intervention context: {self.context!r}. Expected one of: {allowed_contexts}")

        if self.arc_id is not None:
            self.arc_id = _validate_trimmed_string(self.arc_id, label="arc_id")

        self.relational_values_applied = _validate_applied_values(
            self.relational_values_applied,
            registry="relational",
            label="relational_values_applied",
        )
        self.support_values_applied = _validate_applied_values(
            self.support_values_applied,
            registry="support",
            label="support_values_applied",
        )
        self.user_response_signals = _validate_string_list(
            self.user_response_signals,
            label="user_response_signals",
        )
        self.outcome_signals = _validate_string_list(
            self.outcome_signals,
            label="outcome_signals",
        )

        if not isinstance(self.evidence_refs, list):
            actual_type = type(self.evidence_refs).__name__
            raise ValueError(f"evidence_refs must be a list of SupportInterventionMessageRef values, got {actual_type}")
        if not self.evidence_refs:
            raise ValueError("evidence_refs must include at least one transcript span")
        for evidence_ref in self.evidence_refs:
            if not isinstance(evidence_ref, SupportInterventionMessageRef):
                raise ValueError("evidence_refs must contain SupportInterventionMessageRef values")

        first_session_id = self.evidence_refs[0].session_id
        if any(evidence_ref.session_id != first_session_id for evidence_ref in self.evidence_refs[1:]):
            raise ValueError("evidence_refs must all point to the same session_id")

    def to_record(self) -> dict[str, Any]:
        """Convert the intervention into a SQLite-ready record."""
        return {
            "schema_version": self.schema_version,
            "intervention_id": self.intervention_id,
            "episode_id": self.episode_id,
            "timestamp": _dump_datetime(self.timestamp),
            "context": self.context,
            "arc_id": self.arc_id,
            "intervention_type": self.intervention_type,
            "relational_values_applied": _dump_str_dict(self.relational_values_applied),
            "support_values_applied": _dump_str_dict(self.support_values_applied),
            "behavior_contract_summary": self.behavior_contract_summary,
            "user_response_signals": _dump_str_list(self.user_response_signals),
            "outcome_signals": _dump_str_list(self.outcome_signals),
            "evidence_refs": json.dumps([evidence_ref.to_record() for evidence_ref in self.evidence_refs]),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> SupportIntervention:
        """Build a support intervention from a SQLite row or dict."""
        raw_evidence_refs = record.get("evidence_refs")
        if isinstance(raw_evidence_refs, str):
            decoded_evidence_refs: Any = json.loads(raw_evidence_refs)
        else:
            decoded_evidence_refs = raw_evidence_refs
        if decoded_evidence_refs is None:
            decoded_evidence_refs = []
        if not isinstance(decoded_evidence_refs, list):
            raise ValueError("Support intervention evidence_refs must deserialize to a list of records")

        evidence_refs: list[SupportInterventionMessageRef] = []
        for decoded_evidence_ref in decoded_evidence_refs:
            if not isinstance(decoded_evidence_ref, Mapping):
                raise ValueError("Support intervention evidence_refs must contain mapping records")
            evidence_refs.append(SupportInterventionMessageRef.from_record(decoded_evidence_ref))

        arc_id = record.get("arc_id")
        return cls(
            intervention_id=str(record["intervention_id"]),
            episode_id=str(record["episode_id"]),
            timestamp=_load_datetime(record["timestamp"]),
            context=str(record["context"]),
            intervention_type=str(record["intervention_type"]),
            behavior_contract_summary=str(record["behavior_contract_summary"]),
            relational_values_applied=_load_str_dict(record.get("relational_values_applied")),
            support_values_applied=_load_str_dict(record.get("support_values_applied")),
            user_response_signals=_load_str_list(record.get("user_response_signals")),
            outcome_signals=_load_str_list(record.get("outcome_signals")),
            evidence_refs=evidence_refs,
            schema_version=int(record.get("schema_version", 1)),
            arc_id=None if arc_id is None else str(arc_id),
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
