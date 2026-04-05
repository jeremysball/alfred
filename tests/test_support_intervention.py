"""Tests for support intervention contracts."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime

import pytest

from alfred.memory.support_memory import SupportIntervention, SupportInterventionMessageRef


def test_support_intervention_validates_context_applied_values_and_evidence_refs() -> None:
    """Support interventions should validate context, applied values, signals, and typed provenance refs."""
    timestamp = datetime(2026, 3, 30, 12, 0, tzinfo=UTC)
    base_message_refs = [
        SupportInterventionMessageRef(
            session_id="sess_812",
            message_start_id="msg_445",
            message_end_id="msg_446",
        ),
        SupportInterventionMessageRef(
            session_id="sess_812",
            message_start_id="msg_448",
            message_end_id="msg_448",
        ),
    ]

    intervention = SupportIntervention(
        intervention_id="int_55",
        episode_id="ep_204",
        timestamp=timestamp,
        context="execute",
        arc_id="webui_cleanup",
        intervention_type="narrow_next_step",
        relational_values_applied={
            "companionship": "medium",
            "candor": "medium",
            "momentum_pressure": "medium",
        },
        support_values_applied={
            "planning_granularity": "minimal",
            "option_bandwidth": "single",
            "recommendation_forcefulness": "high",
        },
        behavior_contract_summary="Keep this narrow, recommend one next move, do not open a planning tree.",
        user_response_signals=["resonance", "commitment"],
        outcome_signals=["next_step_chosen"],
        evidence_refs=base_message_refs,
    )

    assert asdict(intervention) == {
        "schema_version": 1,
        "intervention_id": "int_55",
        "episode_id": "ep_204",
        "timestamp": timestamp,
        "context": "execute",
        "arc_id": "webui_cleanup",
        "intervention_type": "narrow_next_step",
        "relational_values_applied": {
            "companionship": "medium",
            "candor": "medium",
            "momentum_pressure": "medium",
        },
        "support_values_applied": {
            "planning_granularity": "minimal",
            "option_bandwidth": "single",
            "recommendation_forcefulness": "high",
        },
        "behavior_contract_summary": "Keep this narrow, recommend one next move, do not open a planning tree.",
        "user_response_signals": ["resonance", "commitment"],
        "outcome_signals": ["next_step_chosen"],
        "evidence_refs": [
            {
                "session_id": "sess_812",
                "message_start_id": "msg_445",
                "message_end_id": "msg_446",
            },
            {
                "session_id": "sess_812",
                "message_start_id": "msg_448",
                "message_end_id": "msg_448",
            },
        ],
    }

    invalid_interventions = (
        {
            "context": "brainstorm",
        },
        {
            "relational_values_applied": {
                "tone": "medium",
            },
        },
        {
            "support_values_applied": {
                "option_bandwidth": "wide",
            },
        },
        {
            "user_response_signals": ["commitment", "  "],
        },
        {
            "outcome_signals": ["next_step_chosen", " next_step_chosen "],
        },
        {
            "evidence_refs": ["sess_812:msg_445"],
        },
        {
            "evidence_refs": [
                base_message_refs[0],
                SupportInterventionMessageRef(
                    session_id="sess_other",
                    message_start_id="msg_449",
                    message_end_id="msg_449",
                ),
            ],
        },
    )

    base_kwargs = {
        "intervention_id": "int_55",
        "episode_id": "ep_204",
        "timestamp": timestamp,
        "context": "execute",
        "arc_id": "webui_cleanup",
        "intervention_type": "narrow_next_step",
        "relational_values_applied": {
            "companionship": "medium",
            "candor": "medium",
            "momentum_pressure": "medium",
        },
        "support_values_applied": {
            "planning_granularity": "minimal",
            "option_bandwidth": "single",
            "recommendation_forcefulness": "high",
        },
        "behavior_contract_summary": "Keep this narrow, recommend one next move, do not open a planning tree.",
        "user_response_signals": ["resonance", "commitment"],
        "outcome_signals": ["next_step_chosen"],
        "evidence_refs": base_message_refs,
    }

    for invalid_fields in invalid_interventions:
        with pytest.raises(ValueError):
            SupportIntervention(**(base_kwargs | invalid_fields))


def test_support_intervention_round_trips_through_storage_records() -> None:
    """Support interventions should serialize and deserialize without losing typed fields."""
    intervention = SupportIntervention(
        intervention_id="int_61",
        episode_id="ep_204",
        timestamp=datetime(2026, 3, 30, 12, 4, tzinfo=UTC),
        context="execute",
        arc_id="webui_cleanup",
        intervention_type="narrow_next_step",
        relational_values_applied={
            "companionship": "medium",
            "momentum_pressure": "high",
        },
        support_values_applied={
            "planning_granularity": "minimal",
            "option_bandwidth": "single",
        },
        behavior_contract_summary="Keep this narrow, recommend one next move, and avoid a branching plan.",
        user_response_signals=["resonance", "commitment"],
        outcome_signals=["next_step_chosen"],
        evidence_refs=[
            SupportInterventionMessageRef(
                session_id="sess_812",
                message_start_id="msg_448",
                message_end_id="msg_448",
            ),
            SupportInterventionMessageRef(
                session_id="sess_812",
                message_start_id="msg_450",
                message_end_id="msg_451",
            ),
        ],
    )

    record = intervention.to_record()

    assert record["schema_version"] == 1
    assert record["timestamp"] == "2026-03-30T12:04:00+00:00"
    assert json.loads(record["relational_values_applied"]) == {
        "companionship": "medium",
        "momentum_pressure": "high",
    }
    assert json.loads(record["support_values_applied"]) == {
        "planning_granularity": "minimal",
        "option_bandwidth": "single",
    }
    assert json.loads(record["user_response_signals"]) == ["resonance", "commitment"]
    assert json.loads(record["outcome_signals"]) == ["next_step_chosen"]
    assert json.loads(record["evidence_refs"]) == [
        {
            "session_id": "sess_812",
            "message_start_id": "msg_448",
            "message_end_id": "msg_448",
        },
        {
            "session_id": "sess_812",
            "message_start_id": "msg_450",
            "message_end_id": "msg_451",
        },
    ]

    assert SupportIntervention.from_record(record) == intervention
