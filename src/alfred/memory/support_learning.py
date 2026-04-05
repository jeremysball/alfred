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

_SUPPORTED_NEEDS: frozenset[str] = frozenset({
    "orient",
    "resume",
    "activate",
    "decide",
    "reflect",
    "calibrate",
    "unknown",
})
PatternKind = Literal[
    "support_preference",
    "recurring_blocker",
    "identity_theme",
    "direction_theme",
    "calibration_gap",
]
PatternStatus = Literal["candidate", "confirmed", "rejected"]
UpdateEventStatus = Literal["proposed", "applied", "reverted"]

_SUPPORTED_INTERVENTION_FAMILIES: frozenset[str] = frozenset({
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
})
_SUPPORTED_PATTERN_KINDS: frozenset[str] = frozenset({
    "support_preference",
    "recurring_blocker",
    "identity_theme",
    "direction_theme",
    "calibration_gap",
})
_SUPPORTED_PATTERN_STATUSES: frozenset[str] = frozenset({"candidate", "confirmed", "rejected"})
_SUPPORTED_UPDATE_EVENT_STATUSES: frozenset[str] = frozenset({"proposed", "applied", "reverted"})


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
        support_overrides = (
            json.loads(support_overrides_raw)
            if isinstance(support_overrides_raw, str)
            else support_overrides_raw
        )
        relational_overrides = (
            json.loads(relational_overrides_raw)
            if isinstance(relational_overrides_raw, str)
            else relational_overrides_raw
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


_POSITIVE_LEARNING_SIGNALS: frozenset[str] = frozenset({
    "resonance",
    "commitment",
    "clarity",
    "deepening",
    "next_step_chosen",
    "resume_ready",
    "boundary_decided",
    "comparison_started",
})
_LOW_RISK_SUPPORT_DIMENSIONS: frozenset[str] = frozenset({
    "planning_granularity",
    "option_bandwidth",
    "proactivity_level",
    "accountability_style",
    "recovery_style",
    "pacing",
    "recommendation_forcefulness",
})


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
            support_value_counts.setdefault(dimension, {})[value] = (
                support_value_counts.setdefault(dimension, {}).get(value, 0) + 1
            )
            supporting_ids_by_value.setdefault(("support", dimension, value), []).append(similar_situation.situation_id)
        for dimension, value in similar_situation.relational_values_applied.items():
            relational_value_scores.setdefault(dimension, {})[value] = (
                relational_value_scores.setdefault(dimension, {}).get(value, 0.0) + similarity
            )
            relational_value_counts.setdefault(dimension, {})[value] = (
                relational_value_counts.setdefault(dimension, {}).get(value, 0) + 1
            )
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
    "LearningSituation",
    "SupportLearningStore",
    "SupportPattern",
    "SupportProfileUpdateEvent",
    "SupportTranscriptSpanRef",
    "apply_bounded_adaptation",
    "derive_bounded_adaptation",
]
