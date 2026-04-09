"""Typed support-learning models for Milestone 5 bounded adaptation."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol, cast

from alfred.memory.support_profile import (
    V1_INTERACTION_CONTEXT_IDS,
    SupportProfileRegistryKind,
    SupportProfileScope,
    SupportProfileScopeType,
    SupportProfileValue,
    validate_registry_value,
)

Need = Literal["orient", "resume", "activate", "decide", "reflect", "calibrate", "unknown"]
InterventionFamily = Literal[
    "orient",
    "summarize",
    "narrow",
    "sequence",
    "recommend",
    "mirror",
    "compare",
    "challenge",
    "reset",
    "confirm",
]

_SUPPORTED_NEEDS: frozenset[str] = frozenset(
    {
        "orient",
        "resume",
        "activate",
        "decide",
        "reflect",
        "calibrate",
        "unknown",
    }
)
PatternKind = Literal[
    "support_preference",
    "recurring_blocker",
    "identity_theme",
    "direction_theme",
    "calibration_gap",
]
PatternStatus = Literal["candidate", "confirmed", "rejected"]
UpdateEventStatus = Literal["proposed", "applied", "reverted"]
ObservationSourceType = Literal[
    "next_user_turn",
    "work_state_transition",
    "explicit_feedback",
    "timeout",
    "manual_review",
    "system_inference",
]
ObservationSignalPolarity = Literal["positive", "negative", "mixed", "neutral"]
LearningCaseStatus = Literal["open", "complete", "insufficient_evidence", "superseded"]
SupportValueStatus = Literal["shadow", "active_auto", "confirmed", "rejected", "retired"]
SupportPatternLedgerStatus = Literal["candidate", "active_auto", "confirmed", "rejected", "retired"]
SupportLedgerStatus = Literal["shadow", "candidate", "active_auto", "confirmed", "rejected", "retired"]
SupportLedgerEntityType = Literal["value", "pattern"]

_SUPPORTED_INTERVENTION_FAMILIES: frozenset[str] = frozenset(
    {
        "orient",
        "summarize",
        "narrow",
        "sequence",
        "recommend",
        "mirror",
        "compare",
        "challenge",
        "reset",
        "confirm",
    }
)
_SUPPORTED_PATTERN_KINDS: frozenset[str] = frozenset(
    {
        "support_preference",
        "recurring_blocker",
        "identity_theme",
        "direction_theme",
        "calibration_gap",
    }
)
_SUPPORTED_PATTERN_STATUSES: frozenset[str] = frozenset({"candidate", "confirmed", "rejected"})
_SUPPORTED_UPDATE_EVENT_STATUSES: frozenset[str] = frozenset({"proposed", "applied", "reverted"})
_SUPPORTED_OBSERVATION_SOURCE_TYPES: frozenset[str] = frozenset(
    {
        "next_user_turn",
        "work_state_transition",
        "explicit_feedback",
        "timeout",
        "manual_review",
        "system_inference",
    }
)
_SUPPORTED_OBSERVATION_SIGNAL_POLARITIES: frozenset[str] = frozenset({"positive", "negative", "mixed", "neutral"})
_SUPPORTED_LEARNING_CASE_STATUSES: frozenset[str] = frozenset(
    {"open", "complete", "insufficient_evidence", "superseded"}
)
_SUPPORTED_VALUE_LEDGER_STATUSES: frozenset[str] = frozenset({"shadow", "active_auto", "confirmed", "rejected", "retired"})
_SUPPORTED_PATTERN_LEDGER_STATUSES: frozenset[str] = frozenset(
    {"candidate", "active_auto", "confirmed", "rejected", "retired"}
)
_SUPPORTED_LEDGER_STATUSES: frozenset[str] = frozenset(
    {"shadow", "candidate", "active_auto", "confirmed", "rejected", "retired"}
)
_SUPPORTED_LEDGER_ENTITY_TYPES: frozenset[str] = frozenset({"value", "pattern"})


def _dump_datetime(value: datetime) -> str:
    return value.isoformat()


def _load_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if value is None:
        raise ValueError("Expected a datetime value")
    return datetime.fromisoformat(str(value))


def _validate_trimmed_string(value: Any, *, label: str) -> str:
    if not isinstance(value, str):
        actual_type = type(value).__name__
        raise ValueError(f"{label} must be a string, got {actual_type}")
    if not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty trimmed string")
    return value


def _validate_string_tuple(value: Any, *, label: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        actual_type = type(value).__name__
        raise ValueError(f"{label} must be a tuple of strings, got {actual_type}")
    return tuple(_validate_trimmed_string(item, label=f"{label} entry") for item in value)


def _dump_str_tuple(values: tuple[str, ...]) -> str:
    return json.dumps(list(values))


def _load_str_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        decoded: Any = json.loads(value)
    else:
        decoded = value
    if decoded is None:
        return ()
    return tuple(str(item) for item in decoded)


def _dump_float_tuple(values: tuple[float, ...]) -> str:
    return json.dumps(list(values))


def _load_float_tuple(value: Any) -> tuple[float, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        decoded: Any = json.loads(value)
    else:
        decoded = value
    if decoded is None:
        return ()
    return tuple(float(item) for item in decoded)


def _validate_applied_values(
    value: Any,
    *,
    registry: Literal["relational", "support"],
    label: str,
) -> dict[str, str]:
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


def _validate_confidence(value: Any, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        actual_type = type(value).__name__
        raise ValueError(f"{label} must be numeric, got {actual_type}")
    normalized = float(value)
    if not 0.0 <= normalized <= 1.0:
        raise ValueError(f"{label} must be between 0.0 and 1.0")
    return normalized


def _validate_registry_kind(value: Any, *, label: str) -> SupportProfileRegistryKind:
    normalized = _validate_trimmed_string(value, label=label)
    if normalized not in {"relational", "support"}:
        raise ValueError(f"{label} must be 'relational' or 'support', got {normalized!r}")
    return cast(SupportProfileRegistryKind, normalized)


def _validate_optional_trimmed_string(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    return _validate_trimmed_string(value, label=label)


def _validate_non_negative_int(value: Any, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        actual_type = type(value).__name__
        raise ValueError(f"{label} must be an integer, got {actual_type}")
    normalized = int(value)
    if normalized < 0:
        raise ValueError(f"{label} must be non-negative")
    return normalized


def _validate_bool(value: Any, *, label: str) -> bool:
    if not isinstance(value, bool):
        actual_type = type(value).__name__
        raise ValueError(f"{label} must be a bool, got {actual_type}")
    return value


def _dump_transcript_span_refs(values: tuple[SupportTranscriptSpanRef, ...]) -> str:
    return json.dumps([value.to_record() for value in values])


def _load_transcript_span_refs(value: Any) -> tuple[SupportTranscriptSpanRef, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        decoded: Any = json.loads(value)
    else:
        decoded = value
    if decoded is None:
        return ()
    if not isinstance(decoded, list):
        raise ValueError("Transcript span refs must deserialize to a list of records")

    refs: list[SupportTranscriptSpanRef] = []
    for decoded_ref in decoded:
        if not isinstance(decoded_ref, Mapping):
            raise ValueError("Transcript span refs must contain mapping records")
        refs.append(SupportTranscriptSpanRef.from_record(decoded_ref))
    return tuple(refs)


def _validate_transcript_span_refs(value: Any, *, label: str) -> tuple[SupportTranscriptSpanRef, ...]:
    if not isinstance(value, tuple):
        actual_type = type(value).__name__
        raise ValueError(f"{label} must be a tuple of SupportTranscriptSpanRef values, got {actual_type}")
    for evidence_ref in value:
        if not isinstance(evidence_ref, SupportTranscriptSpanRef):
            raise ValueError(f"{label} must contain SupportTranscriptSpanRef values")
    return value


@dataclass(eq=True, frozen=True)
class SupportTranscriptSpanRef:
    """General same-session transcript span used by learning records."""

    session_id: str
    message_start_id: str
    message_end_id: str

    def __post_init__(self) -> None:
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
        return {
            "session_id": self.session_id,
            "message_start_id": self.message_start_id,
            "message_end_id": self.message_end_id,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> SupportTranscriptSpanRef:
        return cls(
            session_id=str(record["session_id"]),
            message_start_id=str(record["message_start_id"]),
            message_end_id=str(record["message_end_id"]),
        )


@dataclass(eq=True)
class SupportAttempt:
    """Reply-time record of what Alfred tried for one support turn."""

    attempt_id: str
    session_id: str
    user_message_id: str
    assistant_message_id: str
    created_at: datetime
    need: Need
    response_mode: str
    subject_refs: tuple[str, ...] = ()
    active_arc_id: str | None = None
    active_domain_ids: tuple[str, ...] = ()
    effective_support_values: dict[str, str] = field(default_factory=dict)
    effective_relational_values: dict[str, str] = field(default_factory=dict)
    intervention_family: InterventionFamily = "confirm"
    intervention_refs: tuple[str, ...] = ()
    prompt_contract_summary: str = ""
    operational_snapshot_ref: str | None = None

    def __post_init__(self) -> None:
        self.attempt_id = _validate_trimmed_string(self.attempt_id, label="attempt_id")
        self.session_id = _validate_trimmed_string(self.session_id, label="session_id")
        self.user_message_id = _validate_trimmed_string(self.user_message_id, label="user_message_id")
        self.assistant_message_id = _validate_trimmed_string(
            self.assistant_message_id,
            label="assistant_message_id",
        )
        if not isinstance(self.created_at, datetime):
            actual_type = type(self.created_at).__name__
            raise ValueError(f"created_at must be a datetime, got {actual_type}")

        self.need = _validate_trimmed_string(self.need, label="need")  # type: ignore[assignment]
        if self.need not in _SUPPORTED_NEEDS:
            raise ValueError(f"Unsupported support attempt need: {self.need!r}")

        self.response_mode = _validate_trimmed_string(self.response_mode, label="response_mode")
        if self.response_mode not in V1_INTERACTION_CONTEXT_IDS:
            allowed_contexts = ", ".join(V1_INTERACTION_CONTEXT_IDS)
            raise ValueError(
                f"Unsupported support attempt response_mode: {self.response_mode!r}. Expected one of: {allowed_contexts}",
            )

        self.subject_refs = _validate_string_tuple(self.subject_refs, label="subject_refs")
        self.active_domain_ids = _validate_string_tuple(self.active_domain_ids, label="active_domain_ids")
        self.active_arc_id = _validate_optional_trimmed_string(self.active_arc_id, label="active_arc_id")
        self.intervention_family = _validate_trimmed_string(
            self.intervention_family,
            label="intervention_family",
        )  # type: ignore[assignment]
        if self.intervention_family not in _SUPPORTED_INTERVENTION_FAMILIES:
            raise ValueError(f"Unsupported support attempt intervention_family: {self.intervention_family!r}")
        self.intervention_refs = _validate_string_tuple(self.intervention_refs, label="intervention_refs")
        self.prompt_contract_summary = _validate_trimmed_string(
            self.prompt_contract_summary,
            label="prompt_contract_summary",
        )
        self.operational_snapshot_ref = _validate_optional_trimmed_string(
            self.operational_snapshot_ref,
            label="operational_snapshot_ref",
        )
        self.effective_support_values = _validate_applied_values(
            self.effective_support_values,
            registry="support",
            label="effective_support_values",
        )
        self.effective_relational_values = _validate_applied_values(
            self.effective_relational_values,
            registry="relational",
            label="effective_relational_values",
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "session_id": self.session_id,
            "user_message_id": self.user_message_id,
            "assistant_message_id": self.assistant_message_id,
            "created_at": _dump_datetime(self.created_at),
            "need": self.need,
            "response_mode": self.response_mode,
            "subject_refs": _dump_str_tuple(self.subject_refs),
            "active_arc_id": self.active_arc_id,
            "active_domain_ids": _dump_str_tuple(self.active_domain_ids),
            "effective_support_values": json.dumps(self.effective_support_values),
            "effective_relational_values": json.dumps(self.effective_relational_values),
            "intervention_family": self.intervention_family,
            "intervention_refs": _dump_str_tuple(self.intervention_refs),
            "prompt_contract_summary": self.prompt_contract_summary,
            "operational_snapshot_ref": self.operational_snapshot_ref,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> SupportAttempt:
        support_values_raw = record.get("effective_support_values")
        relational_values_raw = record.get("effective_relational_values")
        support_values = json.loads(support_values_raw) if isinstance(support_values_raw, str) else support_values_raw
        relational_values = json.loads(relational_values_raw) if isinstance(relational_values_raw, str) else relational_values_raw
        active_arc_id = record.get("active_arc_id")
        operational_snapshot_ref = record.get("operational_snapshot_ref")
        return cls(
            attempt_id=str(record["attempt_id"]),
            session_id=str(record["session_id"]),
            user_message_id=str(record["user_message_id"]),
            assistant_message_id=str(record["assistant_message_id"]),
            created_at=_load_datetime(record["created_at"]),
            need=cast(Need, str(record["need"])),
            response_mode=str(record["response_mode"]),
            subject_refs=_load_str_tuple(record.get("subject_refs")),
            active_arc_id=None if active_arc_id is None else str(active_arc_id),
            active_domain_ids=_load_str_tuple(record.get("active_domain_ids")),
            effective_support_values=support_values or {},
            effective_relational_values=relational_values or {},
            intervention_family=cast(InterventionFamily, str(record["intervention_family"])),
            intervention_refs=_load_str_tuple(record.get("intervention_refs")),
            prompt_contract_summary=str(record["prompt_contract_summary"]),
            operational_snapshot_ref=None if operational_snapshot_ref is None else str(operational_snapshot_ref),
        )


@dataclass(eq=True)
class OutcomeObservation:
    """One post-reply observation linked to a support attempt."""

    observation_id: str
    attempt_id: str
    observed_at: datetime
    source_type: ObservationSourceType
    signals: tuple[str, ...]
    signal_polarity: ObservationSignalPolarity
    signal_strength: float
    evidence_refs: tuple[SupportTranscriptSpanRef, ...] = ()
    operational_delta_refs: tuple[str, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        self.observation_id = _validate_trimmed_string(self.observation_id, label="observation_id")
        self.attempt_id = _validate_trimmed_string(self.attempt_id, label="attempt_id")
        if not isinstance(self.observed_at, datetime):
            actual_type = type(self.observed_at).__name__
            raise ValueError(f"observed_at must be a datetime, got {actual_type}")

        self.source_type = _validate_trimmed_string(self.source_type, label="source_type")  # type: ignore[assignment]
        if self.source_type not in _SUPPORTED_OBSERVATION_SOURCE_TYPES:
            raise ValueError(f"Unsupported outcome observation source_type: {self.source_type!r}")
        self.signals = _validate_string_tuple(self.signals, label="signals")
        if not self.signals:
            raise ValueError("signals must contain at least one observation signal")
        self.signal_polarity = _validate_trimmed_string(
            self.signal_polarity,
            label="signal_polarity",
        )  # type: ignore[assignment]
        if self.signal_polarity not in _SUPPORTED_OBSERVATION_SIGNAL_POLARITIES:
            raise ValueError(f"Unsupported outcome observation signal_polarity: {self.signal_polarity!r}")
        self.signal_strength = _validate_confidence(self.signal_strength, label="signal_strength")
        self.evidence_refs = _validate_transcript_span_refs(self.evidence_refs, label="evidence_refs")
        self.operational_delta_refs = _validate_string_tuple(
            self.operational_delta_refs,
            label="operational_delta_refs",
        )
        self.notes = _validate_optional_trimmed_string(self.notes, label="notes")

    def to_record(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "attempt_id": self.attempt_id,
            "observed_at": _dump_datetime(self.observed_at),
            "source_type": self.source_type,
            "signals": _dump_str_tuple(self.signals),
            "signal_polarity": self.signal_polarity,
            "signal_strength": self.signal_strength,
            "evidence_refs": _dump_transcript_span_refs(self.evidence_refs),
            "operational_delta_refs": _dump_str_tuple(self.operational_delta_refs),
            "notes": self.notes,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> OutcomeObservation:
        notes = record.get("notes")
        return cls(
            observation_id=str(record["observation_id"]),
            attempt_id=str(record["attempt_id"]),
            observed_at=_load_datetime(record["observed_at"]),
            source_type=cast(ObservationSourceType, str(record["source_type"])),
            signals=_load_str_tuple(record.get("signals")),
            signal_polarity=cast(ObservationSignalPolarity, str(record["signal_polarity"])),
            signal_strength=float(record["signal_strength"]),
            evidence_refs=_load_transcript_span_refs(record.get("evidence_refs")),
            operational_delta_refs=_load_str_tuple(record.get("operational_delta_refs")),
            notes=None if notes is None else str(notes),
        )


@dataclass(eq=True)
class LearningCase:
    """Inspectable case-level synthesis derived from one attempt and its observations."""

    case_id: str
    attempt_id: str
    status: LearningCaseStatus
    scope: SupportProfileScope
    created_at: datetime
    finalized_at: datetime | None = None
    aggregate_signals: tuple[str, ...] = ()
    positive_evidence_count: int = 0
    negative_evidence_count: int = 0
    contradiction_count: int = 0
    conversation_score: float = 0.0
    operational_score: float = 0.0
    overall_score: float = 0.0
    promotion_eligibility: bool = False
    evidence_refs: tuple[SupportTranscriptSpanRef, ...] = ()
    summary: str | None = None

    def __post_init__(self) -> None:
        self.case_id = _validate_trimmed_string(self.case_id, label="case_id")
        self.attempt_id = _validate_trimmed_string(self.attempt_id, label="attempt_id")
        self.status = _validate_trimmed_string(self.status, label="status")  # type: ignore[assignment]
        if self.status not in _SUPPORTED_LEARNING_CASE_STATUSES:
            raise ValueError(f"Unsupported learning case status: {self.status!r}")
        if not isinstance(self.scope, SupportProfileScope):
            raise ValueError("scope must be a SupportProfileScope")
        if not isinstance(self.created_at, datetime):
            actual_type = type(self.created_at).__name__
            raise ValueError(f"created_at must be a datetime, got {actual_type}")
        if self.finalized_at is not None and not isinstance(self.finalized_at, datetime):
            actual_type = type(self.finalized_at).__name__
            raise ValueError(f"finalized_at must be a datetime, got {actual_type}")
        if self.status == "open":
            if self.finalized_at is not None:
                raise ValueError("Open learning cases must not set finalized_at")
        elif self.finalized_at is None:
            raise ValueError(f"Learning case status {self.status!r} requires finalized_at")

        self.aggregate_signals = _validate_string_tuple(self.aggregate_signals, label="aggregate_signals")
        self.positive_evidence_count = _validate_non_negative_int(
            self.positive_evidence_count,
            label="positive_evidence_count",
        )
        self.negative_evidence_count = _validate_non_negative_int(
            self.negative_evidence_count,
            label="negative_evidence_count",
        )
        self.contradiction_count = _validate_non_negative_int(
            self.contradiction_count,
            label="contradiction_count",
        )
        self.conversation_score = _validate_confidence(self.conversation_score, label="conversation_score")
        self.operational_score = _validate_confidence(self.operational_score, label="operational_score")
        self.overall_score = _validate_confidence(self.overall_score, label="overall_score")
        self.promotion_eligibility = _validate_bool(self.promotion_eligibility, label="promotion_eligibility")
        self.evidence_refs = _validate_transcript_span_refs(self.evidence_refs, label="evidence_refs")
        self.summary = _validate_optional_trimmed_string(self.summary, label="summary")
        if self.status != "open" and self.summary is None:
            raise ValueError(f"Learning case status {self.status!r} requires summary")

    def to_record(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "attempt_id": self.attempt_id,
            "status": self.status,
            "scope_type": self.scope.type,
            "scope_id": self.scope.id,
            "created_at": _dump_datetime(self.created_at),
            "finalized_at": None if self.finalized_at is None else _dump_datetime(self.finalized_at),
            "aggregate_signals": _dump_str_tuple(self.aggregate_signals),
            "positive_evidence_count": self.positive_evidence_count,
            "negative_evidence_count": self.negative_evidence_count,
            "contradiction_count": self.contradiction_count,
            "conversation_score": self.conversation_score,
            "operational_score": self.operational_score,
            "overall_score": self.overall_score,
            "promotion_eligibility": self.promotion_eligibility,
            "evidence_refs": _dump_transcript_span_refs(self.evidence_refs),
            "summary": self.summary,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> LearningCase:
        finalized_at = record.get("finalized_at")
        summary = record.get("summary")
        return cls(
            case_id=str(record["case_id"]),
            attempt_id=str(record["attempt_id"]),
            status=cast(LearningCaseStatus, str(record["status"])),
            scope=SupportProfileScope(
                type=cast(SupportProfileScopeType, str(record["scope_type"])),
                id=str(record["scope_id"]),
            ),
            created_at=_load_datetime(record["created_at"]),
            finalized_at=None if finalized_at is None else _load_datetime(finalized_at),
            aggregate_signals=_load_str_tuple(record.get("aggregate_signals")),
            positive_evidence_count=int(record.get("positive_evidence_count", 0)),
            negative_evidence_count=int(record.get("negative_evidence_count", 0)),
            contradiction_count=int(record.get("contradiction_count", 0)),
            conversation_score=float(record.get("conversation_score", 0.0)),
            operational_score=float(record.get("operational_score", 0.0)),
            overall_score=float(record.get("overall_score", 0.0)),
            promotion_eligibility=bool(record.get("promotion_eligibility", False)),
            evidence_refs=_load_transcript_span_refs(record.get("evidence_refs")),
            summary=None if summary is None else str(summary),
        )


_OPERATIONAL_OBSERVATION_SOURCE_TYPES: frozenset[str] = frozenset({"work_state_transition"})
_OBSERVATION_SCORE_WEIGHTS: dict[str, float] = {
    "positive": 1.0,
    "negative": 0.0,
    "mixed": 0.5,
    "neutral": 0.25,
}
_POSITIVE_EVIDENCE_POLARITIES: frozenset[str] = frozenset({"positive", "mixed"})
_NEGATIVE_EVIDENCE_POLARITIES: frozenset[str] = frozenset({"negative", "mixed"})
_SCOPE_PROMOTION_THRESHOLDS: dict[str, int] = {"arc": 2, "context": 4}


def _ordered_unique_strings(values: Sequence[str]) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return tuple(ordered)


def _ordered_unique_transcript_refs(values: Sequence[SupportTranscriptSpanRef]) -> tuple[SupportTranscriptSpanRef, ...]:
    ordered: list[SupportTranscriptSpanRef] = []
    seen: set[tuple[str, str, str]] = set()
    for value in values:
        key = (value.session_id, value.message_start_id, value.message_end_id)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(value)
    return tuple(ordered)


def _score_outcome_observation(observation: OutcomeObservation) -> float:
    weight = _OBSERVATION_SCORE_WEIGHTS[observation.signal_polarity]
    return round(observation.signal_strength * weight, 2)


def _average_score(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def _derive_learning_case_scope(attempt: SupportAttempt) -> SupportProfileScope:
    if attempt.active_arc_id is not None:
        return SupportProfileScope(type="arc", id=attempt.active_arc_id)
    return SupportProfileScope(type="context", id=attempt.response_mode)


def _summarize_learning_case(
    *,
    attempt: SupportAttempt,
    status: LearningCaseStatus,
    promotion_eligibility: bool,
) -> str:
    if status == "insufficient_evidence":
        return f"Attempt {attempt.attempt_id} finalized with insufficient directional evidence."
    if promotion_eligibility:
        return f"Attempt {attempt.attempt_id} produced enough directional evidence to finalize a promotable case."
    return f"Attempt {attempt.attempt_id} finalized with directional evidence but is not promotion-eligible."


def derive_learning_case(
    *,
    attempt: SupportAttempt,
    observations: Sequence[OutcomeObservation],
) -> LearningCase | None:
    """Derive one deterministic learning case from a stored attempt bundle."""
    if not observations:
        return None

    ordered_observations = tuple(sorted(observations, key=lambda observation: (observation.observed_at, observation.observation_id)))
    observation_scores = [_score_outcome_observation(observation) for observation in ordered_observations]
    conversation_scores = [
        _score_outcome_observation(observation)
        for observation in ordered_observations
        if observation.source_type not in _OPERATIONAL_OBSERVATION_SOURCE_TYPES
    ]
    operational_scores = [
        _score_outcome_observation(observation)
        for observation in ordered_observations
        if observation.source_type in _OPERATIONAL_OBSERVATION_SOURCE_TYPES
    ]
    positive_evidence_count = sum(
        len(observation.signals)
        for observation in ordered_observations
        if observation.signal_polarity in _POSITIVE_EVIDENCE_POLARITIES
    )
    negative_evidence_count = sum(
        len(observation.signals)
        for observation in ordered_observations
        if observation.signal_polarity in _NEGATIVE_EVIDENCE_POLARITIES
    )
    contradiction_count = sum(1 for observation in ordered_observations if observation.signal_polarity == "mixed")
    if positive_evidence_count > 0 and negative_evidence_count > 0:
        contradiction_count += 1

    status: LearningCaseStatus = "complete"
    if positive_evidence_count == 0 and negative_evidence_count == 0:
        status = "insufficient_evidence"

    overall_score = _average_score(observation_scores)
    promotion_eligibility = (
        status == "complete"
        and positive_evidence_count > negative_evidence_count
        and contradiction_count == 0
        and overall_score >= 0.65
    )

    return LearningCase(
        case_id=f"case-{attempt.attempt_id}",
        attempt_id=attempt.attempt_id,
        status=status,
        scope=_derive_learning_case_scope(attempt),
        created_at=attempt.created_at,
        finalized_at=ordered_observations[-1].observed_at,
        aggregate_signals=_ordered_unique_strings(
            [signal for observation in ordered_observations for signal in observation.signals]
        ),
        positive_evidence_count=positive_evidence_count,
        negative_evidence_count=negative_evidence_count,
        contradiction_count=contradiction_count,
        conversation_score=_average_score(conversation_scores),
        operational_score=_average_score(operational_scores),
        overall_score=overall_score,
        promotion_eligibility=promotion_eligibility,
        evidence_refs=_ordered_unique_transcript_refs(
            [evidence_ref for observation in ordered_observations for evidence_ref in observation.evidence_refs]
        ),
        summary=_summarize_learning_case(
            attempt=attempt,
            status=status,
            promotion_eligibility=promotion_eligibility,
        ),
    )


@dataclass(eq=True)
class SupportValueLedgerEntry:
    """V2 ledger row for one scoped support or relational value."""

    value_id: str
    registry: SupportProfileRegistryKind
    dimension: str
    scope: SupportProfileScope
    value: str
    status: SupportValueStatus
    source: str
    confidence: float
    evidence_count: int
    contradiction_count: int
    last_case_id: str | None
    created_at: datetime
    updated_at: datetime
    why: str

    def __post_init__(self) -> None:
        self.value_id = _validate_trimmed_string(self.value_id, label="value_id")
        self.registry = _validate_registry_kind(self.registry, label="registry")
        self.dimension = _validate_trimmed_string(self.dimension, label="dimension")
        if not isinstance(self.scope, SupportProfileScope):
            raise ValueError("scope must be a SupportProfileScope")
        self.value = _validate_trimmed_string(self.value, label="value")
        validate_registry_value(self.registry, self.dimension, self.value)
        self.status = _validate_trimmed_string(self.status, label="status")  # type: ignore[assignment]
        if self.status not in _SUPPORTED_VALUE_LEDGER_STATUSES:
            raise ValueError(f"Unsupported support value ledger status: {self.status!r}")
        self.source = _validate_trimmed_string(self.source, label="source")
        self.confidence = _validate_confidence(self.confidence, label="confidence")
        self.evidence_count = _validate_non_negative_int(self.evidence_count, label="evidence_count")
        self.contradiction_count = _validate_non_negative_int(
            self.contradiction_count,
            label="contradiction_count",
        )
        self.last_case_id = _validate_optional_trimmed_string(self.last_case_id, label="last_case_id")
        if not isinstance(self.created_at, datetime):
            actual_type = type(self.created_at).__name__
            raise ValueError(f"created_at must be a datetime, got {actual_type}")
        if not isinstance(self.updated_at, datetime):
            actual_type = type(self.updated_at).__name__
            raise ValueError(f"updated_at must be a datetime, got {actual_type}")
        self.why = _validate_trimmed_string(self.why, label="why")

    def to_record(self) -> dict[str, Any]:
        return {
            "value_id": self.value_id,
            "registry": self.registry,
            "dimension": self.dimension,
            "scope_type": self.scope.type,
            "scope_id": self.scope.id,
            "value": self.value,
            "status": self.status,
            "source": self.source,
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
            "contradiction_count": self.contradiction_count,
            "last_case_id": self.last_case_id,
            "created_at": _dump_datetime(self.created_at),
            "updated_at": _dump_datetime(self.updated_at),
            "why": self.why,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> SupportValueLedgerEntry:
        last_case_id = record.get("last_case_id")
        return cls(
            value_id=str(record["value_id"]),
            registry=cast(SupportProfileRegistryKind, str(record["registry"])),
            dimension=str(record["dimension"]),
            scope=SupportProfileScope(
                type=cast(SupportProfileScopeType, str(record["scope_type"])),
                id=str(record["scope_id"]),
            ),
            value=str(record["value"]),
            status=cast(SupportValueStatus, str(record["status"])),
            source=str(record["source"]),
            confidence=float(record["confidence"]),
            evidence_count=int(record["evidence_count"]),
            contradiction_count=int(record["contradiction_count"]),
            last_case_id=None if last_case_id is None else str(last_case_id),
            created_at=_load_datetime(record["created_at"]),
            updated_at=_load_datetime(record["updated_at"]),
            why=str(record["why"]),
        )


@dataclass(eq=True)
class SupportPatternLedgerEntry:
    """V2 ledger row for one surfaced pattern with explicit provenance."""

    pattern_id: str
    registry: SupportProfileRegistryKind
    kind: PatternKind
    scope: SupportProfileScope
    status: SupportPatternLedgerStatus
    claim: str
    evidence_count: int
    contradiction_count: int
    confidence: float
    source_case_ids: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    why: str = ""

    def __post_init__(self) -> None:
        self.pattern_id = _validate_trimmed_string(self.pattern_id, label="pattern_id")
        self.registry = _validate_registry_kind(self.registry, label="registry")
        self.kind = _validate_trimmed_string(self.kind, label="kind")  # type: ignore[assignment]
        if self.kind not in _SUPPORTED_PATTERN_KINDS:
            raise ValueError(f"Unsupported support pattern ledger kind: {self.kind!r}")
        if not isinstance(self.scope, SupportProfileScope):
            raise ValueError("scope must be a SupportProfileScope")
        self.status = _validate_trimmed_string(self.status, label="status")  # type: ignore[assignment]
        if self.status not in _SUPPORTED_PATTERN_LEDGER_STATUSES:
            raise ValueError(f"Unsupported support pattern ledger status: {self.status!r}")
        self.claim = _validate_trimmed_string(self.claim, label="claim")
        self.evidence_count = _validate_non_negative_int(self.evidence_count, label="evidence_count")
        self.contradiction_count = _validate_non_negative_int(
            self.contradiction_count,
            label="contradiction_count",
        )
        self.confidence = _validate_confidence(self.confidence, label="confidence")
        self.source_case_ids = _validate_string_tuple(self.source_case_ids, label="source_case_ids")
        if not isinstance(self.created_at, datetime):
            actual_type = type(self.created_at).__name__
            raise ValueError(f"created_at must be a datetime, got {actual_type}")
        if not isinstance(self.updated_at, datetime):
            actual_type = type(self.updated_at).__name__
            raise ValueError(f"updated_at must be a datetime, got {actual_type}")
        self.why = _validate_trimmed_string(self.why, label="why")

    def to_record(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "registry": self.registry,
            "kind": self.kind,
            "scope_type": self.scope.type,
            "scope_id": self.scope.id,
            "status": self.status,
            "claim": self.claim,
            "evidence_count": self.evidence_count,
            "contradiction_count": self.contradiction_count,
            "confidence": self.confidence,
            "source_case_ids": _dump_str_tuple(self.source_case_ids),
            "created_at": _dump_datetime(self.created_at),
            "updated_at": _dump_datetime(self.updated_at),
            "why": self.why,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> SupportPatternLedgerEntry:
        return cls(
            pattern_id=str(record["pattern_id"]),
            registry=cast(SupportProfileRegistryKind, str(record["registry"])),
            kind=cast(PatternKind, str(record["kind"])),
            scope=SupportProfileScope(
                type=cast(SupportProfileScopeType, str(record["scope_type"])),
                id=str(record["scope_id"]),
            ),
            status=cast(SupportPatternLedgerStatus, str(record["status"])),
            claim=str(record["claim"]),
            evidence_count=int(record["evidence_count"]),
            contradiction_count=int(record["contradiction_count"]),
            confidence=float(record["confidence"]),
            source_case_ids=_load_str_tuple(record.get("source_case_ids")),
            created_at=_load_datetime(record["created_at"]),
            updated_at=_load_datetime(record["updated_at"]),
            why=str(record["why"]),
        )


@dataclass(eq=True)
class SupportLedgerUpdateEvent:
    """V2 ledger event explaining why one value or pattern changed state."""

    event_id: str
    entity_type: SupportLedgerEntityType
    entity_id: str
    registry: SupportProfileRegistryKind
    dimension_or_kind: str
    scope: SupportProfileScope
    old_status: SupportLedgerStatus | None
    new_status: SupportLedgerStatus
    old_value: str | None = None
    new_value: str | None = None
    trigger_case_ids: tuple[str, ...] = ()
    reason: str = ""
    confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        self.event_id = _validate_trimmed_string(self.event_id, label="event_id")
        self.entity_type = _validate_trimmed_string(self.entity_type, label="entity_type")  # type: ignore[assignment]
        if self.entity_type not in _SUPPORTED_LEDGER_ENTITY_TYPES:
            raise ValueError(f"Unsupported support ledger entity_type: {self.entity_type!r}")
        self.entity_id = _validate_trimmed_string(self.entity_id, label="entity_id")
        self.registry = _validate_registry_kind(self.registry, label="registry")
        self.dimension_or_kind = _validate_trimmed_string(self.dimension_or_kind, label="dimension_or_kind")
        if not isinstance(self.scope, SupportProfileScope):
            raise ValueError("scope must be a SupportProfileScope")
        if self.old_status is not None:
            normalized_old_status = _validate_trimmed_string(self.old_status, label="old_status")
            if normalized_old_status not in _SUPPORTED_LEDGER_STATUSES:
                raise ValueError(f"Unsupported support ledger old_status: {normalized_old_status!r}")
            self.old_status = cast(SupportLedgerStatus, normalized_old_status)
        self.new_status = _validate_trimmed_string(self.new_status, label="new_status")  # type: ignore[assignment]
        if self.new_status not in _SUPPORTED_LEDGER_STATUSES:
            raise ValueError(f"Unsupported support ledger new_status: {self.new_status!r}")
        self.old_value = _validate_optional_trimmed_string(self.old_value, label="old_value")
        self.new_value = _validate_optional_trimmed_string(self.new_value, label="new_value")
        self.trigger_case_ids = _validate_string_tuple(self.trigger_case_ids, label="trigger_case_ids")
        self.reason = _validate_trimmed_string(self.reason, label="reason")
        self.confidence = _validate_confidence(self.confidence, label="confidence")
        if not isinstance(self.created_at, datetime):
            actual_type = type(self.created_at).__name__
            raise ValueError(f"created_at must be a datetime, got {actual_type}")

        if self.entity_type == "value":
            if self.new_value is None:
                raise ValueError("Value ledger update events must set new_value")
            if self.old_value is not None:
                validate_registry_value(self.registry, self.dimension_or_kind, self.old_value)
            validate_registry_value(self.registry, self.dimension_or_kind, self.new_value)
        else:
            if self.dimension_or_kind not in _SUPPORTED_PATTERN_KINDS:
                raise ValueError(f"Unsupported support ledger pattern kind: {self.dimension_or_kind!r}")

    def to_record(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "registry": self.registry,
            "dimension_or_kind": self.dimension_or_kind,
            "scope_type": self.scope.type,
            "scope_id": self.scope.id,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "trigger_case_ids": _dump_str_tuple(self.trigger_case_ids),
            "reason": self.reason,
            "confidence": self.confidence,
            "created_at": _dump_datetime(self.created_at),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> SupportLedgerUpdateEvent:
        old_status = record.get("old_status")
        old_value = record.get("old_value")
        new_value = record.get("new_value")
        return cls(
            event_id=str(record["event_id"]),
            entity_type=cast(SupportLedgerEntityType, str(record["entity_type"])),
            entity_id=str(record["entity_id"]),
            registry=cast(SupportProfileRegistryKind, str(record["registry"])),
            dimension_or_kind=str(record["dimension_or_kind"]),
            scope=SupportProfileScope(
                type=cast(SupportProfileScopeType, str(record["scope_type"])),
                id=str(record["scope_id"]),
            ),
            old_status=None if old_status is None else cast(SupportLedgerStatus, str(old_status)),
            new_status=cast(SupportLedgerStatus, str(record["new_status"])),
            old_value=None if old_value is None else str(old_value),
            new_value=None if new_value is None else str(new_value),
            trigger_case_ids=_load_str_tuple(record.get("trigger_case_ids")),
            reason=str(record["reason"]),
            confidence=float(record["confidence"]),
            created_at=_load_datetime(record["created_at"]),
        )


@dataclass(eq=True)
class FinalizedLearningCaseBundle:
    """One finalized case plus the reply-time attempt that produced it."""

    learning_case: LearningCase
    attempt: SupportAttempt

    def __post_init__(self) -> None:
        if self.learning_case.attempt_id != self.attempt.attempt_id:
            raise ValueError("Finalized learning case bundles must join one case to its source attempt")
        if self.learning_case.finalized_at is None:
            raise ValueError("Finalized learning case bundles require finalized cases")


@dataclass(eq=True, frozen=True)
class SupportLedgerDerivationResult:
    """Deterministic value-ledger writes derived from finalized case bundles."""

    value_entries: tuple[SupportValueLedgerEntry, ...] = ()
    update_events: tuple[SupportLedgerUpdateEvent, ...] = ()


def _value_ledger_key(
    *,
    registry: SupportProfileRegistryKind,
    dimension: str,
    scope: SupportProfileScope,
    value: str,
) -> tuple[SupportProfileRegistryKind, str, SupportProfileScopeType, str, str]:
    return (registry, dimension, scope.type, scope.id, value)


def _iter_attempt_values(attempt: SupportAttempt) -> tuple[tuple[SupportProfileRegistryKind, str, str], ...]:
    values: list[tuple[SupportProfileRegistryKind, str, str]] = []
    for dimension, value in attempt.effective_support_values.items():
        values.append(("support", dimension, value))
    for dimension, value in attempt.effective_relational_values.items():
        values.append(("relational", dimension, value))
    return tuple(values)


def _sort_case_bundle(bundle: FinalizedLearningCaseBundle) -> tuple[datetime, str]:
    finalized_at = bundle.learning_case.finalized_at
    if finalized_at is None:
        raise ValueError("Finalized learning case bundles require finalized_at")
    return (finalized_at, bundle.learning_case.case_id)


def _summarize_value_ledger_entry(
    *,
    registry: SupportProfileRegistryKind,
    dimension: str,
    value: str,
    scope: SupportProfileScope,
    supporting_case_count: int,
    contradiction_count: int,
) -> str:
    return (
        f"{registry} {dimension}={value} has {supporting_case_count} supporting promotable cases and "
        f"{contradiction_count} conflicting promotable cases in this {scope.type} scope."
    )


def derive_value_ledger_updates_from_cases(
    *,
    focus_bundle: FinalizedLearningCaseBundle,
    scoped_bundles: Sequence[FinalizedLearningCaseBundle],
    existing_value_entries: Mapping[
        tuple[SupportProfileRegistryKind, str, SupportProfileScopeType, str, str],
        SupportValueLedgerEntry,
    ],
    now: datetime,
) -> SupportLedgerDerivationResult:
    """Derive deterministic value-ledger updates from finalized case bundles in one exact scope."""
    focus_case = focus_bundle.learning_case
    if focus_case.status != "complete" or not focus_case.promotion_eligibility:
        return SupportLedgerDerivationResult()

    scope = focus_case.scope
    threshold = _SCOPE_PROMOTION_THRESHOLDS.get(scope.type)
    if threshold is None:
        return SupportLedgerDerivationResult()

    promotable_bundles = tuple(
        sorted(
            (
                bundle
                for bundle in scoped_bundles
                if bundle.learning_case.scope == scope
                and bundle.learning_case.status == "complete"
                and bundle.learning_case.promotion_eligibility
            ),
            key=_sort_case_bundle,
        )
    )
    if not any(bundle.learning_case.case_id == focus_case.case_id for bundle in promotable_bundles):
        return SupportLedgerDerivationResult()

    supporting_bundles_by_key: dict[
        tuple[SupportProfileRegistryKind, str, SupportProfileScopeType, str, str],
        list[FinalizedLearningCaseBundle],
    ] = {}
    for bundle in promotable_bundles:
        for registry, dimension, value in _iter_attempt_values(bundle.attempt):
            supporting_bundles_by_key.setdefault(
                _value_ledger_key(registry=registry, dimension=dimension, scope=scope, value=value),
                [],
            ).append(bundle)

    if not supporting_bundles_by_key:
        return SupportLedgerDerivationResult()

    derived_entries: list[SupportValueLedgerEntry] = []
    update_events: list[SupportLedgerUpdateEvent] = []
    for key in sorted(supporting_bundles_by_key):
        registry, dimension, _, _, value = key
        supporting_bundles = tuple(supporting_bundles_by_key[key])
        contradiction_count = sum(
            len(other_bundles)
            for other_key, other_bundles in supporting_bundles_by_key.items()
            if other_key[:4] == key[:4] and other_key[4] != value
        )
        confidence = _average_score(
            [bundle.learning_case.overall_score for bundle in supporting_bundles]
        )
        latest_supporting_bundle = supporting_bundles[-1]
        why = _summarize_value_ledger_entry(
            registry=registry,
            dimension=dimension,
            value=value,
            scope=scope,
            supporting_case_count=len(supporting_bundles),
            contradiction_count=contradiction_count,
        )
        status: SupportValueStatus = (
            "active_auto" if len(supporting_bundles) >= threshold and len(supporting_bundles) > contradiction_count else "shadow"
        )
        existing_entry = existing_value_entries.get(key)
        entry = SupportValueLedgerEntry(
            value_id=f"value-{registry}-{dimension}-{scope.type}-{scope.id}-{value}",
            registry=registry,
            dimension=dimension,
            scope=scope,
            value=value,
            status=status,
            source="auto_case",
            confidence=confidence,
            evidence_count=len(supporting_bundles),
            contradiction_count=contradiction_count,
            last_case_id=latest_supporting_bundle.learning_case.case_id,
            created_at=now if existing_entry is None else existing_entry.created_at,
            updated_at=now,
            why=why,
        )
        derived_entries.append(entry)

        if existing_entry is None or existing_entry.status != entry.status:
            update_events.append(
                SupportLedgerUpdateEvent(
                    event_id=(
                        f"event-{entry.value_id}-{entry.status}-{latest_supporting_bundle.learning_case.case_id}"
                    ),
                    entity_type="value",
                    entity_id=entry.value_id,
                    registry=entry.registry,
                    dimension_or_kind=entry.dimension,
                    scope=entry.scope,
                    old_status=None if existing_entry is None else existing_entry.status,
                    new_status=entry.status,
                    old_value=None if existing_entry is None else existing_entry.value,
                    new_value=entry.value,
                    trigger_case_ids=tuple(bundle.learning_case.case_id for bundle in supporting_bundles),
                    reason=entry.why,
                    confidence=entry.confidence,
                    created_at=now,
                )
            )

    return SupportLedgerDerivationResult(
        value_entries=tuple(derived_entries),
        update_events=tuple(sorted(update_events, key=lambda event: (event.entity_id, event.event_id))),
    )


@dataclass(eq=True)
class LearningSituation:
    """Primary semantic learning unit for bounded adaptation."""

    situation_id: str
    session_id: str
    recorded_at: datetime
    turn_text: str
    embedding: tuple[float, ...]
    need: Need
    response_mode: str
    subject_refs: tuple[str, ...] = ()
    arc_id: str | None = None
    domain_ids: tuple[str, ...] = ()
    intervention_ids: tuple[str, ...] = ()
    behavior_contract_summary: str = ""
    intervention_family: InterventionFamily = "confirm"
    relational_values_applied: dict[str, str] = field(default_factory=dict)
    support_values_applied: dict[str, str] = field(default_factory=dict)
    user_response_signals: tuple[str, ...] = ()
    outcome_signals: tuple[str, ...] = ()
    evidence_refs: tuple[SupportTranscriptSpanRef, ...] = ()

    def __post_init__(self) -> None:
        self.situation_id = _validate_trimmed_string(self.situation_id, label="situation_id")
        self.session_id = _validate_trimmed_string(self.session_id, label="session_id")
        self.turn_text = _validate_trimmed_string(self.turn_text, label="turn_text")
        self.behavior_contract_summary = _validate_trimmed_string(
            self.behavior_contract_summary,
            label="behavior_contract_summary",
        )

        if not isinstance(self.recorded_at, datetime):
            actual_type = type(self.recorded_at).__name__
            raise ValueError(f"recorded_at must be a datetime, got {actual_type}")

        if not isinstance(self.embedding, tuple) or not self.embedding:
            raise ValueError("embedding must be a non-empty tuple of floats")
        normalized_embedding: list[float] = []
        for idx, value in enumerate(self.embedding):
            if isinstance(value, bool) or not isinstance(value, int | float):
                actual_type = type(value).__name__
                raise ValueError(f"embedding entry {idx} must be numeric, got {actual_type}")
            normalized_embedding.append(float(value))
        self.embedding = tuple(normalized_embedding)

        self.need = _validate_trimmed_string(self.need, label="need")  # type: ignore[assignment]
        if self.need not in _SUPPORTED_NEEDS:
            raise ValueError(f"Unsupported learning situation need: {self.need!r}")

        self.response_mode = _validate_trimmed_string(self.response_mode, label="response_mode")
        if self.response_mode not in V1_INTERACTION_CONTEXT_IDS:
            allowed_contexts = ", ".join(V1_INTERACTION_CONTEXT_IDS)
            raise ValueError(
                f"Unsupported learning situation response_mode: {self.response_mode!r}. Expected one of: {allowed_contexts}",
            )

        self.subject_refs = _validate_string_tuple(self.subject_refs, label="subject_refs")
        self.domain_ids = _validate_string_tuple(self.domain_ids, label="domain_ids")
        self.intervention_ids = _validate_string_tuple(self.intervention_ids, label="intervention_ids")
        self.user_response_signals = _validate_string_tuple(self.user_response_signals, label="user_response_signals")
        self.outcome_signals = _validate_string_tuple(self.outcome_signals, label="outcome_signals")

        if self.arc_id is not None:
            self.arc_id = _validate_trimmed_string(self.arc_id, label="arc_id")

        self.intervention_family = _validate_trimmed_string(
            self.intervention_family,
            label="intervention_family",
        )  # type: ignore[assignment]
        if self.intervention_family not in _SUPPORTED_INTERVENTION_FAMILIES:
            raise ValueError(f"Unsupported intervention_family: {self.intervention_family!r}")

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

        if not isinstance(self.evidence_refs, tuple):
            actual_type = type(self.evidence_refs).__name__
            raise ValueError(f"evidence_refs must be a tuple of SupportTranscriptSpanRef values, got {actual_type}")
        for evidence_ref in self.evidence_refs:
            if not isinstance(evidence_ref, SupportTranscriptSpanRef):
                raise ValueError("evidence_refs must contain SupportTranscriptSpanRef values")

    def to_record(self) -> dict[str, Any]:
        return {
            "situation_id": self.situation_id,
            "session_id": self.session_id,
            "recorded_at": _dump_datetime(self.recorded_at),
            "turn_text": self.turn_text,
            "embedding": _dump_float_tuple(self.embedding),
            "need": self.need,
            "response_mode": self.response_mode,
            "subject_refs": _dump_str_tuple(self.subject_refs),
            "arc_id": self.arc_id,
            "domain_ids": _dump_str_tuple(self.domain_ids),
            "intervention_ids": _dump_str_tuple(self.intervention_ids),
            "behavior_contract_summary": self.behavior_contract_summary,
            "intervention_family": self.intervention_family,
            "relational_values_applied": json.dumps(self.relational_values_applied),
            "support_values_applied": json.dumps(self.support_values_applied),
            "user_response_signals": _dump_str_tuple(self.user_response_signals),
            "outcome_signals": _dump_str_tuple(self.outcome_signals),
            "evidence_refs": json.dumps([evidence_ref.to_record() for evidence_ref in self.evidence_refs]),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> LearningSituation:
        raw_evidence_refs = record.get("evidence_refs")
        if isinstance(raw_evidence_refs, str):
            decoded_evidence_refs: Any = json.loads(raw_evidence_refs)
        else:
            decoded_evidence_refs = raw_evidence_refs
        if decoded_evidence_refs is None:
            decoded_evidence_refs = []
        if not isinstance(decoded_evidence_refs, list):
            raise ValueError("Learning situation evidence_refs must deserialize to a list of records")

        evidence_refs: list[SupportTranscriptSpanRef] = []
        for decoded_evidence_ref in decoded_evidence_refs:
            if not isinstance(decoded_evidence_ref, Mapping):
                raise ValueError("Learning situation evidence_refs must contain mapping records")
            evidence_refs.append(SupportTranscriptSpanRef.from_record(decoded_evidence_ref))

        relational_values_raw = record.get("relational_values_applied")
        support_values_raw = record.get("support_values_applied")
        relational_values = json.loads(relational_values_raw) if isinstance(relational_values_raw, str) else relational_values_raw
        support_values = json.loads(support_values_raw) if isinstance(support_values_raw, str) else support_values_raw

        arc_id = record.get("arc_id")
        return cls(
            situation_id=str(record["situation_id"]),
            session_id=str(record["session_id"]),
            recorded_at=_load_datetime(record["recorded_at"]),
            turn_text=str(record["turn_text"]),
            embedding=_load_float_tuple(record.get("embedding")),
            need=cast(Need, str(record["need"])),
            response_mode=str(record["response_mode"]),
            subject_refs=_load_str_tuple(record.get("subject_refs")),
            arc_id=None if arc_id is None else str(arc_id),
            domain_ids=_load_str_tuple(record.get("domain_ids")),
            intervention_ids=_load_str_tuple(record.get("intervention_ids")),
            behavior_contract_summary=str(record["behavior_contract_summary"]),
            intervention_family=cast(InterventionFamily, str(record["intervention_family"])),
            relational_values_applied=relational_values or {},
            support_values_applied=support_values or {},
            user_response_signals=_load_str_tuple(record.get("user_response_signals")),
            outcome_signals=_load_str_tuple(record.get("outcome_signals")),
            evidence_refs=tuple(evidence_refs),
        )


@dataclass(eq=True)
class SupportPattern:
    """First-class recurring support or reflection claim derived from situations."""

    pattern_id: str
    kind: PatternKind
    scope: SupportProfileScope
    status: PatternStatus
    claim: str
    confidence: float
    created_at: datetime
    updated_at: datetime
    supporting_situation_ids: tuple[str, ...] = ()
    support_overrides: dict[str, str] = field(default_factory=dict)
    relational_overrides: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.pattern_id = _validate_trimmed_string(self.pattern_id, label="pattern_id")
        self.claim = _validate_trimmed_string(self.claim, label="claim")
        if not isinstance(self.scope, SupportProfileScope):
            raise ValueError("scope must be a SupportProfileScope")
        self.kind = _validate_trimmed_string(self.kind, label="kind")  # type: ignore[assignment]
        if self.kind not in _SUPPORTED_PATTERN_KINDS:
            raise ValueError(f"Unsupported support pattern kind: {self.kind!r}")
        self.status = _validate_trimmed_string(self.status, label="status")  # type: ignore[assignment]
        if self.status not in _SUPPORTED_PATTERN_STATUSES:
            raise ValueError(f"Unsupported support pattern status: {self.status!r}")
        self.confidence = _validate_confidence(self.confidence, label="confidence")
        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be a datetime")
        if not isinstance(self.updated_at, datetime):
            raise ValueError("updated_at must be a datetime")
        self.supporting_situation_ids = _validate_string_tuple(
            self.supporting_situation_ids,
            label="supporting_situation_ids",
        )
        self.support_overrides = _validate_applied_values(
            self.support_overrides,
            registry="support",
            label="support_overrides",
        )
        self.relational_overrides = _validate_applied_values(
            self.relational_overrides,
            registry="relational",
            label="relational_overrides",
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "kind": self.kind,
            "scope_type": self.scope.type,
            "scope_id": self.scope.id,
            "status": self.status,
            "claim": self.claim,
            "confidence": self.confidence,
            "created_at": _dump_datetime(self.created_at),
            "updated_at": _dump_datetime(self.updated_at),
            "supporting_situation_ids": _dump_str_tuple(self.supporting_situation_ids),
            "support_overrides": json.dumps(self.support_overrides),
            "relational_overrides": json.dumps(self.relational_overrides),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> SupportPattern:
        support_overrides_raw = record.get("support_overrides")
        relational_overrides_raw = record.get("relational_overrides")
        support_overrides = json.loads(support_overrides_raw) if isinstance(support_overrides_raw, str) else support_overrides_raw
        relational_overrides = (
            json.loads(relational_overrides_raw) if isinstance(relational_overrides_raw, str) else relational_overrides_raw
        )
        return cls(
            pattern_id=str(record["pattern_id"]),
            kind=cast(PatternKind, str(record["kind"])),
            scope=SupportProfileScope(
                type=cast(SupportProfileScopeType, str(record["scope_type"])),
                id=str(record["scope_id"]),
            ),
            status=cast(PatternStatus, str(record["status"])),
            claim=str(record["claim"]),
            confidence=float(record["confidence"]),
            created_at=_load_datetime(record["created_at"]),
            updated_at=_load_datetime(record["updated_at"]),
            supporting_situation_ids=_load_str_tuple(record.get("supporting_situation_ids")),
            support_overrides=support_overrides or {},
            relational_overrides=relational_overrides or {},
        )


@dataclass(eq=True)
class SupportProfileUpdateEvent:
    """Durable audit record for bounded support-profile changes."""

    event_id: str
    timestamp: datetime
    registry: SupportProfileRegistryKind
    dimension: str
    scope: SupportProfileScope
    old_value: str | None
    new_value: str
    reason: str
    confidence: float
    status: UpdateEventStatus
    source_pattern_ids: tuple[str, ...] = ()
    source_situation_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.event_id = _validate_trimmed_string(self.event_id, label="event_id")
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime")
        if not isinstance(self.scope, SupportProfileScope):
            raise ValueError("scope must be a SupportProfileScope")
        self.dimension = _validate_trimmed_string(self.dimension, label="dimension")
        self.reason = _validate_trimmed_string(self.reason, label="reason")
        self.confidence = _validate_confidence(self.confidence, label="confidence")
        self.status = _validate_trimmed_string(self.status, label="status")  # type: ignore[assignment]
        if self.status not in _SUPPORTED_UPDATE_EVENT_STATUSES:
            raise ValueError(f"Unsupported support profile update status: {self.status!r}")
        if self.old_value is not None:
            self.old_value = _validate_trimmed_string(self.old_value, label="old_value")
            validate_registry_value(self.registry, self.dimension, self.old_value)
        self.new_value = _validate_trimmed_string(self.new_value, label="new_value")
        validate_registry_value(self.registry, self.dimension, self.new_value)
        self.source_pattern_ids = _validate_string_tuple(self.source_pattern_ids, label="source_pattern_ids")
        self.source_situation_ids = _validate_string_tuple(self.source_situation_ids, label="source_situation_ids")

    def to_record(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": _dump_datetime(self.timestamp),
            "registry": self.registry,
            "dimension": self.dimension,
            "scope_type": self.scope.type,
            "scope_id": self.scope.id,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
            "confidence": self.confidence,
            "status": self.status,
            "source_pattern_ids": _dump_str_tuple(self.source_pattern_ids),
            "source_situation_ids": _dump_str_tuple(self.source_situation_ids),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> SupportProfileUpdateEvent:
        old_value = record.get("old_value")
        return cls(
            event_id=str(record["event_id"]),
            timestamp=_load_datetime(record["timestamp"]),
            registry=cast(SupportProfileRegistryKind, str(record["registry"])),
            dimension=str(record["dimension"]),
            scope=SupportProfileScope(
                type=cast(SupportProfileScopeType, str(record["scope_type"])),
                id=str(record["scope_id"]),
            ),
            old_value=None if old_value is None else str(old_value),
            new_value=str(record["new_value"]),
            reason=str(record["reason"]),
            confidence=float(record["confidence"]),
            status=cast(UpdateEventStatus, str(record["status"])),
            source_pattern_ids=_load_str_tuple(record.get("source_pattern_ids")),
            source_situation_ids=_load_str_tuple(record.get("source_situation_ids")),
        )


class SupportLearningStore(Protocol):
    """Minimal persistence contract for bounded adaptation writes."""

    async def save_learning_situation(self, situation: LearningSituation) -> None: ...

    async def save_support_pattern(self, pattern: SupportPattern) -> None: ...

    async def save_support_profile_update_event(self, event: SupportProfileUpdateEvent) -> None: ...

    async def save_support_profile_value(self, profile_value: SupportProfileValue) -> None: ...


@dataclass(eq=True, frozen=True)
class BoundedAdaptationResult:
    """Deterministic bounded-adaptation output for one current situation."""

    profile_updates: tuple[SupportProfileValue, ...]
    patterns: tuple[SupportPattern, ...]
    update_events: tuple[SupportProfileUpdateEvent, ...]


_POSITIVE_LEARNING_SIGNALS: frozenset[str] = frozenset(
    {
        "resonance",
        "commitment",
        "clarity",
        "deepening",
        "next_step_chosen",
        "resume_ready",
        "boundary_decided",
        "comparison_started",
    }
)
_LOW_RISK_SUPPORT_DIMENSIONS: frozenset[str] = frozenset(
    {
        "planning_granularity",
        "option_bandwidth",
        "proactivity_level",
        "accountability_style",
        "recovery_style",
        "pacing",
        "recommendation_forcefulness",
    }
)


def _existing_profile_key(registry: str, dimension: str, scope: SupportProfileScope) -> tuple[str, str, str, str]:
    return (registry, dimension, scope.type, scope.id)


def _is_successful_learning_signal(situation: LearningSituation) -> bool:
    combined = set(situation.user_response_signals) | set(situation.outcome_signals)
    return bool(combined & _POSITIVE_LEARNING_SIGNALS)


def _select_weighted_winner(value_scores: Mapping[str, float], value_counts: Mapping[str, int]) -> tuple[str, float, float] | None:
    if not value_scores:
        return None
    ranked = sorted(value_scores.items(), key=lambda item: (-item[1], item[0]))
    winner_value, winner_score = ranked[0]
    runner_up_score = ranked[1][1] if len(ranked) > 1 else 0.0
    if value_counts.get(winner_value, 0) < 2:
        return None
    if (winner_score / value_counts[winner_value]) < 0.85:
        return None
    if (winner_score - runner_up_score) < 0.10:
        return None
    return (winner_value, winner_score, runner_up_score)


def derive_bounded_adaptation(
    *,
    current_situation: LearningSituation,
    similar_situations: Sequence[tuple[LearningSituation, float]],
    existing_profile_values: Mapping[tuple[str, str, str, str], SupportProfileValue],
    now: datetime,
) -> BoundedAdaptationResult:
    """Derive bounded profile updates, candidate patterns, and audit events from similar situations."""
    support_value_scores: dict[str, dict[str, float]] = {}
    support_value_counts: dict[str, dict[str, int]] = {}
    relational_value_scores: dict[str, dict[str, float]] = {}
    relational_value_counts: dict[str, dict[str, int]] = {}
    supporting_ids_by_value: dict[tuple[str, str, str], list[str]] = {}

    for similar_situation, similarity in similar_situations:
        if not _is_successful_learning_signal(similar_situation):
            continue
        for dimension, value in similar_situation.support_values_applied.items():
            if dimension not in _LOW_RISK_SUPPORT_DIMENSIONS:
                continue
            support_value_scores.setdefault(dimension, {})[value] = (
                support_value_scores.setdefault(dimension, {}).get(value, 0.0) + similarity
            )
            support_value_counts.setdefault(dimension, {})[value] = support_value_counts.setdefault(dimension, {}).get(value, 0) + 1
            supporting_ids_by_value.setdefault(("support", dimension, value), []).append(similar_situation.situation_id)
        for dimension, value in similar_situation.relational_values_applied.items():
            relational_value_scores.setdefault(dimension, {})[value] = (
                relational_value_scores.setdefault(dimension, {}).get(value, 0.0) + similarity
            )
            relational_value_counts.setdefault(dimension, {})[value] = relational_value_counts.setdefault(dimension, {}).get(value, 0) + 1
            supporting_ids_by_value.setdefault(("relational", dimension, value), []).append(similar_situation.situation_id)

    profile_updates: list[SupportProfileValue] = []
    patterns: list[SupportPattern] = []
    update_events: list[SupportProfileUpdateEvent] = []

    support_scope = (
        SupportProfileScope(type="arc", id=current_situation.arc_id)
        if current_situation.arc_id is not None
        else SupportProfileScope(type="context", id=current_situation.response_mode)
    )
    for dimension, value_scores in support_value_scores.items():
        counts = support_value_counts.get(dimension, {})
        winner = _select_weighted_winner(value_scores, counts)
        if winner is None:
            continue
        winning_value, winning_score, _ = winner
        supporting_situation_ids = tuple(supporting_ids_by_value[("support", dimension, winning_value)])
        existing = existing_profile_values.get(_existing_profile_key("support", dimension, support_scope))
        old_value = None if existing is None else existing.value
        if old_value == winning_value:
            continue
        confidence = min(1.0, winning_score / counts[winning_value])
        profile_updates.append(
            SupportProfileValue(
                registry="support",
                dimension=dimension,
                scope=support_scope,
                value=winning_value,
                status="observed",
                confidence=confidence,
                source="auto_adapted",
                created_at=now,
                updated_at=now,
                evidence_refs=supporting_situation_ids,
            )
        )
        update_events.append(
            SupportProfileUpdateEvent(
                event_id=f"upd-support-{dimension}-{support_scope.type}-{support_scope.id}-{int(now.timestamp())}",
                timestamp=now,
                registry="support",
                dimension=dimension,
                scope=support_scope,
                old_value=old_value,
                new_value=winning_value,
                reason=f"Similar successful situations repeatedly favored {dimension}={winning_value}.",
                confidence=confidence,
                status="applied",
                source_situation_ids=supporting_situation_ids,
            )
        )

    relational_scope = SupportProfileScope(type="context", id=current_situation.response_mode)
    for dimension, value_scores in relational_value_scores.items():
        counts = relational_value_counts.get(dimension, {})
        winner = _select_weighted_winner(value_scores, counts)
        if winner is None:
            continue
        winning_value, winning_score, _ = winner
        existing = existing_profile_values.get(_existing_profile_key("relational", dimension, relational_scope))
        old_value = None if existing is None else existing.value
        if old_value == winning_value:
            continue
        supporting_situation_ids = tuple(supporting_ids_by_value[("relational", dimension, winning_value)])
        confidence = min(1.0, winning_score / counts[winning_value])
        patterns.append(
            SupportPattern(
                pattern_id=f"pattern-{dimension}-{relational_scope.type}-{relational_scope.id}",
                kind="support_preference",
                scope=relational_scope,
                status="candidate",
                claim=f"{dimension}={winning_value} appears to work better in similar situations.",
                confidence=confidence,
                created_at=now,
                updated_at=now,
                supporting_situation_ids=supporting_situation_ids,
                relational_overrides={dimension: winning_value},
            )
        )
        update_events.append(
            SupportProfileUpdateEvent(
                event_id=f"upd-relational-{dimension}-{relational_scope.type}-{relational_scope.id}-{int(now.timestamp())}",
                timestamp=now,
                registry="relational",
                dimension=dimension,
                scope=relational_scope,
                old_value=old_value,
                new_value=winning_value,
                reason=f"Similar successful situations repeatedly favored {dimension}={winning_value}.",
                confidence=confidence,
                status="proposed",
                source_situation_ids=supporting_situation_ids,
            )
        )

    return BoundedAdaptationResult(
        profile_updates=tuple(profile_updates),
        patterns=tuple(patterns),
        update_events=tuple(update_events),
    )


async def apply_bounded_adaptation(
    *,
    store: SupportLearningStore,
    current_situation: LearningSituation,
    similar_situations: Sequence[tuple[LearningSituation, float]],
    existing_profile_values: Mapping[tuple[str, str, str, str], SupportProfileValue],
    now: datetime,
) -> BoundedAdaptationResult:
    """Persist one learning situation plus any bounded adaptation artifacts it produces."""
    await store.save_learning_situation(current_situation)
    result = derive_bounded_adaptation(
        current_situation=current_situation,
        similar_situations=similar_situations,
        existing_profile_values=existing_profile_values,
        now=now,
    )
    for profile_update in result.profile_updates:
        await store.save_support_profile_value(profile_update)
    for pattern in result.patterns:
        await store.save_support_pattern(pattern)
    for update_event in result.update_events:
        await store.save_support_profile_update_event(update_event)
    return result


__all__ = [
    "BoundedAdaptationResult",
    "FinalizedLearningCaseBundle",
    "LearningCase",
    "LearningSituation",
    "OutcomeObservation",
    "SupportAttempt",
    "SupportLearningStore",
    "SupportLedgerDerivationResult",
    "SupportLedgerUpdateEvent",
    "SupportPattern",
    "SupportPatternLedgerEntry",
    "SupportProfileUpdateEvent",
    "SupportTranscriptSpanRef",
    "SupportValueLedgerEntry",
    "apply_bounded_adaptation",
    "derive_bounded_adaptation",
    "derive_learning_case",
    "derive_value_ledger_updates_from_cases",
]
