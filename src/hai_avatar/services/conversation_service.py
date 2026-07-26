"""Minimal in-memory conversation history for CLI and future UI."""

from dataclasses import dataclass, field


@dataclass
class ConversationService:
    """Store recent turns without implementing long-term memory."""

    turns: list[tuple[str, str]] = field(default_factory=list)

    def add_turn(self, user_text: str, reply_text: str) -> None:
        self.turns.append((user_text, reply_text))

    def last_turns(self, limit: int = 10) -> list[tuple[str, str]]:
        return self.turns[-limit:]
