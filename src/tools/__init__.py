"""Tool registry and discovery."""

import logging
from typing import TYPE_CHECKING

from src.tools.base import Tool
from src.type_defs import ToolSchema

if TYPE_CHECKING:
    from src.config import Config
    from src.cron.scheduler import CronScheduler
    from src.embeddings.provider import EmbeddingProvider
    from src.llm import LLMProvider
    from src.memory.base import MemoryStore
    from src.session_storage import SessionStorage

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool instance."""
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting")

        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        """List all registered tools."""
        return list(self._tools.values())

    def get_schemas(self) -> list[ToolSchema]:
        """Get JSON schemas for all tools."""
        return [tool.get_schema() for tool in self._tools.values()]

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()

    def __contains__(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)


# Global registry instance
_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    """Get the global tool registry (creates if needed)."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_tool(tool: Tool) -> Tool:
    """Register a tool instance in the global registry.

    Usage:
        register_tool(ReadTool())
    """
    registry = get_registry()
    registry.register(tool)
    return tool


def clear_registry() -> None:
    """Clear the global registry (mainly for testing)."""
    global _registry
    _registry = None


# Convenience function to get all tool schemas
def get_tool_schemas() -> list[ToolSchema]:
    """Get schemas for all registered tools."""
    return get_registry().get_schemas()


# Auto-discover and register built-in tools
def register_builtin_tools(
    memory_store: "MemoryStore | None" = None,
    scheduler: "CronScheduler | None" = None,
    config: "Config | None" = None,
    session_storage: "SessionStorage | None" = None,
    embedder: "EmbeddingProvider | None" = None,
    llm_client: "LLMProvider | None" = None,
) -> None:
    """Register all built-in tools.

    Args:
        memory_store: Optional MemoryStore to inject into tools that need it
        scheduler: Optional CronScheduler to inject into tools that need it
        config: Optional Config for tool configuration
        session_storage: Optional SessionStorage for session-related tools
        embedder: Optional EmbeddingClient for semantic search tools
        llm_client: Optional LLM client for summary generation
    """
    from src.tools.approve_job import ApproveJobTool
    from src.tools.bash import BashTool
    from src.tools.edit import EditTool
    from src.tools.forget import ForgetTool
    from src.tools.list_jobs import ListJobsTool
    from src.tools.read import ReadTool
    from src.tools.reject_job import RejectJobTool
    from src.tools.remember import RememberTool
    from src.tools.schedule_job import ScheduleJobTool
    from src.tools.search_memories import SearchMemoriesTool
    from src.tools.search_sessions import SearchSessionsTool
    from src.tools.update_memory import UpdateMemoryTool
    from src.tools.write import WriteTool

    register_tool(ReadTool())
    register_tool(WriteTool())
    register_tool(EditTool())
    register_tool(BashTool())

    # Register remember tool with memory store injected
    remember_tool = RememberTool()
    if memory_store:
        remember_tool.set_memory_store(memory_store)
    register_tool(remember_tool)

    # Register search_memories tool with memory store injected
    search_tool = SearchMemoriesTool()
    if memory_store:
        search_tool.set_memory_store(memory_store)
    register_tool(search_tool)

    # Register update_memory tool with memory store injected
    update_tool = UpdateMemoryTool()
    if memory_store:
        update_tool.set_memory_store(memory_store)
    register_tool(update_tool)

    # Register forget tool with memory store injected
    forget_tool = ForgetTool()
    if memory_store:
        forget_tool.set_memory_store(memory_store)
    register_tool(forget_tool)

    # Register search_sessions tool with dependencies injected
    search_sessions_tool = SearchSessionsTool(
        storage=session_storage,
        embedder=embedder,
    )
    register_tool(search_sessions_tool)
    logger.debug("Registered search_sessions tool")

    # Register cron tools with scheduler injected
    if scheduler:
        register_tool(ScheduleJobTool(scheduler=scheduler, config=config))
        register_tool(ListJobsTool(scheduler=scheduler))
        register_tool(ApproveJobTool(scheduler=scheduler))
        register_tool(RejectJobTool(scheduler=scheduler))

    logger.info(f"Registered {len(get_registry())} built-in tools")
