"""Session-isolated in-memory conversation history."""

from dataclasses import dataclass, field


@dataclass
class ConversationService:
    """Store recent turns per session without implementing long-term memory."""

    turns_by_session: dict[str, list[tuple[str, str]]] = field(default_factory=dict)

    def add_turn(self, session_id: str, user_text: str, reply_text: str) -> None:
        self.turns_by_session.setdefault(session_id, []).append((user_text, reply_text))

    def last_turns(self, session_id: str = "default", limit: int = 10) -> list[tuple[str, str]]:
        return self.turns_by_session.get(session_id, [])[-limit:]

    def clear(self, session_id: str) -> None:
        self.turns_by_session.pop(session_id, None)
