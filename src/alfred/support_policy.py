"""Runtime support-policy assessment, resolution, and contract compilation.

Implements PRD #168 Milestone 4:
- assess one support need from the live turn
- resolve ordered subjects
- derive one response mode
- resolve effective support and relational values
- compile a prompt-facing behavior contract
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast

from alfred.embeddings import cosine_similarity
from alfred.memory.support_context import ArcResumeContext, get_support_operational_context
from alfred.memory.support_learning import (
    LearningSituation,
    SupportPattern,
    SupportProfileUpdateEvent,
    apply_bounded_adaptation,
)
from alfred.memory.support_memory import LifeDomain, OperationalArc
from alfred.memory.support_profile import (
    RELATIONAL_REGISTRY_DIMENSIONS,
    SUPPORT_REGISTRY_DIMENSIONS,
    SupportProfileValue,
    validate_registry_value,
)

if TYPE_CHECKING:
    from alfred.embeddings.provider import EmbeddingProvider
    from alfred.storage.sqlite import SQLiteStore

Vector = tuple[float, ...]
Need = Literal["orient", "resume", "activate", "decide", "reflect", "calibrate", "unknown"]
SubjectKind = Literal["global", "arc", "domain", "identity", "direction", "current_turn"]
ResponseMode = Literal["plan", "execute", "decide", "review", "identity_reflect", "direction_reflect"]
EvidenceMode = Literal["none", "light", "explicit", "structured"]
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

_NEEDS_FOR_CLASSIFICATION: tuple[Need, ...] = (
    "orient",
    "resume",
    "activate",
    "decide",
    "reflect",
    "calibrate",
)
_CONCRETE_SUBJECT_KINDS: frozenset[SubjectKind] = frozenset({"arc", "domain"})
_ABSTRACT_SUBJECT_KINDS: frozenset[SubjectKind] = frozenset({"global", "identity", "direction", "current_turn"})

_DEFAULT_NEED_THRESHOLDS = None
_DEFAULT_SUBJECT_THRESHOLDS = None

_DEFAULT_NEED_PROTOTYPE_TEXTS: tuple[tuple[str, Need, str], ...] = (
    ("orient-1", "orient", "what is active right now overall"),
    ("orient-2", "orient", "give me a broad overview of what is in motion"),
    ("resume-1", "resume", "let us continue where we left off"),
    ("resume-2", "resume", "pick back up the thread from before"),
    ("activate-1", "activate", "help me start with one next step"),
    ("activate-2", "activate", "i need momentum and a narrow next move"),
    ("decide-1", "decide", "help me compare options and choose"),
    ("decide-2", "decide", "which direction should i choose"),
    ("reflect-1", "reflect", "help me understand the pattern in me"),
    ("reflect-2", "reflect", "why do i keep doing this"),
    ("calibrate-1", "calibrate", "tell me honestly what you are seeing"),
    ("calibrate-2", "calibrate", "help me evaluate whether this is really working"),
)

_DEFAULT_ABSTRACT_SUBJECT_TEXTS: tuple[tuple[SubjectKind, str, tuple[str, ...]], ...] = (
    (
        "global",
        "overall active picture and broad operational orientation",
        ("overall", "what is active", "what is blocked", "broad picture"),
    ),
    (
        "identity",
        "identity and self-pattern reflection",
        ("self worth", "pattern in me", "what is wrong with me", "why do i keep"),
    ),
    (
        "direction",
        "direction trajectory and longer-horizon reflection",
        ("direction", "trajectory", "headed", "long term", "future"),
    ),
    (
        "current_turn",
        "current local turn and immediate deictic focus",
        ("this", "that", "here", "right now"),
    ),
)


class SupportPolicyStore(Protocol):
    """Minimal store contract required by the policy resolver and runtime."""

    async def resolve_support_profile_value(
        self,
        registry: str,
        dimension: str,
        *,
        context_id: str | None = None,
        arc_id: str | None = None,
    ) -> SupportProfileValue | None: ...

    async def list_resume_arcs(self, limit: int = 12) -> list[OperationalArc]: ...

    async def list_active_life_domains(self, limit: int = 4) -> list[LifeDomain]: ...

    async def list_support_patterns_for_runtime(
        self,
        *,
        response_mode: str,
        arc_id: str | None = None,
    ) -> list[SupportPattern]: ...

    async def search_learning_situations(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 5,
        response_mode: str | None = None,
        need: str | None = None,
    ) -> list[tuple[LearningSituation, float]]: ...

    async def save_learning_situation(self, situation: LearningSituation) -> None: ...

    async def save_support_pattern(self, pattern: SupportPattern) -> None: ...

    async def save_support_profile_update_event(self, event: SupportProfileUpdateEvent) -> None: ...

    async def save_support_profile_value(self, profile_value: SupportProfileValue) -> None: ...


@dataclass(frozen=True)
class EmbeddedTurn:
    """Embedded view of one live user turn."""

    text: str
    vector: Vector


@dataclass(frozen=True)
class NeedPrototype:
    """One labeled embedded need example."""

    prototype_id: str
    need: Need
    text: str
    vector: Vector


@dataclass(frozen=True)
class NeedPrototypeBank:
    """Curated need centroids plus labeled examples."""

    centroids: dict[Need, Vector]
    prototypes: tuple[NeedPrototype, ...]
    top_k: int


@dataclass(frozen=True)
class NeedAssessmentThresholds:
    """Deterministic abstention thresholds for need assessment."""

    absolute_min_similarity: float
    min_margin_to_second: float
    min_top_k_label_hits: int
    min_top_k_label_fraction: float


@dataclass(frozen=True)
class NeedScore:
    """One scored need label."""

    need: Need
    similarity: float


@dataclass(frozen=True)
class NeedNeighbor:
    """One nearest labeled need exemplar."""

    prototype_id: str
    need: Need
    similarity: float


@dataclass(frozen=True)
class NeedAssessmentTrace:
    """Trace data for deterministic need selection or abstention."""

    centroid_scores: tuple[NeedScore, ...]
    top_neighbors: tuple[NeedNeighbor, ...]
    winning_need: Need | None
    winning_similarity: float | None
    second_need: Need | None
    margin: float | None
    top_k_label_hits: int
    abstention_reason: str | None


@dataclass(frozen=True)
class NeedAssessmentResult:
    """Public need outcome plus trace."""

    need: Need
    trace: NeedAssessmentTrace


@dataclass(frozen=True)
class SubjectPrototype:
    """One embedded subject candidate prototype."""

    kind: SubjectKind
    id: str | None
    text: str
    aliases: tuple[str, ...]
    vector: Vector


@dataclass(frozen=True)
class ResolvedSubject:
    """One emitted subject in the public contract."""

    kind: SubjectKind
    id: str | None


@dataclass(frozen=True)
class SubjectCandidate:
    """One scored subject candidate before public emission."""

    kind: SubjectKind
    id: str | None
    semantic_similarity: float
    exact_alias_hit: bool
    ordered_alias_hit: bool
    token_overlap_band: int
    active_scope_hit: bool
    abstract_grounding_hit: bool
    grounding_score: int
    total_score: float
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class SubjectResolutionThresholds:
    """Thresholds for subject shortlist emission."""

    shortlist_k: int
    semantic_min_similarity: float
    concrete_min_grounding_score: int
    abstract_min_grounding_score: int
    concrete_min_total_score: float
    abstract_min_total_score: float
    same_kind_margin: float


@dataclass(frozen=True)
class SubjectResolutionTrace:
    """Trace data for subject shortlisting and emission."""

    shortlisted_candidates: tuple[SubjectCandidate, ...]
    accepted_subjects: tuple[ResolvedSubject, ...]
    dropped_candidates: tuple[SubjectCandidate, ...]


@dataclass(frozen=True)
class SubjectResolutionResult:
    """Resolved ordered subjects plus trace."""

    subjects: tuple[ResolvedSubject, ...]
    trace: SubjectResolutionTrace


@dataclass(frozen=True)
class SupportTurnAssessment:
    """Public runtime turn-assessment contract."""

    need: Need
    subjects: tuple[ResolvedSubject, ...]


@dataclass(frozen=True)
class TurnAssessmentTrace:
    """Combined turn trace for need and subject assessment."""

    need_trace: NeedAssessmentTrace
    subject_trace: SubjectResolutionTrace


@dataclass(frozen=True)
class TurnAssessmentResult:
    """Public assessment plus richer internal trace."""

    assessment: SupportTurnAssessment
    trace: TurnAssessmentTrace


@dataclass(frozen=True)
class SupportTransientState:
    """Transient runtime signals that adjust resolved values."""

    overwhelm: bool = False
    urgency: bool = False
    ambiguity: bool = False
    shame_risk: bool = False


@dataclass(frozen=True)
class SupportPolicyPattern:
    """Pattern-driven explicit overrides for the runtime resolver."""

    name: str
    relational_overrides: Mapping[str, str] = field(default_factory=dict)
    support_overrides: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ResolvedSupportPolicy:
    """Resolved effective values after defaults, learning, and transient adjustments."""

    assessment: SupportTurnAssessment
    response_mode: ResponseMode
    relational_values: dict[str, str]
    support_values: dict[str, str]
    primary_arc_id: str | None
    domain_ids: tuple[str, ...]


@dataclass(frozen=True)
class SupportBehaviorContract:
    """Prompt-facing runtime behavior contract."""

    need: Need
    response_mode: ResponseMode
    subjects: tuple[ResolvedSubject, ...]
    relational_values: dict[str, str]
    support_values: dict[str, str]
    stance_summary: str
    evidence_mode: EvidenceMode
    intervention_family: InterventionFamily


@dataclass(frozen=True)
class SupportPolicyRuntimeResult:
    """End-to-end runtime output for one live turn."""

    assessment: SupportTurnAssessment
    response_mode: ResponseMode
    resolved_policy: ResolvedSupportPolicy
    behavior_contract: SupportBehaviorContract
    trace: TurnAssessmentTrace


def _default_need_thresholds() -> NeedAssessmentThresholds:
    return NeedAssessmentThresholds(
        absolute_min_similarity=0.72,
        min_margin_to_second=0.08,
        min_top_k_label_hits=2,
        min_top_k_label_fraction=0.66,
    )


def _default_subject_thresholds() -> SubjectResolutionThresholds:
    return SubjectResolutionThresholds(
        shortlist_k=8,
        semantic_min_similarity=0.35,
        concrete_min_grounding_score=2,
        abstract_min_grounding_score=2,
        concrete_min_total_score=6.5,
        abstract_min_total_score=5.5,
        same_kind_margin=0.35,
    )


def _normalize_text(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _tokenize(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", text.lower()))


def _normalize_vector(values: Sequence[float]) -> Vector:
    norm = math.sqrt(sum(float(value) * float(value) for value in values))
    if norm == 0.0:
        return tuple(0.0 for _ in values)
    return tuple(float(value) / norm for value in values)


def _average_vectors(vectors: Sequence[Vector]) -> Vector:
    if not vectors:
        raise ValueError("Cannot average an empty vector collection")
    length = len(vectors[0])
    totals = [0.0] * length
    for vector in vectors:
        if len(vector) != length:
            raise ValueError("All vectors must share one dimension")
        for index, value in enumerate(vector):
            totals[index] += value
    return _normalize_vector([value / len(vectors) for value in totals])


def _similarity(a: Vector, b: Vector) -> float:
    return float(cosine_similarity(list(a), list(b)))


async def _embed_many(embedder: EmbeddingProvider, texts: Sequence[str]) -> tuple[Vector, ...]:
    if not texts:
        return ()

    try:
        batch_vectors = await embedder.embed_batch(list(texts))
    except NotImplementedError:
        batch_vectors = [await embedder.embed(text) for text in texts]

    return tuple(_normalize_vector(vector) for vector in batch_vectors)


async def build_need_prototype_bank(
    *,
    embedder: EmbeddingProvider,
    prototype_texts: Sequence[tuple[str, Need, str]],
    top_k: int = 3,
) -> NeedPrototypeBank:
    """Embed and compile one need prototype bank."""
    vectors = await _embed_many(embedder, [text for _, _, text in prototype_texts])
    prototypes = tuple(
        NeedPrototype(prototype_id=prototype_id, need=need, text=text, vector=vector)
        for (prototype_id, need, text), vector in zip(prototype_texts, vectors, strict=True)
    )

    grouped: dict[Need, list[Vector]] = defaultdict(list)
    for prototype in prototypes:
        grouped[prototype.need].append(prototype.vector)

    centroids = {need: _average_vectors(vectors_for_need) for need, vectors_for_need in grouped.items()}
    return NeedPrototypeBank(centroids=centroids, prototypes=prototypes, top_k=top_k)


async def build_subject_prototypes(
    *,
    embedder: EmbeddingProvider,
    prototype_texts: Sequence[tuple[SubjectKind, str | None, str, tuple[str, ...]]],
) -> tuple[SubjectPrototype, ...]:
    """Embed and compile one subject prototype collection."""
    vectors = await _embed_many(embedder, [text for _, _, text, _ in prototype_texts])
    return tuple(
        SubjectPrototype(kind=kind, id=subject_id, text=text, aliases=aliases, vector=vector)
        for (kind, subject_id, text, aliases), vector in zip(prototype_texts, vectors, strict=True)
    )


def assess_need(
    *,
    embedded_turn: EmbeddedTurn,
    prototype_bank: NeedPrototypeBank,
    thresholds: NeedAssessmentThresholds,
) -> NeedAssessmentResult:
    """Assess one support need from one embedded turn with deterministic abstention."""
    scores = tuple(
        sorted(
            (
                NeedScore(need=need, similarity=_similarity(embedded_turn.vector, centroid))
                for need, centroid in prototype_bank.centroids.items()
            ),
            key=lambda score: score.similarity,
            reverse=True,
        )
    )
    if not scores:
        raise ValueError("Need prototype bank must include at least one centroid")

    top_score = scores[0]
    second_score = scores[1] if len(scores) > 1 else None
    margin = top_score.similarity - second_score.similarity if second_score is not None else 1.0

    neighbors = tuple(
        sorted(
            (
                NeedNeighbor(
                    prototype_id=prototype.prototype_id,
                    need=prototype.need,
                    similarity=_similarity(embedded_turn.vector, prototype.vector),
                )
                for prototype in prototype_bank.prototypes
            ),
            key=lambda neighbor: neighbor.similarity,
            reverse=True,
        )[: prototype_bank.top_k]
    )
    top_k_hits = sum(1 for neighbor in neighbors if neighbor.need == top_score.need)
    top_k_fraction = (top_k_hits / len(neighbors)) if neighbors else 0.0

    abstention_reason: str | None = None
    assessed_need: Need = top_score.need
    if top_score.similarity < thresholds.absolute_min_similarity:
        assessed_need = "unknown"
        abstention_reason = "below_absolute_threshold"
    elif margin < thresholds.min_margin_to_second:
        assessed_need = "unknown"
        abstention_reason = "below_margin_threshold"
    elif top_k_hits < thresholds.min_top_k_label_hits or top_k_fraction < thresholds.min_top_k_label_fraction:
        assessed_need = "unknown"
        abstention_reason = "insufficient_top_k_support"

    return NeedAssessmentResult(
        need=assessed_need,
        trace=NeedAssessmentTrace(
            centroid_scores=scores,
            top_neighbors=neighbors,
            winning_need=top_score.need,
            winning_similarity=top_score.similarity,
            second_need=None if second_score is None else second_score.need,
            margin=margin,
            top_k_label_hits=top_k_hits,
            abstention_reason=abstention_reason,
        ),
    )


def _exact_alias_hit(normalized_turn: str, aliases: Sequence[str]) -> bool:
    return any(_normalize_text(alias) in normalized_turn for alias in aliases if _normalize_text(alias))


def _ordered_alias_hit(turn_tokens: Sequence[str], aliases: Sequence[str]) -> bool:
    for alias in aliases:
        alias_tokens = _tokenize(alias)
        if not alias_tokens:
            continue
        turn_index = 0
        matched = 0
        while turn_index < len(turn_tokens) and matched < len(alias_tokens):
            if turn_tokens[turn_index] == alias_tokens[matched]:
                matched += 1
            turn_index += 1
        if matched == len(alias_tokens):
            return True
    return False


def _token_overlap_band(turn_tokens: Sequence[str], canonical_text: str) -> int:
    subject_tokens = set(_tokenize(canonical_text))
    if not subject_tokens:
        return 0
    overlap_count = len(subject_tokens.intersection(turn_tokens))
    if overlap_count == 0:
        return 0
    overlap_ratio = overlap_count / len(subject_tokens)
    if overlap_ratio >= 0.6:
        return 2
    return 1


def _has_abstract_grounding(kind: SubjectKind, normalized_turn: str) -> bool:
    cue_map: dict[SubjectKind, tuple[str, ...]] = {
        "global": (
            "what is active",
            "what s active",
            "overall",
            "broad picture",
            "what is going on overall",
        ),
        "identity": (
            "why do i keep",
            "self worth",
            "what is wrong with me",
            "pattern in me",
            "about me",
        ),
        "direction": (
            "direction",
            "trajectory",
            "headed",
            "long term",
            "future",
            "where am i going",
        ),
        "current_turn": (
            "this",
            "that",
            "here",
            "right now",
        ),
        "arc": (),
        "domain": (),
    }
    return any(cue in normalized_turn for cue in cue_map[kind])


def _score_subject_candidate(
    *,
    prototype: SubjectPrototype,
    embedded_turn: EmbeddedTurn,
    turn_tokens: Sequence[str],
    normalized_turn: str,
    active_arc_id: str | None,
    active_domain_id: str | None,
) -> SubjectCandidate:
    semantic_similarity = _similarity(embedded_turn.vector, prototype.vector)
    aliases = prototype.aliases or (prototype.text,)
    exact_alias_hit = _exact_alias_hit(normalized_turn, aliases)
    ordered_alias_hit = _ordered_alias_hit(turn_tokens, aliases)
    token_overlap_band = _token_overlap_band(turn_tokens, prototype.text)
    active_scope_hit = (prototype.kind == "arc" and prototype.id == active_arc_id) or (
        prototype.kind == "domain" and prototype.id == active_domain_id
    )
    abstract_grounding_hit = _has_abstract_grounding(prototype.kind, normalized_turn)

    grounding_score = (
        (4 if exact_alias_hit else 0)
        + (3 if ordered_alias_hit else 0)
        + (2 * token_overlap_band)
        + (2 if active_scope_hit else 0)
        + (2 if abstract_grounding_hit else 0)
    )
    total_score = (semantic_similarity * 10.0) + grounding_score

    evidence: list[str] = []
    if exact_alias_hit:
        evidence.append("exact_alias")
    if ordered_alias_hit:
        evidence.append("ordered_alias")
    if token_overlap_band > 0:
        evidence.append(f"token_overlap:{token_overlap_band}")
    if active_scope_hit:
        evidence.append("active_scope")
    if abstract_grounding_hit:
        evidence.append("abstract_grounding")

    return SubjectCandidate(
        kind=prototype.kind,
        id=prototype.id,
        semantic_similarity=semantic_similarity,
        exact_alias_hit=exact_alias_hit,
        ordered_alias_hit=ordered_alias_hit,
        token_overlap_band=token_overlap_band,
        active_scope_hit=active_scope_hit,
        abstract_grounding_hit=abstract_grounding_hit,
        grounding_score=grounding_score,
        total_score=total_score,
        evidence=tuple(evidence),
    )


def resolve_subjects(
    *,
    embedded_turn: EmbeddedTurn,
    prototypes: Sequence[SubjectPrototype],
    thresholds: SubjectResolutionThresholds,
    active_arc_id: str | None = None,
    active_domain_id: str | None = None,
) -> SubjectResolutionResult:
    """Resolve ordered subjects from one embedded turn without a compatibility matrix."""
    turn_tokens = _tokenize(embedded_turn.text)
    normalized_turn = _normalize_text(embedded_turn.text)

    scored_candidates = tuple(
        sorted(
            (
                _score_subject_candidate(
                    prototype=prototype,
                    embedded_turn=embedded_turn,
                    turn_tokens=turn_tokens,
                    normalized_turn=normalized_turn,
                    active_arc_id=active_arc_id,
                    active_domain_id=active_domain_id,
                )
                for prototype in prototypes
            ),
            key=lambda candidate: candidate.semantic_similarity,
            reverse=True,
        )
    )
    shortlisted = tuple(
        candidate for candidate in scored_candidates if candidate.semantic_similarity >= thresholds.semantic_min_similarity
    )[: thresholds.shortlist_k]

    threshold_survivors: list[SubjectCandidate] = []
    dropped_candidates: list[SubjectCandidate] = []
    for candidate in shortlisted:
        is_concrete = candidate.kind in _CONCRETE_SUBJECT_KINDS
        min_grounding = thresholds.concrete_min_grounding_score if is_concrete else thresholds.abstract_min_grounding_score
        min_total = thresholds.concrete_min_total_score if is_concrete else thresholds.abstract_min_total_score
        if candidate.grounding_score < min_grounding or candidate.total_score < min_total:
            dropped_candidates.append(candidate)
            continue
        threshold_survivors.append(candidate)

    accepted_candidates: list[SubjectCandidate] = []
    grouped_by_kind: dict[SubjectKind, list[SubjectCandidate]] = defaultdict(list)
    for candidate in threshold_survivors:
        grouped_by_kind[candidate.kind].append(candidate)

    for _kind, candidates in grouped_by_kind.items():
        candidates.sort(key=lambda candidate: candidate.total_score, reverse=True)
        top_candidate = candidates[0]
        if len(candidates) > 1:
            margin = top_candidate.total_score - candidates[1].total_score
            if margin < thresholds.same_kind_margin:
                dropped_candidates.extend(candidates)
                continue
        accepted_candidates.append(top_candidate)
        dropped_candidates.extend(candidates[1:])

    accepted_candidates.sort(key=lambda candidate: candidate.total_score, reverse=True)
    accepted_subjects = tuple(ResolvedSubject(kind=candidate.kind, id=candidate.id) for candidate in accepted_candidates)

    return SubjectResolutionResult(
        subjects=accepted_subjects,
        trace=SubjectResolutionTrace(
            shortlisted_candidates=shortlisted,
            accepted_subjects=accepted_subjects,
            dropped_candidates=tuple(dropped_candidates),
        ),
    )


async def assess_support_turn(
    *,
    turn_text: str,
    embedder: EmbeddingProvider,
    need_bank: NeedPrototypeBank,
    need_thresholds: NeedAssessmentThresholds,
    subject_prototypes: Sequence[SubjectPrototype],
    subject_thresholds: SubjectResolutionThresholds,
    query_embedding: Sequence[float] | None = None,
    active_arc_id: str | None = None,
    active_domain_id: str | None = None,
) -> TurnAssessmentResult:
    """Embed one turn once, then assess need and subjects from the same vector."""
    raw_embedding = query_embedding if query_embedding is not None else await embedder.embed(turn_text)
    embedded_turn = EmbeddedTurn(text=turn_text, vector=_normalize_vector(raw_embedding))

    need_result = assess_need(
        embedded_turn=embedded_turn,
        prototype_bank=need_bank,
        thresholds=need_thresholds,
    )
    subject_result = resolve_subjects(
        embedded_turn=embedded_turn,
        prototypes=subject_prototypes,
        thresholds=subject_thresholds,
        active_arc_id=active_arc_id,
        active_domain_id=active_domain_id,
    )

    assessment = SupportTurnAssessment(need=need_result.need, subjects=subject_result.subjects)
    return TurnAssessmentResult(
        assessment=assessment,
        trace=TurnAssessmentTrace(
            need_trace=need_result.trace,
            subject_trace=subject_result.trace,
        ),
    )


def derive_response_mode(assessment: SupportTurnAssessment) -> ResponseMode:
    """Map the public turn assessment onto the existing context taxonomy."""
    kinds = {subject.kind for subject in assessment.subjects}
    if assessment.need == "unknown":
        return "execute"
    if assessment.need == "orient":
        return "plan"
    if assessment.need in {"resume", "activate"}:
        return "execute"
    if assessment.need == "decide":
        return "decide"
    if assessment.need == "reflect":
        if "identity" in kinds:
            return "identity_reflect"
        if "direction" in kinds:
            return "direction_reflect"
        return "review"
    return "review"


def _default_relational_values(*, need: Need, response_mode: ResponseMode) -> dict[str, str]:
    values = {dimension: definition.default_value for dimension, definition in RELATIONAL_REGISTRY_DIMENSIONS.items()}

    if response_mode == "execute":
        values["companionship"] = "high"
    if response_mode in {"identity_reflect", "direction_reflect", "review"}:
        values["emotional_attunement"] = "high"
        values["analytical_depth"] = "high"
        values["momentum_pressure"] = "low"
    if response_mode == "decide":
        values["analytical_depth"] = "high"
        values["candor"] = "high"

    if need == "orient":
        values["challenge"] = "low"
        values["momentum_pressure"] = "low"
    elif need == "resume":
        values["companionship"] = "high"
        values["authority"] = "medium"
    elif need == "activate":
        values["challenge"] = "medium"
        values["authority"] = "medium"
        values["momentum_pressure"] = "high"
    elif need == "decide":
        values["candor"] = "high"
        values["analytical_depth"] = "high"
    elif need == "reflect":
        values["warmth"] = "high"
        values["emotional_attunement"] = "high"
        values["analytical_depth"] = "high"
        values["momentum_pressure"] = "low"
    elif need == "calibrate":
        values["warmth"] = "high"
        values["candor"] = "high"
        values["challenge"] = "high"
        values["emotional_attunement"] = "high"
        values["analytical_depth"] = "high"
        values["momentum_pressure"] = "low"

    return values


def _default_support_values(*, need: Need, response_mode: ResponseMode) -> dict[str, str]:
    values = {dimension: definition.default_value for dimension, definition in SUPPORT_REGISTRY_DIMENSIONS.items()}

    if response_mode == "execute":
        values["planning_granularity"] = "minimal"
    elif response_mode == "plan":
        values["planning_granularity"] = "short"
    elif response_mode in {"review", "identity_reflect", "direction_reflect"}:
        values["reflection_depth"] = "deep"
        values["pacing"] = "slow"
        values["recommendation_forcefulness"] = "low"

    if need == "orient":
        values["planning_granularity"] = "short"
        values["recommendation_forcefulness"] = "low"
    elif need == "resume":
        values["planning_granularity"] = "minimal"
        values["option_bandwidth"] = "single"
        values["pacing"] = "steady"
    elif need == "activate":
        values["planning_granularity"] = "minimal"
        values["option_bandwidth"] = "single"
        values["proactivity_level"] = "high"
        values["accountability_style"] = "firm"
        values["pacing"] = "brisk"
        values["recommendation_forcefulness"] = "high"
        values["reflection_depth"] = "light"
    elif need == "decide":
        values["planning_granularity"] = "short"
        values["option_bandwidth"] = "few"
        values["recommendation_forcefulness"] = "medium"
    elif need == "reflect":
        values["reflection_depth"] = "deep"
        values["pacing"] = "slow"
        values["recommendation_forcefulness"] = "low"
        values["accountability_style"] = "light"
    elif need == "calibrate":
        values["reflection_depth"] = "deep"
        values["pacing"] = "steady"
        values["recommendation_forcefulness"] = "low"
        values["recovery_style"] = "gentle"

    return values


def _apply_transient_adjustments(
    *,
    relational_values: dict[str, str],
    support_values: dict[str, str],
    transient_state: SupportTransientState,
) -> None:
    if transient_state.overwhelm:
        support_values["option_bandwidth"] = "single"
        support_values["pacing"] = "slow"
        support_values["recovery_style"] = "gentle"
        relational_values["momentum_pressure"] = "low"
        relational_values["warmth"] = "high"
        relational_values["emotional_attunement"] = "high"
    if transient_state.urgency:
        support_values["pacing"] = "brisk"
        support_values["recommendation_forcefulness"] = "high"
        support_values["proactivity_level"] = "high"
    if transient_state.ambiguity:
        support_values["recommendation_forcefulness"] = "low"
        relational_values["analytical_depth"] = "high"
    if transient_state.shame_risk:
        support_values["accountability_style"] = "light"
        support_values["recovery_style"] = "gentle"
        relational_values["challenge"] = "low"
        relational_values["warmth"] = "high"


def _validate_value_map(registry: Literal["relational", "support"], values: Mapping[str, str]) -> dict[str, str]:
    return {dimension: validate_registry_value(registry, dimension, value) for dimension, value in values.items()}


async def resolve_support_policy(
    *,
    store: SupportPolicyStore,
    assessment: SupportTurnAssessment,
    response_mode: ResponseMode,
    patterns: Sequence[SupportPolicyPattern] = (),
    transient_state: SupportTransientState | None = None,
) -> ResolvedSupportPolicy:
    """Resolve composite runtime values from defaults, scoped learning, patterns, and state."""
    relational_values = _default_relational_values(need=assessment.need, response_mode=response_mode)
    support_values = _default_support_values(need=assessment.need, response_mode=response_mode)

    primary_arc_id = next((subject.id for subject in assessment.subjects if subject.kind == "arc"), None)
    domain_ids = tuple(subject.id for subject in assessment.subjects if subject.kind == "domain" and subject.id is not None)

    for dimension in RELATIONAL_REGISTRY_DIMENSIONS:
        stored = await store.resolve_support_profile_value(
            "relational",
            dimension,
            context_id=response_mode,
            arc_id=primary_arc_id,
        )
        if stored is not None:
            relational_values[dimension] = stored.value
    for dimension in SUPPORT_REGISTRY_DIMENSIONS:
        stored = await store.resolve_support_profile_value(
            "support",
            dimension,
            context_id=response_mode,
            arc_id=primary_arc_id,
        )
        if stored is not None:
            support_values[dimension] = stored.value

    for pattern in patterns:
        for dimension, value in pattern.relational_overrides.items():
            relational_values[dimension] = validate_registry_value("relational", dimension, value)
        for dimension, value in pattern.support_overrides.items():
            support_values[dimension] = validate_registry_value("support", dimension, value)

    _apply_transient_adjustments(
        relational_values=relational_values,
        support_values=support_values,
        transient_state=transient_state or SupportTransientState(),
    )

    relational_values = _validate_value_map("relational", relational_values)
    support_values = _validate_value_map("support", support_values)

    return ResolvedSupportPolicy(
        assessment=assessment,
        response_mode=response_mode,
        relational_values=relational_values,
        support_values=support_values,
        primary_arc_id=primary_arc_id,
        domain_ids=domain_ids,
    )


def _derive_stance_summary(relational_values: Mapping[str, str]) -> str:
    warmth = relational_values["warmth"]
    candor = relational_values["candor"]
    challenge = relational_values["challenge"]
    momentum = relational_values["momentum_pressure"]

    warmth_label = {"low": "spare", "medium": "steady", "high": "warm"}[warmth]
    candor_label = {"low": "gentle", "medium": "clear", "high": "direct"}[candor]
    challenge_label = {"low": "light challenge", "medium": "measured challenge", "high": "strong challenge"}[challenge]
    momentum_label = {"low": "low momentum", "medium": "steady momentum", "high": "high momentum"}[momentum]
    return f"{warmth_label}, {candor_label}, {challenge_label}, {momentum_label}"


def _derive_evidence_mode(resolved_policy: ResolvedSupportPolicy) -> EvidenceMode:
    if resolved_policy.assessment.need == "calibrate" or resolved_policy.response_mode == "review":
        return "structured"
    if resolved_policy.response_mode == "decide":
        return "explicit"
    if resolved_policy.assessment.need == "unknown":
        return "none"
    return "light"


def _derive_intervention_family(resolved_policy: ResolvedSupportPolicy) -> InterventionFamily:
    need = resolved_policy.assessment.need
    support_values = resolved_policy.support_values
    relational_values = resolved_policy.relational_values

    if need == "orient":
        return "orient"
    if need == "resume":
        return "summarize"
    if need == "activate":
        if support_values["option_bandwidth"] == "single":
            return "narrow"
        if support_values["planning_granularity"] == "minimal":
            return "sequence"
        return "recommend"
    if need == "decide":
        if relational_values["analytical_depth"] == "high":
            return "compare"
        return "recommend"
    if need == "reflect":
        return "mirror"
    if need == "calibrate":
        if relational_values["candor"] == "high" or relational_values["challenge"] == "high":
            return "challenge"
        return "compare"
    return "confirm"


def compile_support_behavior_contract(resolved_policy: ResolvedSupportPolicy) -> SupportBehaviorContract:
    """Compile resolved values into the prompt-facing support behavior contract."""
    return SupportBehaviorContract(
        need=resolved_policy.assessment.need,
        response_mode=resolved_policy.response_mode,
        subjects=resolved_policy.assessment.subjects,
        relational_values=dict(resolved_policy.relational_values),
        support_values=dict(resolved_policy.support_values),
        stance_summary=_derive_stance_summary(resolved_policy.relational_values),
        evidence_mode=_derive_evidence_mode(resolved_policy),
        intervention_family=_derive_intervention_family(resolved_policy),
    )


def _format_subject(subject: ResolvedSubject) -> str:
    if subject.id is None:
        return subject.kind
    return f"{subject.kind}:{subject.id}"


def render_support_behavior_contract(contract: SupportBehaviorContract) -> str:
    """Render the compiled behavior contract as one prompt section."""
    subjects = ", ".join(_format_subject(subject) for subject in contract.subjects) or "none"
    relational_lines = "\n".join(f"  - {dimension}: {value}" for dimension, value in sorted(contract.relational_values.items()))
    support_lines = "\n".join(f"  - {dimension}: {value}" for dimension, value in sorted(contract.support_values.items()))

    return (
        "## Runtime Support Contract\n\n"
        f"- need: {contract.need}\n"
        f"- response_mode: {contract.response_mode}\n"
        f"- subjects: [{subjects}]\n"
        f"- stance_summary: {contract.stance_summary}\n"
        f"- evidence_mode: {contract.evidence_mode}\n"
        f"- intervention_family: {contract.intervention_family}\n"
        "- realization: Express the response naturally. Use this contract to shape the move; "
        "do not mention internal labels, registry names, or policy metadata unless the user asks.\n"
        "- relational_values:\n"
        f"{relational_lines}\n"
        "- support_values:\n"
        f"{support_lines}\n"
    )


def _summarize_contract_for_learning(contract: SupportBehaviorContract) -> str:
    subjects = ", ".join(_format_subject(subject) for subject in contract.subjects) or "none"
    return f"need={contract.need}; mode={contract.response_mode}; family={contract.intervention_family}; subjects=[{subjects}]"


class SupportPolicyRuntime:
    """Runtime helper that builds one support contract per live turn."""

    def __init__(self, *, store: SQLiteStore, embedder: EmbeddingProvider) -> None:
        self._store = store
        self._embedder = embedder
        self._need_bank: NeedPrototypeBank | None = None
        self._abstract_subjects: tuple[SubjectPrototype, ...] | None = None
        self._need_thresholds = _default_need_thresholds()
        self._subject_thresholds = _default_subject_thresholds()

    async def _ensure_need_bank(self) -> NeedPrototypeBank:
        if self._need_bank is None:
            self._need_bank = await build_need_prototype_bank(
                embedder=self._embedder,
                prototype_texts=_DEFAULT_NEED_PROTOTYPE_TEXTS,
                top_k=3,
            )
        return self._need_bank

    async def _ensure_abstract_subjects(self) -> tuple[SubjectPrototype, ...]:
        if self._abstract_subjects is None:
            prototype_texts = tuple((kind, None, text, aliases) for kind, text, aliases in _DEFAULT_ABSTRACT_SUBJECT_TEXTS)
            self._abstract_subjects = await build_subject_prototypes(
                embedder=self._embedder,
                prototype_texts=prototype_texts,
            )
        return self._abstract_subjects

    async def _build_concrete_subjects(self) -> tuple[SubjectPrototype, ...]:
        arcs = await self._store.list_resume_arcs(limit=12)
        domains = await self._store.list_active_life_domains(limit=6)
        concrete_texts = tuple([arc.title for arc in arcs] + [domain.name for domain in domains])
        vectors = await _embed_many(self._embedder, concrete_texts)

        prototypes: list[SubjectPrototype] = []
        vector_index = 0
        for arc in arcs:
            prototypes.append(
                SubjectPrototype(
                    kind="arc",
                    id=arc.arc_id,
                    text=arc.title,
                    aliases=(arc.title,),
                    vector=vectors[vector_index],
                )
            )
            vector_index += 1
        for domain in domains:
            prototypes.append(
                SubjectPrototype(
                    kind="domain",
                    id=domain.domain_id,
                    text=domain.name,
                    aliases=(domain.name,),
                    vector=vectors[vector_index],
                )
            )
            vector_index += 1
        return tuple(prototypes)

    async def _load_runtime_patterns(
        self,
        *,
        assessment: SupportTurnAssessment,
        response_mode: ResponseMode,
    ) -> tuple[SupportPolicyPattern, ...]:
        primary_arc_id = next((subject.id for subject in assessment.subjects if subject.kind == "arc"), None)
        patterns = await self._store.list_support_patterns_for_runtime(
            response_mode=response_mode,
            arc_id=primary_arc_id,
        )
        return tuple(
            SupportPolicyPattern(
                name=pattern.claim,
                relational_overrides=pattern.relational_overrides,
                support_overrides=pattern.support_overrides,
            )
            for pattern in patterns
        )

    async def _load_existing_profile_values(
        self,
        *,
        assessment: SupportTurnAssessment,
        response_mode: ResponseMode,
    ) -> dict[tuple[str, str, str, str], SupportProfileValue]:
        existing: dict[tuple[str, str, str, str], SupportProfileValue] = {}
        primary_arc_id = next((subject.id for subject in assessment.subjects if subject.kind == "arc"), None)
        for dimension in SUPPORT_REGISTRY_DIMENSIONS:
            if primary_arc_id is not None:
                stored_arc = await self._store.resolve_support_profile_value(
                    "support",
                    dimension,
                    context_id=response_mode,
                    arc_id=primary_arc_id,
                )
                if stored_arc is not None and stored_arc.scope.type == "arc":
                    existing[("support", dimension, stored_arc.scope.type, stored_arc.scope.id)] = stored_arc
                    continue
            stored_context = await self._store.resolve_support_profile_value(
                "support",
                dimension,
                context_id=response_mode,
            )
            if stored_context is not None and stored_context.scope.type == "context":
                existing[("support", dimension, stored_context.scope.type, stored_context.scope.id)] = stored_context
        for dimension in RELATIONAL_REGISTRY_DIMENSIONS:
            stored_context = await self._store.resolve_support_profile_value(
                "relational",
                dimension,
                context_id=response_mode,
            )
            if stored_context is not None and stored_context.scope.type == "context":
                existing[("relational", dimension, stored_context.scope.type, stored_context.scope.id)] = stored_context
        return existing

    async def _maybe_apply_bounded_adaptation(
        self,
        *,
        assessment: SupportTurnAssessment,
        response_mode: ResponseMode,
        query_embedding: Sequence[float] | None,
        behavior_contract: SupportBehaviorContract,
        resolved_policy: ResolvedSupportPolicy,
        turn_text: str,
    ) -> None:
        if query_embedding is None:
            return

        similar_situations = await self._store.search_learning_situations(
            list(query_embedding),
            top_k=6,
            response_mode=response_mode,
            need=None if assessment.need == "unknown" else assessment.need,
        )
        existing_profile_values = await self._load_existing_profile_values(
            assessment=assessment,
            response_mode=response_mode,
        )
        subject_refs = tuple(_format_subject(subject) for subject in assessment.subjects)
        domain_ids = tuple(subject.id for subject in assessment.subjects if subject.kind == "domain" and subject.id is not None)
        current_situation = LearningSituation(
            situation_id=f"sit-{int(datetime.now(UTC).timestamp() * 1000)}",
            session_id="runtime",
            recorded_at=datetime.now(UTC),
            turn_text=turn_text,
            embedding=tuple(float(value) for value in query_embedding),
            need=assessment.need,
            response_mode=response_mode,
            subject_refs=subject_refs,
            arc_id=resolved_policy.primary_arc_id,
            domain_ids=domain_ids,
            intervention_ids=(),
            behavior_contract_summary=_summarize_contract_for_learning(behavior_contract),
            intervention_family=behavior_contract.intervention_family,
            relational_values_applied=dict(behavior_contract.relational_values),
            support_values_applied=dict(behavior_contract.support_values),
            evidence_refs=(),
        )
        await apply_bounded_adaptation(
            store=cast(Any, self._store),
            current_situation=current_situation,
            similar_situations=similar_situations,
            existing_profile_values=existing_profile_values,
            now=datetime.now(UTC),
        )

    async def build_turn_contract(
        self,
        *,
        message: str,
        query_embedding: Sequence[float] | None,
        session_messages: Sequence[tuple[str, str]],
    ) -> SupportPolicyRuntimeResult:
        """Assess, resolve, and compile the runtime support contract for one turn."""
        fresh_session = len(session_messages) == 0
        active_arc_id: str | None = None
        active_domain_id: str | None = None
        if fresh_session:
            operational_context = await get_support_operational_context(self._store, message)
            if isinstance(operational_context, ArcResumeContext):
                active_arc_id = operational_context.arc_snapshot.arc.arc_id
                active_domain_id = operational_context.arc_snapshot.arc.primary_domain_id

        need_bank = await self._ensure_need_bank()
        abstract_subjects = await self._ensure_abstract_subjects()
        concrete_subjects = await self._build_concrete_subjects()
        assessment_result = await assess_support_turn(
            turn_text=message,
            embedder=self._embedder,
            need_bank=need_bank,
            need_thresholds=self._need_thresholds,
            subject_prototypes=tuple(concrete_subjects + abstract_subjects),
            subject_thresholds=self._subject_thresholds,
            query_embedding=query_embedding,
            active_arc_id=active_arc_id,
            active_domain_id=active_domain_id,
        )
        response_mode = derive_response_mode(assessment_result.assessment)
        runtime_patterns = await self._load_runtime_patterns(
            assessment=assessment_result.assessment,
            response_mode=response_mode,
        )
        resolved_policy = await resolve_support_policy(
            store=cast(SupportPolicyStore, self._store),
            assessment=assessment_result.assessment,
            response_mode=response_mode,
            patterns=runtime_patterns,
        )
        behavior_contract = compile_support_behavior_contract(resolved_policy)
        await self._maybe_apply_bounded_adaptation(
            assessment=assessment_result.assessment,
            response_mode=response_mode,
            query_embedding=query_embedding,
            behavior_contract=behavior_contract,
            resolved_policy=resolved_policy,
            turn_text=message,
        )
        if query_embedding is not None:
            runtime_patterns = await self._load_runtime_patterns(
                assessment=assessment_result.assessment,
                response_mode=response_mode,
            )
            resolved_policy = await resolve_support_policy(
                store=cast(SupportPolicyStore, self._store),
                assessment=assessment_result.assessment,
                response_mode=response_mode,
                patterns=runtime_patterns,
            )
            behavior_contract = compile_support_behavior_contract(resolved_policy)
        return SupportPolicyRuntimeResult(
            assessment=assessment_result.assessment,
            response_mode=response_mode,
            resolved_policy=resolved_policy,
            behavior_contract=behavior_contract,
            trace=assessment_result.trace,
        )

    async def build_prompt_section(
        self,
        *,
        message: str,
        query_embedding: Sequence[float] | None,
        session_messages: Sequence[tuple[str, str]],
        session_id: str | None,
    ) -> str:
        """Build the rendered prompt section for one live turn."""
        del session_id  # Reserved for future support-memory logging and trace correlation.
        runtime_result = await self.build_turn_contract(
            message=message,
            query_embedding=query_embedding,
            session_messages=session_messages,
        )
        return render_support_behavior_contract(runtime_result.behavior_contract)


__all__ = [
    "NeedAssessmentThresholds",
    "NeedPrototype",
    "NeedPrototypeBank",
    "ResolvedSubject",
    "ResolvedSupportPolicy",
    "SubjectPrototype",
    "SubjectResolutionThresholds",
    "SupportBehaviorContract",
    "SupportPolicyPattern",
    "SupportPolicyRuntime",
    "SupportPolicyRuntimeResult",
    "SupportTransientState",
    "SupportTurnAssessment",
    "TurnAssessmentResult",
    "assess_support_turn",
    "build_need_prototype_bank",
    "build_subject_prototypes",
    "compile_support_behavior_contract",
    "derive_response_mode",
    "render_support_behavior_contract",
    "resolve_support_policy",
]
