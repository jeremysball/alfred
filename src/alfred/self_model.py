"""Runtime self-model for Alfred.

An internal-only snapshot describing Alfred's current state, identity,
capabilities, and environment. Used for self-awareness in prompt assembly.
"""

import logging
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

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
    role: str = "local-first relational support system"
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

    def to_prompt_section(self) -> str:
        """Serialize self-model to a compact markdown section for prompts.

        Returns a human-readable summary of Alfred's current state,
        suitable for inclusion in system prompts.
        """
        logger.debug(
            "Serializing self-model to prompt section: interface=%s, session=%s, tools=%d, memory=%s, search=%s",
            self.runtime.interface.value if self.runtime.interface else None,
            self.runtime.session_id,
            len(self.capabilities.tools_available),
            self.capabilities.memory_enabled,
            self.capabilities.search_enabled,
        )
        lines = ["## Alfred Self-Model", ""]

        # Identity
        lines.append(f"**Identity**: {self.identity.name}")
        lines.append(f"**Role**: {self.identity.role}")
        if self.identity.version:
            lines.append(f"**Version**: {self.identity.version}")
        lines.append("")

        # Runtime
        lines.append("**Current State**:")
        if self.runtime.interface:
            lines.append(f"- Interface: {self.runtime.interface.value}")
        if self.runtime.session_id:
            lines.append(f"- Session: {self.runtime.session_id}")
        if self.runtime.daemon_mode:
            lines.append("- Mode: daemon/background")
        else:
            lines.append("- Mode: interactive")
        lines.append("")

        # Capabilities
        lines.append("**Capabilities**:")
        lines.append(f"- Memory: {'enabled' if self.capabilities.memory_enabled else 'disabled'}")
        lines.append(f"- Search: {'enabled' if self.capabilities.search_enabled else 'disabled'}")
        if self.capabilities.tools_available:
            tools_str = ", ".join(self.capabilities.tools_available[:10])
            if len(self.capabilities.tools_available) > 10:
                tools_str += f" (+{len(self.capabilities.tools_available) - 10} more)"
            lines.append(f"- Tools: {tools_str}")
        lines.append("")

        # Context pressure
        lines.append("**Context Pressure**:")
        lines.append(f"- Messages: {self.context_pressure.message_count}")
        lines.append(f"- Memories: {self.context_pressure.memory_count}")
        if self.context_pressure.approximate_tokens:
            lines.append(f"- Approximate tokens: {self.context_pressure.approximate_tokens:,}")
        lines.append("")

        # World
        lines.append("**Environment**:")
        if self.world.working_directory:
            lines.append(f"- Working directory: {self.world.working_directory}")
        if self.world.platform:
            lines.append(f"- Platform: {self.world.platform}")

        return "\n".join(lines)


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

    logger.debug("Building runtime self-model for Alfred instance: %s", alfred)

    # Auto-detect interface from Alfred state
    detected_interface = interface
    if detected_interface is None:
        # Check if Telegram bot is initialized (not None)
        detected_interface = InterfaceType.WEBUI if getattr(alfred, "_telegram_bot", None) is not None else InterfaceType.CLI
        logger.debug("Auto-detected interface: %s", detected_interface.value)

    # Get session ID
    current_session_id = session_id or "cli"

    # Get tools from registry
    tools_available: list[str] = []
    tools_registry = getattr(alfred, "tools", None)
    if tools_registry is not None:
        tool_objects = tools_registry.list_tools()
        # Extract tool names from Tool objects
        tools_available = [tool.name for tool in tool_objects]
        logger.debug("Found %d tools in registry", len(tools_available))
    else:
        logger.debug("No tools registry found on Alfred instance")

    # Get context pressure from context_summary
    context_summary = getattr(alfred, "context_summary", None)
    message_count = 0
    memory_count = 0
    if context_summary is not None:
        message_count = getattr(context_summary, "session_messages", 0)
        memory_count = getattr(context_summary, "memories_count", 0)
        logger.debug("Context pressure from summary: messages=%d, memories=%d", message_count, memory_count)
    else:
        logger.debug("No context_summary found on Alfred instance")

    # Get approximate tokens from token_tracker
    approximate_tokens: int | None = None
    token_tracker = getattr(alfred, "token_tracker", None)
    if token_tracker is not None:
        approximate_tokens = getattr(token_tracker, "total_tokens", None)
        logger.debug("Token tracker found: %s tokens", approximate_tokens)
    else:
        logger.debug("No token_tracker found on Alfred instance")

    # Check if memory/search is enabled via core
    memory_enabled = False
    search_enabled = False
    core = getattr(alfred, "core", None)
    if core is not None:
        memory_store = getattr(core, "memory_store", None)
        memory_enabled = memory_store is not None
        search_enabled = memory_store is not None
        logger.debug("Core found: memory_enabled=%s, search_enabled=%s", memory_enabled, search_enabled)
    else:
        logger.debug("No core found on Alfred instance, memory/search disabled")

    model = RuntimeSelfModel(
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

    logger.debug(
        "Self-model built: interface=%s, session=%s, tools=%d, memory=%s, search=%s, messages=%d, memories=%d, tokens=%s",
        detected_interface.value if detected_interface else None,
        current_session_id,
        len(tools_available),
        memory_enabled,
        search_enabled,
        message_count,
        memory_count,
        approximate_tokens,
    )

    return model
