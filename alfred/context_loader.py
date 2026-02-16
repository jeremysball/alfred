"""Load and manage context files for Pi agent."""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ContextLoader:
    """Loads AGENTS.md, SOUL.md, USER.md and other context files."""

    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self._cache: dict[str, str] = {}
        self._last_modified: dict[str, float] = {}

    def _get_file_path(self, filename: str) -> Path | None:
        """Get path to context file if it exists."""
        path = self.workspace_dir / filename
        if path.exists():
            return path
        return None

    def _read_file(self, filename: str) -> str | None:
        """Read a context file, using cache if unchanged."""
        path = self._get_file_path(filename)
        if not path:
            return None

        try:
            mtime = path.stat().st_mtime

            # Use cache if file hasn't changed
            if filename in self._cache and self._last_modified.get(filename) == mtime:
                return self._cache[filename]

            content = path.read_text(encoding="utf-8")
            self._cache[filename] = content
            self._last_modified[filename] = mtime

            logger.debug(f"[CONTEXT] Loaded {filename} ({len(content)} chars)")
            return content

        except Exception as e:
            logger.warning(f"[CONTEXT] Failed to read {filename}: {e}")
            return None

    def _load_skills(self) -> list[tuple[str, str]]:
        """Load available skills from skills directory.

        Returns list of (skill_name, skill_content) tuples.
        Supports both nested directories (with SKILL.md) and flat .md files.
        """
        skills = []
        skills_dir = self.workspace_dir / "skills"

        if not skills_dir.exists():
            return skills

        for item in skills_dir.iterdir():
            if item.is_dir():
                # Nested directory structure - look for SKILL.md
                skill_file = item / "SKILL.md"
                if skill_file.exists():
                    try:
                        content = skill_file.read_text(encoding="utf-8")
                        skills.append((item.name, content))
                        logger.info(f"[CONTEXT] Loaded skill: {item.name}")
                    except Exception as e:
                        logger.warning(f"[CONTEXT] Failed to load skill {item.name}: {e}")
                else:
                    # Check for flat .md files in subdirectory (e.g., superpowers)
                    for md_file in item.glob("*.md"):
                        try:
                            content = md_file.read_text(encoding="utf-8")
                            name = f"{item.name}/{md_file.stem}"
                            skills.append((name, content))
                            logger.info(f"[CONTEXT] Loaded skill: {name}")
                        except Exception as e:
                            logger.warning(f"[CONTEXT] Failed to load skill {md_file}: {e}")
            elif item.suffix == ".md":
                # Flat .md file structure
                try:
                    content = item.read_text(encoding="utf-8")
                    skills.append((item.stem, content))
                    logger.info(f"[CONTEXT] Loaded skill: {item.stem}")
                except Exception as e:
                    logger.warning(f"[CONTEXT] Failed to load skill {item}: {e}")

        return skills

    def load_all_context(self, include_skills: bool = True) -> str:
        """Load all context files and combine them.

        Priority order:
        1. AGENTS.md - behavior rules
        2. SOUL.md - personality
        3. USER.md - user preferences
        4. IDENTITY.md - agent identity
        5. TOOLS.md - tool configuration
        6. Skills (if include_skills=True)
        """
        sections = []

        # Load files in priority order
        context_files = [
            ("AGENTS.md", "AGENT BEHAVIOR"),
            ("SOUL.md", "PERSONALITY"),
            ("USER.md", "USER PROFILE"),
            ("IDENTITY.md", "IDENTITY"),
            ("TOOLS.md", "TOOLS"),
        ]

        for filename, section_name in context_files:
            content = self._read_file(filename)
            if content:
                sections.append(f"# {section_name}\n\n{content}")
                logger.info(f"[CONTEXT] Loaded {filename}")

        # Load skills
        if include_skills:
            skills = self._load_skills()
            if skills:
                skills_sections = []
                for name, content in skills:
                    skills_sections.append(f"## {name}\n\n{content}")
                sections.append("# SKILLS\n\n" + "\n\n---\n\n".join(skills_sections))
                logger.info(f"[CONTEXT] Loaded {len(skills)} skills")

        if not sections:
            logger.warning("[CONTEXT] No context files found in workspace")
            return ""

        full_context = "\n\n---\n\n".join(sections)
        logger.info(f"[CONTEXT] Total context: {len(full_context)} chars from {len(sections)} files")
        return full_context

    def get_system_prompt(self) -> str:
        """Get combined system prompt from all context files."""
        context = self.load_all_context()

        if not context:
            # Default minimal system prompt
            return (
                "You are Alfred, an AI coding assistant with persistent memory. "
                "You help users with coding tasks and remember context across conversations."
            )

        return (
            f"{context}\n\n"
            "---\n\n"
            "INSTRUCTIONS:\n"
            "1. You are Alfred, the AI described above\n"
            "2. Follow the behavior rules in AGENTS.md\n"
            "3. Use the personality from SOUL.md\n"
            "4. Respect the user preferences in USER.md\n"
            "5. This is a persistent conversation - you have access to memory\n"
            "6. Be concise and helpful\n"
        )

    def clear_cache(self) -> None:
        """Clear the file cache (useful for testing)."""
        self._cache.clear()
        self._last_modified.clear()
        logger.debug("[CONTEXT] Cache cleared")
