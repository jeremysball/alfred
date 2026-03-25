"""Runtime self-model for Alfred.

An internal-only snapshot describing Alfred's current state, identity,
capabilities, and environment. Used for self-awareness in prompt assembly.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


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
