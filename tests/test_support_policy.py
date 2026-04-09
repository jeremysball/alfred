"""Tests for Milestone 4 support-policy runtime behavior."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from alfred.memory.support_learning import (
    LearningSituation,
    SupportAttempt,
    SupportPattern,
    SupportProfileUpdateEvent,
)
from alfred.memory.support_memory import LifeDomain, OperationalArc
from alfred.memory.support_profile import SupportProfileScope, SupportProfileValue
from alfred.support_policy import (
    NeedAssessmentThresholds,
    NeedPrototype,
    NeedPrototypeBank,
    ResolvedSubject,
    ResolvedSupportPolicy,
    SubjectPrototype,
    SubjectResolutionThresholds,
    SupportPolicyPattern,
    SupportPolicyRuntime,
    SupportTransientState,
    SupportTurnAssessment,
    assess_support_turn,
    compile_support_behavior_contract,
    derive_response_mode,
    resolve_support_policy,
)

Vector = tuple[float, ...]


@dataclass
class FakeEmbedder:
    """Deterministic embedder fake for support-policy tests."""

    vectors: dict[str, Vector]
    calls: list[str] = field(default_factory=list)

    async def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        try:
            return list(self.vectors[text])
        except KeyError as exc:
            raise AssertionError(f"Missing fake embedding for: {text}") from exc

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(text) for text in texts]


@dataclass
class FakeSupportProfileStore:
    """Explicit fake store that models scoped profile-value precedence."""

    values: list[SupportProfileValue] = field(default_factory=list)
    patterns: list[SupportPattern] = field(default_factory=list)
    similar_situations: list[tuple[LearningSituation, float]] = field(default_factory=list)
    saved_learning_situations: list[LearningSituation] = field(default_factory=list)
    update_events: list[SupportProfileUpdateEvent] = field(default_factory=list)
    arcs: list[OperationalArc] = field(default_factory=list)
    domains: list[LifeDomain] = field(default_factory=list)

    async def resolve_support_profile_value(
        self,
        registry: str,
        dimension: str,
        *,
        context_id: str | None = None,
        arc_id: str | None = None,
    ) -> SupportProfileValue | None:
        scopes_to_try: list[SupportProfileScope] = []
        if arc_id is not None:
            scopes_to_try.append(SupportProfileScope(type="arc", id=arc_id))
        if context_id is not None:
            scopes_to_try.append(SupportProfileScope(type="context", id=context_id))
        scopes_to_try.append(SupportProfileScope(type="global", id="user"))

        for scope in scopes_to_try:
            for value in self.values:
                if (
                    value.registry == registry
                    and value.dimension == dimension
                    and value.scope == scope
                ):
                    return value
        return None

    async def list_resume_arcs(self, limit: int = 12) -> list[OperationalArc]:
        return list(self.arcs)[:limit]

    async def list_active_life_domains(self, limit: int = 4) -> list[LifeDomain]:
        return list(self.domains)[:limit]

    async def list_support_patterns_for_runtime(
        self,
        *,
        response_mode: str,
        arc_id: str | None = None,
    ) -> list[SupportPattern]:
        matched: list[SupportPattern] = []
        for pattern in self.patterns:
            if pattern.status != "confirmed":
                continue
            if pattern.scope == SupportProfileScope(type="global", id="user"):
                matched.append(pattern)
                continue
            if pattern.scope == SupportProfileScope(type="context", id=response_mode):
                matched.append(pattern)
                continue
            if arc_id is not None and pattern.scope == SupportProfileScope(type="arc", id=arc_id):
                matched.append(pattern)
        return matched

    async def search_learning_situations(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 5,
        response_mode: str | None = None,
        need: str | None = None,
    ) -> list[tuple[LearningSituation, float]]:
        del query_embedding
        matches = list(self.similar_situations)
        if response_mode is not None:
            matches = [match for match in matches if match[0].response_mode == response_mode]
        if need is not None:
            matches = [match for match in matches if match[0].need == need]
        return matches[:top_k]

    async def save_learning_situation(self, situation: LearningSituation) -> None:
        self.saved_learning_situations.append(situation)

    async def save_support_pattern(self, pattern: SupportPattern) -> None:
        self.patterns = [existing for existing in self.patterns if existing.pattern_id != pattern.pattern_id]
        self.patterns.append(pattern)

    async def save_support_profile_update_event(self, event: SupportProfileUpdateEvent) -> None:
        self.update_events.append(event)

    async def save_support_profile_value(self, profile_value: SupportProfileValue) -> None:
        self.values = [
            existing
            for existing in self.values
            if not (
                existing.registry == profile_value.registry
                and existing.dimension == profile_value.dimension
                and existing.scope == profile_value.scope
            )
        ]
        self.values.append(profile_value)


NEED_THRESHOLDS = NeedAssessmentThresholds(
    absolute_min_similarity=0.75,
    min_margin_to_second=0.10,
    min_top_k_label_hits=2,
    min_top_k_label_fraction=0.66,
)

SUBJECT_THRESHOLDS = SubjectResolutionThresholds(
    shortlist_k=6,
    semantic_min_similarity=0.45,
    concrete_min_grounding_score=3,
    abstract_min_grounding_score=2,
    concrete_min_total_score=7.5,
    abstract_min_total_score=6.0,
    same_kind_margin=0.50,
)


def _ts(hour: int, minute: int) -> datetime:
    return datetime(2026, 3, 30, hour, minute, tzinfo=UTC)


def _make_need_bank() -> NeedPrototypeBank:
    orient_a = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    orient_b = (0.9, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.9, 0.1)
    resume_a = (0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.1, 0.0, 0.0, 0.0, 0.1)
    resume_b = (0.0, 0.9, 0.1, 0.0, 0.0, 0.0, 0.9, 0.2, 0.0, 0.0, 0.0, 0.1)
    activate_a = (0.0, 0.1, 1.0, 0.0, 0.0, 0.0, 0.8, 0.1, 0.0, 0.0, 0.0, 0.3)
    activate_b = (0.0, 0.0, 0.9, 0.0, 0.0, 0.0, 0.8, 0.0, 0.0, 0.0, 0.0, 0.4)
    decide_a = (0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.1, 0.3, 0.0, 0.8, 0.0, 0.1)
    decide_b = (0.0, 0.0, 0.0, 0.9, 0.0, 0.1, 0.1, 0.2, 0.0, 0.7, 0.0, 0.1)
    reflect_a = (0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.1, 0.0, 0.2)
    reflect_b = (0.0, 0.0, 0.0, 0.1, 0.9, 0.0, 0.0, 0.0, 0.9, 0.2, 0.0, 0.1)
    calibrate_a = (0.0, 0.0, 0.0, 0.1, 0.2, 1.0, 0.0, 0.0, 0.1, 1.0, 0.0, 0.0)
    calibrate_b = (0.0, 0.0, 0.0, 0.0, 0.1, 0.9, 0.0, 0.0, 0.2, 0.9, 0.0, 0.1)

    return NeedPrototypeBank(
        centroids={
            "orient": orient_a,
            "resume": resume_a,
            "activate": activate_a,
            "decide": decide_a,
            "reflect": reflect_a,
            "calibrate": calibrate_a,
        },
        prototypes=(
            NeedPrototype("orient-a", "orient", "overall overview", orient_a),
            NeedPrototype("orient-b", "orient", "what is active overall", orient_b),
            NeedPrototype("resume-a", "resume", "continue the thread", resume_a),
            NeedPrototype("resume-b", "resume", "pick back up where we left off", resume_b),
            NeedPrototype("activate-a", "activate", "give me one next step", activate_a),
            NeedPrototype("activate-b", "activate", "help me start", activate_b),
            NeedPrototype("decide-a", "decide", "compare options and choose", decide_a),
            NeedPrototype("decide-b", "decide", "which direction should I pick", decide_b),
            NeedPrototype("reflect-a", "reflect", "what pattern is this in me", reflect_a),
            NeedPrototype("reflect-b", "reflect", "why do I keep doing this", reflect_b),
            NeedPrototype("cal-a", "calibrate", "tell me honestly what you see", calibrate_a),
            NeedPrototype("cal-b", "calibrate", "help me evaluate whether this is working", calibrate_b),
        ),
        top_k=3,
    )


def _make_subject_prototypes() -> tuple[SubjectPrototype, ...]:
    return (
        SubjectPrototype(
            kind="arc",
            id="webui_cleanup",
            text="Web UI cleanup",
            aliases=("web ui cleanup", "ui cleanup"),
            vector=(0.0, 0.4, 0.1, 0.0, 0.0, 0.0, 1.0, 0.1, 0.0, 0.0, 0.0, 0.0),
        ),
        SubjectPrototype(
            kind="domain",
            id="work",
            text="Work",
            aliases=("work",),
            vector=(0.0, 0.2, 0.1, 0.0, 0.0, 0.0, 0.2, 1.0, 0.0, 0.0, 0.1, 0.0),
        ),
        SubjectPrototype(
            kind="identity",
            id=None,
            text="identity and self-patterns",
            aliases=("self worth", "pattern in me"),
            vector=(0.0, 0.0, 0.0, 0.1, 0.9, 0.1, 0.0, 0.0, 1.0, 0.1, 0.0, 0.0),
        ),
        SubjectPrototype(
            kind="direction",
            id=None,
            text="direction and trajectory",
            aliases=("direction", "trajectory"),
            vector=(0.0, 0.0, 0.0, 0.2, 0.3, 0.9, 0.0, 0.0, 0.1, 1.0, 0.0, 0.0),
        ),
        SubjectPrototype(
            kind="global",
            id=None,
            text="overall active picture",
            aliases=("overall", "what is active"),
            vector=(0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.0, 0.0, 1.0, 0.0),
        ),
        SubjectPrototype(
            kind="current_turn",
            id=None,
            text="current local turn",
            aliases=("this", "that", "here"),
            vector=(0.0, 0.2, 0.1, 0.1, 0.1, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0),
        ),
    )


@pytest.mark.asyncio
async def test_support_turn_assessment_returns_one_need_and_ordered_subjects() -> None:
    """The assessor should embed once, pick one need, and emit ordered grounded subjects."""

    turn_text = "Let's continue the Web UI cleanup work thread."
    embedder = FakeEmbedder(
        {
            turn_text: (0.0, 0.95, 0.1, 0.0, 0.0, 0.0, 0.95, 0.8, 0.0, 0.0, 0.0, 0.2),
        }
    )

    result = await assess_support_turn(
        turn_text=turn_text,
        embedder=embedder,
        need_bank=_make_need_bank(),
        need_thresholds=NEED_THRESHOLDS,
        subject_prototypes=_make_subject_prototypes(),
        subject_thresholds=SUBJECT_THRESHOLDS,
        active_arc_id="webui_cleanup",
    )

    assert embedder.calls == [turn_text]
    assert result.assessment.need == "resume"
    assert result.assessment.subjects == (
        ResolvedSubject(kind="arc", id="webui_cleanup"),
        ResolvedSubject(kind="domain", id="work"),
    )
    assert result.trace.need_trace.abstention_reason is None
    assert result.trace.subject_trace.accepted_subjects == result.assessment.subjects


def test_support_response_mode_maps_unknown_and_subject_aware_assessments_to_existing_context_ids() -> None:
    """Unknown falls back to execute, while reflective and calibration cases map into existing context IDs."""

    assert derive_response_mode(SupportTurnAssessment(need="unknown", subjects=())) == "execute"
    assert (
        derive_response_mode(
            SupportTurnAssessment(
                need="resume",
                subjects=(ResolvedSubject(kind="identity", id=None),),
            )
        )
        == "execute"
    )
    assert (
        derive_response_mode(
            SupportTurnAssessment(
                need="reflect",
                subjects=(ResolvedSubject(kind="identity", id=None),),
            )
        )
        == "identity_reflect"
    )
    assert (
        derive_response_mode(
            SupportTurnAssessment(
                need="reflect",
                subjects=(ResolvedSubject(kind="direction", id=None),),
            )
        )
        == "direction_reflect"
    )
    assert (
        derive_response_mode(
            SupportTurnAssessment(
                need="calibrate",
                subjects=(ResolvedSubject(kind="current_turn", id=None),),
            )
        )
        == "review"
    )


@pytest.mark.asyncio
async def test_support_policy_resolver_combines_defaults_scopes_patterns_and_transient_state() -> None:
    """Resolver should compose defaults, scoped learning, pattern overrides, and transient state."""

    store = FakeSupportProfileStore(
        values=[
            SupportProfileValue(
                registry="support",
                dimension="planning_granularity",
                scope=SupportProfileScope(type="global", id="user"),
                value="full",
                status="confirmed",
                confidence=1.0,
                source="explicit",
                created_at=_ts(12, 0),
                updated_at=_ts(12, 0),
            ),
            SupportProfileValue(
                registry="support",
                dimension="planning_granularity",
                scope=SupportProfileScope(type="context", id="execute"),
                value="short",
                status="confirmed",
                confidence=1.0,
                source="explicit",
                created_at=_ts(12, 1),
                updated_at=_ts(12, 1),
            ),
            SupportProfileValue(
                registry="support",
                dimension="planning_granularity",
                scope=SupportProfileScope(type="arc", id="webui_cleanup"),
                value="minimal",
                status="confirmed",
                confidence=1.0,
                source="explicit",
                created_at=_ts(12, 2),
                updated_at=_ts(12, 2),
            ),
            SupportProfileValue(
                registry="relational",
                dimension="warmth",
                scope=SupportProfileScope(type="global", id="user"),
                value="low",
                status="confirmed",
                confidence=1.0,
                source="explicit",
                created_at=_ts(12, 3),
                updated_at=_ts(12, 3),
            ),
            SupportProfileValue(
                registry="relational",
                dimension="warmth",
                scope=SupportProfileScope(type="context", id="execute"),
                value="high",
                status="confirmed",
                confidence=1.0,
                source="explicit",
                created_at=_ts(12, 4),
                updated_at=_ts(12, 4),
            ),
            SupportProfileValue(
                registry="support",
                dimension="pacing",
                scope=SupportProfileScope(type="context", id="execute"),
                value="slow",
                status="confirmed",
                confidence=1.0,
                source="explicit",
                created_at=_ts(12, 5),
                updated_at=_ts(12, 5),
            ),
        ]
    )

    assessment = SupportTurnAssessment(
        need="activate",
        subjects=(
            ResolvedSubject(kind="arc", id="webui_cleanup"),
            ResolvedSubject(kind="domain", id="work"),
        ),
    )

    resolved = await resolve_support_policy(
        store=store,
        assessment=assessment,
        response_mode="execute",
        patterns=(
            SupportPolicyPattern(
                name="direct_pattern",
                relational_overrides={"candor": "high"},
                support_overrides={"recommendation_forcefulness": "medium"},
            ),
        ),
        transient_state=SupportTransientState(
            overwhelm=True,
            ambiguity=True,
        ),
    )

    assert resolved.primary_arc_id == "webui_cleanup"
    assert resolved.domain_ids == ("work",)
    assert resolved.support_values["planning_granularity"] == "minimal"
    assert resolved.relational_values["warmth"] == "high"
    assert resolved.relational_values["candor"] == "high"
    assert resolved.support_values["pacing"] == "slow"
    assert resolved.support_values["option_bandwidth"] == "single"
    assert resolved.support_values["recommendation_forcefulness"] == "low"


def test_support_behavior_contract_derives_stance_evidence_mode_and_intervention_family() -> None:
    """Compiler should produce readable stance plus compiler-only evidence and intervention decisions."""

    activate_policy = ResolvedSupportPolicy(
        assessment=SupportTurnAssessment(
            need="activate",
            subjects=(ResolvedSubject(kind="arc", id="webui_cleanup"),),
        ),
        response_mode="execute",
        relational_values={
            "warmth": "medium",
            "companionship": "high",
            "candor": "medium",
            "challenge": "medium",
            "authority": "medium",
            "emotional_attunement": "medium",
            "analytical_depth": "medium",
            "momentum_pressure": "high",
        },
        support_values={
            "planning_granularity": "minimal",
            "option_bandwidth": "single",
            "proactivity_level": "high",
            "accountability_style": "firm",
            "recovery_style": "steady",
            "reflection_depth": "light",
            "pacing": "brisk",
            "recommendation_forcefulness": "high",
        },
        primary_arc_id="webui_cleanup",
        domain_ids=("work",),
    )
    calibrate_policy = ResolvedSupportPolicy(
        assessment=SupportTurnAssessment(
            need="calibrate",
            subjects=(ResolvedSubject(kind="current_turn", id=None),),
        ),
        response_mode="review",
        relational_values={
            "warmth": "high",
            "companionship": "medium",
            "candor": "high",
            "challenge": "high",
            "authority": "medium",
            "emotional_attunement": "high",
            "analytical_depth": "high",
            "momentum_pressure": "low",
        },
        support_values={
            "planning_granularity": "short",
            "option_bandwidth": "few",
            "proactivity_level": "medium",
            "accountability_style": "medium",
            "recovery_style": "gentle",
            "reflection_depth": "deep",
            "pacing": "steady",
            "recommendation_forcefulness": "low",
        },
        primary_arc_id=None,
        domain_ids=(),
    )

    activate_contract = compile_support_behavior_contract(activate_policy)
    calibrate_contract = compile_support_behavior_contract(calibrate_policy)

    assert activate_contract.intervention_family == "narrow"
    assert activate_contract.evidence_mode == "light"
    assert "momentum" in activate_contract.stance_summary

    assert calibrate_contract.intervention_family == "challenge"
    assert calibrate_contract.evidence_mode == "structured"
    assert "direct" in calibrate_contract.stance_summary


@pytest.mark.asyncio
async def test_support_policy_runtime_builds_prompt_section_from_runtime_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The runtime helper should orchestrate assessment, resolution, compilation, and prompt rendering."""

    turn_text = "Let's continue the Web UI cleanup work thread."
    embedder = FakeEmbedder(
        {
            turn_text: (0.0, 0.95, 0.1, 0.0, 0.0, 0.0, 0.95, 0.8, 0.0, 0.0, 0.0, 0.2),
        }
    )
    store = FakeSupportProfileStore()
    runtime = SupportPolicyRuntime(store=store, embedder=embedder)  # type: ignore[arg-type]

    async def fake_need_bank() -> NeedPrototypeBank:
        return _make_need_bank()

    async def fake_abstract_subjects() -> tuple[SubjectPrototype, ...]:
        return tuple(
            subject
            for subject in _make_subject_prototypes()
            if subject.kind in {"identity", "direction", "global", "current_turn"}
        )

    async def fake_concrete_subjects() -> tuple[SubjectPrototype, ...]:
        return tuple(
            subject
            for subject in _make_subject_prototypes()
            if subject.kind in {"arc", "domain"}
        )

    monkeypatch.setattr(runtime, "_ensure_need_bank", fake_need_bank)
    monkeypatch.setattr(runtime, "_ensure_abstract_subjects", fake_abstract_subjects)
    monkeypatch.setattr(runtime, "_build_concrete_subjects", fake_concrete_subjects)

    prompt_section = await runtime.build_prompt_section(
        message=turn_text,
        query_embedding=None,
        session_messages=[("user", "previous user turn")],
        session_id=None,
    )

    assert embedder.calls == [turn_text]
    assert "## Runtime Support Contract" in prompt_section
    assert "- need: resume" in prompt_section
    assert "- response_mode: execute" in prompt_section
    assert "arc:webui_cleanup" in prompt_section
    assert "domain:work" in prompt_section
    assert "Express the response naturally" in prompt_section
    assert "do not mention internal labels" in prompt_section


@pytest.mark.asyncio
async def test_support_policy_runtime_loads_active_patterns_and_support_profile_values_together(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runtime resolution should apply confirmed patterns alongside stored support-profile values."""

    turn_text = "Let's continue the Web UI cleanup work thread."
    embedder = FakeEmbedder(
        {
            turn_text: (0.0, 0.95, 0.1, 0.0, 0.0, 0.0, 0.95, 0.8, 0.0, 0.0, 0.0, 0.2),
        }
    )
    store = FakeSupportProfileStore(
        values=[
            SupportProfileValue(
                registry="support",
                dimension="option_bandwidth",
                scope=SupportProfileScope(type="context", id="execute"),
                value="few",
                status="confirmed",
                confidence=0.9,
                source="explicit",
                created_at=_ts(9, 0),
                updated_at=_ts(9, 0),
            ),
        ],
        patterns=[
            SupportPattern(
                pattern_id="pattern-narrow-webui",
                kind="support_preference",
                scope=SupportProfileScope(type="arc", id="webui_cleanup"),
                status="confirmed",
                claim="Single-step next moves work better on this arc.",
                confidence=0.88,
                created_at=_ts(9, 10),
                updated_at=_ts(9, 12),
                supporting_situation_ids=("sit-webui-1", "sit-webui-2"),
                support_overrides={"option_bandwidth": "single"},
                relational_overrides={"candor": "high"},
            )
        ],
    )
    runtime = SupportPolicyRuntime(store=store, embedder=embedder)  # type: ignore[arg-type]

    async def fake_need_bank() -> NeedPrototypeBank:
        return _make_need_bank()

    async def fake_abstract_subjects() -> tuple[SubjectPrototype, ...]:
        return tuple(
            subject
            for subject in _make_subject_prototypes()
            if subject.kind in {"identity", "direction", "global", "current_turn"}
        )

    async def fake_concrete_subjects() -> tuple[SubjectPrototype, ...]:
        return tuple(
            subject
            for subject in _make_subject_prototypes()
            if subject.kind in {"arc", "domain"}
        )

    monkeypatch.setattr(runtime, "_ensure_need_bank", fake_need_bank)
    monkeypatch.setattr(runtime, "_ensure_abstract_subjects", fake_abstract_subjects)
    monkeypatch.setattr(runtime, "_build_concrete_subjects", fake_concrete_subjects)

    runtime_result = await runtime.build_turn_contract(
        message=turn_text,
        query_embedding=None,
        session_messages=[("user", "previous user turn")],
    )

    assert runtime_result.behavior_contract.support_values["option_bandwidth"] == "single"
    assert runtime_result.behavior_contract.relational_values["candor"] == "high"


def test_support_policy_runtime_builds_v2_support_attempt_from_runtime_result() -> None:
    """Runtime should derive one typed v2 support attempt from the reply contract and real refs."""

    runtime = SupportPolicyRuntime(
        store=FakeSupportProfileStore(),
        embedder=FakeEmbedder({}),  # type: ignore[arg-type]
    )
    assessment = SupportTurnAssessment(
        need="activate",
        subjects=(
            ResolvedSubject(kind="arc", id="webui_cleanup"),
            ResolvedSubject(kind="domain", id="work"),
        ),
    )
    resolved_policy = ResolvedSupportPolicy(
        assessment=assessment,
        response_mode="execute",
        relational_values={
            "warmth": "medium",
            "companionship": "medium",
            "candor": "high",
            "challenge": "medium",
            "authority": "medium",
            "emotional_attunement": "medium",
            "analytical_depth": "medium",
            "momentum_pressure": "high",
        },
        support_values={
            "planning_granularity": "minimal",
            "option_bandwidth": "single",
            "proactivity_level": "high",
            "accountability_style": "firm",
            "recovery_style": "steady",
            "reflection_depth": "light",
            "pacing": "brisk",
            "recommendation_forcefulness": "high",
        },
        primary_arc_id="webui_cleanup",
        domain_ids=("work",),
    )
    behavior_contract = compile_support_behavior_contract(resolved_policy)

    attempt = runtime.build_support_attempt(
        runtime_result=type("RuntimeResult", (), {
            "assessment": assessment,
            "response_mode": "execute",
            "resolved_policy": resolved_policy,
            "behavior_contract": behavior_contract,
        })(),
        session_id="session-123",
        user_message_id="msg-user-123",
        assistant_message_id="msg-assistant-123",
        created_at=_ts(9, 45),
    )

    assert attempt == SupportAttempt(
        attempt_id="attempt-msg-assistant-123",
        session_id="session-123",
        user_message_id="msg-user-123",
        assistant_message_id="msg-assistant-123",
        created_at=_ts(9, 45),
        need="activate",
        response_mode="execute",
        subject_refs=("arc:webui_cleanup", "domain:work"),
        active_arc_id="webui_cleanup",
        active_domain_ids=("work",),
        effective_support_values=behavior_contract.support_values,
        effective_relational_values=behavior_contract.relational_values,
        intervention_family="narrow",
        intervention_refs=(),
        prompt_contract_summary="need=activate; mode=execute; family=narrow; subjects=[arc:webui_cleanup, domain:work]",
        operational_snapshot_ref=None,
    )


@pytest.mark.asyncio
async def test_support_policy_runtime_persists_learning_situations_and_applies_bounded_support_updates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runtime should persist the current learning situation and apply low-risk support updates before generation."""

    turn_text = "Let's continue the Web UI cleanup work thread."
    query_embedding = [0.0, 0.95, 0.1, 0.0, 0.0, 0.0, 0.95, 0.8, 0.0, 0.0, 0.0, 0.2]
    embedder = FakeEmbedder({turn_text: tuple(query_embedding)})
    store = FakeSupportProfileStore(
        similar_situations=[
            (
                LearningSituation(
                    situation_id="sit-prior-1",
                    session_id="sess-prior-1",
                    recorded_at=_ts(8, 0),
                    turn_text="One next step worked better here.",
                    embedding=tuple(query_embedding),
                    need="resume",
                    response_mode="execute",
                    subject_refs=("arc:docs_refresh",),
                    arc_id="docs_refresh",
                    intervention_ids=("int-prior-1",),
                    behavior_contract_summary="Keep the next move narrow.",
                    intervention_family="narrow",
                    relational_values_applied={"candor": "high"},
                    support_values_applied={"option_bandwidth": "single"},
                    user_response_signals=("clarity",),
                    outcome_signals=("next_step_chosen",),
                ),
                0.94,
            ),
            (
                LearningSituation(
                    situation_id="sit-prior-2",
                    session_id="sess-prior-2",
                    recorded_at=_ts(8, 10),
                    turn_text="Single-step resumption worked better here too.",
                    embedding=tuple(query_embedding),
                    need="resume",
                    response_mode="execute",
                    subject_refs=("arc:admin_cleanup",),
                    arc_id="admin_cleanup",
                    intervention_ids=("int-prior-2",),
                    behavior_contract_summary="Keep the next move narrow.",
                    intervention_family="narrow",
                    relational_values_applied={"candor": "high"},
                    support_values_applied={"option_bandwidth": "single"},
                    user_response_signals=("resonance",),
                    outcome_signals=("resume_ready",),
                ),
                0.91,
            ),
        ]
    )
    runtime = SupportPolicyRuntime(store=store, embedder=embedder)  # type: ignore[arg-type]

    async def fake_need_bank() -> NeedPrototypeBank:
        return _make_need_bank()

    async def fake_abstract_subjects() -> tuple[SubjectPrototype, ...]:
        return tuple(
            subject
            for subject in _make_subject_prototypes()
            if subject.kind in {"identity", "direction", "global", "current_turn"}
        )

    async def fake_concrete_subjects() -> tuple[SubjectPrototype, ...]:
        return tuple(
            subject
            for subject in _make_subject_prototypes()
            if subject.kind in {"arc", "domain"}
        )

    monkeypatch.setattr(runtime, "_ensure_need_bank", fake_need_bank)
    monkeypatch.setattr(runtime, "_ensure_abstract_subjects", fake_abstract_subjects)
    monkeypatch.setattr(runtime, "_build_concrete_subjects", fake_concrete_subjects)

    runtime_result = await runtime.build_turn_contract(
        message=turn_text,
        query_embedding=query_embedding,
        session_messages=[("user", "previous user turn")],
    )

    assert runtime_result.behavior_contract.support_values["option_bandwidth"] == "single"
    assert len(store.saved_learning_situations) == 1
    assert len(store.update_events) == 2
    assert any(event.status == "applied" and event.dimension == "option_bandwidth" for event in store.update_events)
    assert any(pattern.status == "candidate" and pattern.relational_overrides == {"candor": "high"} for pattern in store.patterns)


def test_support_behavior_contract_changes_across_operational_reflective_and_calibration_contexts() -> None:
    """Representative contexts should compile into meaningfully different runtime contracts."""

    execute_contract = compile_support_behavior_contract(
        ResolvedSupportPolicy(
            assessment=SupportTurnAssessment(
                need="activate",
                subjects=(ResolvedSubject(kind="arc", id="webui_cleanup"),),
            ),
            response_mode="execute",
            relational_values={
                "warmth": "medium",
                "companionship": "high",
                "candor": "medium",
                "challenge": "medium",
                "authority": "medium",
                "emotional_attunement": "medium",
                "analytical_depth": "medium",
                "momentum_pressure": "high",
            },
            support_values={
                "planning_granularity": "minimal",
                "option_bandwidth": "single",
                "proactivity_level": "high",
                "accountability_style": "firm",
                "recovery_style": "steady",
                "reflection_depth": "light",
                "pacing": "brisk",
                "recommendation_forcefulness": "high",
            },
            primary_arc_id="webui_cleanup",
            domain_ids=("work",),
        )
    )
    direction_contract = compile_support_behavior_contract(
        ResolvedSupportPolicy(
            assessment=SupportTurnAssessment(
                need="reflect",
                subjects=(ResolvedSubject(kind="direction", id=None),),
            ),
            response_mode="direction_reflect",
            relational_values={
                "warmth": "high",
                "companionship": "medium",
                "candor": "medium",
                "challenge": "low",
                "authority": "low",
                "emotional_attunement": "high",
                "analytical_depth": "high",
                "momentum_pressure": "low",
            },
            support_values={
                "planning_granularity": "short",
                "option_bandwidth": "few",
                "proactivity_level": "low",
                "accountability_style": "light",
                "recovery_style": "gentle",
                "reflection_depth": "deep",
                "pacing": "slow",
                "recommendation_forcefulness": "low",
            },
            primary_arc_id=None,
            domain_ids=(),
        )
    )
    calibration_contract = compile_support_behavior_contract(
        ResolvedSupportPolicy(
            assessment=SupportTurnAssessment(
                need="calibrate",
                subjects=(ResolvedSubject(kind="current_turn", id=None),),
            ),
            response_mode="review",
            relational_values={
                "warmth": "high",
                "companionship": "medium",
                "candor": "high",
                "challenge": "high",
                "authority": "medium",
                "emotional_attunement": "high",
                "analytical_depth": "high",
                "momentum_pressure": "low",
            },
            support_values={
                "planning_granularity": "short",
                "option_bandwidth": "few",
                "proactivity_level": "medium",
                "accountability_style": "medium",
                "recovery_style": "gentle",
                "reflection_depth": "deep",
                "pacing": "steady",
                "recommendation_forcefulness": "low",
            },
            primary_arc_id=None,
            domain_ids=(),
        )
    )

    assert execute_contract.response_mode == "execute"
    assert direction_contract.response_mode == "direction_reflect"
    assert calibration_contract.response_mode == "review"

    assert execute_contract.intervention_family == "narrow"
    assert direction_contract.intervention_family == "mirror"
    assert calibration_contract.intervention_family == "challenge"

    assert execute_contract.evidence_mode == "light"
    assert direction_contract.evidence_mode == "light"
    assert calibration_contract.evidence_mode == "structured"

    assert execute_contract.support_values != direction_contract.support_values
    assert direction_contract.relational_values != calibration_contract.relational_values
