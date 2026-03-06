"""Tests for search_sessions tool and session summary generation."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from alfred.session import Message, Role, Session, SessionMeta
from alfred.session_storage import SessionStorage
from alfred.tools.search_sessions import SearchSessionsTool, SessionSummarizer


@pytest.fixture
def mock_embedder():
    """Create mock embedder that returns predictable embeddings."""
    embedder = MagicMock()
    embedder.embed_batch = AsyncMock(return_value=[[0.1] * 384, [0.2] * 384])
    embedder.embed = AsyncMock(return_value=[0.5] * 384)
    return embedder


@pytest.fixture
def temp_storage_dir(tmp_path):
    """Create temporary storage directory."""
    return tmp_path / "sessions"


@pytest.fixture
def session_storage(mock_embedder, temp_storage_dir):
    """Create SessionStorage instance."""
    return SessionStorage(mock_embedder, data_dir=temp_storage_dir.parent)


@pytest.fixture
def sample_session(session_storage):
    """Create a sample session with messages."""
    session = Session(
        meta=SessionMeta(
            session_id="sess_test123",
            created_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC),
            last_active=datetime(2026, 3, 1, 11, 0, 0, tzinfo=UTC),
            status="idle",
            current_count=3,
        ),
        messages=[
            Message(
                idx=0,
                role=Role.USER,
                content="How do I implement the search_sessions tool?",
                timestamp=datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC),
                embedding=[0.1] * 384,
            ),
            Message(
                idx=1,
                role=Role.ASSISTANT,
                content="I'll help you implement the search_sessions tool with two-stage retrieval.",
                timestamp=datetime(2026, 3, 1, 10, 5, 0, tzinfo=UTC),
                embedding=[0.2] * 384,
            ),
            Message(
                idx=2,
                role=Role.USER,
                content="Should I use LLM-generated summaries?",
                timestamp=datetime(2026, 3, 1, 10, 10, 0, tzinfo=UTC),
                embedding=[0.3] * 384,
            ),
        ],
    )
    return session


class TestSessionSummarizer:
    """Tests for SessionSummarizer class."""

    @pytest.mark.asyncio
    async def test_generate_summary_with_llm(self, sample_session, mock_embedder):
        """Test generating session summary using LLM."""
        mock_llm = AsyncMock()
        mock_llm.generate_summary = AsyncMock(return_value="Discussion about implementing search_sessions tool with LLM summaries")

        summarizer = SessionSummarizer(llm_client=mock_llm, embedder=mock_embedder)

        summary = await summarizer.generate_summary(sample_session)

        assert summary.text == "Discussion about implementing search_sessions tool with LLM summaries"
        assert summary.session_id == "sess_test123"
        assert summary.message_count == 3
        assert summary.created_at == sample_session.meta.created_at
        assert summary.last_active == sample_session.meta.last_active
        # Embedding should be generated
        assert summary.embedding is not None
        assert len(summary.embedding) == 384

    @pytest.mark.asyncio
    async def test_save_and_load_summary(self, sample_session, mock_embedder, temp_storage_dir):
        """Test saving and loading summary to/from summary.json."""
        mock_llm = AsyncMock()
        mock_llm.generate_summary = AsyncMock(return_value="Test summary")

        summarizer = SessionSummarizer(llm_client=mock_llm, embedder=mock_embedder)
        summary = await summarizer.generate_summary(sample_session)

        # Save summary
        session_dir = temp_storage_dir / "sess_test123"
        session_dir.mkdir(parents=True)
        await summarizer.save_summary(summary, session_dir)

        # Verify file exists
        summary_path = session_dir / "summary.json"
        assert summary_path.exists()

        # Load and verify
        loaded = await summarizer.load_summary(session_dir)
        assert loaded is not None
        assert loaded.text == "Test summary"
        assert loaded.session_id == "sess_test123"

    @pytest.mark.asyncio
    async def test_load_missing_summary(self, mock_embedder, temp_storage_dir):
        """Test loading summary when file doesn't exist."""
        summarizer = SessionSummarizer(llm_client=AsyncMock(), embedder=mock_embedder)

        loaded = await summarizer.load_summary(temp_storage_dir / "nonexistent")

        assert loaded is None


class TestSearchSessionsTool:
    """Tests for SearchSessionsTool."""

    @pytest.fixture
    def search_tool(self, mock_embedder, temp_storage_dir):
        """Create SearchSessionsTool instance."""
        mock_llm = AsyncMock()
        mock_llm.generate_summary = AsyncMock(return_value="Test summary")

        storage = SessionStorage(mock_embedder, data_dir=temp_storage_dir.parent)
        tool = SearchSessionsTool(
            storage=storage,
            embedder=mock_embedder,
            llm_client=mock_llm,
        )
        return tool

    @pytest.mark.asyncio
    async def test_tool_initialization(self, search_tool):
        """Test tool is properly initialized."""
        assert search_tool.name == "search_sessions"
        assert "conversation" in search_tool.description.lower() or "session" in search_tool.description.lower()

    @pytest.mark.asyncio
    async def test_execute_stream_no_query(self, search_tool):
        """Test error when no query provided."""
        results = []
        async for chunk in search_tool.execute_stream(query=""):
            results.append(chunk)

        result = "".join(results)
        assert "Error" in result or "query" in result.lower()

    @pytest.mark.asyncio
    async def test_stage_one_session_search(self, search_tool, temp_storage_dir, mock_embedder):
        """Test stage 1: finding relevant sessions."""
        # Create test sessions with summaries
        for i, session_id in enumerate(["sess_aaa", "sess_bbb", "sess_ccc"]):
            session_dir = temp_storage_dir / session_id
            session_dir.mkdir(parents=True)

            # Create meta.json
            meta = {
                "session_id": session_id,
                "created_at": datetime(2026, 3, i + 1, tzinfo=UTC).isoformat(),
                "last_active": datetime(2026, 3, i + 1, tzinfo=UTC).isoformat(),
                "status": "idle",
                "current_count": 2,
                "archive_count": 0,
            }
            (session_dir / "meta.json").write_text(json.dumps(meta))

            # Create summary.json
            summary = {
                "session_id": session_id,
                "text": f"Session about topic {i}",
                "embedding": [0.1 * (i + 1)] * 384,
                "message_count": 2,
                "created_at": meta["created_at"],
                "last_active": meta["last_active"],
            }
            (session_dir / "summary.json").write_text(json.dumps(summary))

        # Mock query embedding
        mock_embedder.embed = AsyncMock(return_value=[0.15] * 384)

        # Test finding relevant sessions
        sessions = await search_tool._find_relevant_sessions("topic 1", top_k=2)

        assert len(sessions) <= 2
        assert all(s["session_id"] in ["sess_aaa", "sess_bbb", "sess_ccc"] for s in sessions)

    @pytest.mark.asyncio
    async def test_stage_two_message_search(self, search_tool, temp_storage_dir, mock_embedder):
        """Test stage 2: searching messages within a session."""
        # Create a session with messages
        session_dir = temp_storage_dir / "sess_msg_test"
        session_dir.mkdir(parents=True)

        # Create meta.json
        meta = {
            "session_id": "sess_msg_test",
            "created_at": datetime(2026, 3, 1, tzinfo=UTC).isoformat(),
            "last_active": datetime(2026, 3, 1, tzinfo=UTC).isoformat(),
            "status": "idle",
            "current_count": 3,
            "archive_count": 0,
        }
        (session_dir / "meta.json").write_text(json.dumps(meta))

        # Create current.jsonl with messages
        messages = [
            {
                "idx": 0,
                "role": "user",
                "content": "How do I search sessions?",
                "timestamp": datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC).isoformat(),
                "embedding": [0.1] * 384,
            },
            {
                "idx": 1,
                "role": "assistant",
                "content": "Use the search_sessions tool with a query.",
                "timestamp": datetime(2026, 3, 1, 10, 1, 0, tzinfo=UTC).isoformat(),
                "embedding": [0.2] * 384,
            },
            {
                "idx": 2,
                "role": "user",
                "content": "What about memories?",
                "timestamp": datetime(2026, 3, 1, 10, 2, 0, tzinfo=UTC).isoformat(),
                "embedding": [0.3] * 384,
            },
        ]
        with open(session_dir / "current.jsonl", "w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        # Mock query embedding to match first message
        mock_embedder.embed = AsyncMock(return_value=[0.1] * 384)

        # Search messages
        results = await search_tool._search_session_messages("sess_msg_test", "search sessions", top_k=2)

        assert len(results) <= 2
        # First result should be most relevant
        assert "search" in results[0]["content"].lower()

    @pytest.mark.asyncio
    async def test_full_search_integration(self, search_tool, temp_storage_dir, mock_embedder):
        """Test complete two-stage search flow."""
        # Create a complete session
        session_dir = temp_storage_dir / "sess_full_test"
        session_dir.mkdir(parents=True)

        # Create meta.json
        meta = {
            "session_id": "sess_full_test",
            "created_at": datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC).isoformat(),
            "last_active": datetime(2026, 3, 1, 11, 0, 0, tzinfo=UTC).isoformat(),
            "status": "idle",
            "current_count": 2,
            "archive_count": 0,
        }
        (session_dir / "meta.json").write_text(json.dumps(meta))

        # Create summary.json
        summary = {
            "session_id": "sess_full_test",
            "text": "Discussion about memory system implementation",
            "embedding": [0.1] * 384,
            "message_count": 2,
            "created_at": meta["created_at"],
            "last_active": meta["last_active"],
        }
        (session_dir / "summary.json").write_text(json.dumps(summary))

        # Create messages
        messages = [
            {
                "idx": 0,
                "role": "user",
                "content": "How do I implement memory search?",
                "timestamp": datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC).isoformat(),
                "embedding": [0.1] * 384,
            },
            {
                "idx": 1,
                "role": "assistant",
                "content": "Use the MemorySearcher class with embeddings.",
                "timestamp": datetime(2026, 3, 1, 10, 5, 0, tzinfo=UTC).isoformat(),
                "embedding": [0.2] * 384,
            },
        ]
        with open(session_dir / "current.jsonl", "w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        # Mock embeddings
        mock_embedder.embed = AsyncMock(return_value=[0.1] * 384)

        # Execute search
        results = []
        async for chunk in search_tool.execute_stream(query="memory search implementation", top_k=1):
            results.append(chunk)

        result_text = "".join(results)

        # Verify hierarchical format
        assert "Session:" in result_text
        assert "sess_full_test" in result_text
        assert "2026-03-01" in result_text
        assert "memory search" in result_text.lower()
        assert "MemorySearcher" in result_text or "embeddings" in result_text.lower()

    @pytest.mark.asyncio
    async def test_no_sessions_found(self, search_tool, mock_embedder):
        """Test behavior when no sessions match."""
        mock_embedder.embed = AsyncMock(return_value=[0.99] * 384)  # Different from all

        results = []
        async for chunk in search_tool.execute_stream(query="xyz nonexistent topic", top_k=3):
            results.append(chunk)

        result_text = "".join(results)
        assert "No relevant sessions found" in result_text or "No sessions" in result_text

    @pytest.mark.asyncio
    async def test_configurable_top_k(self, search_tool, temp_storage_dir, mock_embedder):
        """Test that top_k is configurable."""
        # Create multiple sessions
        for i in range(5):
            session_dir = temp_storage_dir / f"sess_{i}"
            session_dir.mkdir(parents=True)

            meta = {
                "session_id": f"sess_{i}",
                "created_at": datetime(2026, 3, i + 1, tzinfo=UTC).isoformat(),
                "last_active": datetime(2026, 3, i + 1, tzinfo=UTC).isoformat(),
                "status": "idle",
                "current_count": 1,
                "archive_count": 0,
            }
            (session_dir / "meta.json").write_text(json.dumps(meta))

            summary = {
                "session_id": f"sess_{i}",
                "text": f"Session {i} content",
                "embedding": [0.1 * (i + 1)] * 384,
                "message_count": 1,
                "created_at": meta["created_at"],
                "last_active": meta["last_active"],
            }
            (session_dir / "summary.json").write_text(json.dumps(summary))

        mock_embedder.embed = AsyncMock(return_value=[0.3] * 384)

        # Search with different top_k values
        for top_k in [1, 3, 5]:
            results = []
            async for chunk in search_tool.execute_stream(query="session", top_k=top_k):
                results.append(chunk)

            result_text = "".join(results)
            # Should not error with different top_k values
            assert "Error" not in result_text or "No relevant" in result_text


class TestSearchSessionsIntegration:
    """Integration tests for search_sessions with real components."""

    @pytest.mark.asyncio
    async def test_end_to_end_with_llm_summary(self, mock_embedder, temp_storage_dir):
        """Test complete flow: create session → generate summary → search."""
        # This test demonstrates the full workflow

        # Setup storage
        storage = SessionStorage(mock_embedder, data_dir=temp_storage_dir.parent)

        # Create session with messages
        session = Session(
            meta=SessionMeta(
                session_id="sess_integration",
                created_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC),
                last_active=datetime(2026, 3, 1, 11, 0, 0, tzinfo=UTC),
                status="idle",
                current_count=2,
            ),
            messages=[
                Message(
                    idx=0,
                    role=Role.USER,
                    content="Tell me about the memory system",
                    timestamp=datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC),
                    embedding=[0.1] * 384,
                ),
                Message(
                    idx=1,
                    role=Role.ASSISTANT,
                    content="The memory system has three components: files, memories, and session archive.",
                    timestamp=datetime(2026, 3, 1, 10, 5, 0, tzinfo=UTC),
                    embedding=[0.2] * 384,
                ),
            ],
        )

        # Save session components (meta and messages)
        storage.save_meta(session.meta)
        for msg in session.messages:
            await storage.append_message(session.meta.session_id, msg)

        # Mock LLM for summary generation
        mock_llm = AsyncMock()
        mock_llm.generate_summary = AsyncMock(
            return_value="Overview of the three-component memory system"
        )

        # Generate and save summary
        summarizer = SessionSummarizer(llm_client=mock_llm, embedder=mock_embedder)
        summary = await summarizer.generate_summary(session)
        session_dir = temp_storage_dir / "sess_integration"
        await summarizer.save_summary(summary, session_dir)

        # Create search tool
        tool = SearchSessionsTool(
            storage=storage,
            embedder=mock_embedder,
            llm_client=mock_llm,
        )

        # Mock query embedding
        mock_embedder.embed = AsyncMock(return_value=[0.15] * 384)

        # Search
        results = []
        async for chunk in tool.execute_stream(query="memory system components", top_k=1):
            results.append(chunk)

        result_text = "".join(results)

        # Verify results
        assert "sess_integration" in result_text
        assert "memory" in result_text.lower()
        assert "Session:" in result_text
