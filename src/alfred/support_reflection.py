"""Support reflection contracts and read-model helpers for PRD #169."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol, cast

from alfred.memory.support_learning import LearningSituation, SupportPattern, SupportProfileUpdateEvent
from alfred.memory.support_memory import LifeDomain, OperationalArc
from alfred.memory.support_profile import (
    SupportProfileScope,
    SupportProfileValue,
    get_registry_dimension,
    validate_registry_value,
)
from alfred.support_policy import ResolvedSubject, SupportPolicyPattern, SupportTurnAssessment, resolve_support_policy

ReviewCardKind = Literal["support_fit", "blocker", "identity_theme", "direction_theme", "calibration_gap"]
CorrectionRegistry = Literal["relational", "support"]

_SUPPORTED_REVIEW_CARD_KINDS: frozenset[str] = frozenset(
    {"support_fit", "blocker", "identity_theme", "direction_theme", "calibration_gap"}
)
_SUPPORTED_PATTERN_STATUSES: frozenset[str] = frozenset({"candidate", "confirmed", "rejected"})
_SUPPORTED_CORRECTION_REGISTRIES: frozenset[str] = frozenset({"relational", "support"})



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



def _validate_confidence(value: Any, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        actual_type = type(value).__name__
        raise ValueError(f"{label} must be numeric, got {actual_type}")
    normalized = float(value)
    if not 0.0 <= normalized <= 1.0:
        raise ValueError(f"{label} must be between 0.0 and 1.0")
    return normalized



def _pattern_to_card_kind(kind: str) -> ReviewCardKind:
    mapping: dict[str, ReviewCardKind] = {
        "support_preference": "support_fit",
        "recurring_blocker": "blocker",
        "identity_theme": "identity_theme",
        "direction_theme": "direction_theme",
        "calibration_gap": "calibration_gap",
    }
    try:
        return mapping[kind]
    except KeyError as exc:
        raise ValueError(f"Unsupported support pattern kind for review cards: {kind!r}") from exc



def _default_proposed_action(kind: str) -> str:
    if kind == "support_preference":
        return "Confirm whether this help shape fits and keep it active when relevant."
    if kind == "recurring_blocker":
        return "Confirm whether this blocker is real and keep it visible in future planning."
    if kind == "identity_theme":
        return "Confirm whether this identity-level theme feels real before Alfred keeps it active."
    if kind == "direction_theme":
        return "Confirm whether this direction-level tension is real and worth keeping visible."
    if kind == "calibration_gap":
        return "Confirm whether this contradiction is real and whether Alfred should surface it more directly."
    raise ValueError(f"Unsupported support pattern kind for proposed_action: {kind!r}")


@dataclass(frozen=True)
class ReviewCard:
    """Derived, user-facing reflection object projected from one durable pattern."""

    card_id: str
    source_pattern_id: str
    card_kind: ReviewCardKind
    scope: SupportProfileScope
    status: str
    statement: str
    confidence: float
    evidence_refs: tuple[str, ...]
    proposed_action: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "card_id", _validate_trimmed_string(self.card_id, label="card_id"))
        object.__setattr__(
            self,
            "source_pattern_id",
            _validate_trimmed_string(self.source_pattern_id, label="source_pattern_id"),
        )
        if not isinstance(self.scope, SupportProfileScope):
            raise ValueError("scope must be a SupportProfileScope")
        if self.card_kind not in _SUPPORTED_REVIEW_CARD_KINDS:
            raise ValueError(f"Unsupported review card kind: {self.card_kind!r}")
        if self.status not in _SUPPORTED_PATTERN_STATUSES:
            raise ValueError(f"Unsupported review card status: {self.status!r}")
        object.__setattr__(self, "statement", _validate_trimmed_string(self.statement, label="statement"))
        object.__setattr__(self, "confidence", _validate_confidence(self.confidence, label="confidence"))
        object.__setattr__(self, "evidence_refs", _validate_string_tuple(self.evidence_refs, label="evidence_refs"))
        object.__setattr__(
            self,
            "proposed_action",
            _validate_trimmed_string(self.proposed_action, label="proposed_action"),
        )



def review_card_from_pattern(pattern: SupportPattern) -> ReviewCard:
    """Project one durable support pattern into a bounded review card."""

    return ReviewCard(
        card_id=f"card-{pattern.pattern_id}",
        source_pattern_id=pattern.pattern_id,
        card_kind=_pattern_to_card_kind(pattern.kind),
        scope=pattern.scope,
        status=pattern.status,
        statement=pattern.claim,
        confidence=pattern.confidence,
        evidence_refs=pattern.supporting_situation_ids,
        proposed_action=_default_proposed_action(pattern.kind),
    )


@dataclass(frozen=True)
class PatternSummary:
    pattern_id: str
    kind: str
    scope: SupportProfileScope
    status: str
    claim: str
    confidence: float

    @classmethod
    def from_pattern(cls, pattern: SupportPattern) -> PatternSummary:
        return cls(
            pattern_id=pattern.pattern_id,
            kind=pattern.kind,
            scope=pattern.scope,
            status=pattern.status,
            claim=pattern.claim,
            confidence=pattern.confidence,
        )


@dataclass(frozen=True)
class UpdateEventSummary:
    event_id: str
    registry: str
    dimension: str
    scope: SupportProfileScope
    status: str
    old_value: str | None
    new_value: str
    reason: str
    confidence: float
    timestamp: datetime

    @classmethod
    def from_event(cls, event: SupportProfileUpdateEvent) -> UpdateEventSummary:
        return cls(
            event_id=event.event_id,
            registry=event.registry,
            dimension=event.dimension,
            scope=event.scope,
            status=event.status,
            old_value=event.old_value,
            new_value=event.new_value,
            reason=event.reason,
            confidence=event.confidence,
            timestamp=event.timestamp,
        )


@dataclass(frozen=True)
class LearningSituationSummary:
    situation_id: str
    session_id: str
    response_mode: str
    intervention_family: str
    behavior_contract_summary: str
    recorded_at: datetime

    @classmethod
    def from_situation(cls, situation: LearningSituation) -> LearningSituationSummary:
        return cls(
            situation_id=situation.situation_id,
            session_id=situation.session_id,
            response_mode=situation.response_mode,
            intervention_family=situation.intervention_family,
            behavior_contract_summary=situation.behavior_contract_summary,
            recorded_at=situation.recorded_at,
        )


@dataclass(frozen=True)
class SupportInspectionRequest:
    response_mode: str
    arc_id: str | None = None


@dataclass(frozen=True)
class ActiveRuntimeState:
    response_mode: str
    active_arc_id: str | None
    effective_support_values: dict[str, str]
    effective_relational_values: dict[str, str]
    active_patterns: tuple[PatternSummary, ...]


@dataclass(frozen=True)
class LearnedState:
    candidate_patterns: tuple[PatternSummary, ...]
    confirmed_patterns: tuple[PatternSummary, ...]
    recent_update_events: tuple[UpdateEventSummary, ...]
    recent_interventions: tuple[LearningSituationSummary, ...]


@dataclass(frozen=True)
class SupportInspectionSnapshot:
    request: SupportInspectionRequest
    active_runtime_state: ActiveRuntimeState
    learned_state: LearnedState
    active_domains: tuple[LifeDomain, ...]
    active_arcs: tuple[OperationalArc, ...]


@dataclass(frozen=True)
class PatternDetail:
    pattern: SupportPattern
    supporting_situations: tuple[LearningSituation, ...]
    review_card: ReviewCard


@dataclass(frozen=True)
class UpdateEventDetail:
    event: SupportProfileUpdateEvent
    source_patterns: tuple[SupportPattern, ...]
    source_situations: tuple[LearningSituation, ...]


@dataclass(frozen=True)
class EffectiveValueExplanation:
    registry: str
    dimension: str
    response_mode: str
    arc_id: str | None
    winning_value: str
    source_kind: Literal["default", "stored", "pattern"]
    source_scope: SupportProfileScope
    source_pattern_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConfirmPatternAction:
    pattern_id: str
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "pattern_id", _validate_trimmed_string(self.pattern_id, label="pattern_id"))
        object.__setattr__(self, "reason", _validate_trimmed_string(self.reason, label="reason"))


@dataclass(frozen=True)
class RejectPatternAction:
    pattern_id: str
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "pattern_id", _validate_trimmed_string(self.pattern_id, label="pattern_id"))
        object.__setattr__(self, "reason", _validate_trimmed_string(self.reason, label="reason"))


@dataclass(frozen=True)
class CorrectProfileValueAction:
    registry: CorrectionRegistry
    dimension: str
    scope: SupportProfileScope
    new_value: str
    reason: str

    def __post_init__(self) -> None:
        if self.registry not in _SUPPORTED_CORRECTION_REGISTRIES:
            raise ValueError(f"Unsupported correction registry: {self.registry!r}")
        object.__setattr__(self, "dimension", _validate_trimmed_string(self.dimension, label="dimension"))
        if not isinstance(self.scope, SupportProfileScope):
            raise ValueError("scope must be a SupportProfileScope")
        normalized_value = _validate_trimmed_string(self.new_value, label="new_value")
        validate_registry_value(self.registry, self.dimension, normalized_value)
        object.__setattr__(self, "new_value", normalized_value)
        object.__setattr__(self, "reason", _validate_trimmed_string(self.reason, label="reason"))


@dataclass(frozen=True)
class ResetProfileValueAction:
    registry: CorrectionRegistry
    dimension: str
    scope: SupportProfileScope
    reason: str

    def __post_init__(self) -> None:
        if self.registry not in _SUPPORTED_CORRECTION_REGISTRIES:
            raise ValueError(f"Unsupported correction registry: {self.registry!r}")
        object.__setattr__(self, "dimension", _validate_trimmed_string(self.dimension, label="dimension"))
        if not isinstance(self.scope, SupportProfileScope):
            raise ValueError("scope must be a SupportProfileScope")
        object.__setattr__(self, "reason", _validate_trimmed_string(self.reason, label="reason"))


@dataclass(frozen=True)
class ScopeLimitProfileValueAction:
    registry: CorrectionRegistry
    dimension: str
    source_scope: SupportProfileScope
    target_scope: SupportProfileScope
    reason: str

    def __post_init__(self) -> None:
        if self.registry not in _SUPPORTED_CORRECTION_REGISTRIES:
            raise ValueError(f"Unsupported correction registry: {self.registry!r}")
        object.__setattr__(self, "dimension", _validate_trimmed_string(self.dimension, label="dimension"))
        if not isinstance(self.source_scope, SupportProfileScope):
            raise ValueError("source_scope must be a SupportProfileScope")
        if not isinstance(self.target_scope, SupportProfileScope):
            raise ValueError("target_scope must be a SupportProfileScope")
        if self.source_scope == self.target_scope:
            raise ValueError("source_scope and target_scope must differ")
        object.__setattr__(self, "reason", _validate_trimmed_string(self.reason, label="reason"))


SupportCorrectionAction = (
    ConfirmPatternAction
    | RejectPatternAction
    | CorrectProfileValueAction
    | ResetProfileValueAction
    | ScopeLimitProfileValueAction
)


class SupportReflectionStore(Protocol):
    async def resolve_support_profile_value(
        self,
        registry: str,
        dimension: str,
        *,
        context_id: str | None = None,
        arc_id: str | None = None,
    ) -> SupportProfileValue | None: ...

    async def get_support_profile_value(
        self,
        registry: str,
        dimension: str,
        scope: SupportProfileScope,
    ) -> SupportProfileValue | None: ...

    async def list_support_patterns_for_runtime(
        self,
        *,
        response_mode: str,
        arc_id: str | None = None,
    ) -> list[SupportPattern]: ...

    async def list_support_patterns_for_inspection(
        self,
        *,
        statuses: tuple[str, ...] = ("candidate", "confirmed"),
        limit: int = 12,
    ) -> list[SupportPattern]: ...

    async def get_support_pattern(self, pattern_id: str) -> SupportPattern | None: ...

    async def list_support_profile_update_events(self, *, limit: int = 12) -> list[SupportProfileUpdateEvent]: ...

    async def get_support_profile_update_event(self, event_id: str) -> SupportProfileUpdateEvent | None: ...

    async def list_recent_learning_situations(self, *, limit: int = 6) -> list[LearningSituation]: ...

    async def list_learning_situations_by_ids(self, situation_ids: tuple[str, ...]) -> list[LearningSituation]: ...

    async def list_resume_arcs(self, limit: int = 12) -> list[OperationalArc]: ...

    async def list_active_life_domains(self, limit: int = 6) -> list[LifeDomain]: ...


class SupportReflectionRuntime:
    """Small reflection helper that derives review and inspection read models."""

    def __init__(self, *, store: SupportReflectionStore) -> None:
        self._store = store

    async def build_inspection_snapshot(
        self,
        *,
        response_mode: str,
        arc_id: str | None = None,
    ) -> SupportInspectionSnapshot:
        runtime_patterns = await self._store.list_support_patterns_for_runtime(
            response_mode=response_mode,
            arc_id=arc_id,
        )
        resolved = await resolve_support_policy(
            store=cast(Any, self._store),
            assessment=SupportTurnAssessment(
                need="unknown",
                subjects=(ResolvedSubject(kind="arc", id=arc_id),) if arc_id is not None else (),
            ),
            response_mode=cast(Any, response_mode),
            patterns=tuple(
                SupportPolicyPattern(
                    name=pattern.claim,
                    relational_overrides=pattern.relational_overrides,
                    support_overrides=pattern.support_overrides,
                )
                for pattern in runtime_patterns
            ),
        )
        inspection_patterns = await self._store.list_support_patterns_for_inspection()
        update_events = await self._store.list_support_profile_update_events(limit=12)
        recent_situations = await self._store.list_recent_learning_situations(limit=6)
        arcs = await self._store.list_resume_arcs(limit=12)
        domains = await self._store.list_active_life_domains(limit=6)

        candidate_patterns = tuple(
            PatternSummary.from_pattern(pattern)
            for pattern in inspection_patterns
            if pattern.status == "candidate"
        )
        confirmed_patterns = tuple(
            PatternSummary.from_pattern(pattern)
            for pattern in inspection_patterns
            if pattern.status == "confirmed"
        )
        return SupportInspectionSnapshot(
            request=SupportInspectionRequest(response_mode=response_mode, arc_id=arc_id),
            active_runtime_state=ActiveRuntimeState(
                response_mode=response_mode,
                active_arc_id=arc_id,
                effective_support_values=dict(resolved.support_values),
                effective_relational_values=dict(resolved.relational_values),
                active_patterns=tuple(PatternSummary.from_pattern(pattern) for pattern in runtime_patterns),
            ),
            learned_state=LearnedState(
                candidate_patterns=candidate_patterns,
                confirmed_patterns=confirmed_patterns,
                recent_update_events=tuple(UpdateEventSummary.from_event(event) for event in update_events),
                recent_interventions=tuple(LearningSituationSummary.from_situation(situation) for situation in recent_situations),
            ),
            active_domains=tuple(domains),
            active_arcs=tuple(arcs),
        )

    async def get_pattern_detail(self, pattern_id: str) -> PatternDetail | None:
        pattern = await self._store.get_support_pattern(pattern_id)
        if pattern is None:
            return None
        situations = await self._store.list_learning_situations_by_ids(pattern.supporting_situation_ids)
        return PatternDetail(
            pattern=pattern,
            supporting_situations=tuple(situations),
            review_card=review_card_from_pattern(pattern),
        )

    async def get_update_event_detail(self, event_id: str) -> UpdateEventDetail | None:
        event = await self._store.get_support_profile_update_event(event_id)
        if event is None:
            return None
        patterns: list[SupportPattern] = []
        for pattern_id in event.source_pattern_ids:
            pattern = await self._store.get_support_pattern(pattern_id)
            if pattern is not None:
                patterns.append(pattern)
        situations = await self._store.list_learning_situations_by_ids(event.source_situation_ids)
        return UpdateEventDetail(
            event=event,
            source_patterns=tuple(patterns),
            source_situations=tuple(situations),
        )

    async def explain_effective_value(
        self,
        *,
        registry: str,
        dimension: str,
        response_mode: str,
        arc_id: str | None = None,
    ) -> EffectiveValueExplanation:
        runtime_patterns = await self._store.list_support_patterns_for_runtime(
            response_mode=response_mode,
            arc_id=arc_id,
        )
        matching_patterns = [
            pattern
            for pattern in runtime_patterns
            if (
                registry == "support" and dimension in pattern.support_overrides
            ) or (
                registry == "relational" and dimension in pattern.relational_overrides
            )
        ]
        if matching_patterns:
            winner = matching_patterns[-1]
            value = (
                winner.support_overrides[dimension]
                if registry == "support"
                else winner.relational_overrides[dimension]
            )
            return EffectiveValueExplanation(
                registry=registry,
                dimension=dimension,
                response_mode=response_mode,
                arc_id=arc_id,
                winning_value=value,
                source_kind="pattern",
                source_scope=winner.scope,
                source_pattern_ids=tuple(pattern.pattern_id for pattern in matching_patterns),
            )

        stored = await self._store.resolve_support_profile_value(
            registry,
            dimension,
            context_id=response_mode,
            arc_id=arc_id,
        )
        if stored is not None:
            return EffectiveValueExplanation(
                registry=registry,
                dimension=dimension,
                response_mode=response_mode,
                arc_id=arc_id,
                winning_value=stored.value,
                source_kind="stored",
                source_scope=stored.scope,
            )

        definition = get_registry_dimension(cast(Any, registry), dimension)
        return EffectiveValueExplanation(
            registry=registry,
            dimension=dimension,
            response_mode=response_mode,
            arc_id=arc_id,
            winning_value=definition.default_value,
            source_kind="default",
            source_scope=SupportProfileScope(type="global", id="user"),
        )


__all__ = [
    "ActiveRuntimeState",
    "ConfirmPatternAction",
    "CorrectProfileValueAction",
    "EffectiveValueExplanation",
    "LearnedState",
    "LearningSituationSummary",
    "PatternDetail",
    "PatternSummary",
    "RejectPatternAction",
    "ResetProfileValueAction",
    "ReviewCard",
    "ScopeLimitProfileValueAction",
    "SupportCorrectionAction",
    "SupportInspectionRequest",
    "SupportInspectionSnapshot",
    "SupportReflectionRuntime",
    "UpdateEventDetail",
    "UpdateEventSummary",
    "review_card_from_pattern",
]
