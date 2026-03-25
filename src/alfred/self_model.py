"""Runtime self-model for Alfred.

An internal-only snapshot describing Alfred's current state, identity,
capabilities, and environment. Used for self-awareness in prompt assembly.
"""

from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from alfred.alfred import Alfred


class InterfaceType(StrEnum):
    """The interface Alfred is currently operating through."""

    CLI = "cli"
    WEBUI = "webui"


class Visibility(StrEnum):
    """Visibility level for self-model content."""

    INTERNAL = "internal"  # Never shown to user directly


class Identity(BaseModel):
    """Who Alfred is."""

    model_config = ConfigDict(extra="forbid")

    name: str = "Alfred"
    role: str = "persistent memory-augmented assistant"
    version: str | None = None  # From package metadata


class Runtime(BaseModel):
    """Current operating state."""

    model_config = ConfigDict(extra="forbid")

    interface: InterfaceType | None = None
    session_id: str | None = None
    daemon_mode: bool = False  # Is cron/background mode active?


class World(BaseModel):
    """Environment Alfred is operating in."""

    model_config = ConfigDict(extra="forbid")

    working_directory: str | None = None
    python_version: str | None = None
    platform: str | None = None


class Capabilities(BaseModel):
    """What Alfred can do right now."""

    model_config = ConfigDict(extra="forbid")

    tools_available: list[str] = []
    memory_enabled: bool = True
    search_enabled: bool = True


class ContextPressure(BaseModel):
    """How loaded the current session is."""

    model_config = ConfigDict(extra="forbid")

    message_count: int = 0
    memory_count: int = 0
    approximate_tokens: int | None = None


class RuntimeSelfModel(BaseModel):
    """Complete self-model snapshot.

    This model is internal-only and should never be exposed directly
    to users in ordinary responses. Use for prompt assembly and
    self-awareness only.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    visibility: Visibility = Visibility.INTERNAL
    identity: Identity
    runtime: Runtime
    world: World
    capabilities: Capabilities
    context_pressure: ContextPressure


def build_runtime_self_model(
    alfred: "Alfred",
    *,
    interface: InterfaceType | None = None,
    session_id: str | None = None,
) -> RuntimeSelfModel:
    """Build a self-model snapshot from live Alfred runtime state.

    Args:
        alfred: The Alfred instance to introspect
        interface: Override the detected interface (auto-detected if None)
        session_id: Override the session ID (uses current session if None)

    Returns:
        RuntimeSelfModel populated with current runtime facts
    """
    import os
    import platform

    # Auto-detect interface from Alfred state
    detected_interface = interface
    if detected_interface is None:
        # Check if Telegram bot is initialized (not None)
        detected_interface = (
            InterfaceType.WEBUI
            if getattr(alfred, "_telegram_bot", None) is not None
            else InterfaceType.CLI
        )

    # Get session ID
    current_session_id = session_id or "cli"

    # Get tools from registry
    tools_available: list[str] = []
    tools_registry = getattr(alfred, "tools", None)
    if tools_registry is not None:
        tools_available = tools_registry.list_tools()

    # Get context pressure from context_summary
    context_summary = getattr(alfred, "context_summary", None)
    message_count = 0
    memory_count = 0
    if context_summary is not None:
        message_count = getattr(context_summary, "session_messages", 0)
        memory_count = getattr(context_summary, "memories_count", 0)

    # Get approximate tokens from token_tracker
    approximate_tokens: int | None = None
    token_tracker = getattr(alfred, "token_tracker", None)
    if token_tracker is not None:
        approximate_tokens = getattr(token_tracker, "total_tokens", None)

    # Check if memory/search is enabled via core
    memory_enabled = False
    search_enabled = False
    core = getattr(alfred, "core", None)
    if core is not None:
        memory_store = getattr(core, "memory_store", None)
        memory_enabled = memory_store is not None
        search_enabled = memory_store is not None

    return RuntimeSelfModel(
        identity=Identity(),
        runtime=Runtime(
            interface=detected_interface,
            session_id=current_session_id,
            daemon_mode=False,  # TODO: Detect from runtime context
        ),
        world=World(
            working_directory=os.getcwd(),
            python_version=platform.python_version(),
            platform=platform.platform(),
        ),
        capabilities=Capabilities(
            tools_available=tools_available,
            memory_enabled=memory_enabled,
            search_enabled=search_enabled,
        ),
        context_pressure=ContextPressure(
            message_count=message_count,
            memory_count=memory_count,
            approximate_tokens=approximate_tokens,
        ),
    )
