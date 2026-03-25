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
    build_runtime_self_model,
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


class FakeAlfred:
    """Test double for Alfred that exposes runtime state for self-model building."""

    def __init__(
        self,
        tools: list[str] | None = None,
        session_messages: int = 0,
        memories_count: int = 0,
        total_tokens: int | None = None,
        has_memory_store: bool = True,
    ) -> None:
        self.tools = FakeTools(tools or [])
        self.context_summary = FakeContextSummary(session_messages, memories_count)
        self.token_tracker = FakeTokenTracker(total_tokens)
        self.core = FakeCore(has_memory_store)
        self._telegram_bot = None  # CLI mode by default


class FakeTools:
    """Fake tools registry."""

    def __init__(self, tool_names: list[str]) -> None:
        self._tool_names = tool_names

    def list_tools(self) -> list[str]:
        return self._tool_names


class FakeContextSummary:
    """Fake context summary."""

    def __init__(self, session_messages: int, memories_count: int) -> None:
        self.session_messages = session_messages
        self.memories_count = memories_count


class FakeTokenTracker:
    """Fake token tracker."""

    def __init__(self, total_tokens: int | None) -> None:
        self.total_tokens = total_tokens


class FakeCore:
    """Fake AlfredCore."""

    def __init__(self, has_memory_store: bool) -> None:
        self.memory_store = object() if has_memory_store else None


def test_build_runtime_self_model_uses_current_alfred_state():
    """Verify builder extracts live facts from Alfred runtime."""
    # Create a fake Alfred with known state
    fake_alfred = FakeAlfred(
        tools=["read", "write", "bash"],
        session_messages=10,
        memories_count=5,
        total_tokens=1500,
        has_memory_store=True,
    )

    # Build self-model
    model = build_runtime_self_model(
        fake_alfred,
        interface=InterfaceType.CLI,
        session_id="test-session-123",
    )

    # Verify runtime facts
    assert model.runtime.interface == InterfaceType.CLI
    assert model.runtime.session_id == "test-session-123"
    assert model.runtime.daemon_mode is False

    # Verify capabilities
    assert "read" in model.capabilities.tools_available
    assert "write" in model.capabilities.tools_available
    assert "bash" in model.capabilities.tools_available
    assert model.capabilities.memory_enabled is True
    assert model.capabilities.search_enabled is True

    # Verify context pressure
    assert model.context_pressure.message_count == 10
    assert model.context_pressure.memory_count == 5
    assert model.context_pressure.approximate_tokens == 1500

    # Verify world state is populated
    assert model.world.working_directory is not None
    assert model.world.python_version is not None
    assert model.world.platform is not None

    # Verify identity is present
    assert model.identity.name == "Alfred"
    assert model.visibility == Visibility.INTERNAL


class MinimalAlfred:
    """Test double with minimal attributes to verify fail-closed behavior."""

    def __init__(self) -> None:
        # Intentionally empty - simulates degraded Alfred runtime
        pass


def test_runtime_self_model_omits_unknown_fields_instead_of_fabricating_them():
    """Verify missing runtime facts become unknown/omitted and never get invented.

    When Alfred subsystems are unavailable, the builder should:
    - Not crash
    - Use safe defaults (empty lists, False flags, 0 counts)
    - Not fabricate data (None stays None)
    """
    # Create a minimal Alfred with almost no attributes
    minimal_alfred = MinimalAlfred()

    # Build self-model - should not crash
    model = build_runtime_self_model(
        minimal_alfred,
        interface=InterfaceType.CLI,
        session_id="test-session",
    )

    # Verify safe defaults for capabilities
    assert model.capabilities.tools_available == []
    assert model.capabilities.memory_enabled is False
    assert model.capabilities.search_enabled is False

    # Verify safe defaults for context pressure
    assert model.context_pressure.message_count == 0
    assert model.context_pressure.memory_count == 0
    assert model.context_pressure.approximate_tokens is None

    # Verify world state is still populated (from os/platform, not Alfred)
    assert model.world.working_directory is not None
    assert model.world.python_version is not None
    assert model.world.platform is not None

    # Verify runtime uses provided overrides
    assert model.runtime.interface == InterfaceType.CLI
    assert model.runtime.session_id == "test-session"

    # Verify model serializes cleanly without fabricated data
    data = model.model_dump(exclude_none=True)
    assert "identity" in data
    assert "runtime" in data
    assert "capabilities" in data
    # approximate_tokens should be excluded since it's None
    assert "approximate_tokens" not in data.get("context_pressure", {})
