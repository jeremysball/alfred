"""Tool for searching memories in the unified memory store."""

from collections.abc import AsyncIterator

from .base import Tool


class SearchMemoriesTool(Tool):
    """Search through saved memories for relevant information."""
    
    name = "search_memories"
    description = "Search through your memory store for relevant information"
    
    def __init__(self, memory_store=None):
        super().__init__()
        self._memory_store = memory_store
    
    def set_memory_store(self, memory_store):
        """Set the memory store after initialization."""
        self._memory_store = memory_store
    
    def execute(
        self,
        query: str = "",
        entry_id: str = "",
        top_k: int = 5,
    ) -> str:
        """Search memories (sync wrapper - use execute_stream).
        
        Args:
            query: Search query to find relevant memories
            entry_id: Direct lookup by memory ID
            top_k: Maximum number of results to return
        
        Returns:
            Error message directing to use async method
        """
        return "Error: SearchMemoriesTool must be called via execute_stream in async context"
    
    async def execute_stream(
        self,
        query: str = "",
        entry_id: str = "",
        top_k: int = 5,
    ) -> AsyncIterator[str]:
        """Search memories and return formatted results.
        
        Args:
            query: Search query to find relevant memories (semantic search)
            entry_id: Direct lookup by memory ID (bypasses search)
            top_k: Maximum number of results to return (ignored if entry_id provided)
        
        Yields:
            Formatted search results
        """
        if not self._memory_store:
            yield "Error: Memory store not initialized"
            return
        
        # Direct ID lookup takes precedence
        if entry_id:
            try:
                entry = await self._memory_store.get_by_id(entry_id)
                if not entry:
                    yield f"No memory found with ID: {entry_id}"
                    return
                
                date_str = entry.timestamp.strftime("%Y-%m-%d")
                result = f"- [{date_str}] {entry.content} (importance: {entry.importance:.1f}, id: {entry.entry_id})"
                yield result
                return
            except Exception as e:
                yield f"Error retrieving memory: {e}"
                return
        
        # Semantic search
        if not query:
            yield "Error: Provide either query or entry_id"
            return
        
        try:
            results = await self._memory_store.search(query, top_k=top_k)
            
            if not results:
                yield "No relevant memories found."
                return
            
            lines = []
            for entry in results:
                date_str = entry.timestamp.strftime("%Y-%m-%d")
                lines.append(
                    f"- [{date_str}] {entry.content} "
                    f"(importance: {entry.importance:.1f}, id: {entry.entry_id})"
                )
            
            yield "\n".join(lines)
        except Exception as e:
            yield f"Error searching memories: {e}"
