"""Tool for searching session summaries."""

import json
from collections.abc import AsyncIterator
from datetime import datetime

from pydantic import BaseModel, Field

from src.embeddings.provider import EmbeddingProvider
from src.search import search_session_summaries
from src.session_storage import SessionStorage
from src.type_defs import JsonValue

from .base import Tool, ToolResult


class SearchSessionsToolParams(BaseModel):
    """Parameters for SearchSessionsTool."""

    query: str = Field("", description="Search query to find relevant sessions")
    top_k: int = Field(3, description="Maximum number of results to return")

    class Config:
        extra = "forbid"


class SearchSessionsResultItem(BaseModel):
    """Single search result item."""

    session_id: str
    summary_text: str
    message_count: int
    message_range: list[int]
    timestamp: datetime
    version: int
    similarity: float


class SearchSessionsResult(ToolResult):
    """Result payload for search_sessions."""

    query: str
    top_k: int
    count: int
    results: list[SearchSessionsResultItem] = Field(default_factory=list)


class SearchSessionsTool(Tool):
    """Search session summaries for relevant discussions."""

    name = "search_sessions"
    description = "Search summaries of past conversations"
    param_model = SearchSessionsToolParams

    def __init__(
        self,
        storage: SessionStorage | None = None,
        embedder: EmbeddingProvider | None = None,
        min_similarity: float = 0.3,
    ) -> None:
        super().__init__()
        self.storage = storage
        self.embedder = embedder
        self.min_similarity = min_similarity

    async def execute_stream(self, **kwargs: JsonValue) -> AsyncIterator[str]:
        """Search session summaries and return JSON results."""
        query_value = kwargs.get("query", "")
        top_k_value = kwargs.get("top_k", 3)

        if not isinstance(query_value, str):
            query_value = ""
        if not isinstance(top_k_value, int):
            top_k_value = 3

        query = query_value
        top_k = top_k_value

        if not self.storage or not self.embedder:
            result = SearchSessionsResult(
                success=False,
                error="Error: search_sessions tool not initialized",
                query=query,
                top_k=top_k,
                count=0,
                results=[],
            )
            yield json.dumps(result.model_dump(mode="json"))
            return

        if not query:
            result = SearchSessionsResult(
                success=False,
                error="Error: query is required",
                query="",
                top_k=top_k,
                count=0,
                results=[],
            )
            yield json.dumps(result.model_dump(mode="json"))
            return

        query_embedding = await self.embedder.embed(query)
        matches = await search_session_summaries(
            query_embedding=query_embedding,
            storage=self.storage,
            top_k=top_k,
            min_similarity=self.min_similarity,
        )

        results = [
            SearchSessionsResultItem(
                session_id=match["session_id"],
                summary_text=match["summary"].summary_text,
                message_count=match["summary"].message_count,
                message_range=list(match["summary"].message_range),
                timestamp=match["summary"].timestamp,
                version=match["summary"].version,
                similarity=match["similarity"],
            )
            for match in matches
        ]

        result = SearchSessionsResult(
            success=True,
            error=None,
            query=query,
            top_k=top_k,
            count=len(results),
            results=results,
        )

        yield json.dumps(result.model_dump(mode="json"))
