# PRD: M11 - Learning System

## Overview

**Issue**: #21  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #20 (M10: Distillation)  
**Status**: Planning  
**Priority**: High  
**Created**: 2026-02-16

Implement learning system that updates agent files (USER.md, SOUL.md, TOOLS.md) based on conversation insights using model-driven decisions.

---

## Problem Statement

Alfred must evolve. User preferences change. New tools appear. Alfred's personality refines. The learning system observes conversations and updates agent files automatically. The model decides what to learn and record.

---

## Solution

Create learning system that:
1. Analyzes conversations for user pattern changes
2. Detects new tool configurations
3. Refines personality based on interaction style
4. Updates agent files (USER.md, SOUL.md, TOOLS.md)
5. Asks permission before changes (per AGENTS.md)

---

## Acceptance Criteria

- [ ] `src/learning.py` - Learning engine
- [ ] User preference learning (USER.md updates)
- [ ] Tool configuration learning (TOOLS.md updates)
- [ ] Personality refinement (SOUL.md updates)
- [ ] Permission requests before file changes
- [ ] Change proposal generation

---

## File Structure

```
src/
└── learning.py            # Learning engine
```

---

## Learning Engine (src/learning.py)

```python
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from src.types import MemoryEntry
from src.llm import LLMProvider, ChatMessage
from src.config import Config


@dataclass
class ProposedChange:
    file: str  # "USER.md", "SOUL.md", "TOOLS.md"
    section: str | None
    action: str  # "add", "update", "remove"
    current_content: str | None
    proposed_content: str
    reason: str


@dataclass
class LearningResult:
    proposals: list[ProposedChange]
    applied: list[ProposedChange]
    rejected: list[ProposedChange]


class LearningEngine:
    """Learn from conversations and propose file updates."""
    
    def __init__(
        self,
        config: Config,
        llm: LLMProvider,
    ) -> None:
        self.config = config
        self.llm = llm
    
    async def analyze(
        self,
        recent_memories: list[MemoryEntry],
    ) -> LearningResult:
        """Analyze conversations and propose changes."""
        if len(recent_memories) < 5:
            return LearningResult(proposals=[], applied=[], rejected=[])
        
        conversation = self._format_conversation(recent_memories)
        
        # Load current files
        user_md = self._load_file("USER.md")
        soul_md = self._load_file("SOUL.md")
        tools_md = self._load_file("TOOLS.md")
        
        # Generate proposals
        proposals = await self._generate_proposals(
            conversation=conversation,
            user_md=user_md,
            soul_md=soul_md,
            tools_md=tools_md,
        )
        
        return LearningResult(
            proposals=proposals,
            applied=[],
            rejected=[],
        )
    
    def _format_conversation(self, memories: list[MemoryEntry]) -> str:
        """Format memories for analysis."""
        lines = []
        for mem in memories:
            role = "User" if mem.role == "user" else "Assistant"
            lines.append(f"{role}: {mem.content}")
        return "\n".join(lines)
    
    def _load_file(self, filename: str) -> str:
        """Load agent file content."""
        path = Path(filename)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")
    
    async def _generate_proposals(
        self,
        conversation: str,
        user_md: str,
        soul_md: str,
        tools_md: str,
    ) -> list[ProposedChange]:
        """Use LLM to generate change proposals."""
        messages = [
            ChatMessage(
                role="system",
                content=f"""Analyze this conversation and current agent files.

Propose changes to agent files based on new information learned.

Current files:

USER.md:
{user_md}

SOUL.md:
{soul_md}

TOOLS.md:
{tools_md}

For each proposal, specify:
- file: Which file to change
- section: Which section (if applicable)
- action: add, update, or remove
- current_content: What's there now (null if adding)
- proposed_content: What to change it to
- reason: Why this change matters

Only propose substantive changes. Skip trivial updates.

Format as JSON array:
[
  {{
    "file": "USER.md",
    "section": "Preferences",
    "action": "add",
    "current_content": null,
    "proposed_content": "communication_style: concise",
    "reason": "User repeatedly asks for brief responses"
  }}
]""",
            ),
            ChatMessage(
                role="user",
                content=conversation,
            ),
        ]
        
        response = await self.llm.chat(messages)
        
        # Parse proposals
        try:
            import json
            data = json.loads(response.content)
            return [ProposedChange(**item) for item in data]
        except Exception:
            return []
    
    async def apply_proposal(
        self,
        proposal: ProposedChange,
        user_approved: bool = False,
    ) -> bool:
        """Apply a proposed change if approved."""
        if not user_approved:
            # Per AGENTS.md: always ask permission
            return False
        
        path = Path(proposal.file)
        
        if proposal.action == "add":
            await self._add_to_file(path, proposal.proposed_content, proposal.section)
        elif proposal.action == "update" and proposal.current_content:
            await self._update_file(path, proposal.current_content, proposal.proposed_content)
        elif proposal.action == "remove" and proposal.current_content:
            await self._remove_from_file(path, proposal.current_content)
        
        return True
    
    async def _add_to_file(
        self,
        path: Path,
        content: str,
        section: str | None,
    ) -> None:
        """Add content to file, optionally in a section."""
        if not path.exists():
            path.write_text(f"# {path.stem}\n\n")
        
        current = path.read_text(encoding="utf-8")
        
        if section and f"## {section}" in current:
            # Add under section
            lines = current.split("\n")
            section_idx = None
            for i, line in enumerate(lines):
                if line.startswith(f"## {section}"):
                    section_idx = i
                    break
            
            if section_idx is not None:
                lines.insert(section_idx + 1, f"\n{content}")
                path.write_text("\n".join(lines), encoding="utf-8")
                return
        
        # Append to end
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n\n{content}\n")
    
    async def _update_file(
        self,
        path: Path,
        old_content: str,
        new_content: str,
    ) -> None:
        """Replace old content with new content."""
        if not path.exists():
            return
        
        current = path.read_text(encoding="utf-8")
        updated = current.replace(old_content, new_content)
        path.write_text(updated, encoding="utf-8")
    
    async def _remove_from_file(
        self,
        path: Path,
        content: str,
    ) -> None:
        """Remove content from file."""
        if not path.exists():
            return
        
        current = path.read_text(encoding="utf-8")
        updated = current.replace(content, "")
        path.write_text(updated, encoding="utf-8")
    
    def format_proposal(self, proposal: ProposedChange) -> str:
        """Format proposal for user review."""
        lines = [
            f"Proposed change to {proposal.file}:",
            f"",
            f"Action: {proposal.action}",
        ]
        
        if proposal.section:
            lines.append(f"Section: {proposal.section}")
        
        if proposal.current_content:
            lines.extend([
                f"",
                f"Current:",
                f"```",
                f"{proposal.current_content}",
                f"```",
            ])
        
        lines.extend([
            f"",
            f"Proposed:",
            f"```",
            f"{proposal.proposed_content}",
            f"```",
            f"",
            f"Reason: {proposal.reason}",
        ])
        
        return "\n".join(lines)


class PermissionRequester:
    """Request user permission for file changes."""
    
    def __init__(self, bot) -> None:
        self.pending: dict[str, ProposedChange] = {}
        self.bot = bot
    
    async def request_permission(
        self,
        chat_id: int,
        proposal: ProposedChange,
    ) -> str:
        """Send permission request to user."""
        import uuid
        request_id = str(uuid.uuid4())[:8]
        
        self.pending[request_id] = proposal
        
        engine = LearningEngine(None, None)  # type: ignore
        message = engine.format_proposal(proposal)
        
        full_message = f"""{message}

Reply with:
- "approve {request_id}" to apply this change
- "reject {request_id}" to discard
- "approve all" to auto-approve future changes"""
        
        await self.bot.send_message(chat_id, full_message)
        
        return request_id
    
    async def handle_response(self, chat_id: int, text: str) -> ProposedChange | None:
        """Handle user response to permission request."""
        text_lower = text.lower().strip()
        
        if text_lower.startswith("approve "):
            request_id = text_lower.split()[1]
            return self.pending.pop(request_id, None)
        
        if text_lower.startswith("reject "):
            request_id = text_lower.split()[1]
            self.pending.pop(request_id, None)
            return None
        
        return None
