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


def test_alfred_class_has_build_self_model_method():
    """Verify Alfred class has build_self_model method with correct signature."""
    import inspect

    from alfred.alfred import Alfred

    # Verify the method exists and has correct return type annotation
    method = getattr(Alfred, "build_self_model", None)
    assert method is not None, "Alfred should have build_self_model method"

    # Check signature
    sig = inspect.signature(method)
    return_annotation = sig.return_annotation
    assert "RuntimeSelfModel" in str(return_annotation), "Method should return RuntimeSelfModel"


def test_fake_alfred_with_build_self_model_method():
    """Verify FakeAlfred can use build_self_model pattern."""
    # Create a fake Alfred that mimics the real Alfred's structure
    fake_alfred = FakeAlfred(
        tools=["read", "write"],
        session_messages=5,
        memories_count=3,
        total_tokens=1000,
        has_memory_store=True,
    )

    # Simulate calling build_self_model (like the real Alfred would)
    model = build_runtime_self_model(fake_alfred)

    # Verify it produces a valid self-model
    assert isinstance(model, RuntimeSelfModel)
    assert model.identity.name == "Alfred"
    assert model.visibility == Visibility.INTERNAL
    assert "read" in model.capabilities.tools_available
    assert model.context_pressure.message_count == 5


def test_runtime_self_model_to_prompt_section():
    """Verify self-model serializes to a well-formatted prompt section."""
    model = RuntimeSelfModel(
        identity=Identity(name="Alfred", role="assistant"),
        runtime=Runtime(interface=InterfaceType.CLI, session_id="test-123"),
        world=World(working_directory="/workspace", python_version="3.12.0", platform="Linux-5.15.0"),
        capabilities=Capabilities(
            tools_available=["read", "write", "bash"],
            memory_enabled=True,
            search_enabled=True,
        ),
        context_pressure=ContextPressure(
            message_count=10,
            memory_count=5,
            approximate_tokens=1500,
        ),
    )

    prompt_section = model.to_prompt_section()

    # Verify markdown structure
    assert "## Alfred Self-Model" in prompt_section
    assert "**Identity**: Alfred" in prompt_section
    assert "**Role**: assistant" in prompt_section

    # Verify runtime state
    assert "Interface: cli" in prompt_section
    assert "Session: test-123" in prompt_section
    assert "Mode: interactive" in prompt_section

    # Verify capabilities
    assert "Memory: enabled" in prompt_section
    assert "Search: enabled" in prompt_section
    assert "Tools: read, write, bash" in prompt_section

    # Verify context pressure
    assert "Messages: 10" in prompt_section
    assert "Memories: 5" in prompt_section
    assert "Approximate tokens: 1,500" in prompt_section

    # Verify environment
    assert "Working directory: /workspace" in prompt_section
    assert "Platform:" in prompt_section


def test_runtime_self_model_to_prompt_section_daemon_mode():
    """Verify daemon mode is reflected in prompt section."""
    model = RuntimeSelfModel(
        identity=Identity(),
        runtime=Runtime(interface=InterfaceType.CLI, daemon_mode=True),
        world=World(),
        capabilities=Capabilities(),
        context_pressure=ContextPressure(),
    )

    prompt_section = model.to_prompt_section()
    assert "Mode: daemon/background" in prompt_section


def test_runtime_self_model_to_prompt_section_limits_tools():
    """Verify long tool lists are truncated in prompt section."""
    many_tools = [f"tool_{i}" for i in range(15)]
    model = RuntimeSelfModel(
        identity=Identity(),
        runtime=Runtime(),
        world=World(),
        capabilities=Capabilities(tools_available=many_tools),
        context_pressure=ContextPressure(),
    )

    prompt_section = model.to_prompt_section()
    assert "(+5 more)" in prompt_section


def test_self_model_visibility_is_always_internal():
    """Verify self-model is always marked as internal-only.

    Safety test: The self-model should never be exposed directly to users.
    It should only appear in LLM prompts with visibility: INTERNAL.
    """
    # Create self-model with various configurations
    model = RuntimeSelfModel(
        identity=Identity(),
        runtime=Runtime(),
        world=World(),
        capabilities=Capabilities(),
        context_pressure=ContextPressure(),
    )

    # Verify visibility is INTERNAL
    assert model.visibility == Visibility.INTERNAL

    # Verify visibility in serialized form
    data = model.model_dump()
    assert data["visibility"] == "internal"

    # Verify visibility defaults to INTERNAL even when not specified
    model_no_explicit = RuntimeSelfModel(
        identity=Identity(),
        runtime=Runtime(),
        world=World(),
        capabilities=Capabilities(),
        context_pressure=ContextPressure(),
        # visibility not specified - should default to INTERNAL
    )
    assert model_no_explicit.visibility == Visibility.INTERNAL


def test_self_model_fails_closed_with_none_alfred():
    """Verify builder handles None Alfred gracefully (fail-closed).

    Safety test: The builder uses getattr with defaults, so None Alfred
    should produce a minimal but valid self-model with safe defaults.
    """
    # Builder handles None gracefully - produces minimal self-model
    model = build_runtime_self_model(None)  # type: ignore

    # Should produce a valid RuntimeSelfModel with safe defaults
    assert isinstance(model, RuntimeSelfModel)
    assert model.visibility == Visibility.INTERNAL

    # All capabilities should be disabled (safe defaults)
    assert model.capabilities.memory_enabled is False
    assert model.capabilities.search_enabled is False
    assert model.capabilities.tools_available == []

    # Context pressure should be zeroed
    assert model.context_pressure.message_count == 0
    assert model.context_pressure.memory_count == 0


def test_self_model_with_partial_alfred_state():
    """Verify self-model builds safely with partial Alfred state.

    Regression test: Alfred may have some subsystems initialized but not others.
    Self-model should gracefully handle partial state.
    """
    # Create Alfred with only some attributes
    class PartialAlfred:
        def __init__(self) -> None:
            self.tools = None  # Missing tools
            self.context_summary = None  # Missing context
            self.token_tracker = FakeTokenTracker(1000)  # Has tokens
            self.core = FakeCore(True)  # Has memory
            self._telegram_bot = None

    partial_alfred = PartialAlfred()

    # Should build without crashing
    model = build_runtime_self_model(partial_alfred)

    # Verify safe defaults for missing data
    assert model.capabilities.tools_available == []
    assert model.context_pressure.message_count == 0
    assert model.context_pressure.approximate_tokens == 1000  # This was available
    assert model.capabilities.memory_enabled is True  # This was available


def test_self_model_context_injection_is_internal():
    """Verify self-model in context is marked internal and properly formatted.

    Integration test: When self-model is injected into context assembly,
    it should appear in the system prompt (for LLM) but not be user-facing.
    """

    model = RuntimeSelfModel(
        identity=Identity(name="Alfred", role="test assistant"),
        runtime=Runtime(interface=InterfaceType.CLI, session_id="test-123"),
        world=World(working_directory="/test"),
        capabilities=Capabilities(
            tools_available=["read", "write"],
            memory_enabled=True,
            search_enabled=True,
        ),
        context_pressure=ContextPressure(message_count=5, memory_count=3),
    )

    # Simulate what ContextLoader.assemble_with_self_model() does
    self_model_section = model.to_prompt_section()

    # Verify it's formatted for LLM consumption
    assert "## Alfred Self-Model" in self_model_section
    assert "Alfred" in self_model_section
    assert "Interface: cli" in self_model_section

    # Verify it's not a raw JSON dump (user-unfriendly)
    assert '"identity":' not in self_model_section
    assert '"runtime":' not in self_model_section


def test_self_model_rebuilds_fresh_each_time():
    """Verify self-model is rebuilt from current state, not cached.

    Regression test: Self-model should reflect current runtime state,
    not a stale snapshot.
    """
    fake_alfred = FakeAlfred(
        tools=["read"],
        session_messages=1,
        memories_count=1,
        total_tokens=100,
        has_memory_store=True,
    )

    # Build first self-model
    model1 = build_runtime_self_model(fake_alfred)
    assert model1.context_pressure.message_count == 1

    # Simulate state change
    fake_alfred.context_summary.session_messages = 5

    # Build second self-model - should reflect new state
    model2 = build_runtime_self_model(fake_alfred)
    assert model2.context_pressure.message_count == 5

    # Models should be independent
    assert model1.context_pressure.message_count == 1  # Unchanged
