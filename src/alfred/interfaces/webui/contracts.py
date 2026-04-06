"""Web UI contract Protocols.

These types define the small Alfred surface the Web UI server depends on.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any, Protocol, runtime_checkable

from alfred.agent import ToolEvent
from alfred.session import Session, SessionMeta
from alfred.token_tracker import TokenTracker


@runtime_checkable
class WebUIContextLoader(Protocol):
    """Context loader methods the Web UI server uses."""

    def toggle_section(self, section: str, enabled: bool) -> bool: ...


@runtime_checkable
class WebUISessionManager(Protocol):
    """Session manager methods the Web UI server uses."""

    async def new_session_async(self) -> Session: ...

    async def resume_session_async(self, session_id: str) -> Session: ...

    async def list_sessions_async(self) -> list[SessionMeta]: ...

    def get_current_cli_session(self) -> Session | None: ...

    def start_session(self) -> Session: ...


@runtime_checkable
class WebUICore(Protocol):
    """Core services the Web UI server uses."""

    session_manager: WebUISessionManager

    @property
    def summarizer(self) -> Any | None: ...


@runtime_checkable
class WebUIAlfred(Protocol):
    """Top-level Alfred surface the Web UI server uses."""

    core: WebUICore
    token_tracker: TokenTracker
    context_loader: WebUIContextLoader

    @property
    def model_name(self) -> str: ...

    def chat_stream(
        self,
        message: str,
        tool_callback: Callable[[ToolEvent], None] | None = None,
        session_id: str | None = None,
        persist_partial: bool = False,
        assistant_message_id: str | None = None,
        reuse_user_message: bool = False,
    ) -> AsyncIterator[str]: ...

    async def stop(self) -> None: ...

    async def get_support_snapshot_text(
        self,
        *,
        response_mode: str = "execute",
        arc_id: str | None = None,
    ) -> str | None: ...

    async def get_support_pattern_text(self, pattern_id: str) -> str | None: ...

    async def get_support_update_event_text(self, event_id: str) -> str | None: ...

    async def explain_support_value_text(
        self,
        *,
        registry: str,
        dimension: str,
        response_mode: str,
        arc_id: str | None = None,
    ) -> str | None: ...

    async def build_support_review_text(self, *, mode: str = "on_demand") -> str | None: ...

    async def apply_support_correction_text(self, action: Any) -> str | None: ...

    def sync_token_tracker_from_session(
        self,
        session_id: str | None = None,
    ) -> None: ...
