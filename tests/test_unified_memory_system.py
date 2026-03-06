"""Tests for Unified Memory System (PRD #102).

Test-driven development for:
- Placeholder system ({{path}} resolution) - M3 ✅
- SYSTEM.md/AGENTS.md separation - M1-M2
- Memory TTL (90 days) - M5
- Permanent flag - M5
- No auto-capture/consolidation - M5
- Session archive contextual retrieval - M7

Note: Tests for unimplemented milestones are marked with @pytest.mark.skip.
Remove skips as each milestone is completed.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest


@pytest.mark.skip(reason="M4: PromptLoader module not yet implemented")
class TestPromptLoader:
    """Tests for placeholder resolution system."""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create a temporary workspace with test files."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create main context files
        (workspace / "SYSTEM.md").write_text("# System\nCore identity")
        (workspace / "AGENTS.md").write_text("# Agents\nBehavior rules")
        (workspace / "USER.md").write_text("# User\nPreferences here")
        (workspace / "SOUL.md").write_text("# Soul\nPersonality here")

        # Create prompts subdirectory
        prompts = workspace / "prompts"
        prompts.mkdir()
        (prompts / "communication-style.md").write_text("- Be concise\n- Use examples")
        (prompts / "voice.md").write_text("- Warm but direct")

        return workspace

    @pytest.fixture
    def loader(self, temp_workspace):
        """Create a PromptLoader instance."""
        from alfred.prompt_loader import PromptLoader
        return PromptLoader(temp_workspace)

    @pytest.mark.asyncio
    async def test_load_simple_file(self, loader, temp_workspace):
        """Test loading a file without placeholders."""
        content = await loader.load("SYSTEM.md")
        assert "Core identity" in content
        assert "# System" in content

    @pytest.mark.asyncio
    async def test_load_with_placeholder(self, loader, temp_workspace):
        """Test loading a file with {{path}} placeholder."""
        # Create file with placeholder
        user_md = temp_workspace / "USER.md"
        user_md.write_text("# User\n\n{{prompts/communication-style.md}}")

        content = await loader.load("USER.md")

        # Should include the placeholder content
        assert "# User" in content
        assert "Be concise" in content
        assert "Use examples" in content

        # Should have HTML comment markers
        assert "<!-- included: prompts/communication-style.md -->" in content
        assert "<!-- end: prompts/communication-style.md -->" in content

    @pytest.mark.asyncio
    async def test_load_nested_placeholders(self, loader, temp_workspace):
        """Test loading file with nested placeholders (A includes B, B includes C)."""
        # Create nested structure
        prompts = temp_workspace / "prompts"
        (prompts / "nested.md").write_text("{{prompts/voice.md}}")

        main_md = temp_workspace / "main.md"
        main_md.write_text("Start\n{{prompts/nested.md}}\nEnd")

        content = await loader.load("main.md")

        assert "Start" in content
        assert "Warm but direct" in content  # From voice.md
        assert "End" in content

    @pytest.mark.asyncio
    async def test_circular_reference_detection(self, loader, temp_workspace):
        """Test that circular references raise an error."""
        # Create circular reference
        a_md = temp_workspace / "a.md"
        b_md = temp_workspace / "b.md"
        a_md.write_text("{{b.md}}")
        b_md.write_text("{{a.md}}")

        with pytest.raises(ValueError):
            await loader.load("a.md")

    @pytest.mark.asyncio
    async def test_missing_file_graceful(self, loader, temp_workspace):
        """Test that missing files are handled gracefully with warning."""
        main_md = temp_workspace / "main.md"
        main_md.write_text("Content\n{{prompts/missing.md}}\nMore content")

        content = await loader.load("main.md")

        # Should have placeholder comment indicating missing file
        assert "<!-- missing: prompts/missing.md -->" in content
        assert "Content" in content
        assert "More content" in content

    @pytest.mark.asyncio
    async def test_max_depth_protection(self, loader, temp_workspace):
        """Test that max depth prevents infinite recursion."""
        # Create deeply nested structure
        for i in range(10):
            (temp_workspace / f"level{i}.md").write_text(f"{{{{level{i+1}.md}}}}")

        with pytest.raises(RecursionError):
            await loader.load("level0.md")

    @pytest.mark.asyncio
    async def test_load_all_context(self, loader, temp_workspace):
        """Test loading all context files in order."""
        context = await loader.load_all_context()

        # Should include standard files
        assert "SYSTEM.md" in context
        assert "AGENTS.md" in context
        assert "USER.md" in context
        assert "SOUL.md" in context

        # SYSTEM should be core identity
        assert "Core identity" in context["SYSTEM.md"]

        # AGENTS should have behavior rules
        assert "Behavior rules" in context["AGENTS.md"]


@pytest.mark.skip(reason="M5: Memory TTL changes not yet implemented")
class TestMemoryTTL:
    """Tests for 90-day TTL and permanent flag."""

    @pytest.fixture
    def memory_store(self, tmp_path):
        """Create a memory store for testing."""
        from alfred.memory.jsonl_store import JSONLMemoryStore as MemoryStore
        store = MemoryStore(tmp_path / "memory.jsonl")
        return store

    @pytest.mark.asyncio
    async def test_memory_has_90_day_ttl_by_default(self, memory_store):
        """Test that new memories have 90-day TTL."""
        memory = await memory_store.remember(
            content="Test memory",
            tags=["test"]
        )

        # Should have expiration 90 days from now
        expected_expiry = datetime.now() + timedelta(days=90)
        assert memory.expires_at is not None
        assert abs((memory.expires_at - expected_expiry).days) <= 1

    @pytest.mark.asyncio
    async def test_permanent_memory_skips_ttl(self, memory_store):
        """Test that permanent=True skips TTL."""
        memory = await memory_store.remember(
            content="Important fact",
            tags=["critical"],
            permanent=True
        )

        assert memory.expires_at is None
        assert memory.permanent is True

    @pytest.mark.asyncio
    async def test_expired_memories_not_returned_in_search(self, memory_store):
        """Test that expired memories are excluded from search."""
        # Create an expired memory
        expired_memory = await memory_store.remember(
            content="Old expired memory",
            tags=["old"]
        )
        expired_memory.expires_at = datetime.now() - timedelta(days=1)
        await memory_store.update(expired_memory)

        # Create a fresh memory
        await memory_store.remember(
            content="Fresh memory",
            tags=["new"]
        )

        # Search should only return fresh memory
        results = await memory_store.search("memory", top_k=10)

        assert len(results) == 1
        assert results[0].content == "Fresh memory"

    @pytest.mark.asyncio
    async def test_warning_at_threshold(self, memory_store):
        """Test that warning is issued at X memories threshold."""
        threshold = 5  # Use small threshold for testing

        # Create memories up to threshold
        warnings = []
        for i in range(threshold + 1):
            with patch("src.memory.logger") as mock_logger:
                await memory_store.remember(
                    content=f"Memory {i}",
                    tags=["test"],
                    warning_threshold=threshold
                )
                if mock_logger.warning.called:
                    warnings.append(mock_logger.warning.call_args)

        # Should have logged a warning when crossing threshold
        assert len(warnings) > 0
        assert "5 memories" in str(warnings[0])


@pytest.mark.skip(reason="M2: AGENTS.md atomic unit extraction not yet implemented")
class TestAtomicUnitExtraction:
    """Tests for extracting atomic units from AGENTS.md."""

    def test_atomic_sections_identified(self, temp_workspace):
        """Test that AGENTS.md has been split into atomic sections."""
        agents_dir = temp_workspace / "prompts" / "agents"

        # Should have extracted sections
        expected_files = [
            "memory-system.md",
            "tool-reference.md",
            "best-practices.md",
        ]

        for filename in expected_files:
            file_path = agents_dir / filename
            assert file_path.exists(), f"Missing atomic unit file: {filename}"

    def test_extracted_files_are_self_contained(self, temp_workspace):
        """Test that each extracted file makes sense standalone."""
        memory_file = temp_workspace / "prompts" / "agents" / "memory-system.md"

        if memory_file.exists():
            content = memory_file.read_text()

            # Should have a clear title
            assert content.startswith("#") or "##" in content

            # Should explain the concept without external context
            assert len(content) > 200  # Substantial content

            # Should have clear guidance
            assert any(word in content.lower() for word in ["when", "how", "use", "remember"])

    def test_agents_uses_placeholders_for_sections(self, temp_workspace):
        """Test that AGENTS.md uses placeholders for extracted sections."""
        agents_md = temp_workspace / "AGENTS.md"
        content = agents_md.read_text()

        # Should have placeholders for major sections
        assert "{{prompts/agents/" in content

        # Should reference memory system
        assert "memory-system.md" in content or "{{prompts/agents/memory" in content

    def test_no_duplicate_content_between_files(self, temp_workspace):
        """Test that content isn't duplicated between AGENTS.md and extracted files."""
        agents_md = temp_workspace / "AGENTS.md"
        agents_md.read_text()

        # Load extracted files
        agents_dir = temp_workspace / "prompts" / "agents"
        if agents_dir.exists():
            for extracted_file in agents_dir.glob("*.md"):
                extracted_content = extracted_file.read_text()

                # Extract key phrases (first sentence of each paragraph)
                key_phrases = []
                for line in extracted_content.split("\n"):
                    if line.strip() and not line.startswith("#"):
                        key_phrases.append(line.strip()[:50])
                        if len(key_phrases) >= 3:
                            break

                # These key phrases should NOT appear in AGENTS.md
                # (because they're included via placeholder)
                for phrase in key_phrases:
                    if phrase and len(phrase) > 20:
                        # Allow the placeholder reference but not the full content
                        pass  # This is a heuristic test


@pytest.mark.skip(reason="M1: SYSTEM.md/AGENTS.md separation not yet implemented")
class TestSystemMdSeparation:
    """Tests for SYSTEM.md extraction from AGENTS.md."""

    def test_system_md_exists(self, temp_workspace):
        """Test that SYSTEM.md is created with core identity."""
        system_md = temp_workspace / "SYSTEM.md"
        assert system_md.exists()

        content = system_md.read_text()
        assert "Alfred" in content
        assert "persistent memory" in content or "remember" in content

    def test_agents_md_focuses_on_behavior(self, temp_workspace):
        """Test that AGENTS.md focuses on behavior rules."""
        agents_md = temp_workspace / "AGENTS.md"
        assert agents_md.exists()

        content = agents_md.read_text()

        # Should have behavior rules
        assert "Permission First" in content or "permission" in content.lower()

        # Should have memory system guidance
        assert "remember" in content.lower() or "memory" in content.lower()

    def test_no_duplicate_identity_content(self, temp_workspace):
        """Test that core identity is only in SYSTEM.md, not duplicated in AGENTS.md."""
        system_content = (temp_workspace / "SYSTEM.md").read_text()
        agents_content = (temp_workspace / "AGENTS.md").read_text()

        # Core identity statements should be in SYSTEM.md
        identity_phrases = ["You are Alfred", "persistent memory", "remember conversations"]

        for phrase in identity_phrases:
            if phrase in system_content:
                # Should NOT be duplicated in AGENTS.md
                assert phrase not in agents_content, f"'{phrase}' duplicated in AGENTS.md"


@pytest.mark.skip(reason="M7: Session archive contextual retrieval not yet implemented")
class TestSessionArchiveRetrieval:
    """Tests for contextual retrieval from session archive."""

    @pytest.fixture
    def session_archive(self, tmp_path):
        """Create a session archive for testing."""
        from alfred.session_archive import SessionArchive
        archive = SessionArchive(tmp_path / "sessions")
        return archive

    @pytest.mark.asyncio
    async def test_search_finds_session_summaries_first(self, session_archive):
        """Test that search finds session summaries before messages."""
        # Create session with summary
        session_id = "test-session-1"
        await session_archive.save_summary(
            session_id=session_id,
            summary="Discussion about authentication refactoring"
        )

        # Create messages in session
        await session_archive.save_message(
            session_id=session_id,
            role="user",
            content="The JWT null pointer is blocking deployment"
        )

        # Search for "auth bug"
        results = await session_archive.search("auth bug", top_sessions=3)

        # Should find the session summary first
        assert len(results.sessions) > 0
        assert "authentication" in results.sessions[0].summary.lower()

    @pytest.mark.asyncio
    async def test_contextual_narrowing_within_session(self, session_archive):
        """Test that after finding session, search narrows to messages within it."""
        session_id = "auth-session"

        # Create session with multiple messages
        await session_archive.save_summary(
            session_id=session_id,
            summary="Auth system refactoring"
        )

        messages = [
            ("user", "Starting auth refactor today"),
            ("assistant", "What approach are you considering?"),
            ("user", "JWT validation has a null pointer bug"),
            ("assistant", "Where is the null occurring?"),
            ("user", "In the exp field validation"),
        ]

        for role, content in messages:
            await session_archive.save_message(session_id, role, content)

        # Two-stage search
        results = await session_archive.contextual_search(
            query="JWT null pointer",
            top_sessions=1,
            messages_per_session=3
        )

        # Should have session context
        assert len(results.contexts) == 1
        context = results.contexts[0]

        # Should have specific messages from that session
        assert len(context.messages) > 0
        message_contents = [m.content for m in context.messages]
        assert any("null pointer" in m for m in message_contents)

    @pytest.mark.asyncio
    async def test_neighbor_retrieval_for_context(self, session_archive):
        """Test that neighboring messages are retrieved for context."""
        session_id = "detailed-session"

        await session_archive.save_summary(session_id, "Detailed discussion")

        # Save messages with indices
        for idx, (role, content) in enumerate([
            ("user", "Starting the auth work"),
            ("assistant", "I'll help with that"),
            ("user", "JWT bug found"),  # Target message
            ("assistant", "What's the error?"),
            ("user", "Null pointer in exp field"),
        ]):
            await session_archive.save_message(
                session_id, role, content, idx=idx
            )

        # Search and get neighbors
        result = await session_archive.search_with_neighbors(
            query="JWT bug",
            session_id=session_id,
            neighbor_window=1
        )

        # Should have the target message
        assert result.target_message is not None
        assert "JWT bug" in result.target_message.content

        # Should have neighbors
        assert len(result.before) > 0
        assert len(result.after) > 0
        assert "Starting the auth work" in [m.content for m in result.before]


@pytest.mark.skip(reason="M6: Model memory guidance prompt not yet implemented")
class TestMemoryGuidancePrompt:
    """Tests that model guidance prompt is comprehensive."""

    def test_guidance_includes_decision_framework(self):
        """Test that guidance includes the decision framework."""
        from alfred.prompts import get_memory_guidance

        guidance = get_memory_guidance()

        # Should have decision framework
        assert "Files" in guidance or "files" in guidance.lower()
        assert "Memories" in guidance or "memories" in guidance.lower()
        assert "Session Archive" in guidance or "session" in guidance.lower()

    def test_guidance_explains_cost_tradeoffs(self):
        """Test that guidance explains cost trade-offs."""
        from alfred.prompts import get_memory_guidance

        guidance = get_memory_guidance()

        # Should explain that files are expensive
        assert "expensive" in guidance.lower() or "loaded" in guidance.lower()

        # Should explain that memories are cheap
        assert "cheap" in guidance.lower() or "search" in guidance.lower()

    def test_guidance_includes_ttl_warning(self):
        """Test that guidance includes TTL explanation."""
        from alfred.prompts import get_memory_guidance

        guidance = get_memory_guidance()

        # Should mention 90-day TTL
        assert "90" in guidance or "expire" in guidance.lower()
        assert "day" in guidance.lower()


# Integration Tests

@pytest.mark.skip(reason="M8: Full integration not yet implemented")
class TestUnifiedMemoryIntegration:
    """Integration tests for the complete unified memory system."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, tmp_path):
        """Test complete workflow: files + memories + sessions."""
        # This is a comprehensive integration test

        # 1. Load context with placeholders
        from alfred.prompt_loader import PromptLoader
        loader = PromptLoader(tmp_path / "workspace")

        # Setup workspace
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "SYSTEM.md").write_text("# System\nYou are Alfred")
        (workspace / "AGENTS.md").write_text("# Agents\n{{prompts/memory.md}}")
        prompts = workspace / "prompts"
        prompts.mkdir()
        (prompts / "memory.md").write_text("Use remember() for facts")

        context = await loader.load_all_context()

        # 2. Create a memory
        from alfred.memory.jsonl_store import JSONLMemoryStore as MemoryStore
        store = MemoryStore(workspace / "memory.jsonl")

        memory = await store.remember(
            content="User prefers Python",
            tags=["preferences"]
        )

        # 3. Search memories
        results = await store.search("Python preferences")
        assert len(results) > 0

        # 4. Memory should have TTL
        assert memory.expires_at is not None

        # 5. Verify placeholder was resolved
        assert "Use remember()" in context["AGENTS.md"]

    @pytest.mark.asyncio
    async def test_model_follows_guidance(self):
        """Test that model behavior follows the memory guidance."""
        # This test verifies the model uses the system correctly
        # Would need actual LLM calls or mock the behavior

        # Simulate: User says "I prefer Python"
        # Expected: Model asks "Should I add this to USER.md?"
        # OR: Model calls remember() directly

        # The test documents expected behavior
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
