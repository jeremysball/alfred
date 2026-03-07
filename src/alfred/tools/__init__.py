"""Tool registry and discovery."""

import logging
from typing import Any

from alfred.tools.base import Tool

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

    def get_schemas(self) -> list[dict[str, Any]]:
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
def get_tool_schemas() -> list[dict[str, Any]]:
    """Get schemas for all registered tools."""
    return get_registry().get_schemas()


# Auto-discover and register built-in tools
def register_builtin_tools(
    memory_store: Any = None,
    scheduler: Any = None,
    config: Any = None,
    session_manager: Any = None,
    embedder: Any = None,
    llm_client: Any = None,
    summarizer: Any = None,
) -> None:
    """Register all built-in tools.

    Args:
        memory_store: Optional MemoryStore to inject into tools that need it
        scheduler: Optional CronScheduler to inject into tools that need it
        config: Optional Config for tool configuration
        session_manager: Optional SessionManager for session-related tools
        embedder: Optional EmbeddingClient for semantic search tools
        llm_client: Optional LLM client for summary generation
        summarizer: Optional SessionSummarizer for session summarization
    """
    from alfred.tools.approve_job import ApproveJobTool
    from alfred.tools.bash import BashTool
    from alfred.tools.edit import EditTool
    from alfred.tools.forget import ForgetTool
    from alfred.tools.list_jobs import ListJobsTool
    from alfred.tools.read import ReadTool
    from alfred.tools.reject_job import RejectJobTool
    from alfred.tools.remember import RememberTool
    from alfred.tools.schedule_job import ScheduleJobTool
    from alfred.tools.search_memories import SearchMemoriesTool
    from alfred.tools.search_sessions import SearchSessionsTool
    from alfred.tools.update_memory import UpdateMemoryTool
    from alfred.tools.write import WriteTool

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
    if session_manager and embedder:
        search_sessions_tool = SearchSessionsTool(
            session_manager=session_manager,
            embedder=embedder,
            llm_client=llm_client,
            summarizer=summarizer,
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
