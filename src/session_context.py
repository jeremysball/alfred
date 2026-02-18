"""Context builder that integrates session history (PRD #54).

Builds LLM context including full conversation history.
Messages formatted with simple prefix (User:/Assistant:/System:).
"""

from src.session import Role, SessionManager


class SessionContextBuilder:
    """Builds context with session history injected.

    Formats messages as simple prefix:
        User: <message>
        Assistant: <message>
        System: <message>
    """

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

    def build_context(self, current_input: str) -> str:
        """Build full context with session history and current input.

        Args:
            current_input: The user's current message

        Returns:
            Formatted context string

        Raises:
            RuntimeError: If no active session
        """
        if not self.session_manager.has_active_session():
            raise RuntimeError("No active session")

        messages = self.session_manager.get_messages()

        # Build history section
        history_parts = []
        for msg in messages:
            prefix = self._get_prefix(msg.role)
            history_parts.append(f"{prefix}: {msg.content}")

        history_text = "\n".join(history_parts) if history_parts else ""

        return f"""## CONVERSATION HISTORY

{history_text}

## CURRENT MESSAGE

{current_input}"""

    def _get_prefix(self, role: Role) -> str:
        """Get display prefix for role."""
        prefix_map = {
            Role.USER: "User",
            Role.ASSISTANT: "Assistant",
            Role.SYSTEM: "System",
        }
        return prefix_map.get(role, "Unknown")
