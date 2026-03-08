# PRD: M7 - Personality & Context Mechanism

## Overview

**Issue**: #17  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #16 (M6: Kimi Provider)  
**Status**: Planning  
**Priority**: High  
**Created**: 2026-02-16

Implement personality and user context injection from SOUL.md and USER.md into every prompt.

---

## Problem Statement

Alfred needs consistent personality and user awareness. SOUL.md defines Alfred's voice. USER.md tracks user preferences. Both inject into every system prompt.

---

## Solution

Create mechanism to:
1. Parse SOUL.md into personality instructions
2. Parse USER.md into user profile
3. Inject both into system prompts
4. Ensure consistency across conversations

---

## Acceptance Criteria

- [ ] `src/personality.py` - SOUL.md parser and injector
- [ ] `src/user_profile.py` - USER.md parser
- [ ] Personality consistency enforcement
- [ ] User preference awareness
- [ ] System prompt assembly with personality
- [ ] Updates to ContextLoader

---

## File Structure

```
src/
├── personality.py    # SOUL.md handling
└── user_profile.py   # USER.md handling
```

---

## Personality (src/personality.py)

```python
from pathlib import Path
from dataclasses import dataclass
from typing import Any
import yaml


@dataclass
class Personality:
    name: str
    traits: list[str]
    voice: str
    values: list[str]
    background: str
    raw: str


class PersonalityLoader:
    """Load and parse SOUL.md."""
    
    def __init__(self, path: Path = Path("SOUL.md")) -> None:
        self.path = path
    
    def load(self) -> Personality:
        """Load personality from SOUL.md."""
        if not self.path.exists():
            return self._default_personality()
        
        content = self.path.read_text(encoding="utf-8")
        return self._parse(content)
    
    def _parse(self, content: str) -> Personality:
        """Parse SOUL.md content."""
        # Extract sections
        sections = self._extract_sections(content)
        
        return Personality(
            name=sections.get("name", "Alfred"),
            traits=sections.get("traits", []),
            voice=sections.get("voice", "Direct and concise"),
            values=sections.get("values", []),
            background=sections.get("background", ""),
            raw=content,
        )
    
    def _extract_sections(self, content: str) -> dict[str, Any]:
        """Extract sections from markdown."""
        sections: dict[str, Any] = {}
        current_section = None
        current_content: list[str] = []
        
        for line in content.split("\n"):
            if line.startswith("# "):
                # Main title
                sections["name"] = line[2:].strip()
            elif line.startswith("## "):
                # Save previous section
                if current_section:
                    sections[current_section.lower()] = self._parse_section(
                        current_section, current_content
                    )
                # Start new section
                current_section = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        if current_section:
            sections[current_section.lower()] = self._parse_section(
                current_section, current_content
            )
        
        return sections
    
    def _parse_section(self, name: str, lines: list[str]) -> Any:
        """Parse section content based on type."""
        content = "\n".join(line.strip() for line in lines if line.strip())
        
        # Check for list items
        if any(line.strip().startswith("- ") for line in lines):
            items = [
                line.strip()[2:]
                for line in lines
                if line.strip().startswith("- ")
            ]
            return items
        
        return content
    
    def _default_personality(self) -> Personality:
        """Return default personality."""
        return Personality(
            name="Alfred",
            traits=["helpful", "persistent", "concise"],
            voice="Direct and clear",
            values=["honesty", "privacy", "growth"],
            background="A memory-augmented assistant",
            raw="",
        )
    
    def to_system_instruction(self, personality: Personality) -> str:
        """Convert personality to system instruction."""
        lines = [
            f"You are {personality.name}.",
            "",
            "## Personality",
        ]
        
        if personality.traits:
            lines.append("Traits: " + ", ".join(personality.traits))
        
        if personality.voice:
            lines.append(f"Voice: {personality.voice}")
        
        if personality.values:
            lines.append("Values: " + ", ".join(personality.values))
        
        if personality.background:
            lines.append(f"\n{background}")
        
        return "\n".join(lines)
```

---

## User Profile (src/user_profile.py)

```python
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UserProfile:
    background: str
    preferences: dict[str, Any]
    goals: list[str]
    facts: dict[str, str]
    raw: str


class UserProfileLoader:
    """Load and parse USER.md."""
    
    def __init__(self, path: Path = Path("USER.md")) -> None:
        self.path = path
    
    def load(self) -> UserProfile:
        """Load user profile from USER.md."""
        if not self.path.exists():
            return self._empty_profile()
        
        content = self.path.read_text(encoding="utf-8")
        return self._parse(content)
    
    def _parse(self, content: str) -> UserProfile:
        """Parse USER.md content."""
        sections = self._extract_sections(content)
        
        return UserProfile(
            background=sections.get("background", ""),
            preferences=sections.get("preferences", {}),
            goals=sections.get("goals", []),
            facts=sections.get("facts", {}),
            raw=content,
        )
    
    def _extract_sections(self, content: str) -> dict[str, Any]:
        """Extract sections from markdown."""
        sections: dict[str, Any] = {}
        current_section = None
        current_content: list[str] = []
        
        for line in content.split("\n"):
            if line.startswith("## "):
                if current_section:
                    sections[current_section.lower()] = self._parse_section(
                        current_content
                    )
                current_section = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)
        
        if current_section:
            sections[current_section.lower()] = self._parse_section(current_content)
        
        return sections
    
    def _parse_section(self, lines: list[str]) -> Any:
        """Parse section content."""
        content = "\n".join(line.strip() for line in lines if line.strip())
        
        # Parse key-value pairs
        if ": " in content and not content.startswith("-"):
            facts = {}
            for line in lines:
                line = line.strip()
                if ": " in line and not line.startswith("-"):
                    key, value = line.split(": ", 1)
                    facts[key.lower().replace(" ", "_")] = value
            return facts if facts else content
        
        # Parse list
        if any(line.strip().startswith("- ") for line in lines):
            return [
                line.strip()[2:]
                for line in lines
                if line.strip().startswith("- ")
            ]
        
        return content
    
    def _empty_profile(self) -> UserProfile:
        """Return empty profile."""
        return UserProfile(
            background="",
            preferences={},
            goals=[],
            facts={},
            raw="",
        )
    
    def to_context(self, profile: UserProfile) -> str:
        """Convert profile to context string."""
        lines = ["# USER PROFILE\n"]
        
        if profile.background:
            lines.append(f"## Background\n{profile.background}\n")
        
        if profile.facts:
            lines.append("## Facts")
            for key, value in profile.facts.items():
                lines.append(f"- {key}: {value}")
            lines.append("")
        
        if profile.preferences:
            lines.append("## Preferences")
            for key, value in profile.preferences.items():
                if isinstance(value, list):
                    lines.append(f"- {key}: {', '.join(value)}")
                else:
                    lines.append(f"- {key}: {value}")
            lines.append("")
        
        if profile.goals:
            lines.append("## Goals")
            for goal in profile.goals:
                lines.append(f"- {goal}")
        
        return "\n".join(lines)
```

---

## Updated Context Loader

```python
# Update src/context.py

from src.personality import PersonalityLoader
from src.user_profile import UserProfileLoader


class ContextLoader:
    def __init__(
        self,
        config: Config,
        searcher: MemorySearcher,
        personality_loader: PersonalityLoader | None = None,
        user_loader: UserProfileLoader | None = None,
    ) -> None:
        self.config = config
        self.searcher = searcher
        self.builder = ContextBuilder(searcher)
        self.personality = personality_loader or PersonalityLoader()
        self.user = user_loader or UserProfileLoader()
    
    def _build_system_prompt(self, files: dict[str, ContextFile]) -> str:
        """Combine all context into system prompt."""
        personality = self.personality.load()
        user_profile = self.user.load()
        
        parts = [
            "# AGENTS\n\n" + files["agents"].content,
            self.personality.to_system_instruction(personality),
            self.user.to_context(user_profile),
            "# TOOLS\n\n" + files["tools"].content,
        ]
        
        return "\n\n---\n\n".join(parts)
```

---

## Tests

```python
# tests/test_personality.py
import pytest
from src.personality import PersonalityLoader, Personality


def test_parse_soul_md():
    content = """# Alfred

## Personality
You are a helpful assistant.

## Traits
- Warm
- Professional
- Concise

## Voice
Direct and clear.
"""
    
    loader = PersonalityLoader()
    personality = loader._parse(content)
    
    assert personality.name == "Alfred"
    assert "Warm" in personality.traits
    assert "Professional" in personality.traits


def test_default_personality():
    loader = PersonalityLoader(path=Path("/nonexistent"))
    personality = loader.load()
    
    assert personality.name == "Alfred"
    assert len(personality.traits) > 0
```

---

## Success Criteria

- [ ] SOUL.md parses correctly
- [ ] USER.md parses correctly
- [ ] Personality injects into system prompt
- [ ] User profile injects into system prompt
- [ ] Context assembly includes both
- [ ] All tests pass
- [ ] Type-safe throughout
