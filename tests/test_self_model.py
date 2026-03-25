"""Tests for the runtime self-model contract.

The self-model is an internal-only runtime snapshot describing Alfred's
current state, capabilities, and environment.
"""

from alfred.self_model import (
    Capabilities,
    ContextPressure,
    Identity,
    InterfaceType,
    Runtime,
    RuntimeSelfModel,
    Visibility,
    World,
)


def test_runtime_self_model_includes_identity_runtime_and_world_sections():
    """Verify the contract contains all required sections and fields."""
    # Build a complete self-model
    model = RuntimeSelfModel(
        identity=Identity(name="Alfred", role="assistant"),
        runtime=Runtime(interface=InterfaceType.CLI, daemon_mode=False),
        world=World(working_directory="/workspace"),
        capabilities=Capabilities(tools_available=["read", "write"]),
        context_pressure=ContextPressure(message_count=5),
    )

    # Verify all sections present
    assert model.identity.name == "Alfred"
    assert model.identity.role == "assistant"
    assert model.runtime.interface == InterfaceType.CLI
    assert model.runtime.daemon_mode is False
    assert model.world.working_directory == "/workspace"
    assert "read" in model.capabilities.tools_available
    assert model.context_pressure.message_count == 5

    # Verify internal-only visibility
    assert model.visibility == Visibility.INTERNAL

    # Verify serializable (no Nones in output if we use exclude_none)
    data = model.model_dump(exclude_none=True)
    assert "visibility" in data
    assert data["identity"]["name"] == "Alfred"
    assert data["runtime"]["interface"] == "cli"
