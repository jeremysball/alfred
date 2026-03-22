"""Integration tests for search_sessions tool.

Tests that the tool:
1. Can be called by the LLM with just a query
2. Properly validates parameters
3. Returns appropriate results when configured
4. Handles errors gracefully
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from alfred.tools.search_sessions import (
    SearchSessionsTool,
    SearchSessionsToolParams,
)


class TestSearchSessionsLLMIntegration:
    """Test that LLM can properly call search_sessions."""

    def test_tool_schema_for_llm(self):
        """Schema should be compatible with OpenAI function calling."""
        tool = SearchSessionsTool()
        schema = tool.get_schema()

        # Verify OpenAI function format
        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "search_sessions"
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]

        params = schema["function"]["parameters"]
        assert params["type"] == "object"
        assert "properties" in params

        # Query should be the primary parameter
        assert "query" in params["properties"]
        assert params["properties"]["query"]["type"] == "string"

        # top_k and messages_per_session should have defaults
        assert "top_k" in params["properties"]
        assert params["properties"]["top_k"]["default"] == 3
        assert "messages_per_session" in params["properties"]
        assert params["properties"]["messages_per_session"]["default"] == 3

    def test_llm_can_call_with_only_query(self):
        """LLM should be able to call with just the query parameter."""
        # Simulate LLM calling with only query
        llm_arguments = {"query": "find my python project session"}

        # Should validate successfully
        params = SearchSessionsToolParams(**llm_arguments)
        assert params.query == "find my python project session"
        assert params.top_k == 3  # default
        assert params.messages_per_session == 3  # default

    def test_llm_can_call_with_all_params(self):
        """LLM should be able to override defaults."""
        llm_arguments = {
            "query": "find my python project session",
            "top_k": 5,
            "messages_per_session": 10
        }

        params = SearchSessionsToolParams(**llm_arguments)
        assert params.query == "find my python project session"
        assert params.top_k == 5
        assert params.messages_per_session == 10

    @pytest.mark.asyncio
    async def test_tool_execution_with_mocked_dependencies(self):
        """Tool should execute successfully with mocked dependencies."""
        # Create mock embedder
        mock_embedder = MagicMock()
        mock_embedder.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        # Create mock store with search results
        mock_store = MagicMock()
        mock_store.search_summaries = AsyncMock(return_value=[
            {
                "summary_id": "sum-1",
                "session_id": "sess-123",
                "summary_text": "Python project discussion",
                "similarity": 0.85
            }
        ])
        mock_store.search_session_messages = AsyncMock(return_value=[
            {
                "message_idx": 0,
                "role": "user",
                "content_snippet": "How do I structure my Python project?",
                "similarity": 0.90
            }
        ])

        # Create mock summarizer
        mock_summarizer = MagicMock()
        mock_summarizer.store = mock_store

        # Create tool with mocked dependencies
        tool = SearchSessionsTool(
            embedder=mock_embedder,
            summarizer=mock_summarizer,
        )

        # Execute with just query (LLM-style call)
        chunks = []
        async for chunk in tool.execute_stream(query="python project"):
            chunks.append(chunk)

        result = "".join(chunks)

        # Verify results
        assert "Python project discussion" in result
        assert "sess-123" in result
        assert "How do I structure my Python project?" in result

        # Verify search was called with correct parameters
        mock_store.search_summaries.assert_called_once()
        call_args = mock_store.search_summaries.call_args
        assert call_args[0][1] == 3  # default top_k

    @pytest.mark.asyncio
    async def test_tool_handles_no_results_gracefully(self):
        """Tool should handle case when no sessions found."""
        mock_embedder = MagicMock()
        mock_embedder.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        mock_store = MagicMock()
        mock_store.search_summaries = AsyncMock(return_value=[])

        mock_summarizer = MagicMock()
        mock_summarizer.store = mock_store

        tool = SearchSessionsTool(
            embedder=mock_embedder,
            summarizer=mock_summarizer,
        )

        chunks = []
        async for chunk in tool.execute_stream(query="nonexistent topic"):
            chunks.append(chunk)

        result = "".join(chunks)
        assert "No relevant sessions found" in result

    @pytest.mark.asyncio
    async def test_tool_respects_top_k_parameter(self):
        """Tool should respect top_k when specified by LLM."""
        mock_embedder = MagicMock()
        mock_embedder.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        mock_store = MagicMock()
        mock_store.search_summaries = AsyncMock(return_value=[])

        mock_summarizer = MagicMock()
        mock_summarizer.store = mock_store

        tool = SearchSessionsTool(
            embedder=mock_embedder,
            summarizer=mock_summarizer,
        )

        # Call with custom top_k
        async for _ in tool.execute_stream(query="test", top_k=7):
            pass

        # Verify search was called with top_k=7
        mock_store.search_summaries.assert_called_once()
        call_args = mock_store.search_summaries.call_args
        assert call_args[0][1] == 7

    @pytest.mark.asyncio
    async def test_tool_respects_messages_per_session(self):
        """Tool should respect messages_per_session parameter."""
        mock_embedder = MagicMock()
        mock_embedder.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        mock_store = MagicMock()
        mock_store.search_summaries = AsyncMock(return_value=[
            {
                "summary_id": "sum-1",
                "session_id": "sess-123",
                "summary_text": "Test session",
                "similarity": 0.85
            }
        ])
        mock_store.search_session_messages = AsyncMock(return_value=[])

        mock_summarizer = MagicMock()
        mock_summarizer.store = mock_store

        tool = SearchSessionsTool(
            embedder=mock_embedder,
            summarizer=mock_summarizer,
        )

        # Call with custom messages_per_session
        async for _ in tool.execute_stream(query="test", messages_per_session=5):
            pass

        # Verify message search was called with correct parameter
        mock_store.search_session_messages.assert_called_once()
        call_args = mock_store.search_session_messages.call_args
        assert call_args[0][2] == 5  # messages_per_session


class TestSearchSessionsErrorHandling:
    """Test error handling in search_sessions."""

    @pytest.mark.asyncio
    async def test_empty_query_error(self):
        """Should error when query is empty."""
        tool = SearchSessionsTool()

        chunks = []
        async for chunk in tool.execute_stream(query=""):
            chunks.append(chunk)

        result = "".join(chunks)
        assert "Please provide a search query" in result

    @pytest.mark.asyncio
    async def test_missing_embedder_error(self):
        """Should error when embedder not configured."""
        tool = SearchSessionsTool()

        chunks = []
        async for chunk in tool.execute_stream(query="test search"):
            chunks.append(chunk)

        result = "".join(chunks)
        assert "Embedder not configured" in result

    @pytest.mark.asyncio
    async def test_missing_store_error(self):
        """Should error when store not configured."""
        mock_embedder = MagicMock()
        mock_embedder.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        tool = SearchSessionsTool(embedder=mock_embedder)

        chunks = []
        async for chunk in tool.execute_stream(query="test search"):
            chunks.append(chunk)

        result = "".join(chunks)
        assert "Session search not configured" in result


class TestSearchSessionsViaAgent:
    """Test search_sessions integration with Agent."""

    @pytest.mark.asyncio
    async def test_tool_registered_with_registry(self):
        """Tool should be properly registered in tool registry."""
        from unittest.mock import MagicMock

        from alfred.tools import get_registry, register_builtin_tools

        # Create mock dependencies
        mock_session_manager = MagicMock()
        mock_embedder = MagicMock()
        mock_llm_client = MagicMock()
        mock_summarizer = MagicMock()

        # Register tools with mocked dependencies
        register_builtin_tools(
            session_manager=mock_session_manager,
            embedder=mock_embedder,
            llm_client=mock_llm_client,
            summarizer=mock_summarizer,
        )

        registry = get_registry()
        tool = registry.get("search_sessions")

        assert tool is not None, "search_sessions tool should be registered"
        assert tool.name == "search_sessions"

    def test_validate_and_run_method(self):
        """Tool should have validate_and_run method for agent use."""
        tool = SearchSessionsTool()

        # Should have validate_and_run method
        assert hasattr(tool, 'validate_and_run')
        assert hasattr(tool, 'validate_and_run_stream')

    @pytest.mark.asyncio
    async def test_tool_filters_summaries_using_normalized_similarity(self):
        """The best semantic match should survive the similarity threshold."""
        mock_embedder = MagicMock()
        mock_embedder.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        mock_store = MagicMock()
        mock_store.search_summaries = AsyncMock(
            return_value=[
                {
                    "summary_id": "sum-close",
                    "session_id": "sess-close",
                    "summary_text": "Best semantic match",
                    "similarity": 0.95,
                },
                {
                    "summary_id": "sum-far",
                    "session_id": "sess-far",
                    "summary_text": "Worse semantic match",
                    "similarity": 0.05,
                },
            ]
        )
        mock_store.search_session_messages = AsyncMock(return_value=[])

        mock_summarizer = MagicMock()
        mock_summarizer.store = mock_store

        tool = SearchSessionsTool(
            embedder=mock_embedder,
            summarizer=mock_summarizer,
        )

        chunks = []
        async for chunk in tool.execute_stream(query="semantic match"):
            chunks.append(chunk)

        result = "".join(chunks)

        assert "Best semantic match" in result
        assert "Worse semantic match" not in result
        assert "Relevance: 0.95" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
