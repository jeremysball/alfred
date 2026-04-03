"""Typed support-profile contracts for scoped relational and support values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SupportProfileScopeType = Literal["global", "context", "arc"]
SupportProfileRegistryKind = Literal["relational", "support"]
SupportProfileValueStatus = Literal["observed", "candidate", "confirmed"]
SupportProfileValueSource = Literal["explicit", "auto_adapted", "corrected", "imported"]

SUPPORT_PROFILE_SCHEMA_VERSION = 1

V1_INTERACTION_CONTEXT_IDS: tuple[str, ...] = (
    "plan",
    "execute",
    "decide",
    "review",
    "identity_reflect",
    "direction_reflect",
)

_SUPPORTED_SCOPE_TYPES = frozenset(("global", "context", "arc"))
_SUPPORTED_REGISTRY_KINDS = frozenset(("relational", "support"))
_SUPPORTED_VALUE_STATUSES = frozenset(("observed", "candidate", "confirmed"))
_SUPPORTED_VALUE_SOURCES = frozenset(("explicit", "auto_adapted", "corrected", "imported"))
_RELATIONAL_VALUE_LEVELS: tuple[str, ...] = ("low", "medium", "high")
_PLANNING_GRANULARITY_VALUES: tuple[str, ...] = ("minimal", "short", "full")
_OPTION_BANDWIDTH_VALUES: tuple[str, ...] = ("single", "few", "many")
_ACCOUNTABILITY_STYLE_VALUES: tuple[str, ...] = ("light", "medium", "firm")
_RECOVERY_STYLE_VALUES: tuple[str, ...] = ("gentle", "steady", "directive")
_REFLECTION_DEPTH_VALUES: tuple[str, ...] = ("light", "medium", "deep")
_PACING_VALUES: tuple[str, ...] = ("brisk", "steady", "slow")
_CANONICAL_SCOPE_TYPES: tuple[SupportProfileScopeType, ...] = ("global", "context", "arc")


@dataclass(eq=True, frozen=True)
class SupportProfileRegistryFamily:
    """One validated family inside the support-profile registry catalog."""

    kind: SupportProfileRegistryKind

    def __post_init__(self) -> None:
        """Reject unsupported registry kinds."""
        if not isinstance(self.kind, str) or self.kind not in _SUPPORTED_REGISTRY_KINDS:
            raise ValueError(f"Unsupported support-profile registry kind: {self.kind!r}")


@dataclass(eq=True, frozen=True)
class SupportProfileRegistryCatalog:
    """Versioned catalog of registry families Alfred supports."""

    schema_version: int
    relational: SupportProfileRegistryFamily
    support: SupportProfileRegistryFamily

    def __post_init__(self) -> None:
        """Validate schema version and family placement."""
        if self.schema_version != SUPPORT_PROFILE_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported support-profile schema version: {self.schema_version!r}. "
                f"Expected {SUPPORT_PROFILE_SCHEMA_VERSION}",
            )
        if self.relational.kind != "relational":
            raise ValueError("relational family must use kind='relational'")
        if self.support.kind != "support":
            raise ValueError("support family must use kind='support'")

    @property
    def kinds(self) -> tuple[SupportProfileRegistryKind, SupportProfileRegistryKind]:
        """Return supported registry-family kinds in canonical order."""
        return ("relational", "support")

    def get_family(self, kind: SupportProfileRegistryKind) -> SupportProfileRegistryFamily:
        """Return one registry family by validated kind."""
        if kind == "relational":
            return self.relational
        if kind == "support":
            return self.support
        raise ValueError(f"Unsupported support-profile registry kind: {kind!r}")


@dataclass(eq=True, frozen=True)
class SupportProfileDimensionDefinition:
    """Validated dimension definition inside one registry family."""

    registry: SupportProfileRegistryKind
    dimension: str
    allowed_values: tuple[str, ...]
    default_value: str
    allowed_scope_types: tuple[SupportProfileScopeType, ...] = _CANONICAL_SCOPE_TYPES

    def __post_init__(self) -> None:
        """Reject malformed dimension definitions."""
        if not isinstance(self.registry, str) or self.registry not in _SUPPORTED_REGISTRY_KINDS:
            raise ValueError(f"Unsupported support-profile registry kind: {self.registry!r}")
        if not isinstance(self.dimension, str) or not self.dimension or self.dimension != self.dimension.strip():
            raise ValueError("Support-profile dimension id must be a non-empty trimmed string")
        if not self.allowed_values:
            raise ValueError(f"Support-profile dimension {self.dimension!r} must define at least one allowed value")
        if len(set(self.allowed_values)) != len(self.allowed_values):
            raise ValueError(f"Support-profile dimension {self.dimension!r} has duplicate allowed values")
        for value in self.allowed_values:
            if not isinstance(value, str) or not value or value != value.strip():
                raise ValueError(
                    f"Support-profile dimension {self.dimension!r} must use non-empty trimmed string values",
                )
        if self.default_value not in self.allowed_values:
            raise ValueError(
                f"Support-profile dimension {self.dimension!r} default {self.default_value!r} "
                f"must be one of {self.allowed_values!r}",
            )
        if not self.allowed_scope_types:
            raise ValueError(f"Support-profile dimension {self.dimension!r} must allow at least one scope type")
        for scope_type in self.allowed_scope_types:
            if scope_type not in _SUPPORTED_SCOPE_TYPES:
                raise ValueError(
                    f"Support-profile dimension {self.dimension!r} has unsupported scope type {scope_type!r}",
                )


RELATIONAL_REGISTRY_DIMENSIONS: dict[str, SupportProfileDimensionDefinition] = {
    "warmth": SupportProfileDimensionDefinition(
        registry="relational",
        dimension="warmth",
        allowed_values=_RELATIONAL_VALUE_LEVELS,
        default_value="medium",
    ),
    "companionship": SupportProfileDimensionDefinition(
        registry="relational",
        dimension="companionship",
        allowed_values=_RELATIONAL_VALUE_LEVELS,
        default_value="medium",
    ),
    "candor": SupportProfileDimensionDefinition(
        registry="relational",
        dimension="candor",
        allowed_values=_RELATIONAL_VALUE_LEVELS,
        default_value="medium",
    ),
    "challenge": SupportProfileDimensionDefinition(
        registry="relational",
        dimension="challenge",
        allowed_values=_RELATIONAL_VALUE_LEVELS,
        default_value="medium",
    ),
    "authority": SupportProfileDimensionDefinition(
        registry="relational",
        dimension="authority",
        allowed_values=_RELATIONAL_VALUE_LEVELS,
        default_value="medium",
    ),
    "emotional_attunement": SupportProfileDimensionDefinition(
        registry="relational",
        dimension="emotional_attunement",
        allowed_values=_RELATIONAL_VALUE_LEVELS,
        default_value="medium",
    ),
    "analytical_depth": SupportProfileDimensionDefinition(
        registry="relational",
        dimension="analytical_depth",
        allowed_values=_RELATIONAL_VALUE_LEVELS,
        default_value="medium",
    ),
    "momentum_pressure": SupportProfileDimensionDefinition(
        registry="relational",
        dimension="momentum_pressure",
        allowed_values=_RELATIONAL_VALUE_LEVELS,
        default_value="medium",
    ),
}

SUPPORT_REGISTRY_DIMENSIONS: dict[str, SupportProfileDimensionDefinition] = {
    "planning_granularity": SupportProfileDimensionDefinition(
        registry="support",
        dimension="planning_granularity",
        allowed_values=_PLANNING_GRANULARITY_VALUES,
        default_value="short",
    ),
    "option_bandwidth": SupportProfileDimensionDefinition(
        registry="support",
        dimension="option_bandwidth",
        allowed_values=_OPTION_BANDWIDTH_VALUES,
        default_value="few",
    ),
    "proactivity_level": SupportProfileDimensionDefinition(
        registry="support",
        dimension="proactivity_level",
        allowed_values=_RELATIONAL_VALUE_LEVELS,
        default_value="medium",
    ),
    "accountability_style": SupportProfileDimensionDefinition(
        registry="support",
        dimension="accountability_style",
        allowed_values=_ACCOUNTABILITY_STYLE_VALUES,
        default_value="medium",
    ),
    "recovery_style": SupportProfileDimensionDefinition(
        registry="support",
        dimension="recovery_style",
        allowed_values=_RECOVERY_STYLE_VALUES,
        default_value="steady",
    ),
    "reflection_depth": SupportProfileDimensionDefinition(
        registry="support",
        dimension="reflection_depth",
        allowed_values=_REFLECTION_DEPTH_VALUES,
        default_value="medium",
    ),
    "pacing": SupportProfileDimensionDefinition(
        registry="support",
        dimension="pacing",
        allowed_values=_PACING_VALUES,
        default_value="steady",
    ),
    "recommendation_forcefulness": SupportProfileDimensionDefinition(
        registry="support",
        dimension="recommendation_forcefulness",
        allowed_values=_RELATIONAL_VALUE_LEVELS,
        default_value="medium",
    ),
}

DEFAULT_SUPPORT_PROFILE_REGISTRY_CATALOG = SupportProfileRegistryCatalog(
    schema_version=SUPPORT_PROFILE_SCHEMA_VERSION,
    relational=SupportProfileRegistryFamily(kind="relational"),
    support=SupportProfileRegistryFamily(kind="support"),
)


def get_registry_dimension(
    registry: SupportProfileRegistryKind,
    dimension: str,
) -> SupportProfileDimensionDefinition:
    """Return one validated dimension definition from the selected registry family."""
    if registry == "relational":
        dimensions = RELATIONAL_REGISTRY_DIMENSIONS
    elif registry == "support":
        dimensions = SUPPORT_REGISTRY_DIMENSIONS
    else:
        raise ValueError(f"Unsupported support-profile registry kind: {registry!r}")

    try:
        return dimensions[dimension]
    except KeyError as exc:
        raise ValueError(f"Unsupported {registry} support-profile dimension: {dimension!r}") from exc


def validate_registry_value(
    registry: SupportProfileRegistryKind,
    dimension: str,
    value: str,
) -> str:
    """Reject values that are not allowed for the selected registry dimension."""
    definition = get_registry_dimension(registry, dimension)
    if value not in definition.allowed_values:
        raise ValueError(
            f"Unsupported {registry} value {value!r} for dimension {dimension!r}. "
            f"Expected one of: {', '.join(definition.allowed_values)}",
        )
    return value


@dataclass(eq=True, frozen=True)
class SupportProfileScope:
    """Validated scope selector for support-profile values."""

    type: SupportProfileScopeType
    id: str

    def __post_init__(self) -> None:
        """Reject malformed scope types and unsupported IDs."""
        scope_type = self.type
        scope_id = self.id

        if not isinstance(scope_type, str) or scope_type not in _SUPPORTED_SCOPE_TYPES:
            raise ValueError(f"Unsupported support-profile scope type: {scope_type!r}")

        if not isinstance(scope_id, str):
            actual_type = type(scope_id).__name__
            raise ValueError(f"Support-profile scope id must be a string, got {actual_type}")

        if not scope_id or scope_id != scope_id.strip():
            raise ValueError("Support-profile scope id must be non-empty and must not include surrounding whitespace")

        if scope_type == "global":
            if scope_id != "user":
                raise ValueError("Global support-profile scope must use id='user'")
            return

        if scope_type == "context" and scope_id not in V1_INTERACTION_CONTEXT_IDS:
            allowed_contexts = ", ".join(V1_INTERACTION_CONTEXT_IDS)
            raise ValueError(
                f"Unsupported support-profile context id: {scope_id!r}. Expected one of: {allowed_contexts}",
            )


@dataclass(eq=True, frozen=True)
class SupportProfileValue:
    """Validated scoped relational or support profile value."""

    registry: SupportProfileRegistryKind
    dimension: str
    scope: SupportProfileScope
    value: str
    status: SupportProfileValueStatus
    confidence: float
    source: SupportProfileValueSource
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Reject malformed scoped support-profile value records."""
        if not isinstance(self.scope, SupportProfileScope):
            raise ValueError("Support-profile value scope must be a SupportProfileScope")

        definition = get_registry_dimension(self.registry, self.dimension)
        if self.scope.type not in definition.allowed_scope_types:
            raise ValueError(
                f"Support-profile dimension {self.dimension!r} does not allow scope type {self.scope.type!r}",
            )

        validate_registry_value(self.registry, self.dimension, self.value)

        if not isinstance(self.status, str) or self.status not in _SUPPORTED_VALUE_STATUSES:
            raise ValueError(f"Unsupported support-profile value status: {self.status!r}")

        if not isinstance(self.source, str) or self.source not in _SUPPORTED_VALUE_SOURCES:
            raise ValueError(f"Unsupported support-profile value source: {self.source!r}")

        if isinstance(self.confidence, bool) or not isinstance(self.confidence, int | float):
            actual_type = type(self.confidence).__name__
            raise ValueError(f"Support-profile confidence must be numeric, got {actual_type}")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("Support-profile confidence must be between 0.0 and 1.0")
        object.__setattr__(self, "confidence", float(self.confidence))

        if not isinstance(self.evidence_refs, tuple):
            raise ValueError("Support-profile evidence_refs must be a tuple of evidence ids")
        for evidence_ref in self.evidence_refs:
            if not isinstance(evidence_ref, str) or not evidence_ref or evidence_ref != evidence_ref.strip():
                raise ValueError("Support-profile evidence refs must be non-empty trimmed strings")
