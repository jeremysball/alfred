"""Tests for support-profile registry contracts."""

from __future__ import annotations

from dataclasses import asdict

import pytest

from alfred.memory.support_profile import (
    DEFAULT_SUPPORT_PROFILE_REGISTRY_CATALOG,
    RELATIONAL_REGISTRY_DIMENSIONS,
    SUPPORT_PROFILE_SCHEMA_VERSION,
    SUPPORT_REGISTRY_DIMENSIONS,
    SupportProfileRegistryFamily,
    SupportProfileScope,
    SupportProfileValue,
    get_registry_dimension,
    validate_registry_value,
)


def test_support_profile_scope_accepts_only_global_context_and_arc_targets() -> None:
    """Scope validation should accept only the documented global, context, and arc targets."""
    global_scope = SupportProfileScope(type="global", id="user")
    assert asdict(global_scope) == {"type": "global", "id": "user"}

    for context_id in (
        "plan",
        "execute",
        "decide",
        "review",
        "identity_reflect",
        "direction_reflect",
    ):
        assert SupportProfileScope(type="context", id=context_id) == SupportProfileScope(
            type="context",
            id=context_id,
        )

    assert SupportProfileScope(type="arc", id="webui_cleanup") == SupportProfileScope(
        type="arc",
        id="webui_cleanup",
    )

    invalid_scopes = (
        {"type": "global", "id": "workspace"},
        {"type": "global", "id": ""},
        {"type": "context", "id": ""},
        {"type": "context", "id": "unknown_context"},
        {"type": "context", "id": " execute "},
        {"type": "arc", "id": ""},
        {"type": "arc", "id": "   "},
        {"type": "thread", "id": "webui_cleanup"},
        {"type": None, "id": "user"},
        {"type": "global", "id": None},
    )
    for invalid_scope in invalid_scopes:
        with pytest.raises(ValueError):
            SupportProfileScope(**invalid_scope)


def test_registry_catalog_exposes_versioned_relational_and_support_families() -> None:
    """Registry catalog should expose one versioned relational/support split."""
    catalog = DEFAULT_SUPPORT_PROFILE_REGISTRY_CATALOG

    assert catalog.schema_version == SUPPORT_PROFILE_SCHEMA_VERSION == 1
    assert catalog.kinds == ("relational", "support")

    assert catalog.get_family("relational") == catalog.relational
    assert catalog.get_family("support") == catalog.support

    assert catalog.relational == SupportProfileRegistryFamily(kind="relational")
    assert catalog.support == SupportProfileRegistryFamily(kind="support")

    with pytest.raises(ValueError):
        catalog.get_family("freeform")


def test_relational_registry_rejects_unknown_dimensions_and_invalid_values() -> None:
    """Relational registry should expose only the documented dimensions and values."""
    assert tuple(RELATIONAL_REGISTRY_DIMENSIONS) == (
        "warmth",
        "companionship",
        "candor",
        "challenge",
        "authority",
        "emotional_attunement",
        "analytical_depth",
        "momentum_pressure",
    )

    warmth = get_registry_dimension("relational", "warmth")
    assert warmth.registry == "relational"
    assert warmth.dimension == "warmth"
    assert warmth.allowed_values == ("low", "medium", "high")
    assert warmth.default_value == "medium"
    assert warmth.allowed_scope_types == ("global", "context", "arc")

    assert validate_registry_value("relational", "candor", "high") == "high"
    assert validate_registry_value("relational", "momentum_pressure", "low") == "low"

    with pytest.raises(ValueError):
        get_registry_dimension("relational", "tone")

    with pytest.raises(ValueError):
        validate_registry_value("relational", "warmth", "max")


def test_support_registry_rejects_unknown_dimensions_and_invalid_values() -> None:
    """Support registry should expose only the documented dimensions and values."""
    assert tuple(SUPPORT_REGISTRY_DIMENSIONS) == (
        "planning_granularity",
        "option_bandwidth",
        "proactivity_level",
        "accountability_style",
        "recovery_style",
        "reflection_depth",
        "pacing",
        "recommendation_forcefulness",
    )

    option_bandwidth = get_registry_dimension("support", "option_bandwidth")
    assert option_bandwidth.registry == "support"
    assert option_bandwidth.dimension == "option_bandwidth"
    assert option_bandwidth.allowed_values == ("single", "few", "many")
    assert option_bandwidth.default_value == "few"
    assert option_bandwidth.allowed_scope_types == ("global", "context", "arc")

    accountability_style = get_registry_dimension("support", "accountability_style")
    assert accountability_style.allowed_values == ("light", "medium", "firm")
    assert accountability_style.default_value == "medium"

    recovery_style = get_registry_dimension("support", "recovery_style")
    assert recovery_style.allowed_values == ("gentle", "steady", "directive")
    assert recovery_style.default_value == "steady"

    assert validate_registry_value("support", "planning_granularity", "full") == "full"
    assert validate_registry_value("support", "proactivity_level", "high") == "high"
    assert validate_registry_value("support", "recommendation_forcefulness", "medium") == "medium"

    with pytest.raises(ValueError):
        get_registry_dimension("support", "tone")

    with pytest.raises(ValueError):
        validate_registry_value("support", "pacing", "warp")


def test_support_profile_value_accepts_valid_scoped_records_and_rejects_cross_registry_mismatches() -> None:
    """Scoped support-profile values should validate registry, value, source, and evidence shape."""
    support_value = SupportProfileValue(
        registry="support",
        dimension="option_bandwidth",
        scope=SupportProfileScope(type="context", id="execute"),
        value="single",
        status="observed",
        confidence=0.87,
        source="auto_adapted",
        evidence_refs=("int_55", "int_61", "int_64"),
    )

    assert asdict(support_value) == {
        "registry": "support",
        "dimension": "option_bandwidth",
        "scope": {"type": "context", "id": "execute"},
        "value": "single",
        "status": "observed",
        "confidence": 0.87,
        "source": "auto_adapted",
        "evidence_refs": ("int_55", "int_61", "int_64"),
    }

    relational_value = SupportProfileValue(
        registry="relational",
        dimension="warmth",
        scope=SupportProfileScope(type="global", id="user"),
        value="high",
        status="confirmed",
        confidence=1.0,
        source="explicit",
        evidence_refs=(),
    )
    assert relational_value.value == "high"

    invalid_records = (
        {
            "registry": "relational",
            "dimension": "option_bandwidth",
            "scope": SupportProfileScope(type="context", id="execute"),
            "value": "single",
            "status": "observed",
            "confidence": 0.87,
            "source": "auto_adapted",
            "evidence_refs": ("int_55",),
        },
        {
            "registry": "support",
            "dimension": "warmth",
            "scope": SupportProfileScope(type="global", id="user"),
            "value": "high",
            "status": "observed",
            "confidence": 0.87,
            "source": "auto_adapted",
            "evidence_refs": ("int_55",),
        },
        {
            "registry": "support",
            "dimension": "option_bandwidth",
            "scope": SupportProfileScope(type="context", id="execute"),
            "value": "high",
            "status": "observed",
            "confidence": 0.87,
            "source": "auto_adapted",
            "evidence_refs": ("int_55",),
        },
        {
            "registry": "support",
            "dimension": "option_bandwidth",
            "scope": SupportProfileScope(type="context", id="execute"),
            "value": "single",
            "status": "active",
            "confidence": 0.87,
            "source": "auto_adapted",
            "evidence_refs": ("int_55",),
        },
        {
            "registry": "support",
            "dimension": "option_bandwidth",
            "scope": SupportProfileScope(type="context", id="execute"),
            "value": "single",
            "status": "observed",
            "confidence": 1.2,
            "source": "auto_adapted",
            "evidence_refs": ("int_55",),
        },
        {
            "registry": "support",
            "dimension": "option_bandwidth",
            "scope": SupportProfileScope(type="context", id="execute"),
            "value": "single",
            "status": "observed",
            "confidence": 0.87,
            "source": "inferred",
            "evidence_refs": ("int_55",),
        },
        {
            "registry": "support",
            "dimension": "option_bandwidth",
            "scope": SupportProfileScope(type="context", id="execute"),
            "value": "single",
            "status": "observed",
            "confidence": 0.87,
            "source": "auto_adapted",
            "evidence_refs": ("int_55", " "),
        },
    )
    for invalid_record in invalid_records:
        with pytest.raises(ValueError):
            SupportProfileValue(**invalid_record)


def test_memory_package_reexports_support_profile_contracts() -> None:
    """Public memory exports should expose the support-profile contract surface."""
    import alfred.memory as exported_memory

    assert exported_memory.DEFAULT_SUPPORT_PROFILE_REGISTRY_CATALOG is DEFAULT_SUPPORT_PROFILE_REGISTRY_CATALOG
    assert exported_memory.SupportProfileScope is SupportProfileScope
    assert exported_memory.SupportProfileValue is SupportProfileValue
